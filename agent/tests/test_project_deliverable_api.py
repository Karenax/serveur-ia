"""L3 adapter on fictional stores, independently of runtime registration."""
import hashlib
import io
import json

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event

from app.security import local_guard
from backend.app.db import get_db
from backend.app.models import Deliverable, DeliveryVersion, NetworkLink
from backend.app.project_deliverable_models import (
    DeliverableChecklistItem, DeliverableFileVersion, DeliverablePlan, DeliverableVersionMetadata,
)
from backend.app.project_deliverable_schemas import ChecklistCreate, ChecklistPatch, DeliverablePatch, FilePublication
from backend.app.project_identity_models import ProjectProfile
from backend.app.project_identity_schemas import ReferenceCreate
from backend.app.routers import project_deliverables as http
from backend.app.services import deliverable_files as files, deliverable_queries as reads, project_deliverables as commands
from backend.app.services import document_file_access
from backend.app.services.migration_guard import capture_baseline
from backend.app.services.planning_revision import revision
from backend.app.services.project_identity import create_reference
from backend.app.services.project_operator import Operator, operator_context
from tests.test_project_deliverables import create, store as base_store, transaction

store = base_store


@pytest.fixture
def api(store, monkeypatch):
    factory, ids, path, *_ = store
    monkeypatch.setattr(files, 'APP_DIR', path.parent / 'managed')
    monkeypatch.setenv('AGENT_DOCUMENT_ROOTS', json.dumps([str(path.parent)]))
    monkeypatch.setenv('AGENT_DOCUMENT_PROJECT_ROOT', '""')
    monkeypatch.setenv('AGENT_DOCUMENT_DRIVE_MAPPINGS', '{}')
    import app.config
    monkeypatch.setattr(app.config, 'STORAGE_DIR', path.parent / 'brain-storage')
    app = FastAPI()
    app.middleware('http')(local_guard)
    for router in (http.router, http.catalog_router, http.typology_router):
        app.include_router(router)

    def isolated_db():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = isolated_db
    client = TestClient(app, base_url='http://127.0.0.1:8001')
    return client, ids, '/api/v1/projects/' + ids['project'] + '/deliverable-plan'


def upload(client, root, owner, rev, *, content=b'Version exacte', filename='analyse.md', **fields):
    return client.post(f'{root}/{owner}/versions/upload', data={'expected_revision': str(rev), 'reference': 'AF-001', **fields},
                       files={'file': (filename, content, 'application/octet-stream')})


def test_condition_typologies_use_static_route_and_preserve_scope_and_state(api, store):
    client, ids, _ = api
    factory, _, path, *_ = store
    with transaction(factory) as db:
        row = create_reference(db, ReferenceCreate(kind='typology', code='Étude_ß', label='Études'))
        db.add(ProjectProfile(project_id=ids['project'], typology_id=row['id']))
    before = capture_baseline(path)
    with operator_context(Operator('reader', 'reader', frozenset([ids['project']]))):
        response = client.get('/api/v1/deliverable-types/condition-typologies', params={'limit': 1})
        assert response.status_code == 200
        assert response.json()['items'][0]['condition_code'] == 'etude_ss'
    with operator_context(Operator('reader', 'reader', frozenset([ids['foreign']]))):
        assert client.get('/api/v1/deliverable-types/condition-typologies').json()['total'] == 0
    for query in ({'limit': 201}, {'offset': -1}, {'search': 'x' * 201}):
        assert client.get('/api/v1/deliverable-types/condition-typologies', params=query).status_code == 422
    assert capture_baseline(path) == before


