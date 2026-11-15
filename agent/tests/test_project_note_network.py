"""Real Windows handles on fictional note links, no source or canonical writes."""
from copy import deepcopy
import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest
from sqlalchemy import select

from backend.app.models import NetworkLink, Project
from backend.app.db import get_db
from backend.app.project_note_models import ProjectNote, NoteVersion
from backend.app.project_note_import_schemas import SourceDescriptor, NoteImportCommand
from backend.app.services import project_note_imports as imports, project_note_files as managed
from backend.app.services.project_note_source_preview import preview_source
from backend.app.services.project_operator import Operator, operator_context
from tests import test_project_notes_core as core
from tests.test_project_note_source_preview import sources, KEY, encoded

from backend.app.services import project_note_network as network
from backend.app.routers import project_note_network as http_service
store = core.store


@pytest.fixture
def linked(store, tmp_path):
    engine, factory, ids, _ = store
    NetworkLink.__table__.create(engine)
    root = tmp_path / 'read-authorized'
    root.mkdir()
    folders = [root / 'project-A', root / 'project-B']
    for folder in folders:
        folder.mkdir()
        for name, data in sources().items():
            path = folder / 'notes' / 'note-selected' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        (folder / 'notes' / 'other-note.html').write_bytes(b'<p>Other unrelated note</p>')
        (folder / 'legacy.txt').write_bytes(b'Legacy original')
        (folder / 'Office.docx').write_bytes(b'Opaque Office original')
    with factory() as db:
        links = [NetworkLink(project_id=pid, code='affaire', libelle='Dossier', chemin=str(folder))
                 for pid, folder in zip(ids, folders)]
        db.add_all(links)
        db.commit()
        link_ids = [link.id for link in links]
    return store, root, folders, link_ids, network.access.FilePolicy((str(root),))


def descriptor(linked, path='notes/note-selected'):
    return SourceDescriptor(kind='project_link', link_id=linked[3][0], relative_path=path)


def acquire(linked, path='notes/note-selected', **kwargs):
    store, _, _, _, policy = linked
    with store[1]() as db:
        return network.acquire_note(db, store[2][0], descriptor(linked, path), policy=policy, **kwargs)


def test_complete_single_note_acquisition_preserves_all_files_and_database(linked):
    store, root, _, _, _ = linked
    before = {path: path.read_bytes() for path in root.rglob('*') if path.is_file()}
    assert acquire(linked) == sources()
    with store[1]() as db:
        assert len(db.scalars(select(Project)).all()) == 2
        assert len(db.scalars(select(NetworkLink)).all()) == 2
        assert not db.new and not db.dirty and not db.deleted
    assert before == {path: path.read_bytes() for path in root.rglob('*') if path.is_file()}


@pytest.mark.parametrize('path, name, expected', [
    ('legacy.txt', 'legacy.txt', b'Legacy original'),
    ('Office.docx', 'Office.docx', b'Opaque Office original'),
    ('notes/other-note.html', 'other-note.html', b'<p>Other unrelated note</p>')])
def test_explicit_legacy_or_office_file_only_no_sibling_note(linked, path, name, expected):
    assert acquire(linked, path) == {name: expected}


def test_explicit_file_link_allows_only_itself(linked):
    store, _, folders, link_ids, policy = linked
    with store[1]() as db:
        link = db.get(NetworkLink, link_ids[0])
        link.chemin = str(folders[0] / 'legacy.txt')
        db.commit()
        for relative in ('', 'legacy.txt'):
            assert network.acquire_note(db, store[2][0], descriptor(linked, relative), policy=policy) == {'legacy.txt': b'Legacy original'}
        core.error(403, lambda: network.acquire_note(db, store[2][0], descriptor(linked, 'Office.docx'), policy=policy))


def test_reader_foreign_scope_and_link_denied_before_configuration_or_files(linked, monkeypatch):
    store, _, _, links, policy = linked
    def forbidden(*args, **kwargs):
        pytest.fail('No filesystem or configuration before project/link authorization')
    monkeypatch.setattr(Path, 'resolve', forbidden)
    monkeypatch.setattr(network.access, 'configured_policy', forbidden)
    with store[1]() as db:
        with operator_context(Operator('reader', 'reader')):
            core.error(403, lambda: network.acquire_note(db, store[2][0], descriptor(linked), policy=policy))
        with operator_context(Operator('scoped', 'editor', frozenset({store[2][0]}))):
            core.error(404, lambda: network.acquire_note(db, store[2][1], descriptor(linked), policy=policy))
        core.error(404, lambda: network.acquire_note(db, store[2][0], SourceDescriptor(kind='project_link', link_id=links[1]), policy=policy))


