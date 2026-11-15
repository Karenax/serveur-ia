"""Persistent EG2 evidence index; SQL remains the authority for ownership and truth."""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
import uuid
from pathlib import Path
from contextlib import contextmanager

from .embedding_channel import EmbeddingChannel, normalize, rank_vectors, shared_api_key
from .current_evidence import current_contents


def dataset_name_for(project_id: str, purpose: str, prefix: str = "pb") -> str:
    if purpose not in {"evidence", "truth"}:
        raise ValueError("Unknown memory scope")
    return f"{prefix}_{project_id}__{purpose}"


def split_passages(content: str, words: int = 160, overlap: int = 32) -> list[str]:
    """Keep every character; split oversized paragraphs with overlapping word windows."""
    chunks = []
    for paragraph in re.split(r"\n\s*\n", content):
        if not paragraph.strip():
            continue
        spans = list(re.finditer(r"\S+", paragraph))
        if len(spans) <= words:
            chunks.append(paragraph)
            continue
        start = 0
        while start < len(spans):
            end = min(start + words, len(spans))
            chunks.append(paragraph[0 if start == 0 else spans[start].start():
                                    len(paragraph) if end == len(spans) else spans[end].start()])
            if end == len(spans):
                break
            start = end - overlap
    return chunks


def eg2_passages(content: str) -> list[str]:
    """Bound dense passages while preserving all text and preferring word breaks."""
    char_limit = 1536
    parts = []
    for passage in split_passages(content):
        start = 0
        while len(passage) - start > char_limit:
            end = start + char_limit
            boundary = passage.rfind(' ', start + char_limit // 2, end)
            if boundary >= 0:
                end = boundary + 1
            parts.append(passage[start:end])
            start = end
        parts.append(passage[start:])
    return parts


def index_path(memory: dict) -> Path:
    from ..config import settings
    storage = Path(settings.storage_dir)
    configured = memory.get('index_path')
    if not configured:
        return storage / 'eg2' / 'index.db'
    path = Path(configured).expanduser()
    if path.is_file():
        return path
    from .backup import restored_eg2_index
    return restored_eg2_index(configured, storage) or path


def evidence_ref(project, source, content, profile):
    return "eg2:" + hashlib.sha256(json.dumps([project, source, content, profile]).encode()).hexdigest()


class EG2MemoryAdapter:
    def __init__(self, db_factory=None, config=None, channel=None, path=None, *, ai_config=None):
        self.db_factory = db_factory
        if config is None and db_factory:
            from .settings_service import get_section
            with db_factory() as db:
                config = get_section(db, "memory")
        self.config = config or {}
        endpoint = self.config.get("embedding_endpoint") or "http://192.9.110.115:1234"
        api_key = ''
        if db_factory and channel is None and ai_config is None:
            from .settings_service import get_section
            with db_factory() as db:
                ai_config = get_section(db, 'ai')
        if channel is None:
            api_key = shared_api_key(ai_config or {}, endpoint)
        self.channel = channel or EmbeddingChannel(
            endpoint,
            self.config.get("embedding_model") or "text-embedding-embeddinggemma-2",
            timeout_s=self.config.get("timeout_s", 600), batch_size=self.config.get("batch_size", 8),
            api_key=api_key)
        self.path = Path(path) if path else index_path(self.config)

    @contextmanager
    def _connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=30)
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("CREATE TABLE IF NOT EXISTS passages (project TEXT NOT NULL, ref TEXT NOT NULL, "
                   "source TEXT NOT NULL, ordinal INTEGER NOT NULL, text TEXT NOT NULL, vector TEXT NOT NULL, "
                   "profile TEXT NOT NULL, PRIMARY KEY(project,ref,ordinal))")
        db.execute("CREATE INDEX IF NOT EXISTS passages_project ON passages(project)")
        db.execute("CREATE INDEX IF NOT EXISTS passages_source ON passages(project,source)")
        db.execute("CREATE INDEX IF NOT EXISTS passages_source_scope ON passages(source,project)")
        db.execute("CREATE TABLE IF NOT EXISTS embedding_cache (profile TEXT NOT NULL, "
                   "digest TEXT NOT NULL, vector TEXT NOT NULL, PRIMARY KEY(profile,digest))")
        try:
            with db:
                yield db
        finally:
            db.close()

    async def remember_evidence(self, project_id: str, content: str, metadata: dict) -> str:
        source = metadata.get("source_id")
        if not source:
            raise ValueError("Source provenance required")
        ref = evidence_ref(project_id, source, content, self.channel.profile)
        passages = eg2_passages(content)
        with self._connect() as db:
            count = db.execute("SELECT count(*) FROM passages WHERE project=? AND ref=?", (project_id, ref)).fetchone()[0]
            retained = db.execute("SELECT text,vector FROM passages WHERE project=? AND source=? AND profile=?",
                                  (project_id, source, self.channel.profile)).fetchall()
        if count == len(passages) and passages:
            return ref
        # Adding attachments should not send an unchanged mail body through EG2 again.
        reusable = {}
        for text, raw in retained:
            try:
                vector = json.loads(raw)
                normalize(vector, getattr(self.channel, 'dimensions', len(vector)))
                reusable[text] = vector
            except (ValueError, TypeError, OverflowError):
                continue
        missing = list(dict.fromkeys(text for text in passages if text not in reusable))
        # Byte-identical documents recur in forwarded/replied mails. Cache only vectors,
        # never text/ownership; canonical provenance still comes exclusively from passages.
        with self._connect() as db:
            for text in missing:
                digest = hashlib.sha256(text.encode()).hexdigest()
                cached = db.execute('SELECT vector FROM embedding_cache WHERE profile=? AND digest=?',
                                    (self.channel.profile, digest)).fetchone()
                if cached:
                    try:
                        vector = json.loads(cached[0])
                        normalize(vector, getattr(self.channel, 'dimensions', len(vector)))
                        reusable[text] = vector
                    except (ValueError, TypeError, OverflowError):
                        continue
        missing = [text for text in missing if text not in reusable]
        if missing:
            batch_size = getattr(self.channel, 'batch_size', 8)
            for offset in range(0, len(missing), batch_size):
                batch = missing[offset:offset + batch_size]
                fresh = await self.channel.embed(batch)
                pairs = list(zip(batch, fresh, strict=True))
                with self._connect() as db:
                    db.executemany('INSERT OR REPLACE INTO embedding_cache VALUES (?,?,?)', [
                        (self.channel.profile, hashlib.sha256(text.encode()).hexdigest(), json.dumps(vector))
                        for text, vector in pairs])
                reusable.update(pairs)
        vectors = [reusable[text] for text in passages]
        with self._connect() as db:
            db.execute("DELETE FROM passages WHERE project=? AND source=?", (project_id, source))
            db.executemany("INSERT INTO passages VALUES (?,?,?,?,?,?,?)", [
                (project_id, ref, source, i, text, json.dumps(vector), self.channel.profile)
                for i, (text, vector) in enumerate(zip(passages, vectors, strict=True))])
        return ref

    async def remember_truth(self, project_id: str, knowledge_item: dict) -> str:
        # Validated facts are read directly from the authoritative database.
        return "truth:" + str(knowledge_item["id"])

    async def recall(self, project_id: str, query: str, scopes: list[str]) -> list[dict]:
        from .memory_port import canonical_truth
        out = canonical_truth(self.db_factory, project_id, query) if "truth" in scopes and self.db_factory else []
        if "evidence" not in scopes:
            return out
        try:
            with self._connect() as db:
                rows = db.execute("SELECT ref,source,ordinal,text,vector,profile FROM passages WHERE project=?", (project_id,)).fetchall()
        except Exception:
            if out:
                return out + [{"error": "Index EG2 indisponible : preuves non recherchées", "level": "proposed"}]
            raise
        if self.db_factory:
            with self.db_factory() as db:
                contents = current_contents(db, [project_id])
            # A source can remain resolved while its text is replaced. Never recall an old revision.
            current = {(source, profile): evidence_ref(project_id, source, content, profile)
                       for source, content in contents.items() for profile in {r[5] for r in rows}}
            rows = [r for r in rows if r[1] in contents and r[0] == current.get((r[1], r[5]))]
        if not rows:
            return out
        compatible = [r for r in rows if r[5] == self.channel.profile]
        if len(compatible) != len(rows):
            warning = "Profil EG2 incompatible pour une partie des preuves : reconstruction nécessaire"
            if not compatible and not out:
                raise ValueError(warning)
            out.append({"error": warning, "level": "proposed"})
        rows = compatible
        if not rows:
            return out
        try:
            vector = (await self.channel.embed([query], query=True))[0]
        except Exception:
            if out:
                return out + [{"error": "EG2 indisponible : preuves non recherchées", "level": "proposed"}]
            raise
        # A slow query embedding must not expose a note edited while it ran.
        if self.db_factory:
            with self.db_factory() as db:
                contents = current_contents(db, [project_id])
            rows = [r for r in rows if r[1] in contents and
                    r[0] == evidence_ref(project_id, r[1], contents[r[1]], r[5])]
        docs = [{"id": str(i), "text": r[3]} for i, r in enumerate(rows)]
        for hit in rank_vectors(vector, docs, [json.loads(r[4]) for r in rows], 24):
            row = rows[int(hit["id"])]
            out.append({"scope": "evidence", "level": "proposed", "engine": "eg2",
                        "source_id": row[1], "text": hit["text"], "excerpt": hit["text"],
                        "score": hit["score"], "id": f"{row[0]}:{row[2]}"})
        return out

    async def forget_projection(self, project_id: str, projection_id: str) -> bool:
        with self._connect() as db:
            db.execute("DELETE FROM passages WHERE project=? AND ref=?", (project_id, projection_id))
        return True

    async def rebuild_project(self, project_id: str) -> dict:
        from .projections import rebuild_from_canon
        # remember_evidence replaces a source only after its vectors are ready.
        # Keep the older passages of sources that could not be rebuilt.
        result = await rebuild_from_canon(self.db_factory, self, project_id)
        if result['status'] == 'rebuilt':
            with self._connect() as db:
                db.execute("DELETE FROM passages WHERE project=? AND profile<>?", (project_id, self.channel.profile))
        return result

    async def health(self) -> dict:
        try:
            with self._connect() as db:
                count, profiles = db.execute("SELECT count(*), count(DISTINCT profile) FROM passages").fetchone()
                mismatch = db.execute("SELECT count(*) FROM passages WHERE profile<>?", (self.channel.profile,)).fetchone()[0]
            return {"engine": "eg2", "status": "reindex_required" if mismatch else "ok",
                    "data_dir": str(self.path), "passages": count, "profiles": profiles,
                    "embedding": {"provider": "openai_compatible", "model": self.channel.model},
                    "remote_embedding_verified": False}
        except Exception as exc:
            return {"engine": "eg2", "status": "unavailable", "error": type(exc).__name__}

    async def probe(self):
        import tempfile
        with tempfile.TemporaryDirectory(prefix="eg2-probe-") as tmp:
            adapter = EG2MemoryAdapter(channel=self.channel, path=Path(tmp) / "index.db")
            project = str(uuid.uuid4())
            started = time.perf_counter()
            ref = await adapter.remember_evidence(project, "La réception FAT de la sonde est prévue le 18 décembre.", {"source_id": "probe"})
            remember_s = time.perf_counter() - started
            started = time.perf_counter()
            hits = await adapter.recall(project, "Quand a lieu la réception FAT ?", ["evidence"])
            recall_s = time.perf_counter() - started
            await adapter.forget_projection(project, ref)
            remaining = await adapter.recall(project, "FAT", ["evidence"])
            return {"status": "ok" if hits and not remaining else "failed", "engine": "eg2",
                    "remember_s": round(remember_s, 3), "recall_s": round(recall_s, 3),
                    "recall_hits": len(hits), "cleanup_confirmed": not remaining}
