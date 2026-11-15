"""V4 closure, immutable history, two-store UUIDs and rejection before writes."""
from copy import deepcopy
import hashlib
import json
import uuid

from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.db_support import backup_sqlite, configure_sqlite
from app.models import Project as BrainProject, Source, SourceArtifact, MeetingRecording
from backend.app.db import Base
from backend.app.models import BrainLink, CdcSource, DeliveryVersion, Meeting, Milestone, Project
from backend.app.project_identity_schemas import IdentityPatch, PersonCreate, ReferenceCreate
from backend.app.project_planning_models import PlanningBaseline, PlanningChange, PlanningTemplate, PlanningTemplateVersion
from backend.app.project_planning_schemas import (
    BaselineMetadataPatch, PlanningTemplateApply, PlanningTemplateCreate, PlanningTemplatePreview, TaskPlanningPatch,
)
from backend.app.services import project_archive as archive, project_identity as identity
from backend.app.services import planning_templates as templates, project_planning as planning
from backend.app.services.project_planning_migration import install_planning_schema
from backend.app.services.project_planning_rules import default_template
from tests.test_project_planning import transaction


@pytest.fixture
def stores(tmp_path, monkeypatch):
    import app.db
    import app.config
    from app.db import Base as BrainBase
    engines, factories = {}, {}
    for name in ('source', 'target', 'source_brain', 'target_brain'):
        path = tmp_path / (name + '.db')
        engine = create_engine(f'sqlite:///{path}')
        configure_sqlite(engine)
        metadata = BrainBase.metadata if name.endswith('brain') else Base.metadata
        metadata.create_all(engine)
        if not name.endswith('brain'):
            install_planning_schema(engine, backup=lambda p=path: backup_sqlite(p, p.with_suffix('.backup.db')))
        engines[name] = engine
        factories[name] = sessionmaker(bind=engine, autoflush=False)
    monkeypatch.setattr(app.db, 'SessionLocal', factories['source_brain'])
    monkeypatch.setattr(app.config, 'RAW_DIR', tmp_path / 'raw')
    yield factories, engines, monkeypatch
    for engine in engines.values():
        engine.dispose()