def test_no_implicit_root_and_policy_before_any_directory_listing(linked, monkeypatch):
    store, _, _, _, _ = linked
    monkeypatch.setattr(network, '_directory', lambda *args: pytest.fail('No implicit namespace acquisition'))
    monkeypatch.setattr(network.os, 'scandir', lambda *args: pytest.fail('No directory enumeration'))
    with store[1]() as db:
        core.error(409, lambda: network.acquire_note(db, store[2][0], descriptor(linked), policy=network.access.FilePolicy(())))


def test_link_outside_allowed_roots_refused_before_filesystem_probe(linked, monkeypatch):
    store, root, _, _, _ = linked
    policy = network.access.FilePolicy((str(root / 'other'),))
    monkeypatch.setattr(Path, 'resolve', lambda *args, **kwargs: pytest.fail('Forbidden namespace must not be probed'))
    with store[1]() as db:
        core.error(403, lambda: network.acquire_note(db, store[2][0], descriptor(linked), policy=policy))


@pytest.mark.parametrize('path', ['../project-B', 'V:/secret', '/absolute', 'notes/../other', 'notes\\other', 'a:stream'])
def test_source_descriptor_rejects_absolute_escape_and_ambiguous_paths(path):
    with pytest.raises(ValidationError):
        SourceDescriptor(kind='project_link', link_id=core.command(), relative_path=path)


def test_choosing_project_or_parent_notes_folder_does_not_discover_other_notes(linked):
    for path in ('', 'notes'):
        with pytest.raises(HTTPException) as caught:
            acquire(linked, path)
        assert caught.value.status_code == 422


@pytest.mark.parametrize('unexpected', ['unknown.txt', 'subfolder/extra.txt', 'attachments/child/extra.txt', f'versions/{KEY}/manifest.json'])
def test_unknown_note_entries_block_selection_not_silent_omission(linked, unexpected):
    path = linked[2][0] / 'notes' / 'note-selected' / unexpected
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'Original unexpected entry')
    with pytest.raises(HTTPException) as caught:
        acquire(linked)
    assert caught.value.status_code in {403, 422}
    assert path.read_bytes() == b'Original unexpected entry'


def test_empty_html_and_text_remain_exact_original_files(linked):
    folder = linked[2][0] / 'notes' / 'note-selected'
    (folder / 'content.html').write_bytes(b'')
    (folder / 'content.txt').write_bytes(b'')
    result = acquire(linked)
    assert result['content.html'] == result['content.txt'] == b''
    assert len(result) == len(sources())


def test_empty_historic_folder_is_not_omitted(linked):
    (linked[2][0] / 'notes' / 'note-selected' / 'versions' / '20261008T101112123456Z').mkdir()
    with pytest.raises(HTTPException) as caught:
        acquire(linked)
    assert caught.value.status_code == 422


@pytest.mark.parametrize('maximum', ['entries', 'directories'])
def test_bounded_enumeration_returns_no_partial_data_and_reads_no_file(linked, maximum, monkeypatch):
    limits = network.ReadLimits(**{maximum: 1})
    monkeypatch.setattr(network, '_read', lambda *args: pytest.fail('Bounds should stop before any file read'))
    with pytest.raises(HTTPException) as caught:
        acquire(linked, limits=limits)
    assert caught.value.status_code == 413


def test_time_limit_aborts_without_returning_partial_selection(linked, monkeypatch):
    ticks = iter([0, 21])
    monkeypatch.setattr(network.time, 'monotonic', lambda: next(ticks))
    with pytest.raises(HTTPException) as caught:
        acquire(linked)
    assert caught.value.status_code == 408


def test_oversize_file_refused_from_metadata_before_read(linked, monkeypatch):
    path = linked[2][0] / 'notes' / 'note-selected' / 'content.txt'
    path.write_bytes(b'x' * 2_000_001)
    monkeypatch.setattr(network, '_read', lambda *args: pytest.fail('No oversized read'))
    with pytest.raises(HTTPException) as caught:
        acquire(linked)
    assert caught.value.status_code == 413


