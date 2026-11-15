"""L4 on fictional stores only: freeze, races, provenance and recovery."""
import base64
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import io
import json

from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.db_support import backup_sqlite, configure_sqlite
from backend.app.db import Base
from backend.app.models import BrainLink, Deliverable, Milestone, Project
from backend.app.project_identity_models import ProjectMember, ProjectPerson
from backend.app.project_review_models import ProjectReview, REVIEW_TABLES, ReviewEvent
from backend.app.project_review_schemas import (
    RecordingImport, ReviewCommand, ReviewContent, ReviewCreate, ReviewItem, ReviewParticipant,
    ReviewPublish, ReviewSave,
)
from backend.app.services import project_reviews as service
from backend.app.services.migration_guard import capture_baseline, compare_baseline
from backend.app.services.planning_revision import revision
from backend.app.services.project_operator import Operator, operator_context
from backend.app.services.project_review_migration import install_review_schema, validate_review_schema


@contextmanager
def transaction(factory):
    with factory() as db:
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise


@pytest.fixture
def store(tmp_path):
    path = tmp_path / 'erp.db'
    engine = create_engine(f'sqlite:///{path}', connect_args={'check_same_thread': False})
    configure_sqlite(engine)
    Base.metadata.create_all(engine, tables=[table for table in Base.metadata.sorted_tables if table not in REVIEW_TABLES])
    factory = sessionmaker(bind=engine, autoflush=False)
    with transaction(factory) as db:
        project, foreign = Project(code='L4-0001', title='Lancement fictif'), Project(code='L4-0002', title='Autre projet')
        person = ProjectPerson(first_name='Alice', last_name='Recette', function='Chargée de projet')
        db.add_all([project, foreign, person])
        db.flush()
        milestone = Milestone(project_id=project.id, title='RLP')
        deliverable = Deliverable(project_id=project.id, title='Analyse fonctionnelle')
        other = Deliverable(project_id=foreign.id, title='Autre livrable')
        db.add_all([milestone, deliverable, other, ProjectMember(project_id=project.id, person_id=person.id,
                                                               role='responsable_projet')])
        db.flush()
        ids = {'project': project.id, 'foreign': foreign.id, 'person': person.id,
               'milestone': milestone.id, 'deliverable': deliverable.id, 'other': other.id}
    baseline = capture_baseline(path)
    backup = tmp_path / 'before-l4.db'
    result = install_review_schema(engine, backup=lambda: backup_sqlite(path, backup))
    yield factory, ids, path, baseline, backup, result
    engine.dispose()


def content(ids, **kwargs):
    return ReviewContent(meeting_date='2026-10-06', location='Salle projets',
        participants=[ReviewParticipant(person_id=ids['person'], name='Nom saisi')],
        deliverable_ids=[ids['deliverable']], milestone_id=ids['milestone'],
        items=[ReviewItem(id=f'manual-{index}', section_code=section, text=label, reviewed=True)
               for index, (section, label) in enumerate((('vigilance_points', 'Disponibilité des composants'),
                   ('expected_functions', 'Éclairer la zone de travail'), ('initial_constraints', 'Qualification client obligatoire')))],
        **kwargs)


def create(store, value=None):
    factory, ids, *_ = store
    with transaction(factory) as db:
        return service.create_review(db, ids['project'], ReviewCreate(expected_revision=revision(db, ids['project']),
                                      content=value or content(ids)))


def command(store, fn, owner, cls, **kwargs):
    factory, ids, *_ = store
    with transaction(factory) as db:
        row = service.read_review(db, ids['project'], owner)
        payload = cls(expected_revision=row['revision'], expected_review_revision=row['review_revision'], **kwargs)
        return fn(db, ids['project'], owner, payload)


def fake_pdf(_):
    return b'%PDF-1.4\nFictional PDF adapter\n%%EOF'


def publish(store, owner, builder=fake_pdf):
    factory, ids, *_ = store
    with transaction(factory) as db:
        row = service.read_review(db, ids['project'], owner)
        return service.publish_review(db, ids['project'], owner, ReviewPublish(expected_revision=row['revision'],
            expected_review_revision=row['review_revision'], confirmed=True), pdf_builder=builder)


def test_migration_preserves_all_existing_cells_and_idempotence(store):
    factory, ids, path, baseline, backup, result = store
    assert len(result['created_tables']) == 3 and len(result['created_triggers']) == 6
    assert capture_baseline(backup) == baseline
    assert compare_baseline(baseline, capture_baseline(path))['preserved']
    assert install_review_schema(factory.kw['bind'], backup=lambda: pytest.fail('Repeated backup')) == {
        'created_tables': [], 'created_triggers': []}
    assert validate_review_schema(factory.kw['bind']) == {'created_tables': [], 'created_triggers': []}