def build(stores, *, with_brain=False):
    factories, _, _ = stores
    with transaction(factories['source']) as db:
        project = Project(code='V4-0205', title='Planning recette', hourly_rate=91.5, margin_pct=12)
        db.add(project)
        db.flush()
        project_id = project.id
        typology = identity.create_reference(db, ReferenceCreate(kind='typology', code='TEST', label='Recette'))
        identity.patch_identity(db, project_id, IdentityPatch(expected_revision=0, typology_id=typology['id']))
        person = identity.create_person(db, PersonCreate(first_name='Alice', last_name='Historique', email='alice@example.test'))
        secret = templates.create_template(db, PlanningTemplateCreate(code='SECRET', name='Autre projet', definition=default_template()))
        historical = templates.create_template(db, PlanningTemplateCreate(code='HISTORY', name='Modèle historique', definition=default_template()))
        inputs = PlanningTemplatePreview(expected_revision=0)
        preview = templates.preview_application(db, project_id, historical['version']['id'], inputs)
        templates.apply_template(db, project_id, historical['version']['id'], PlanningTemplateApply(
            **inputs.model_dump(), expected_preview_sha256=preview['preview_sha256']))
        definition = default_template().model_dump()
        definition['tasks'] = [
            {'key': 'group', 'title': 'Groupe'},
            {'key': 'design', 'title': 'Études', 'parent_key': 'group', 'milestone_code': 'pdr',
             'planned_hours': 6, 'start_offset_workdays': 0, 'end_offset_workdays': 1, 'design': True},
            {'key': 'control', 'title': 'Contrôle', 'parent_key': 'group', 'planned_hours': 2,
             'start_offset_workdays': 0, 'end_offset_workdays': 2, 'manufacturing': True},
        ]
        template = templates.create_template(db, PlanningTemplateCreate(
            code='STANDARD', name='Cycle recette', typology_id=typology['id'], definition=definition))
        inputs = PlanningTemplatePreview(expected_revision=1, start_date='2026-10-02', excluded_dates=['2026-10-05'])
        view = templates.preview_application(db, project_id, template['version']['id'], inputs)
        applied = templates.apply_template(db, project_id, template['version']['id'], PlanningTemplateApply(
            **inputs.model_dump(), expected_preview_sha256=view['preview_sha256']))
        task_id = applied['task_map']['design']
        planning.patch_task(db, project_id, task_id, TaskPlanningPatch(expected_revision=2,
            title=task_id, responsible_id=person['id'], comment=task_id))
        milestone_id = applied['milestone_map']['pdr']
        if with_brain:
            meeting = Meeting(id=str(uuid.uuid4()), project_id=project_id, title='Réunion', decisions=task_id)
            db.add(meeting)
            db.add(BrainLink(project_id=project_id, brain_project_id=project_id))
            db.flush()
            evidence = {'kind': 'brain', 'source_id': task_id, 'artifact_id': meeting.id,
                        'quote': task_id, 'hash': hashlib.sha256(task_id.encode()).hexdigest()}
            db.get(Milestone, milestone_id).date_sources = {'contractual_date': evidence}
            db.flush()
            with transaction(factories['source_brain']) as brain:
                brain.add(BrainProject(id=project_id, code='V4-0205', name='Planning recette'))
                brain.flush()
                brain.add(Source(id=task_id, project_id=project_id, source_type='meeting', status='resolved',
                                 original_uri='', sha256=hashlib.sha256(('source:' + task_id).encode()).hexdigest()))
                brain.flush()
                brain.add(SourceArtifact(id=meeting.id, source_id=task_id, kind='body_text', content_text=task_id))
                brain.add(MeetingRecording(project_id=project_id, erp_project_id=project_id, source_id=task_id,
                    title='Réunion', filename='recette.wav', published_meeting_id=meeting.id, job_status='running'))
        baseline = planning.create_baseline(db, project_id, expected_revision=3, kind='initial', label='État initial')
        planning.patch_task(db, project_id, task_id, TaskPlanningPatch(expected_revision=4,
            responsible_id=None, planned_hours=9, end_date='2026-10-09'))
        expected_compare = planning.compare_baseline(db, project_id, baseline['id'])
    with factories['source']() as db:
        exported = archive.export_archive(db, project_id)
    return exported, {'project_id': project_id, 'task_id': task_id, 'template': template,
                      'historical': historical, 'secret': secret, 'person': person, 'baseline': baseline,
                      'compare': expected_compare, 'milestone_id': milestone_id}


def restore(stores, exported, *, same_store=False, code='RESTORED-0205'):
    import app.db
    factories, _, monkeypatch = stores
    monkeypatch.setattr(app.db, 'SessionLocal', factories['source_brain' if same_store else 'target_brain'])
    with transaction(factories['source' if same_store else 'target']) as db:
        return archive.import_archive(db, exported, code=code)


def test_v4_roundtrip_preserves_tree_history_and_rehashes_frozen_references(stores):
    exported, ids = build(stores)
    before = deepcopy(exported)
    assert exported['version'] == 4
    refs = exported['planning_references']
    assert {row['id'] for row in refs['project_planning_templates']} == {ids['template']['id'], ids['historical']['id']}
    assert ids['secret']['id'] not in json.dumps(exported)
    assert [row['id'] for row in exported['references']['project_people']] == [ids['person']['id']]
    result = restore(stores, exported)
    assert exported == before and result['version'] == 4
    with stores[0]['target']() as db:
        view = planning.read_planning(db, result['id'])
        assert view['revision'] == 5 and view['excluded_dates'] == ['2026-10-05']
        leaf = next(row for row in view['tasks'] if row['template_key'] == 'design')
        group = next(row for row in view['tasks'] if row['template_key'] == 'group')
        assert leaf['id'] != ids['task_id'] and leaf['title'] == leaf['comment'] == ids['task_id']
        assert leaf['parent_id'] == group['id'] and group['planned_hours'] == 11
        assert leaf['milestone_id'] in {row['id'] for row in view['milestones']}
        baseline = db.query(PlanningBaseline).one()
        assert baseline.sha256 != ids['baseline']['sha256']
        assert hashlib.sha256(baseline.payload.encode()).hexdigest() == baseline.sha256
        assert json.loads(baseline.payload)['project_id'] == result['id']
        frozen_leaf = next(row for row in json.loads(baseline.payload)['tasks'] if row['id'] == leaf['id'])
        assert frozen_leaf['responsible_id'] != ids['person']['id'] and frozen_leaf['title'] == ids['task_id']
        compare = planning.compare_baseline(db, result['id'], baseline.id)
        assert len(compare['changes']) == len(ids['compare']['changes'])
        assert compare['planned_hours_delta'] == ids['compare']['planned_hours_delta'] == 3
        def normalized_changes(value):
            return sorted((row['field'], 'person' if row['field'] == 'responsible_id' and row['before'] else row['before'], row['after'])
                          for row in value['changes'])
        assert normalized_changes(compare) == normalized_changes(ids['compare'])
        event = db.query(PlanningChange).filter_by(action='baseline_created').one()
        assert event.value['baseline_id'] == baseline.id and event.value['sha256'] == baseline.sha256
        assert db.get(Project, result['id']).hourly_rate == 91.5
        assert db.execute(text('PRAGMA foreign_key_check')).all() == []
        assert archive.export_archive(db, result['id'])['version'] == 4
        with pytest.raises(IntegrityError):
            db.execute(PlanningBaseline.__table__.update().values(label='Interdit'))
        db.rollback()