def test_gate_page_reports_all_blockers_beyond_page_and_exact_publication_people(api, store):
    client, ids, root = api
    factory, _, path, *_ = store
    owner, gate = create(store)
    response = upload(client, root, owner, 2)
    assert response.status_code == 201, response.text
    version = response.json()['version_id']
    with transaction(factory) as db:
        commands.patch_deliverable(db, ids['project'], owner, DeliverablePatch(
            expected_revision=3, responsible_id=ids['person'], verifier_id=ids['person']))
        commands.create_check(db, ids['project'], owner, ChecklistCreate(
            expected_revision=4, code='other_gate', label='Second visa obligatoire', is_gate=True,
            milestone_id=ids['milestone']))
    before = capture_baseline(path)
    url = f"{root}/milestones/{ids['milestone']}/gates/page"
    with operator_context(Operator('reader', 'reader', frozenset({ids['project']}))):
        response = client.get(url, params={'limit': 1})
        assert response.status_code == 200, response.text
        page = response.json()
        assert page['total'] == page['blocking_total'] == page['checks_total'] == 2
        assert not page['can_validate'] and page['revision'] == 5
        assert len(page['items']) == 1 and page['items'][0]['id'] == gate
        item = page['items'][0]
        assert item['version'] == {'id': version, 'number': 1, 'filename': 'analyse.md', 'reference': 'AF-001'}
        assert item['responsible_id'] == item['verifier_id'] == ids['person']
        assert item['verifier_name'] and item['responsible_name']
        second = client.get(url, params={'offset': 1, 'limit': 1, 'include_ready': True}).json()
        assert second['items'][0]['id'] != gate and not second['can_validate']
        empty = client.get(url, params={'offset': 2, 'limit': 1}).json()
        assert empty['items'] == [] and empty['blocking_total'] == 2 and not empty['can_validate']
    assert capture_baseline(path) == before


def test_gate_page_bounds_scope_and_empty_version_do_not_write(api, store):
    client, ids, root = api
    _, _, path, *_ = store
    create(store)
    before = capture_baseline(path)
    url = f"{root}/milestones/{ids['milestone']}/gates/page"
    result = client.get(url).json()
    assert result['items'][0]['version'] is None
    assert result['items'][0]['reason'] == 'Publier une version avant le visa humain'
    with operator_context(Operator('reader', 'reader', frozenset({ids['foreign']}))):
        assert client.get(url).status_code == 404
    for query in ({'limit': 201}, {'limit': 0}, {'offset': -1}, {'offset': 1000001}):
        assert client.get(url, params=query).status_code == 422
    assert capture_baseline(path) == before


def test_paged_reads_do_not_create_plan_or_upgrade_historical_done_and_escape_search(api, store):
    client, ids, root = api
    factory, _, path, *_ = store
    with transaction(factory) as db:
        db.add_all([Deliverable(project_id=ids['project'], title='ÉTUDE 100%_A'),
                    Deliverable(project_id=ids['foreign'], title='ÉTUDE secrète')])
    before = capture_baseline(path)
    result = client.get(root, params={'limit': 1}).json()
    assert result['total'] == 2 and len(result['items']) == 1 and result['revision'] == 0
    exact = client.get(root, params={'search': 'etude 100%_a'}).json()
    assert exact['total'] == 1 and exact['items'][0]['title'] == 'ÉTUDE 100%_A'
    legacy = client.get(f"{root}/{ids['legacy']}").json()
    assert legacy['legacy_status'] == 'done' and legacy['document_status'] == 'draft' and legacy['latest_version_id'] is None
    assert client.get(root, params={'search': 'secrete'}).json()['total'] == 0
    assert capture_baseline(path) == before
    with factory() as db:
        assert db.query(DeliverablePlan).count() == 0


def test_page_batch_queries_stay_bounded_independently_of_deliverable_count(store):
    factory, ids, *_ = store
    with transaction(factory) as db:
        db.add_all([Deliverable(project_id=ids['project'], title=f'Lot {index:04d}') for index in range(120)])
    engine = factory.kw['bind']
    statements = []

    def observe(*args):
        statements.append(args[2])

    event.listen(engine, 'before_cursor_execute', observe)
    try:
        with factory() as db:
            result = reads.list_deliverables(db, ids['project'], limit=100)
    finally:
        event.remove(engine, 'before_cursor_execute', observe)
    assert result['total'] == 121 and len(result['items']) == 100
    assert len(statements) <= 9


