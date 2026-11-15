"""KnowledgeMemoryPort + Fake adapter (canonical truth and test adapter)."""
from typing import Protocol
import re
import unicodedata


def search_words(text: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", text.lower())
    normalized = "".join(c for c in normalized if not unicodedata.combining(c))
    stop = {"quel", "quelle", "quels", "quelles", "est", "les", "des", "une", "nous",
            "dans", "pour", "sur", "avec", "que", "qui", "sont", "projet", "avons",
            "informations", "information", "resume", "donne"}
    return {t for t in re.findall(r"\w+", normalized) if len(t) > 2 and t not in stop}


class KnowledgeMemoryPort(Protocol):
    async def remember_evidence(self, project_id: str, content: str, metadata: dict) -> str: ...
    async def remember_truth(self, project_id: str, knowledge_item: dict) -> str: ...
    async def recall(self, project_id: str, query: str, scopes: list[str]) -> list[dict]: ...
    async def forget_projection(self, project_id: str, projection_id: str) -> bool: ...
    async def rebuild_project(self, project_id: str) -> dict: ...
    async def health(self) -> dict: ...


def canonical_truth(db_factory, project_id: str, query: str) -> list[dict]:
    """Read only live validated facts and resolved provenance from the canonical store."""
    from ..models import KnowledgeItem
    from .knowledge_context import contexts, usable_as_current
    q = (query or "").lower()
    words = search_words(q)
    out = []
    with db_factory() as db:
        items = db.query(KnowledgeItem).filter(
            KnowledgeItem.project_id == project_id,
            KnowledgeItem.status == "validated",
        ).all()
        qualifications = contexts(db, items)
        for it in items:
            context = qualifications[it.id]
            if not usable_as_current(it, context):
                continue
            blob = f"{it.kind} {it.subject} {it.value}".lower()
            if not words or q in blob or words & search_words(blob):
                out.append({"scope": "truth", "kind": it.kind, "subject": it.subject,
                            "value": it.value, "id": it.id, "level": "validated", "source_id": context['source_id'],
                            "context": context,
                            "validation_mode": "default" if it.validated_by == "auto-default" else "human"})
    out.sort(key=lambda hit: len(words & search_words(str(hit.get("subject") or "") + " " + str(hit.get("value") or ""))), reverse=True)
    return out[:50]


class FakeMemoryAdapter:
    """MVP: recherche plein-texte en DB via MemoryProjection + KnowledgeItems.

    Respecte le contrat evidence/truth sans dépendre de EG2.
    """

    def __init__(self, db_factory):
        self.db_factory = db_factory
        self._evidence: dict[str, list[dict]] = {}

    async def remember_evidence(self, project_id: str, content: str, metadata: dict) -> str:
        self._evidence.setdefault(project_id, []).append({"content": content, "metadata": metadata})
        return f"fake-ev-{len(self._evidence[project_id])}"

    async def remember_truth(self, project_id: str, knowledge_item: dict) -> str:
        self._evidence.setdefault(f"{project_id}__truth", []).append(knowledge_item)
        return f"fake-tr-{len(self._evidence[f'{project_id}__truth'])}"

    async def recall(self, project_id: str, query: str, scopes: list[str]) -> list[dict]:
        from ..models import SourceArtifact, Source
        q = (query or "").lower()
        words = search_words(q)
        out: list[dict] = []
        db = self.db_factory()
        try:
            if "truth" in scopes:
                out.extend(canonical_truth(self.db_factory, project_id, query))
            if "evidence" in scopes:
                arts = db.query(SourceArtifact).join(Source, Source.id == SourceArtifact.source_id).filter(
                    Source.project_id == project_id, Source.status == "resolved").all()
                for a in arts:
                    if (a.content_json or {}).get("superseded") or a.kind == "audio_pending":
                        continue
                    txt = (a.content_text or "").lower()
                    if not words or q in txt or words & search_words(txt):
                        out.append({"scope": "evidence", "kind": a.kind,
                                    "excerpt": a.content_text or "",
                                    "source_id": a.source_id, "level": "proposed"})
        finally:
            db.close()
        # Rank all matching canonical rows before bounding the response. A newly
        # retained fact must remain searchable beyond the first 50 database rows.
        out.sort(key=lambda hit: (hit.get('scope') == 'truth', len(words & search_words(
            str(hit.get('subject') or '') + ' ' + str(hit.get('value') or hit.get('excerpt') or '')))), reverse=True)
        return out[:50]

    async def forget_projection(self, project_id: str, projection_id: str) -> bool:
        return True

    async def rebuild_project(self, project_id: str) -> dict:
        self._evidence.clear()
        from .projections import rebuild_from_canon
        return await rebuild_from_canon(self.db_factory, self, project_id)

    async def health(self) -> dict:
        return {"engine": "fake", "status": "ok"}