@pytest.mark.parametrize('snapshot_version', [1, 2])
def test_project_commitments_roundtrip_and_legacy_capture_remains_v1(stores, snapshot_version):
    exported, ids = build(stores)
    with transaction(stores[0]['source']) as db:
        identity.patch_identity(db, ids['project_id'], IdentityPatch(expected_revision=1,
            start_date='2026-10-05', planned_end_date='2026-12-15'))
        db.get(Project, ids['project_id']).tdao_budget_h = 180
    with stores[0]['source']() as db:
        exported = archive.export_archive(db, ids['project_id'])
    row = exported['tables']['project_planning_baselines'][0]
    if snapshot_version == 1:
        value = json.loads(row['payload'])
        value.pop('project')
        value['version'] = 1
        row['payload'] = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        row['sha256'] = hashlib.sha256(row['payload'].encode()).hexdigest()
        event = next(event for event in exported['tables']['project_planning_changes'] if event['action'] == 'baseline_created')
        event['value']['sha256'] = row['sha256']
    frozen_project = json.loads(row['payload']).get('project')
    result = restore(stores, exported)
    with stores[0]['target']() as db:
        baseline = db.query(PlanningBaseline).one()
        assert json.loads(baseline.payload)['version'] == snapshot_version
        assert json.loads(baseline.payload).get('project') == frozen_project
        assert db.get(Project, result['id']).tdao_budget_h == 180
        diff = planning.compare_baseline(db, result['id'], baseline.id)
        assert diff['project_comparison_available'] is (snapshot_version == 2)
        assert diff['project_budget_hours_delta'] == (180 if snapshot_version == 2 else None)
        if snapshot_version == 2:
            assert {change['field'] for change in diff['changes'] if change['kind'] == 'project'} == {'start_date', 'planned_end_date', 'budget_hours'}
        else:
            assert all(change['kind'] != 'project' for change in diff['changes'])
        event = db.query(PlanningChange).filter_by(action='project_changed').one()
        assert event.previous['project']['start_date'] == '' and event.value['project']['start_date'] == '2026-10-05'
        reexported = archive.export_archive(db, result['id'])
        assert json.loads(reexported['tables']['project_planning_baselines'][0]['payload'])['version'] == snapshot_version
        assert db.execute(text('PRAGMA foreign_key_check')).all() == []


@pytest.mark.parametrize('mutation', ['finance', 'invalid_dates', 'missing_budget'])
def test_bad_project_commitments_archive_is_rejected_before_import(stores, mutation):
    exported, ids = build(stores)
    baseline = exported['tables']['project_planning_baselines'][0]
    value = json.loads(baseline['payload'])
    if mutation == 'finance':
        value['project']['hourly_rate'] = 80
    elif mutation == 'invalid_dates':
        value['project'].update(start_date='2026-12-02', planned_end_date='2026-12-01')
    else:
        value['project'].pop('budget_hours')
    baseline['payload'] = json.dumps(value, sort_keys=True, separators=(',', ':'))
    baseline['sha256'] = hashlib.sha256(baseline['payload'].encode()).hexdigest()
    next(event for event in exported['tables']['project_planning_changes'] if event['action'] == 'baseline_created')['value']['sha256'] = baseline['sha256']
    with pytest.raises(HTTPException) as error:
        restore(stores, exported)
    assert error.value.status_code == 400
    with stores[0]['target']() as db:
        assert db.query(Project).count() == 0