def test_filters_and_checklist_progress_are_distinct_from_human_document_validation(api, store):
    client, ids, root = api
    factory, *_ = store
    owner, gate = create(store)
    with transaction(factory) as db:
        check = commands.create_check(db, ids['project'], owner, ChecklistCreate(expected_revision=revision(db, ids['project']),
            code='prep', label='Préparation', transverse=True))
        commands.patch_check(db, ids['project'], owner, check['item']['id'], ChecklistPatch(
            expected_revision=check['revision'], completed=True))
    result = client.get(root, params={'milestone_id': ids['milestone'], 'verifier_id': ids['person'], 'category': 'custom'}).json()
    assert result['total'] == 1
    assert result['items'][0]['transverse_progress']['percentage'] == 100
    assert result['items'][0]['progress']['percentage'] == 0 and result['items'][0]['document_status'] == 'draft'
    assert client.get(f'{root}/{owner}/checklist', params={'limit': 1}).json()['total'] == 2
    assert client.get(root, params={'milestone_id': ids['other']}).status_code == 404
    with transaction(factory) as db:
        commands.patch_deliverable(db, ids['project'], owner, DeliverablePatch(expected_revision=revision(db, ids['project']), active=False))
    assert client.get(root, params={'milestone_id': ids['milestone']}).json()['total'] == 0
    assert client.get(root, params={'milestone_id': ids['milestone'], 'include_inactive': True}).json()['total'] == 1


@pytest.mark.parametrize('query', [{'limit': 201}, {'offset': -1}, {'status': 'done'}, {'category': 'money'}, {'search': 'a' * 201}])
def test_http_bounds_refuse_invalid_queries(api, query):
    client, _, root = api
    assert client.get(root, params=query).status_code == 422


def test_upload_download_manifest_metadata_and_history_keep_original_bytes(api, store):
    client, ids, root = api
    owner, _ = create(store, with_gate=False)
    result = upload(client, root, owner, 1, filename='Analyse électricité.md', content=b'bytes exacts')
    assert result.status_code == 201, result.text
    identity = result.json()['version_id']
    prefix = f'{root}/{owner}/versions/{identity}'
    download = client.get(prefix + '/file')
    assert download.content == b'bytes exacts' and download.headers['content-type'] == 'application/octet-stream'
    assert 'UTF-8' in download.headers['content-disposition'] and download.headers['x-content-type-options'] == 'nosniff'
    manifest = client.get(prefix + '/manifest')
    detail = client.get(prefix).json()
    assert hashlib.sha256(manifest.content).hexdigest() == detail['manifest_sha256']
    assert detail['manifest']['reference'] == 'AF-001' and 'path' not in detail and 'storage_path' not in detail
    patch = client.patch(prefix, json={'expected_revision': 2, 'reference': 'AF-002', 'comment': 'Corrigé'})
    assert patch.status_code == 200 and patch.json()['revision'] == 3
    assert client.get(prefix).json()['reference'] == 'AF-002'
    assert client.get(prefix + '/manifest').content == manifest.content
    listed = client.get(f'{root}/{owner}/versions', params={'limit': 1}).json()
    assert listed['total'] == 1 and listed['items'][0]['filename'] == 'Analyse électricité.md'
    history = client.get(f'{root}/{owner}/history', params={'limit': 2}).json()
    assert history['total'] == 3 and len(history['items']) == 2
    event = client.get(f"{root}/{owner}/history/{history['items'][0]['id']}").json()
    assert event['value']['reference'] == 'AF-002' and event['previous']['reference'] == 'AF-001'


def test_missing_or_changed_bytes_refuse_download_but_preserve_manifest_inspection(api, store):
    client, _, root = api
    factory, *_ = store
    owner, _ = create(store, with_gate=False)
    identity = upload(client, root, owner, 1).json()['version_id']
    with factory() as db:
        path = commands.version_file_path(db, db.get(DeliverableFileVersion, identity))
    from pathlib import Path
    Path(path).write_bytes(b'changed')
    prefix = f'{root}/{owner}/versions/{identity}'
    assert client.get(prefix + '/file').status_code == 409
    assert client.get(prefix).status_code == client.get(prefix + '/manifest').status_code == 200


@pytest.mark.parametrize('filename', ['../escape.md', 'NUL.txt', 'COM1.txt', 'file.md ', 'a:b.md'])
def test_upload_invalid_filename_refuses_before_storage_or_database_write(api, store, filename):
    client, _, root = api
    _, _, path, *_ = store
    owner, _ = create(store, with_gate=False)
    before = capture_baseline(path)
    assert upload(client, root, owner, 1, filename=filename).status_code == 422
    assert not files.APP_DIR.exists() and capture_baseline(path) == before