def test_file_changed_after_its_read_but_before_end_of_selection_is_detected(linked, monkeypatch):
    original_read = network._read
    prior = []
    def changed(path, metadata, check):
        data = original_read(path, metadata, check)
        if prior:
            prior[0].write_bytes(b'Different after first successful read')
        prior.append(path)
        return data
    monkeypatch.setattr(network, '_read', changed)
    with pytest.raises(HTTPException) as caught:
        acquire(linked)
    assert caught.value.status_code == 409


def test_actual_file_handle_must_match_selected_path(linked, monkeypatch):
    monkeypatch.setattr(network.access, '_handle_path', lambda _: linked[2][1] / 'outside.txt')
    with pytest.raises(HTTPException) as caught:
        acquire(linked, 'legacy.txt')
    assert caught.value.status_code == 409


def test_missing_link_and_missing_selected_note_have_distinct_results(linked):
    store, _, _, links, policy = linked
    with pytest.raises(HTTPException) as caught:
        acquire(linked, 'missing.txt')
    assert caught.value.status_code == 404
    with store[1]() as db:
        db.get(NetworkLink, links[0]).chemin += '-unavailable'
        db.commit()
        core.error(409, lambda: network.acquire_note(db, store[2][0], descriptor(linked), policy=policy))


def test_drive_mapping_reuses_server_policy_and_project_namespace(linked):
    store, root, _, links, _ = linked
    policy = network.access.FilePolicy((str(root),), (('V:', str(root)),))
    with store[1]() as db:
        db.get(NetworkLink, links[0]).chemin = 'V:\\project-A'
        db.commit()
        assert network.acquire_note(db, store[2][0], descriptor(linked), policy=policy) == sources()


def test_native_windows_junction_child_refused_even_when_pointing_inside_allowed_root(linked):
    if os.name != 'nt':
        pytest.skip('Windows junction qualification')
    import subprocess
    root, folders = linked[1], linked[2]
    junction = folders[0] / 'redirect-note'
    result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(junction), str(folders[1] / 'notes' / 'note-selected')],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    with pytest.raises(HTTPException) as caught:
        acquire(linked, 'redirect-note')
    assert caught.value.status_code == 403
    assert junction.is_junction() and junction.resolve().is_relative_to(root)
    # No deletion of either link or target; retained in the fictional test tree.


def test_prepared_network_adapter_composes_with_actual_immutable_import_and_retry(linked, tmp_path, monkeypatch):
    store, root, _, _, policy = linked
    core.install(store)
    destination = tmp_path / 'managed-network'
    destination.mkdir()
    monkeypatch.setattr(managed, 'APP_DIR', destination)
    before = {path: path.read_bytes() for path in root.rglob('*') if path.is_file()}
    descriptor_value = descriptor(linked)
    with store[1]() as db:
        selected = network.acquire_note(db, store[2][0], descriptor_value, policy=policy)
        note_id = core.command()
        preview = preview_source(selected, planned_note_id=note_id)
        payload = NoteImportCommand(command_id=core.command(), planned_note_id=note_id,
            expected_preview_sha256=preview['preview_sha256'], source=descriptor_value)
        first = imports.import_selected(db, store[2][0], payload,
            acquire=lambda origin: network.acquire_note(db, store[2][0], origin, policy=policy))
        db.commit()
        assert first['note']['revision'] == 2 and first['note']['plain_text'] == 'Actuel'
        replay = imports.import_selected(db, store[2][0], payload,
            acquire=lambda _: pytest.fail('No repeated network acquisition after committed receipt'))
        assert replay['replayed'] and len(db.scalars(select(NoteVersion)).all()) == 2
        assert len(db.scalars(select(ProjectNote)).all()) == 1
        assert imports.original_file(db, store[2][0], note_id, 'manifest.json')[0] == selected['manifest.json']
    assert before == {path: path.read_bytes() for path in root.rglob('*') if path.is_file()}


