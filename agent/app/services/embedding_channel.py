"""EG2 embeddings client; never mutates canonical facts."""
from __future__ import annotations

import asyncio
import hashlib
import json
import math
import time
from dataclasses import dataclass, field
from urllib.parse import urlsplit

import httpx
from .inference_scheduler import async_lease, engine_key


def shared_api_key(ai: dict, endpoint: str) -> str:
    """Reuse the LLM credential only for the exact same OpenAI API base."""
    def api_base(value):
        parsed = urlsplit(value.rstrip('/'))
        return (parsed.scheme.lower(), parsed.hostname, parsed.port,
                parsed.path.removesuffix('/v1'), parsed.query, parsed.fragment)

    if ai.get('provider') == 'openai_compatible' and api_base(ai.get('base_url') or '') == api_base(endpoint):
        return ai.get('api_key') or ''
    return ''


@dataclass(frozen=True)
class EmbeddingChannel:
    endpoint: str
    model: str = "text-embedding-embeddinggemma-2"
    dimensions: int = 768
    timeout_s: float = 600
    batch_size: int = 8
    api_key: str = field(default='', repr=False, compare=False)

    def __post_init__(self):
        parsed = urlsplit(self.endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Adresse HTTP(S) du serveur d'embeddings invalide")
        if not 1 <= self.batch_size <= 32 or self.dimensions != 768:
            raise ValueError("Ce canal utilise 768 dimensions et des lots de 1 à 32 textes")

    @property
    def profile(self) -> str:
        # Pin a revision/quantization in model identity when changing deployment.
        raw = json.dumps([self.endpoint.rstrip('/'), self.model, self.dimensions,
                          "SearchQuery/Document", "l2-v1"], separators=(',', ':'))
        return hashlib.sha256(raw.encode()).hexdigest()

    async def embed(self, texts: list[str], *, query: bool = False) -> list[list[float]]:
        prefix = "task: search result | query: " if query else "title: none | text: "
        vectors = []
        url = self.endpoint.rstrip('/')
        if not url.endswith('/v1'):
            url += '/v1'
        queue = engine_key(url, category='embedding')
        headers = {'Authorization': f'Bearer {self.api_key}'} if self.api_key else {}
        async with httpx.AsyncClient(timeout=self.timeout_s, follow_redirects=False, headers=headers) as client:
            for offset in range(0, len(texts), self.batch_size):
                batch = texts[offset:offset + self.batch_size]
                async with asyncio.timeout(self.timeout_s):
                    for attempt in range(20):
                        async with async_lease(queue, timeout=self.timeout_s):
                            response = await client.post(url + '/embeddings', json={
                                "model": self.model, "input": [prefix + text for text in batch],
                                "encoding_format": "float",
                            })
                        if response.status_code not in {429, 503} or attempt == 19:
                            break
                        try:
                            delay = float(response.headers.get('Retry-After', str(min(30, 2 ** (attempt + 1)))))
                        except ValueError:
                            delay = 2
                        await asyncio.sleep(min(60, max(0.25, delay)))
                response.raise_for_status()
                data = response.json().get('data', [])
                if len(data) != len(batch) or sorted(row.get('index', -1) for row in data) != list(range(len(batch))):
                    raise ValueError("Réponse d'embeddings incomplète ou indices invalides")
                for row in sorted(data, key=lambda item: item['index']):
                    vectors.append(normalize(row.get('embedding', []), self.dimensions))
        return vectors

    async def rank(self, query: str, documents: list[dict], limit: int = 5) -> dict:
        if len({doc['id'] for doc in documents}) != len(documents):
            raise ValueError("Identifiants de documents dupliqués")
        started = time.perf_counter()
        vectors = await self.embed([doc['text'] for doc in documents])
        index_s = time.perf_counter() - started
        started = time.perf_counter()
        query_vector = (await self.embed([query], query=True))[0]
        hits = rank_vectors(query_vector, documents, vectors, limit)
        return {"channel": "embeddinggemma2", "model": self.model, "profile": self.profile,
                "dimensions": self.dimensions, "documents": len(documents), "hits": hits,
                "index_s": round(index_s, 4), "search_s": round(time.perf_counter() - started, 4),
                "experimental": True, "persistent_index": False}


def normalize(vector, dimensions: int) -> list[float]:
    if len(vector) != dimensions or any(isinstance(v, bool) or not isinstance(v, (float, int))
                                         or not math.isfinite(v) for v in vector):
        raise ValueError(f"Vecteur invalide : {dimensions} valeurs finies attendues")
    norm = math.sqrt(sum(v * v for v in vector))
    if not math.isfinite(norm) or norm <= 0:
        raise ValueError("Vecteur nul ou norme invalide")
    return [v / norm for v in vector]


def rank_vectors(query: list[float], documents: list[dict], vectors: list[list[float]], limit: int) -> list[dict]:
    if len(documents) != len(vectors) or any(len(v) != len(query) for v in vectors):
        raise ValueError("Dimensions ou nombre de vecteurs incohérents")
    scored = [{"id": doc['id'], "text": doc['text'],
               "score": sum(a * b for a, b in zip(query, vector, strict=True))}
              for doc, vector in zip(documents, vectors, strict=True)]
    return sorted(scored, key=lambda hit: (-hit['score'], hit['id']))[:limit]