def test_multipart_windows_filename_uses_basename_and_direct_service_rejects_raw_path(api, store):
    client, ids, root = api
    factory, *_ = store
    owner, _ = create(store, with_gate=False)
    with factory() as db, pytest.raises(HTTPException) as error:
        files.publish_upload(db, ids['project'], owner, FilePublication(expected_revision=1, reference='DOC'),
                             filename='C:\\escape.md', stream=io.BytesIO(b'private'))
    assert error.value.status_code == 422 and not files.APP_DIR.exists()
    response = upload(client, root, owner, 1, filename='C:\\fakepath\\document.md')
    assert response.status_code == 201  # Browser/parser strips the Windows path before the endpoint.
    identity = response.json()['version_id']
    assert client.get(f'{root}/{owner}/versions/{identity}').json()['filename'] == 'document.md'


def test_stale_and_reader_upload_refuse_before_storing_bytes(api, store):
    client, ids, root = api
    _, _, path, *_ = store
    owner, _ = create(store, with_gate=False)
    before = capture_baseline(path)
    assert upload(client, root, owner, 0).status_code == 409
    with operator_context(Operator('reader', 'reader', frozenset({ids['project']}))):
        assert upload(client, root, owner, 1).status_code == 403
        detail = client.get(f'{root}/{owner}').json()
        assert not detail['can_edit'] and not detail['can_verify']
    assert not files.APP_DIR.exists() and capture_baseline(path) == before


def test_size_cap_partial_copy_is_retained_without_version_or_revision(api, store, monkeypatch):
    client, _, root = api
    _, _, path, *_ = store
    owner, _ = create(store, with_gate=False)
    before = capture_baseline(path)
    monkeypatch.setattr(files, 'MAX_FILE_BYTES', 5)
    assert upload(client, root, owner, 1, content=b'too large').status_code == 413
    assert capture_baseline(path) == before
    assert list(files.APP_DIR.rglob('analyse.md'))  # Failed storage retained, no data purge.


def test_network_link_copy_is_frozen_and_other_project_links_are_refused(api, store):
    client, ids, root = api
    factory, _, path, *_ = store
    network = path.parent / 'network'
    network.mkdir()
    source = network / 'document.md'
    source.write_bytes(b'reseau version originale')
    with transaction(factory) as db:
        own = NetworkLink(project_id=ids['project'], code='docs', libelle='Documents', chemin=str(network))
        foreign = NetworkLink(project_id=ids['foreign'], code='docs', libelle='Autre', chemin=str(network))
        db.add_all([own, foreign])
        db.flush()
        own_id, foreign_id = own.id, foreign.id
    owner, _ = create(store, with_gate=False)
    payload = {'expected_revision': 1, 'reference': 'DOC', 'relative_path': 'document.md', 'link_id': foreign_id}
    assert client.post(f'{root}/{owner}/versions/network', json=payload).status_code == 404
    assert not files.APP_DIR.exists()
    payload['link_id'] = own_id
    response = client.post(f'{root}/{owner}/versions/network', json=payload)
    assert response.status_code == 201, response.text
    source.write_bytes(b'reseau modifie ensuite')
    identity = response.json()['version_id']
    assert client.get(f'{root}/{owner}/versions/{identity}/file').content == b'reseau version originale'


@pytest.mark.parametrize('relative_path', ['../document.md', '/document.md', 'C:\\document.md', '\\host\\file', 'sub/../../file', 'doc:stream'])
def test_network_escapes_refuse_without_files_or_rows(api, store, relative_path):
    client, ids, root = api
    factory, _, path, *_ = store
    with transaction(factory) as db:
        link = NetworkLink(project_id=ids['project'], code='docs', libelle='Documents', chemin=str(path.parent))
        db.add(link)
        db.flush()
        link_id = link.id
    owner, _ = create(store, with_gate=False)
    before = capture_baseline(path)
    response = client.post(f'{root}/{owner}/versions/network', json={'expected_revision': 1, 'reference': 'DOC',
                            'link_id': link_id, 'relative_path': relative_path})
    assert response.status_code == 422
    assert capture_baseline(path) == before and not files.APP_DIR.exists()


