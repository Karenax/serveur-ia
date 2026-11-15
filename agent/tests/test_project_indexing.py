import asyncio
import sqlite3
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.db import SessionLocal
from app.models import SourceArtifact
from app.services import project_indexing
from app.services.eg2_memory import EG2MemoryAdapter
import uuid
from app.models import Project, Source
from tests.test_unified_search import Channel as SearchChannel


class Channel(SearchChannel):
    endpoint = "http://network.test:1234"
    model = "test-eg2"


def test_coverage_requires_current_content_and_profile(tmp_path, monkeypatch):
    pid, ids = seed(2)
    adapter = EG2MemoryAdapter(channel=Channel(), path=tmp_path / 'eg2.db')
    monkeypatch.setattr(project_indexing, 'EG2MemoryAdapter', lambda **kwargs: adapter)
    with SessionLocal() as db:
        content = db.get(SourceArtifact, ids[0][1]).content_text
    asyncio.run(adapter.remember_evidence(pid, content, {'source_id': ids[0][0]}))
    with SessionLocal() as db:
        result = project_indexing.snapshot(db, pid)
        assert result['indexed'] == 1 and result['sources'] == 2
        assert result['projects'][0]['missing'] == 1
        db.get(SourceArtifact, ids[0][1]).content_text = 'Document modifié'
        db.commit()
        assert project_indexing.snapshot(db, pid)['indexed'] == 0
    with sqlite3.connect(adapter.path) as db:
        db.execute("UPDATE passages SET profile='obsolete'")
    with SessionLocal() as db:
        assert project_indexing.snapshot(db, pid)['indexed'] == 0


def test_missing_index_is_reported_as_unverified_without_creating_file(tmp_path, monkeypatch):
    pid, _ = seed()
    adapter = EG2MemoryAdapter(channel=Channel(), path=tmp_path / 'absent.db')
    monkeypatch.setattr(project_indexing, 'EG2MemoryAdapter', lambda **kwargs: adapter)
    with SessionLocal() as db:
        result = project_indexing.snapshot(db, pid)
    assert result['indexed'] is None and result['error']
    assert not adapter.path.exists()



def seed(count=1):
    with SessionLocal() as db:
        project = Project(code="EG2-" + uuid.uuid4().hex, name="Sources fictives")
        db.add(project)
        db.flush()
        ids = []
        for number in range(count):
            source = Source(project_id=project.id, source_type="document", status="resolved",
                original_uri="fixture://local", sha256=uuid.uuid4().hex)
            db.add(source)
            db.flush()
            artifact = SourceArtifact(source_id=source.id, kind="document_page",
                content_text=f"Éclairage industriel passage {number}.", content_json={"physical_page": number + 1})
            db.add(artifact)
            db.flush()
            ids.append((source.id, artifact.id))
        db.commit()
        return project.id, ids


def test_source_library_returns_eg2_citations(monkeypatch):
    from app.routers import source_search as router
    monkeypatch.setattr(router, 'scope', lambda *args: None)
    mock = AsyncMock(return_value={'items': [{'id':'a','source_id':'a','excerpt':'Texte',
                                              'locator':{'physical_page': 2}}], 'warnings':[]})
    monkeypatch.setattr(router, 'text_search', mock)
    with SessionLocal() as db:
        result = asyncio.run(router.search(query='Texte', project_id=None, source_ids='a', limit=10, modality='all', db=db))
        assert result['engine'] == 'eg2'
        assert result['items'][0]['locator'] == {'physical_page': 2}
        assert result['items'][0]['source_url'] == '/v1/sources/a'
        mock.assert_awaited_once_with(db, query='Texte', project_id=None, source_ids={'a'}, limit=10)
        for modality in ('image', 'audio'):
            with pytest.raises(HTTPException) as error:
                asyncio.run(router.search(query='Texte', project_id=None, source_ids='a', limit=10, modality=modality, db=db))
            assert error.value.status_code == 410