def metadata_archive(stores):
    exported, ids = build(stores)
    with transaction(stores[0]['source']) as db:
        planning.patch_baseline_metadata(db, ids['project_id'], ids['baseline']['id'],
            BaselineMetadataPatch(expected_revision=5, label='Revue conservée', comment=ids['baseline']['id'], active=False))
        planning.patch_baseline_metadata(db, ids['project_id'], ids['baseline']['id'],
            BaselineMetadataPatch(expected_revision=6, comment='Dernière revue'))
    with stores[0]['source']() as db:
        return archive.export_archive(db, ids['project_id']), ids


def test_baseline_metadata_archive_preserves_chain_and_remaps_only_pointer(stores):
    exported, ids = metadata_archive(stores)
    baseline_before = next(row for row in exported['tables']['project_planning_baselines'])
    assert baseline_before['label'] == 'État initial' and baseline_before['sha256'] == ids['baseline']['sha256']
    result = restore(stores, exported)
    with stores[0]['target']() as db:
        assert planning.list_baselines(db, result['id'])['total'] == 0
        row = planning.list_baselines(db, result['id'], include_inactive=True)['items'][0]
        assert row['label'] == 'Revue conservée' and row['comment'] == 'Dernière revue'
        events = db.query(PlanningChange).filter_by(project_id=result['id'], action='baseline_metadata_changed').order_by(PlanningChange.revision).all()
        assert events[0].value['baseline_id'] == row['id'] != ids['baseline']['id']
        assert events[0].value['comment'] == ids['baseline']['id']  # prose remains unchanged
        assert events[1].previous == events[0].value
        assert planning.compare_baseline(db, result['id'], row['id'])['planned_hours_delta'] == 3
        assert archive.export_archive(db, result['id'])['version'] == 4


@pytest.mark.parametrize('mutation', ['chain', 'pointer', 'type', 'field'])
def test_bad_baseline_metadata_archive_is_rejected_before_import(stores, mutation):
    exported, _ = metadata_archive(stores)
    event = next(row for row in exported['tables']['project_planning_changes'] if row['action'] == 'baseline_metadata_changed')
    if mutation == 'chain':
        event['previous']['label'] = 'Autre chaîne'
    elif mutation == 'pointer':
        event['previous']['baseline_id'] = str(uuid.uuid4())
    elif mutation == 'type':
        event['value']['active'] = 'false'
    else:
        event['value']['payload'] = '{}'
    with pytest.raises(HTTPException) as exc:
        restore(stores, exported)
    assert exc.value.status_code == 400
    with stores[0]['target']() as db:
        assert db.query(Project).count() == 0 and db.query(PlanningChange).count() == 0


def test_same_store_reuses_models_versions_and_people_without_mutating_them(stores):
    exported, _ = build(stores)
    tables = ['project_planning_templates', 'project_planning_template_versions', 'project_people', 'project_references']
    with stores[0]['source']() as db:
        before = {name: list(db.execute(select(Base.metadata.tables[name])).mappings()) for name in tables}
    restore(stores, exported, same_store=True)
    with stores[0]['source']() as db:
        after = {name: list(db.execute(select(Base.metadata.tables[name])).mappings()) for name in tables}
    assert after == before


@pytest.mark.parametrize('same_store', [False, True])
def test_two_store_uuid_collisions_preserve_correct_proofs_and_audio_links(stores, same_store):
    exported, ids = build(stores, with_brain=True)
    result = restore(stores, exported, same_store=same_store)
    factory = stores[0]['source' if same_store else 'target']
    brain_factory = stores[0]['source_brain' if same_store else 'target_brain']
    with factory() as db, brain_factory() as brain:
        link = db.get(BrainLink, result['id'])
        view = planning.read_planning(db, result['id'])
        leaf = next(row for row in view['tasks'] if row['template_key'] == 'design')
        milestone = next(row for row in view['milestones'] if row['code'] == 'pdr')
        proof = milestone['date_sources']['contractual_date']
        assert proof['source_id'] != leaf['id'] and proof['quote'] == ids['task_id']
        assert brain.get(Source, proof['source_id']).project_id == link.brain_project_id
        assert brain.get(SourceArtifact, proof['artifact_id']).source_id == proof['source_id']
        assert brain.get(SourceArtifact, proof['artifact_id']).content_text == ids['task_id']
        recording = brain.query(MeetingRecording).filter_by(erp_project_id=result['id']).one()
        assert recording.project_id == link.brain_project_id and recording.source_id == proof['source_id']
        assert recording.job_status == 'interrupted'
        assert db.get(Meeting, recording.published_meeting_id).project_id == result['id']
        frozen = json.loads(db.query(PlanningBaseline).filter_by(project_id=result['id']).one().payload)
        frozen_proof = next(row for row in frozen['milestones'] if row['id'] == milestone['id'])['date_sources']['contractual_date']
        assert frozen_proof == proof
        assert db.execute(text('PRAGMA foreign_key_check')).all() == brain.execute(text('PRAGMA foreign_key_check')).all() == []


