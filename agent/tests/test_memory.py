"""Contrat mémoire : fabrique, sérialisation, datasets (sans EG2 live)."""
from app.services.memory_factory import get_memory_adapter, resolve_engine
from app.services.eg2_memory import dataset_name_for
from app.services.memory_port import FakeMemoryAdapter
from app.db import SessionLocal


def test_factory_defaults_to_fake():
    assert resolve_engine(SessionLocal) in ("fake", "eg2")
    assert isinstance(get_memory_adapter(SessionLocal), FakeMemoryAdapter)


def test_dataset_naming_convention():
    assert dataset_name_for("12345678-abcd", "evidence") == "pb_12345678-abcd__evidence"
    assert dataset_name_for("12345678-abcd", "truth") == "pb_12345678-abcd__truth"


def test_text_fallback_keeps_whole_artifact_around_search_match():
    import asyncio
    import uuid
    from app.models import Project, Source, SourceArtifact

    text = 'Contexte initial. ' * 200 + 'Décision inox 316L. ' + 'Annexes finales. ' * 200
    with SessionLocal() as db:
        project = Project(code='LONG-' + uuid.uuid4().hex, name='Rappel complet')
        db.add(project)
        db.flush()
        source = Source(project_id=project.id, source_type='email', status='resolved',
                        original_uri='test://long-text', sha256=uuid.uuid4().hex)
        db.add(source)
        db.flush()
        db.add(SourceArtifact(source_id=source.id, kind='body_text', content_text=text))
        db.commit()
        hits = asyncio.run(FakeMemoryAdapter(SessionLocal).recall(project.id, '316L', ['evidence']))
        assert len(hits) == 1
        assert hits[0]['excerpt'] == text