def test_changed_source_after_network_preview_blocks_actual_import_and_no_managed_copy(linked, tmp_path, monkeypatch):
    store, _, folders, _, policy = linked
    core.install(store)
    destination = tmp_path / 'managed-stale-network'
    destination.mkdir()
    monkeypatch.setattr(managed, 'APP_DIR', destination)
    with store[1]() as db:
        selected = network.acquire_note(db, store[2][0], descriptor(linked), policy=policy)
        note_id = core.command()
        preview = preview_source(selected, planned_note_id=note_id)
        payload = NoteImportCommand(command_id=core.command(), planned_note_id=note_id,
            expected_preview_sha256=preview['preview_sha256'], source=descriptor(linked))
        (folders[0] / 'notes' / 'note-selected' / 'content.html').write_bytes(b'<p>Changed after preview</p>')
        core.error(422, lambda: imports.import_selected(db, store[2][0], payload,
            acquire=lambda origin: network.acquire_note(db, store[2][0], origin, policy=policy)))
        db.rollback()
        assert db.scalar(select(ProjectNote.id)) is None
    assert not list(destination.iterdir())


def test_incomplete_source_history_preview_blocks_import_without_source_loss(linked):
    folder = linked[2][0] / 'notes' / 'note-selected'
    manifest = json.loads((folder / 'manifest.json').read_bytes())
    manifest['version'] = 3
    (folder / 'manifest.json').write_bytes(encoded(manifest))
    selected = acquire(linked)
    with pytest.raises(ValueError, match='Historique source incomplet'):
        preview_source(selected, planned_note_id=core.command())
    assert selected == deepcopy({name: (folder / name).read_bytes() for name in sources()})


@pytest.fixture
def http(linked, tmp_path, monkeypatch):
    store, root, _, _, _ = linked
    core.install(store)
    destination = tmp_path / 'managed-network-http'
    destination.mkdir()
    monkeypatch.setattr(managed, 'APP_DIR', destination)
    monkeypatch.setenv('AGENT_DOCUMENT_ROOTS', json.dumps([str(root)]))
    app = FastAPI()
    app.include_router(http_service.router)
    def database():
        with store[1]() as db:
            yield db
    app.dependency_overrides[get_db] = database
    with TestClient(app) as client:
        yield client, linked, destination


def http_payload(linked):
    return {'planned_note_id': core.command(), 'source': descriptor(linked).model_dump(mode='json')}


def test_http_network_preview_import_and_committed_retry_after_share_configuration_unavailable(http, monkeypatch):
    client, linked, _ = http
    base = '/api/v1/projects/' + linked[0][2][0] + '/notes/imports/network'
    payload = http_payload(linked)
    preview = client.post(base + '/preview', json=payload)
    assert preview.status_code == 200 and preview.json()['can_apply']
    assert len(preview.json()['versions']) == 2
    command = {**payload, 'command_id': core.command(), 'expected_preview_sha256': preview.json()['preview_sha256']}
    first = client.post(base, json=command)
    assert first.status_code == 201 and first.json()['note']['revision'] == 2
    monkeypatch.setenv('AGENT_DOCUMENT_ROOTS', '[]')
    monkeypatch.setattr(http_service, 'acquire_note', lambda *args, **kwargs: pytest.fail('Committed retry must not probe network'))
    replay = client.post(base, json=command)
    assert replay.status_code == 201 and replay.json()['replayed']
    assert replay.json()['import_id'] == first.json()['import_id']


@pytest.mark.parametrize('extra', [{'actor_id': 'forged'}, {'role': 'owner'}, {'absolute_path': 'V:/secret'}, {'policy': {'roots': ['V:/']}}])
def test_http_network_request_does_not_grant_authority_or_roots(http, extra):
    client, linked, destination = http
    base = '/api/v1/projects/' + linked[0][2][0] + '/notes/imports/network'
    payload = {**http_payload(linked), **extra}
    assert client.post(base + '/preview', json=payload).status_code == 422
    assert client.post(base, json={**payload, 'command_id': core.command(), 'expected_preview_sha256': 'a' * 64}).status_code == 422
    assert not list(destination.iterdir())


def test_http_reader_denied_before_network_calls(http, monkeypatch):
    client, linked, destination = http
    base = '/api/v1/projects/' + linked[0][2][0] + '/notes/imports/network'
    payload = http_payload(linked)
    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'reader')
    monkeypatch.setattr(http_service, 'acquire_note', lambda *args: pytest.fail('No network call for reader'))
    assert client.post(base + '/preview', json=payload).status_code == 403
    assert client.post(base, json={**payload, 'command_id': core.command(), 'expected_preview_sha256': 'a' * 64}).status_code == 403
    assert not list(destination.iterdir())