@pytest.mark.parametrize('corruption', ['hash', 'history_type', 'history_foreign', 'template_hash', 'extra_template',
                                     'load', 'cycle', 'duplicate_revision', 'calendar', 'missing_state', 'downgrade', 'foreign_proof',
                                     'baseline_history_hash', 'history_cycle', 'mapping_type'])
def test_malformed_archive_rejected_without_any_target_write(stores, corruption):
    exported, ids = build(stores)
    tables = exported['tables']
    if corruption == 'hash':
        tables['project_planning_baselines'][0]['sha256'] = '0' * 64
    elif corruption == 'history_type':
        tables['project_planning_changes'][0]['previous'] = []
    elif corruption == 'history_foreign':
        tables['project_planning_changes'][0]['value']['project_id'] = str(uuid.uuid4())
    elif corruption == 'template_hash':
        exported['planning_references']['project_planning_template_versions'][0]['sha256'] = '0' * 64
    elif corruption == 'extra_template':
        row = deepcopy(exported['planning_references']['project_planning_templates'][0])
        row.update(id=str(uuid.uuid4()), code='FOREIGN', normalized_code='foreign', name='Étranger', search_text='foreign etranger')
        exported['planning_references']['project_planning_templates'].append(row)
    elif corruption == 'load':
        tables['project_task_plans'][0]['planned_hours'] = -1
    elif corruption == 'cycle':
        group = next(row for row in tables['project_task_plans'] if row['template_key'] == 'group')
        group['parent_task_id'] = ids['task_id']
    elif corruption == 'duplicate_revision':
        tables['project_planning_changes'][1]['revision'] = tables['project_planning_changes'][0]['revision']
    elif corruption == 'calendar':
        tables['project_planning_states'][0]['excluded_dates'] = ['2026-02-30']
    elif corruption == 'missing_state':
        tables['project_planning_states'] = []
    elif corruption == 'downgrade':
        exported['version'] = 3
    elif corruption == 'baseline_history_hash':
        next(row for row in tables['project_planning_changes'] if row['action'] == 'baseline_created')['value']['sha256'] = '0' * 64
    elif corruption == 'history_cycle':
        event = next(row for row in tables['project_planning_changes'] if row['action'] == 'task_changed')
        next(row for row in event['value']['tasks'] if row['template_key'] == 'group')['parent_id'] = ids['task_id']
    elif corruption == 'mapping_type':
        tables['project_planning_changes'][0]['value']['inputs']['milestone_mapping'] = []
    else:
        tables['milestones'][0]['date_sources'] = {'forecast_date': {'kind': 'meeting', 'meeting_id': str(uuid.uuid4())}}
    with pytest.raises(HTTPException) as error:
        restore(stores, exported)
    assert error.value.status_code == 400
    with stores[0]['target']() as db:
        assert db.query(Project).count() == db.query(PlanningTemplate).count() == db.query(PlanningChange).count() == 0


def test_changed_same_store_template_conflicts_without_overwrite(stores):
    exported, ids = build(stores)
    with transaction(stores[0]['source']) as db:
        db.get(PlanningTemplate, ids['template']['id']).name = 'Version locale conservée'
    with pytest.raises(HTTPException) as error:
        restore(stores, exported, same_store=True)
    assert error.value.status_code == 409
    with stores[0]['source']() as db:
        assert db.query(Project).count() == 1
        assert db.get(PlanningTemplate, ids['template']['id']).name == 'Version locale conservée'