def test_backup_failure_and_incompatible_schema_cannot_install(store):
    factory, _, path, *_ = store
    isolated = create_engine(f'sqlite:///{path.parent / "failed.db"}')
    Base.metadata.create_all(isolated, tables=[table for table in Base.metadata.sorted_tables if table not in REVIEW_TABLES])
    with pytest.raises(RuntimeError, match='backup failed'):
        install_review_schema(isolated, backup=lambda: (_ for _ in ()).throw(RuntimeError('backup failed')))
    with isolated.connect() as db:
        assert not db.exec_driver_sql("SELECT name FROM sqlite_master WHERE name LIKE 'project_review%'").all()
    with isolated.begin() as db:
        db.exec_driver_sql('CREATE TABLE project_reviews (id TEXT PRIMARY KEY)')
    with pytest.raises(ValueError, match='Schéma'):
        validate_review_schema(isolated, require_prerequisites=False)
    isolated.dispose()
    with factory.kw['bind'].begin() as db:
        db.exec_driver_sql('DROP TRIGGER trg_project_review_events_update_immutable')
        db.exec_driver_sql('CREATE TRIGGER trg_project_review_events_update_immutable BEFORE UPDATE '
                           'ON project_review_events BEGIN SELECT 1; END')
    with pytest.raises(ValueError, match='Protection'):
        validate_review_schema(factory.kw['bind'])


def test_reads_are_neutral_and_only_operational_type_is_exposed(store):
    factory, ids, path, *_ = store
    before = capture_baseline(path)
    with factory() as db:
        assert service.list_reviews(db, ids['project'])['total'] == 0
        assert [row['code'] for row in service.catalogue()] == ['rlp']
    assert capture_baseline(path) == before


def test_structured_draft_saves_identity_and_exact_dependencies(store):
    initial = create(store)
    assert initial['review_revision'] == 1 and initial['revision'] == 1
    assert initial['content']['participants'][0]['name'] == 'Alice Recette'
    assert not initial['publication_blockers']
    edited = deepcopy(initial['content'])
    edited['items'][1]['text'] = 'Éclairer une zone étendue'
    result = command(store, service.save_review, initial['id'], ReviewSave, content=ReviewContent.model_validate(edited))
    assert result['review_revision'] == 2 and result['revision'] == 2
    factory, ids, *_ = store
    with factory() as db:
        events = db.query(ReviewEvent).order_by(ReviewEvent.planning_revision).all()
        assert events[1].previous['content'] == initial['content']
        assert events[1].value['content'] == result['content']


def test_publication_is_frozen_and_next_revision_independent(store):
    initial = create(store)
    published = publish(store, initial['id'])
    assert published['status'] == 'published' and not published['can_edit']
    factory, ids, *_ = store
    with factory() as db:
        row, pdf = service.publication(db, ids['project'], initial['id'])
        snapshot = json.loads(row.snapshot)
        assert snapshot['review']['status'] == 'published'
        assert snapshot['review']['content'] == initial['content']
        assert snapshot['deliverables'][0]['id'] == ids['deliverable']
        assert pdf == fake_pdf(None) and row.pdf_sha256 == hashlib.sha256(pdf).hexdigest()
        original_payload = row.snapshot
    next_row = command(store, service.create_revision, initial['id'], ReviewCommand)
    assert next_row['number'] == 2 and next_row['review_revision'] == 1
    assert next_row['previous_review_id'] == initial['id'] and next_row['status'] == 'draft'
    edited = ReviewContent.model_validate(next_row['content'])
    edited.items[0].text = 'Nouveau point de vigilance'
    command(store, service.save_review, next_row['id'], ReviewSave, content=edited)
    with factory() as db:
        assert service.publication(db, ids['project'], initial['id'])[0].snapshot == original_payload
        assert service.read_review(db, ids['project'], initial['id'])['content'] == initial['content']
    with pytest.raises(HTTPException) as error:
        command(store, service.create_revision, initial['id'], ReviewCommand)
    assert error.value.status_code == 409


@pytest.mark.parametrize('table,statement', [
    ('project_reviews', "UPDATE project_reviews SET status='draft'"),
    ('project_reviews', 'DELETE FROM project_reviews'),
    ('project_review_publications', "UPDATE project_review_publications SET snapshot='changed'"),
    ('project_review_publications', 'DELETE FROM project_review_publications'),
    ('project_review_events', "UPDATE project_review_events SET action='changed'"),
    ('project_review_events', 'DELETE FROM project_review_events'),
])
def test_sql_freeze_cannot_be_bypassed(store, table, statement):
    initial = create(store)
    publish(store, initial['id'])
    with pytest.raises(IntegrityError, match='immutable'):
        with store[0].kw['bind'].begin() as db:
            db.execute(text(statement))