def test_http_foreign_project_link_refused_before_policy_or_filesystem(http, monkeypatch):
    client, linked, destination = http
    base = '/api/v1/projects/' + linked[0][2][0] + '/notes/imports/network'
    payload = http_payload(linked)
    payload['source']['link_id'] = linked[3][1]
    monkeypatch.setattr(network.access, 'configured_policy', lambda: pytest.fail('No policy/IO for foreign link'))
    assert client.post(base + '/preview', json=payload).status_code == 404
    assert client.post(base, json={**payload, 'command_id': core.command(), 'expected_preview_sha256': 'a' * 64}).status_code == 404
    assert not list(destination.iterdir())


def test_http_changed_network_source_refused_without_managed_writes(http):
    client, linked, destination = http
    base = '/api/v1/projects/' + linked[0][2][0] + '/notes/imports/network'
    payload = http_payload(linked)
    preview = client.post(base + '/preview', json=payload)
    assert preview.status_code == 200
    (linked[2][0] / 'notes' / 'note-selected' / 'content.html').write_bytes(b'<p>Changed after preview</p>')
    command = {**payload, 'command_id': core.command(), 'expected_preview_sha256': preview.json()['preview_sha256']}
    assert client.post(base, json=command).status_code == 422
    assert not list(destination.iterdir())


def test_http_source_descriptor_requires_relative_project_link(http):
    client, linked, destination = http
    base = '/api/v1/projects/' + linked[0][2][0] + '/notes/imports/network'
    payload = http_payload(linked)
    for source in ({'kind': 'upload'}, {'kind': 'project_link', 'link_id': linked[3][0], 'relative_path': 'V:/secret'},
                   {'kind': 'project_link', 'link_id': linked[3][0], 'roots': ['V:/']}):
        assert client.post(base + '/preview', json={**payload, 'source': source}).status_code == 422
    assert not list(destination.iterdir())


def test_source_file_changed_while_parent_held_no_false_stable_selection(linked, monkeypatch):
    original_read = network._read
    mutated = False
    def changed(path, metadata, check):
        nonlocal mutated
        if not mutated:
            data = original_read(path, metadata, check)
            path.write_bytes(b'Changed before complete selection ends')
            mutated = True
            return data
        return original_read(path, metadata, check)
    monkeypatch.setattr(network, '_read', changed)
    with pytest.raises(HTTPException) as caught:
        acquire(linked)
    assert caught.value.status_code == 409


def test_source_directory_changed_during_reads_rejected(linked, monkeypatch):
    original_read = network._read
    folder = linked[2][0] / 'notes' / 'note-selected'
    mutated = False
    def changed(path, metadata, check):
        nonlocal mutated
        data = original_read(path, metadata, check)
        if not mutated:
            (folder / 'new-original.txt').write_bytes(b'New source element')
            before = folder.lstat()
            os.utime(folder, ns=(before.st_atime_ns, before.st_mtime_ns + 1_000_000_000))
            mutated = True
        return data
    monkeypatch.setattr(network, '_read', changed)
    with pytest.raises(HTTPException) as caught:
        acquire(linked)
    assert caught.value.status_code == 409


def test_attachment_count_preflight_limits_without_reading_partial_content(linked, monkeypatch):
    folder = linked[2][0] / 'notes' / 'note-selected' / 'attachments'
    for index in range(20):
        (folder / f'piece-{index}.txt').write_bytes(b'Original')
    monkeypatch.setattr(network, '_read', lambda *args: pytest.fail('Quotas must be checked before body reads'))
    with pytest.raises(HTTPException) as caught:
        acquire(linked)
    assert caught.value.status_code == 413


def test_total_source_bytes_preflight_without_partial_read(linked, monkeypatch):
    folder = linked[2][0] / 'notes' / 'note-selected'
    for path, size in ((folder / 'content.html', 49 * 1024 * 1024),
                       (folder / 'versions' / KEY / 'content.html', 2 * 1024 * 1024)):
        with path.open('wb') as output:
            output.truncate(size)
    monkeypatch.setattr(network, '_read', lambda *args: pytest.fail('Total bytes bound must be checked before body reads'))
    with pytest.raises(HTTPException) as caught:
        acquire(linked)
    assert caught.value.status_code == 413
