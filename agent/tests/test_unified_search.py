"""Hybrid ranking, no stale evidence, scoped HTTP, failure visibility and read-only index."""
import asyncio
import uuid
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import KnowledgeItem, Project, Source, SourceArtifact
from app.services.eg2_memory import EG2MemoryAdapter
from app.services.unified_search import search

client = TestClient(app)


class Channel:
    profile = "search-profile"
    calls = 0

    async def embed(self, texts, query=False):
        if query:
            self.calls += 1
        return [[1.0, 0.0] if query or "décalage" in text else [0.0, 1.0] for text in texts]


@pytest.fixture
def corpus(tmp_path, monkeypatch):
    monkeypatch.delenv("AGENT_OPERATOR_PROJECT_IDS", raising=False)
    monkeypatch.setenv("AGENT_OPERATOR_ROLE", "owner")
    with SessionLocal() as db:
        p = Project(code="SEARCH-" + uuid.uuid4().hex, name="Recherche")
        db.add(p)
        db.flush()
        sources = []
        for text, kind in [("Le fournisseur confirme un décalage de trois semaines.", "email"),
                           ("Exigence AIRB25LTH0806-A : éclairage de 350 lux.", "document"),
                           ("Ancienne décision secrète.", "email")]:
            source = Source(project_id=p.id, status="resolved", source_type=kind, original_uri="test://search",
                            received_at=datetime(2026, 10, 11), sha256=uuid.uuid4().hex,
                            source_metadata={"subject": text[:80]})
            db.add(source)
            db.flush()
            db.add(SourceArtifact(source_id=source.id, kind="body_text", content_text=text))
            sources.append((source.id, text))
        fact = KnowledgeItem(project_id=p.id, kind="requirement", subject="Éclairage confirmé", value="350 lux",
                             status="validated", created_at=datetime(2026, 10, 11))
        db.add(fact)
        db.commit()
        pid, kid = p.id, fact.id
    adapter = EG2MemoryAdapter(SessionLocal, channel=Channel(), path=tmp_path / "index.db")
    for sid, text in sources:
        asyncio.run(adapter.remember_evidence(pid, text, {"source_id": sid}))
    adapter.channel.calls = 0
    return pid, sources, kid, adapter


def run(corpus, query, **filters):
    pid, _, _, adapter = corpus
    with SessionLocal() as db:
        return asyncio.run(search(db, query=query, project_id=pid, adapter=adapter, **filters))


def test_semantic_query_exact_reference_priority_and_read_only_index(corpus):
    _, sources, _, adapter = corpus
    before = adapter.path.read_bytes()
    found = run(corpus, "retard livraison")
    assert found["items"][0]["id"] == sources[0][0]
    assert found["items"][0]["methods"] == ["semantic"]
    assert found["semantic_status"] == "ok" and found["indexed_sources"] == 3
    assert adapter.channel.calls == 1  # One query vector, independent of project or passage count.
    exact = run(corpus, "Où est AIRB25LTH0806-A ?")
    assert exact["items"][0]["id"] == sources[1][0]
    assert "exact" in exact["items"][0]["methods"]
    assert "AIRB25LTH0806-A" in exact["items"][0]["excerpt"]
    assert exact["total"] == 1  # A precise identifier must not retrieve unrelated semantic neighbours.
    assert adapter.path.read_bytes() == before


def test_discarded_replaced_and_superseded_artifacts_never_recalled(corpus):
    _, sources, _, _ = corpus
    with SessionLocal() as db:
        db.get(Source, sources[0][0]).status = "discarded"
        db.query(SourceArtifact).filter_by(source_id=sources[1][0]).one().content_text = "Nouveau document sans référence"
        db.get(Source, sources[1][0]).source_metadata = {"subject": "Nouveau document"}
        db.query(SourceArtifact).filter_by(source_id=sources[2][0]).one().content_json = {"superseded": True}
        db.commit()
    result = run(corpus, "AIRB25LTH0806-A")
    assert not result["items"] and result["indexed_sources"] == 0
    assert result["warnings"]


def test_failure_preserves_exact_results_and_reports_incomplete_search(corpus):
    async def fail(*args, **kwargs):
        raise RuntimeError("private remote error")
    corpus[3].channel.embed = fail
    result = run(corpus, "AIRB25LTH0806-A")
    assert result["semantic_status"] == "unavailable"
    assert result["items"][0]["id"] == corpus[1][1][0]
    assert result["warnings"] and "private" not in str(result)


def test_incompatible_profile_uses_only_current_text_and_reports_reindex(corpus):
    corpus[3].channel.profile = "other-profile"
    result = run(corpus, "AIRB25LTH0806-A")
    assert result["semantic_status"] == "empty" and result["indexed_sources"] == 0
    assert result["items"][0]["methods"] == ["exact"]
    assert any("réindex" in warning for warning in result["warnings"])


def test_missing_index_keeps_canonical_search_without_creating_index(corpus, tmp_path):
    corpus[3].path = tmp_path / "absent" / "index.db"
    result = run(corpus, "AIRB25LTH0806-A")
    assert result["items"][0]["id"] == corpus[1][1][0]
    assert result["semantic_status"] == "unavailable"
    assert not corpus[3].path.exists() and not corpus[3].path.parent.exists()