def test_changed_canonical_brain_proof_refuses_reuse_without_new_project(stores):
    exported, _ = build(stores, with_brain=True)
    with transaction(stores[0]['source_brain']) as brain:
        brain.query(SourceArtifact).one().content_text = 'Preuve différente'
    with pytest.raises(HTTPException) as error:
        restore(stores, exported, same_store=True)
    assert error.value.status_code == 409
    with stores[0]['source']() as db:
        assert db.query(Project).count() == 1


def test_different_uuids_same_template_and_versions_reused_exactly(stores):
    exported, _ = build(stores)
    refs = exported['planning_references']
    mapping = {row['id']: str(uuid.uuid4()) for rows in [*refs.values(), *exported['references'].values()] for row in rows}
    from backend.app.services import project_planning_archive
    with transaction(stores[0]['target']) as db:
        archive._insert(db, Base.metadata, exported['references'], mapping)
        archive._insert(db, Base.metadata, refs, mapping, planning_context={})
    with stores[0]['target']() as db:
        before = list(db.execute(select(PlanningTemplateVersion.__table__)).mappings())
    restored = restore(stores, exported)
    with stores[0]['target']() as db:
        assert list(db.execute(select(PlanningTemplateVersion.__table__)).mappings()) == before
        assert db.query(PlanningTemplate).count() == 2
        state = planning.read_planning(db, restored['id'])
        assert state['active_template_version_id'] in mapping.values()
        assert all(row['template_id'] in mapping.values() for row in state['tasks'])
        project_planning_archive.require_schema(db)


def test_conflicting_immutable_version_refused_without_catalog_mutation(stores):
    exported, _ = build(stores)
    local = deepcopy(exported)
    version = local['planning_references']['project_planning_template_versions'][0]
    value = json.loads(version['definition'])
    value['milestones'][0]['title'] = 'Définition locale conservée'
    version['definition'] = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    version['sha256'] = hashlib.sha256(version['definition'].encode()).hexdigest()
    restore(stores, local)
    with stores[0]['target']() as db:
        before = list(db.execute(select(PlanningTemplateVersion.__table__)).mappings())
    with pytest.raises(HTTPException) as error:
        restore(stores, exported, code='SECOND-0205')
    assert error.value.status_code == 409
    with stores[0]['target']() as db:
        assert db.query(Project).count() == 1
        assert list(db.execute(select(PlanningTemplateVersion.__table__)).mappings()) == before


@pytest.mark.parametrize('missing_piece', [False, True])
def test_v4_restores_cdc_and_delivery_files_or_rejects_incomplete_bundle(stores, tmp_path, missing_piece):
    from pathlib import Path
    import backend.app.db
    factories, _, monkeypatch = stores
    exported, ids = build(stores)
    root = tmp_path / 'cdc'
    root.mkdir()
    document = root / 'document.bin'
    document.write_bytes(b'Archive CDC recette')
    monkeypatch.setattr('backend.app.routers.cdc.cdc_storage_root', lambda: root)
    monkeypatch.setattr(backend.app.db, 'APP_DIR', tmp_path)
    delivery = tmp_path / 'exports' / 'initial.md'
    delivery.parent.mkdir()
    delivery.write_bytes(b'Compte rendu portable')
    with transaction(factories['source']) as db:
        db.add(CdcSource(project_id=ids['project_id'], filename='document.bin', storage_path=str(document)))
        db.add(DeliveryVersion(project_id=ids['project_id'], kind='report', version=1, path=str(delivery),
                               sha256=hashlib.sha256(delivery.read_bytes()).hexdigest()))
    with factories['source']() as db:
        exported = archive.export_archive(db, ids['project_id'])
    if missing_piece:
        exported['files'] = exported['files'][:1]
        with pytest.raises(HTTPException) as error:
            restore(stores, exported)
        assert error.value.status_code == 400
        assert sorted(path.name for path in root.iterdir()) == ['document.bin']
        with factories['target']() as db:
            assert db.query(Project).count() == db.query(PlanningTemplate).count() == 0
    else:
        result = restore(stores, exported)
        assert result['version'] == 4
        with factories['target']() as db:
            cdc = db.query(CdcSource).one()
            stored = db.query(DeliveryVersion).one()
            assert Path(cdc.storage_path).is_relative_to(root / result['id'])
            assert Path(cdc.storage_path).read_bytes() == document.read_bytes()
            assert Path(stored.path).is_relative_to(tmp_path / 'exports' / result['id'])
            assert Path(stored.path).read_bytes() == delivery.read_bytes()