def test_publication_requires_date_team_deliverable_sections_review_and_confirmation(store):
    initial = create(store, ReviewContent())
    assert len(initial['publication_blockers']) == 6
    before = capture_baseline(store[2])
    with pytest.raises(HTTPException) as error:
        publish(store, initial['id'])
    assert error.value.status_code == 409 and capture_baseline(store[2]) == before
    with pytest.raises(ValueError):
        ReviewPublish(expected_revision=1, expected_review_revision=1, confirmed=False)
    valid = content(store[1])
    valid.items[0].reviewed = False
    command(store, service.save_review, initial['id'], ReviewSave, content=valid)
    with pytest.raises(HTTPException, match='409'):
        publish(store, initial['id'])


def test_pdf_failure_rolls_back_both_freeze_and_revision(store):
    initial = create(store)
    before = capture_baseline(store[2])
    def failed(_):
        raise HTTPException(503, 'PDF unavailable')
    with pytest.raises(HTTPException):
        publish(store, initial['id'], failed)
    assert capture_baseline(store[2]) == before
    with pytest.raises(HTTPException):
        publish(store, initial['id'], lambda _: b'not a pdf')
    assert capture_baseline(store[2]) == before


def test_stale_command_and_cross_project_reads_cannot_mutate(store):
    initial = create(store)
    command(store, service.save_review, initial['id'], ReviewSave, content=content(store[1]))
    before = capture_baseline(store[2])
    with pytest.raises(HTTPException) as error, transaction(store[0]) as db:
        service.save_review(db, store[1]['project'], initial['id'], ReviewSave(
            expected_revision=1, expected_review_revision=1, content=content(store[1])))
    assert error.value.status_code == 409 and capture_baseline(store[2]) == before
    with pytest.raises(HTTPException) as error, store[0]() as db:
        service.read_review(db, store[1]['foreign'], initial['id'])
    assert error.value.status_code == 404
    with pytest.raises(HTTPException), transaction(store[0]) as db:
        service.save_review(db, store[1]['project'], initial['id'], ReviewSave(
            expected_revision=2, expected_review_revision=2,
            content=ReviewContent(deliverable_ids=[store[1]['other']])))
    assert capture_baseline(store[2]) == before


def test_reader_and_scoped_operator_rules_apply_without_http(store):
    initial = create(store)
    with operator_context(Operator('reader', 'reader', frozenset([store[1]['project']]))):
        with store[0]() as db:
            assert not service.read_review(db, store[1]['project'], initial['id'])['can_edit']
        with pytest.raises(HTTPException) as error:
            command(store, service.save_review, initial['id'], ReviewSave, content=content(store[1]))
        assert error.value.status_code == 403
    with operator_context(Operator('foreign', 'owner', frozenset([store[1]['foreign']]))):
        with pytest.raises(HTTPException) as error, store[0]() as db:
            service.read_review(db, store[1]['project'], initial['id'])
        assert error.value.status_code == 404


def test_concurrent_creates_have_one_winner_and_no_duplicate_revision(store):
    def attempt(_):
        try:
            with transaction(store[0]) as db:
                return service.create_review(db, store[1]['project'], ReviewCreate(expected_revision=0))['number']
        except HTTPException as exc:
            return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attempt, range(2))) == [1, 409]
    with store[0]() as db:
        assert db.query(ProjectReview).count() == db.query(ReviewEvent).count() == 1


def test_coordinated_sqlite_backup_contains_exact_frozen_pdf_and_history(store):
    initial = create(store)
    publish(store, initial['id'])
    path = store[2].parent / 'frozen-copy.db'
    backup_sqlite(store[2], path)
    copied = create_engine(f'sqlite:///{path}')
    try:
        with sessionmaker(bind=copied)() as db:
            row, pdf = service.publication(db, store[1]['project'], initial['id'])
            assert base64.b64decode(row.pdf_base64) == pdf == fake_pdf(None)
            assert db.query(ReviewEvent).count() == 2
        assert capture_baseline(path) == capture_baseline(store[2])
        assert not validate_review_schema(copied)['created_triggers']
    finally:
        copied.dispose()