def test_exact_file_network_link_cannot_authorize_its_parent_directory(api, store):
    client, ids, root = api
    factory, _, path, *_ = store
    source = path.parent / 'own.md'
    source.write_bytes(b'own')
    sibling = path.parent / 'other.md'
    sibling.write_bytes(b'private')
    with transaction(factory) as db:
        link = NetworkLink(project_id=ids['project'], code='docs', libelle='Un fichier', chemin=str(source))
        db.add(link)
        db.flush()
        link_id = link.id
    owner, _ = create(store, with_gate=False)
    payload = {'expected_revision': 1, 'reference': 'DOC', 'link_id': link_id, 'relative_path': 'other.md'}
    assert client.post(f'{root}/{owner}/versions/network', json=payload).status_code == 403
    assert not files.APP_DIR.exists()
    payload['relative_path'] = ''
    assert client.post(f'{root}/{owner}/versions/network', json=payload).status_code == 201


def test_publication_respects_the_configured_project_directory(api, store, monkeypatch):
    client, ids, root = api
    factory, _, path, *_ = store
    clients = path.parent / 'clients'
    own = clients / ids['project']
    other = clients / ids['foreign']
    for directory in (own, other):
        directory.mkdir(parents=True)
        (directory / 'document.md').write_bytes(b'Fichier fictif')
    monkeypatch.setenv('AGENT_DOCUMENT_ROOTS', '[]')
    monkeypatch.setenv('AGENT_DOCUMENT_PROJECT_ROOT', json.dumps(str(clients)))
    with transaction(factory) as db:
        links = [NetworkLink(project_id=ids['project'], code=code, libelle='Dossier', chemin=str(directory))
                 for code, directory in (('local', own), ('autre', other))]
        db.add_all(links)
        db.flush()
        local, excluded = (link.id for link in links)
    owner, _ = create(store, with_gate=False)
    url = f'{root}/{owner}/versions/network'
    payload = {'expected_revision': 1, 'reference': 'REC', 'relative_path': 'document.md'}
    before = capture_baseline(path)
    with operator_context(Operator('editeur', 'editor', frozenset({ids['project']}))):
        assert client.post(url, json={**payload, 'link_id': excluded}).status_code == 403
        assert not files.APP_DIR.exists() and capture_baseline(path) == before
        response = client.post(url, json={**payload, 'link_id': local})
        assert response.status_code == 201, response.text


def test_cdc_link_preserves_original_delivery_without_regeneration(api, store):
    client, ids, root = api
    factory, *_ = store
    files.APP_DIR.mkdir()
    original = files.APP_DIR / 'cdc.md'
    original.write_bytes(b'CDC original')
    with transaction(factory) as db:
        delivery = DeliveryVersion(project_id=ids['project'], kind='transfer-be', version=1, draft=False,
            path=str(original), sha256=hashlib.sha256(original.read_bytes()).hexdigest(), snapshot={})
        db.add(delivery)
        db.flush()
        source_id = delivery.id
    owner, _ = create(store, with_gate=False)
    response = client.post(f'{root}/{owner}/versions/cdc', json={'expected_revision': 1, 'reference': 'CDC', 'source_delivery_id': source_id})
    assert response.status_code == 201, response.text
    identity = response.json()['version_id']
    with factory() as db:
        assert db.query(DeliveryVersion).count() == 1
        assert db.get(DeliverableFileVersion, identity).path == str(original.resolve())
    detail = client.get(f'{root}/{owner}/versions/{identity}').json()
    assert detail['generated'] and detail['source_delivery_id'] == source_id
    assert client.get(f'{root}/{owner}').json()['document_status'] == 'draft'