def test_search_by_source_does_not_include_other_projects(corpus):
    pid, sources, _, adapter = corpus
    selected = sources[0][0]
    with adapter._connect() as db:
        db.execute("UPDATE passages SET profile='foreign-profile' WHERE source=?", (sources[1][0],))
        db.execute("INSERT INTO passages SELECT 'foreign-project',ref,source,ordinal,text,vector,'foreign-profile' "
                   "FROM passages WHERE project=? AND source=?", (pid, selected))
    result = run(corpus, 'retard livraison', source_ids={selected})
    assert [item['source_id'] for item in result['items']] == [selected]
    assert result['semantic_status'] == 'ok'
    assert not any('réindex' in warning for warning in result['warnings'])


def test_reference_in_document_ranks_above_assigned_project_only(corpus):
    with SessionLocal() as db:
        code = db.get(Project, corpus[0]).code
        db.query(SourceArtifact).filter_by(source_id=corpus[1][1][0]).one().content_text = "Référence " + code
        db.commit()
    result = run(corpus, code)
    assert result["items"][0]["id"] == corpus[1][1][0]
    assert "exact" in result["items"][0]["methods"]
    assigned = next(hit for hit in result["items"] if hit["id"] == corpus[1][0][0])
    assert "project" in assigned["methods"] and "exact" not in assigned["methods"]


def test_excerpt_keeps_accents_and_targets_match_beyond_first_screen():
    from app.services.unified_search import excerpt
    text = "Texte antérieur. " * 100 + "La réception est reportée."
    result = excerpt(text, "reception")
    assert "réception est reportée" in result and result.startswith("…")


@pytest.mark.parametrize("raw", ['[true, 0]', '[NaN, 0]', '["x", 0]', '{}', '[1]'])
def test_invalid_vector_cannot_create_semantic_match(corpus, raw):
    import sqlite3
    with sqlite3.connect(corpus[3].path) as db:
        db.execute("UPDATE passages SET vector=?", (raw,))
    result = run(corpus, "retard livraison")
    assert not result["items"]
    assert any("invalides" in warning for warning in result["warnings"])


def test_source_changed_while_embedding_is_in_flight_is_excluded(corpus):
    original = corpus[3].channel.embed
    async def change(texts, query=False):
        with SessionLocal() as db:
            db.get(Source, corpus[1][0][0]).status = "discarded"
            db.commit()
        return await original(texts, query=query)
    corpus[3].channel.embed = change
    assert not run(corpus, "retard livraison")["items"]


def test_types_dates_pagination_and_knowledge_do_not_call_eg2(corpus):
    result = run(corpus, "350 lux", source_type="document", limit=1)
    assert result["total"] == 1 and result["items"][0]["source_type"] == "document"
    from datetime import date
    assert not run(corpus, "350 lux", after=date(2026, 10, 12))["items"]
    assert run(corpus, "350 lux", before=date(2026, 10, 11))["total"] == 3
    calls = corpus[3].channel.calls
    result = run(corpus, "350 lux", source_type="knowledge")
    assert result["items"][0]["id"] == corpus[2] and corpus[3].channel.calls == calls
    result = run(corpus, "350 lux", limit=1, offset=1)
    assert result["total"] == 3 and result["has_next"] and len(result["items"]) == 1


def test_http_validation_and_scoped_reader_cannot_search_foreign_projects(corpus, monkeypatch):
    import json
    from backend.app.db import SessionLocal as ERP
    from backend.app.models import BrainLink, Project as ERPProject
    from app.services import unified_search
    monkeypatch.setattr(unified_search, "EG2MemoryAdapter", lambda **kw: corpus[3])
    with ERP() as db:
        project = ERPProject(code="SEARCH-" + uuid.uuid4().hex, title="Recherche")
        db.add(project)
        db.flush()
        db.add(BrainLink(project_id=project.id, brain_project_id=corpus[0], brain_code="SEARCH"))
        db.commit()
        erp_id = project.id
    monkeypatch.setenv("AGENT_OPERATOR_ROLE", "reader")
    monkeypatch.setenv("AGENT_OPERATOR_PROJECT_IDS", json.dumps([erp_id]))
    result = client.get("/v1/search", params={"q": "AIRB25LTH0806-A"})
    assert result.status_code == 200, result.text
    assert all(hit["project_id"] == corpus[0] for hit in result.json()["items"])
    assert client.get("/v1/search", params={"q": "350 lux", "project_id": "foreign"}).status_code == 404
    assert client.get("/v1/search", params={"q": "  "}).status_code == 422
    assert client.get("/v1/search", params={"q": "xx", "after": "2026-10-12", "before": "2026-10-11"}).status_code == 422
    monkeypatch.setenv("AGENT_OPERATOR_PROJECT_IDS", "[]")
    calls = corpus[3].channel.calls
    assert client.get("/v1/search", params={"q": "350 lux"}).json()["total"] == 0
    assert corpus[3].channel.calls == calls