@pytest.fixture
def audio(store):
    from app.db import Base as BrainBase
    from app.models import MeetingRecording, Project as BrainProject, Source
    path = store[2].parent / 'brain.db'
    engine = create_engine(f'sqlite:///{path}')
    configure_sqlite(engine)
    BrainBase.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False)
    with transaction(factory) as db:
        project = BrainProject(code='AUDIO-L4-0001', name='Réunion fictive')
        db.add(project)
        db.flush()
        source = Source(project_id=project.id, source_type='meeting', original_uri='fictional://meeting', sha256='1' * 64)
        db.add(source)
        db.flush()
        row = MeetingRecording(project_id=project.id, source_id=source.id, erp_project_id=store[1]['project'],
            title='Réunion de lancement', date='2026-10-06', filename='recette.wav', revision=3, reviewed_revision=3,
            summary_revision=3, summary_model='local-test', job_status='done', stage='summarized',
            segments=[{'id': 'segment-1', 'start': 0.0, 'end': 4.0, 'speaker': 'speaker-1',
                       'text': 'Nous devons attendre la qualification client.'}], speaker_names={'speaker-1': 'Alice'},
            summary={'overview': 'Qualification à préparer.', 'decisions': [
                {'text': 'Attendre la qualification', 'quote': 'attendre la qualification client', 'segment_id': 'segment-1'}],
                'actions': [], 'open_points': []})
        db.add(row)
        db.flush()
        identity, brain_id = row.id, project.id
    with transaction(store[0]) as db:
        db.add(BrainLink(project_id=store[1]['project'], brain_project_id=brain_id))
    yield factory, identity, path
    engine.dispose()


def import_audio(store, audio, initial):
    with transaction(store[0]) as db, audio[0]() as brain:
        current = service.read_review(db, store[1]['project'], initial['id'])
        return service.import_recording(db, brain, store[1]['project'], initial['id'], RecordingImport(
            expected_revision=current['revision'], expected_review_revision=current['review_revision'],
            recording_id=audio[1], expected_recording_revision=3))


def test_audio_import_is_readonly_sourced_human_draft_and_keeps_speaker_excerpt(store, audio):
    initial = create(store)
    before = capture_baseline(audio[2])
    result = import_audio(store, audio, initial)
    assert result['status'] == 'draft' and not result['publication']
    item = result['content']['items'][-1]
    assert item['section_code'] == 'decisions' and not item['reviewed']
    proof = result['provenance'][item['evidence_ids'][0]]
    assert proof['revision'] == 3 and proof['speaker'] == 'Alice'
    assert proof['recording_id'] == audio[1] and proof['summary_model'] == 'local-test'
    assert proof['quote'] in proof['text']
    assert capture_baseline(audio[2]) == before
    with pytest.raises(HTTPException):
        publish(store, initial['id'])
    with pytest.raises(HTTPException, match='409'):
        import_audio(store, audio, initial)
    edited = ReviewContent.model_validate(result['content'])
    edited.items[-1].text = 'Qualification exigée avant démarrage'
    edited.items[-1].reviewed = True
    command(store, service.save_review, initial['id'], ReviewSave, content=edited)
    frozen = publish(store, initial['id'])
    assert frozen['provenance'] == result['provenance']
    assert capture_baseline(audio[2]) == before


@pytest.mark.parametrize('field,value', [('summary_revision', 2), ('reviewed_revision', 2), ('job_status', 'running'),
                                       ('erp_project_id', 'other-project')])
def test_invalid_or_foreign_audio_cannot_be_imported(store, audio, field, value):
    from app.models import MeetingRecording
    initial = create(store)
    with transaction(audio[0]) as db:
        setattr(db.get(MeetingRecording, audio[1]), field, value)
    before = capture_baseline(store[2])
    with pytest.raises(HTTPException) as error:
        import_audio(store, audio, initial)
    assert error.value.status_code in (404, 409) and capture_baseline(store[2]) == before


def test_fabricated_quote_cannot_reach_review_and_unknown_evidence_cannot_be_saved(store, audio):
    from app.models import MeetingRecording
    initial = create(store)
    with transaction(audio[0]) as db:
        row = db.get(MeetingRecording, audio[1])
        changed = deepcopy(row.summary)
        changed['decisions'][0]['quote'] = 'Une décision jamais prononcée'
        row.summary = changed
    before = capture_baseline(store[2])
    with pytest.raises(HTTPException):
        import_audio(store, audio, initial)
    edited = content(store[1])
    edited.items[0].evidence_ids = ['fabricated']
    with pytest.raises(HTTPException):
        command(store, service.save_review, initial['id'], ReviewSave, content=edited)
    assert capture_baseline(store[2]) == before


def test_actual_pdf_carries_snapshot_text_and_long_notes_paginate(store):
    pytest.importorskip('reportlab')
    from pypdf import PdfReader
    from backend.app.services.project_review_pdf import build_pdf
    initial = create(store, content(store[1], notes=('Contexte français : contrôle de réception et validation client.\n' * 100)))
    publish(store, initial['id'], build_pdf)
    with store[0]() as db:
        _, pdf = service.publication(db, store[1]['project'], initial['id'])
    parsed = PdfReader(io.BytesIO(pdf))
    extracted = '\n'.join(page.extract_text() for page in parsed.pages)
    assert len(parsed.pages) > 2
    assert all(value in extracted for value in ['L4-0001', 'Alice Recette', 'Fonctions attendues', 'Éclairer la zone',
                                               'Contexte français', 'Qualification client obligatoire'])