def test_cross_project_scope_and_nested_owner_mismatches_refuse_every_read_and_write(api, store):
    client, ids, root = api
    owner, _ = create(store, with_gate=False)
    identity = upload(client, root, owner, 1).json()['version_id']
    with operator_context(Operator('limited', 'editor', frozenset({ids['foreign']}))):
        for path in [root, f'{root}/{owner}', f'{root}/{owner}/versions', f'{root}/{owner}/versions/{identity}/file',
                     f'{root}/{owner}/versions/{identity}/manifest', f'{root}/{owner}/history', f'{root}/{owner}/checklist']:
            assert client.get(path).status_code == 404
        with store[0]() as db, pytest.raises(HTTPException) as error:
            reads.list_deliverables(db, ids['project'])
        assert error.value.status_code == 404
    assert client.get(f"{root}/{ids['legacy']}/versions/{identity}").status_code == 404
    assert client.get(f"{root}/{ids['legacy']}/versions/{identity}/file").status_code == 404


def test_http_gate_visa_latest_version_transition_and_failed_commands_rollback(api, store):
    client, ids, root = api
    factory, _, path, *_ = store
    owner, gate = create(store)
    published = upload(client, root, owner, 2).json()
    payload = {'expected_revision': 3, 'status': 'to_verify', 'version_id': published['version_id']}
    assert client.post(f'{root}/{owner}/transition', json=payload).status_code == 200
    before = capture_baseline(path)
    payload.update(expected_revision=4, status='validated', comment='Visa humain')
    assert client.post(f'{root}/{owner}/transition', json=payload).status_code == 409
    assert capture_baseline(path) == before
    check = client.patch(f'{root}/{owner}/checklist/{gate}', json={'expected_revision': 4, 'completed': True, 'proof': 'Relu'})
    assert check.status_code == 200, check.text
    payload['expected_revision'] = 5
    assert client.post(f'{root}/{owner}/transition', json=payload).json()['document_status'] == 'validated'
    assert upload(client, root, owner, 6).status_code == 201
    with factory() as db:
        assert not db.get(DeliverableChecklistItem, gate).completed
    payload.update(expected_revision=7, status='to_verify')
    assert client.post(f'{root}/{owner}/transition', json=payload).status_code == 409  # Former bytes cannot be submitted.


def test_catalogue_http_versions_selection_preview_reader_and_reference_permissions(api, store):
    client, ids, root = api
    factory, _, path, *_ = store
    assert client.get('/api/v1/deliverable-types/standard-definition').status_code == 200
    head = client.post('/api/v1/deliverable-types', json={'code': 'af', 'label': 'Analyse', 'definition': {'checklist': []}})
    assert head.status_code == 201, head.text
    head = head.json()
    assert client.get('/api/v1/deliverable-types').json()['total'] == 1
    assert client.get(f"/api/v1/deliverable-types/{head['id']}/versions/{head['version_id']}").json()['number'] == 1
    preview = {'expected_revision': 0, 'type_version_ids': [head['version_id']]}
    with operator_context(Operator('reader', 'reader', frozenset({ids['project']}))):
        response = client.post(root + '/selection/preview', json=preview)
        assert response.status_code == 200, response.text
        assert client.get('/api/v1/deliverable-types').status_code == 200
        assert client.post('/api/v1/deliverable-types', json={'code': 'ar', 'label': 'AR', 'definition': {}}).status_code == 403
    with transaction(factory) as db:
        typology = create_reference(db, ReferenceCreate(kind='typology', code='T', label='Typologie'))
        db.add(ProjectProfile(project_id=ids['project'], typology_id=typology['id']))
    composition = f"/api/v1/project-references/{typology['id']}/deliverable-types"
    assert client.patch(composition, json={'expected_revision': 1, 'type_ids': [head['id']]}).status_code == 200
    with operator_context(Operator('editor', 'editor', frozenset({ids['foreign']}))):
        assert client.get(composition).status_code == 404
    before = capture_baseline(path)
    bad = client.post(root + '/selection/apply', json={**preview, 'expected_preview_sha256': '0' * 64})
    assert bad.status_code == 409 and capture_baseline(path) == before


def test_network_service_enforces_reader_policy_without_http(api, store):
    factory, ids, *_ = store
    owner, _ = create(store, with_gate=False)
    with operator_context(Operator('reader', 'reader')), factory() as db, pytest.raises(HTTPException) as error:
        files.publish_upload(db, ids['project'], owner, FilePublication(expected_revision=1, reference='DOC'),
                             filename='document.md', stream=io.BytesIO(b'private'))
    assert error.value.status_code == 403 and not files.APP_DIR.exists()


@pytest.mark.parametrize('mode', ['missing', 'outside'])
def test_relocated_read_path_missing_or_outside_managed_roots_preserves_recorded_proof(api, store, mode):
    client, _, root = api
    factory, _, path, *_ = store
    owner, _ = create(store, with_gate=False)
    identity = upload(client, root, owner, 1).json()['version_id']
    with transaction(factory) as db:
        metadata = db.get(DeliverableVersionMetadata, identity)
        original = metadata.storage_path
        outside = path.parent / 'unmanaged.md'
        if mode == 'outside':
            outside.write_bytes(b'Version exacte')
        metadata.storage_path = str(outside)
    prefix = f'{root}/{owner}/versions/{identity}'
    assert client.get(prefix + '/file').status_code == 409
    assert client.get(prefix + '/manifest').status_code == 200
    with factory() as db:
        assert db.get(DeliverableFileVersion, identity).path == original


def test_source_mutation_during_network_acquisition_never_publishes(api, store, monkeypatch):
    client, ids, root = api
    factory, _, path, *_ = store
    source = path.parent / 'source.md'
    source.write_bytes(b'original')
    with transaction(factory) as db:
        link = NetworkLink(project_id=ids['project'], code='docs', libelle='Document', chemin=str(source))
        db.add(link)
        db.flush()
        link_id = link.id
    owner, _ = create(store, with_gate=False)
    before = capture_baseline(path)
    handle_path = document_file_access._handle_path

    def mutate(stream):
        opened = handle_path(stream)
        source.write_bytes(b'now a different length')
        return opened

    monkeypatch.setattr(document_file_access, '_handle_path', mutate)
    response = client.post(f'{root}/{owner}/versions/network', json={'expected_revision': 1,
        'reference': 'DOC', 'link_id': link_id})
    assert response.status_code == 409 and capture_baseline(path) == before
    assert not files.APP_DIR.exists()


def test_positive_preview_apply_and_catalogue_publish_keep_exact_previous_definition(api, store):
    client, _, root = api
    head = client.post('/api/v1/deliverable-types', json={'code': 'af', 'label': 'Analyse', 'definition': {'checklist': []}}).json()
    old_prefix = f"/api/v1/deliverable-types/{head['id']}/versions/{head['version_id']}"
    original = client.get(old_prefix).json()
    published = client.post(f"/api/v1/deliverable-types/{head['id']}/versions", json={
        'expected_revision': 1, 'definition': {'category': 'fabrication', 'checklist': [{'code': 'prep', 'label': 'Préparation'}]}})
    assert published.status_code == 201, published.text
    payload = {'expected_revision': 0, 'type_version_ids': [head['version_id']]}
    preview = client.post(root + '/selection/preview', json=payload).json()
    response = client.post(root + '/selection/apply', json={**payload, 'expected_preview_sha256': preview['sha256']})
    assert response.status_code == 200, response.text
    assert client.get(old_prefix).json() == original
    selected = client.get(root, params={'category': 'studies'}).json()
    assert selected['total'] == 1 and selected['items'][0]['type_version_id'] == head['version_id']
    assert client.get(f"/api/v1/deliverable-types/{head['id']}/versions").json()['total'] == 2


def test_managed_storage_junction_cannot_redirect_an_upload_outside_agent_home(api, store):
    import os
    import subprocess
    client, _, root = api
    _, _, path, *_ = store
    files.APP_DIR.mkdir()
    outside = path.parent / 'outside-home'
    outside.mkdir()
    redirected = files.APP_DIR / 'deliverable-files'
    if os.name == 'nt':
        # A junction works without granting Windows symlink privileges.
        quoted_path = "'" + str(redirected).replace("'", "''") + "'"
        quoted_target = "'" + str(outside).replace("'", "''") + "'"
        subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
            f'New-Item -ItemType Junction -Path {quoted_path} -Value {quoted_target} -ErrorAction Stop'],
            check=True, capture_output=True)
    else:
        redirected.symlink_to(outside, target_is_directory=True)
    owner, _ = create(store, with_gate=False)
    before = capture_baseline(path)
    assert upload(client, root, owner, 1).status_code == 409
    assert list(outside.iterdir()) == [] and capture_baseline(path) == before
