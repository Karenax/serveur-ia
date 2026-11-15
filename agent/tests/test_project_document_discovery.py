"""Scoped discovery on real Windows directories; source contents are not read."""
import os
from pathlib import Path
import subprocess
import sys

from fastapi import HTTPException
import pytest

from backend.app.models import NetworkLink
from backend.app.services import document_discovery as discovery
from backend.app.services import document_file_access as files
from backend.app.services.document_template_catalogue import catalogue, document_spec
from backend.app.services.migration_guard import capture_baseline
from backend.app.services.project_operator import Operator, operator_context
from tests.test_project_document_files import store as store
from tests.test_project_document_api import api as api


def make_template(store, filename='Fiche demande déclaration CE V10.docx', folders=('04 - Qualité', '06 - CE')):
    path = store[3][0].joinpath(*folders, filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'Observation de fichier, sans lecture Office')
    return path


def scan(store, **changes):
    factory, ids, links, _, policy = store
    with factory() as db:
        return discovery.discover(db, ids[0], link_id=links[0], document_id='ce_request', policy=policy, **changes)


def test_real_handle_scope_source_preservation_candidates_and_explanations(store, monkeypatch):
    path = make_template(store)
    before = capture_baseline(store[0].kw['bind'].url.database)
    original = {p: p.read_bytes() for folder in store[3] for p in folder.rglob('*') if p.is_file()}
    monkeypatch.setattr(Path, 'open', lambda *a, **k: pytest.fail('Discovery opened a source file'))
    with operator_context(Operator('reader', 'reader', frozenset({store[1][0]}))):
        result = scan(store)
    assert result['read_only'] and result['requires_manual_choice'] and result['status'] == 'completed'
    assert result['total'] is None and result['examined']['directories'] == 3
    assert len(result['candidates']) == 1 and not result['ambiguous']
    item = result['candidates'][0]
    assert item['relative_path'] == path.relative_to(store[3][0]).as_posix()
    assert item['version'] == 10 and item['version_origin'] == 'explicit' and item['rank'] == 0
    assert item['matched_paths'] == ['04 qualite/06 ce']
    assert item['matched_patterns'] == ['fiche demande declaration ce'] and item['requires_preview']
    assert result['recommended_path'] == item['relative_path'] and 'sha256' not in item
    monkeypatch.undo()
    assert capture_baseline(store[0].kw['bind'].url.database) == before
    assert {p: p.read_bytes() for p in original} == original


@pytest.mark.parametrize('document_id', [row['id'] for row in catalogue()['documents']])
def test_all_eight_default_rules_match_folded_folder_name_format_and_version(store, document_id):
    spec = document_spec(document_id)
    path = make_template(store, ' '.join(spec['filename_tokens']) + f' V{spec["preferred_version"]}.' + spec['format'].lower(),
                         folders=tuple(spec['folder_tokens']))
    with store[0]() as db:
        result = discovery.discover(db, store[1][0], link_id=store[2][0], document_id=document_id, policy=store[4])
    assert result['candidates'][0]['relative_path'] == path.relative_to(store[3][0]).as_posix()
    assert result['candidates'][0]['version'] == spec['preferred_version']


def test_and_matching_order_whole_words_and_excluded_names(store):
    good = make_template(store)
    make_template(store, 'Fiche demande déclaration CE V9.docx')
    make_template(store, 'Fiche demande déclaration CE V10 OLD.docx')
    make_template(store, 'Fiche demande déclaration CE V10.docm')
    make_template(store, 'Fiche demande déclaration CECI V10.docx')
    make_template(store, 'Demande CE V10.docx')
    make_template(store, folders=('06 CE', '04 Qualité'))
    rule = discovery.SearchRule('ce_request', ('04 qualite/06 ce',), ('fiche demande declaration ce',), ('old',), 10)
    result = scan(store, rule=rule)
    assert len(result['candidates']) == 2
    assert result['candidates'][0]['relative_path'] == good.relative_to(store[3][0]).as_posix()
    assert result['skipped']['excluded'] == 1 and result['skipped']['wrong_format'] >= 1
    assert result['skipped']['unrelated_directory'] == 1


def test_equal_rank_is_ambiguous_without_automatic_choice(store):
    make_template(store)
    make_template(store, 'Copie Fiche demande déclaration CE V10.docx')
    result = scan(store)
    assert len(result['candidates']) == 2 and result['ambiguous']
    assert result['recommended_path'] is None and result['requires_manual_choice']


@pytest.mark.parametrize('name,expected,origin', [
    ('FML-007 TDAO.xlsm', 7, 'name_numbers'), ('TDAO V7.xlsm', 7, 'explicit'),
    ('AIRB26LTH0205-A TDAO V7.xlsm', 7, 'explicit'), ('TDAO version 10.xlsm', 10, 'explicit'),
    ('TDAO Rev2.xlsm', 2, 'explicit'), ('TDAO.xlsm', None, 'unknown'),
    ('TDAO 2026.xlsm', None, 'unknown')])
def test_version_provenance_does_not_claim_document_metadata(name, expected, origin):
    assert discovery._version(name) == (expected, origin)


def test_direct_file_and_selected_subfolder_links_have_relative_choices(store):
    path = make_template(store)
    with store[0]() as db:
        db.get(NetworkLink, store[2][0]).chemin = str(path.parent)
        db.commit()
    result = scan(store)
    assert result['candidates'][0]['relative_path'] == path.name
    with store[0]() as db:
        db.get(NetworkLink, store[2][0]).chemin = str(path)
        db.commit()
    result = scan(store)
    assert result['candidates'][0]['relative_path'] == ''
    assert result['candidates'][0]['direct_file_link'] and result['recommended_path'] == ''


def test_foreign_project_or_link_refused_before_configuration_or_disk(store, monkeypatch):
    def fail(*a, **k):
        pytest.fail('Unauthorized discovery touched configuration/disk')
    monkeypatch.setattr(files, 'configured_policy', fail)
    monkeypatch.setattr(Path, 'resolve', fail)
    with store[0]() as db, operator_context(Operator('reader', 'reader', frozenset({store[1][0]}))):
        for project, link in ((store[1][1], store[2][1]), (store[1][0], store[2][1])):
            with pytest.raises(HTTPException) as error:
                discovery.discover(db, project, link_id=link, document_id='ce_request')
            assert error.value.status_code == 404


def test_unrelated_roots_and_project_branches_are_not_probed(store, monkeypatch):
    make_template(store)
    unrelated = store[3][0] / '99 autre partage'
    unrelated.mkdir()
    broken = store[3][0].parent / 'unrelated-offline'
    original_resolve, original_scan = Path.resolve, os.scandir
    def resolve(path, *args, **kwargs):
        assert path != broken
        return original_resolve(path, *args, **kwargs)
    def scandir(path):
        assert Path(path) != unrelated
        return original_scan(path)
    monkeypatch.setattr(Path, 'resolve', resolve)
    if os.name == 'nt':
        monkeypatch.setattr(os, 'scandir', scandir)
    with store[0]() as db:
        result = discovery.discover(db, store[1][0], link_id=store[2][0], document_id='ce_request',
            policy=files.FilePolicy((*store[4].roots, str(broken))))
    assert len(result['candidates']) == 1 and result['skipped']['unrelated_directory'] == 1


def test_data_input_and_excluded_folders_are_pruned(store):
    make_template(store)
    make_template(store, folders=('04 Qualité', 'Données d’entrées', '06 CE'))
    make_template(store, folders=('04 Qualité', 'Data Input', '06 CE'))
    make_template(store, folders=('04 Qualité', 'old', '06 CE'))
    rule = discovery.SearchRule('ce_request', ('04 qualite/06 ce',), ('fiche demande declaration ce',), ('old',))
    result = scan(store, rule=rule)
    assert len(result['candidates']) == 1 and result['skipped']['input_directory'] == 2
    assert result['skipped']['excluded'] == 1


@pytest.mark.skipif(sys.platform != 'win32', reason='Actual Windows junction and handle')
def test_junction_to_other_project_is_skipped_without_enumeration(store, monkeypatch):
    parent = store[3][0] / '04 Qualité'
    parent.mkdir()
    junction = parent / '06 CE'
    command = subprocess.run(['cmd', '/c', 'mklink', '/J', str(junction), str(store[3][1])], capture_output=True, text=True)
    assert command.returncode == 0, command.stderr
    original = os.scandir
    def guard(path):
        assert Path(path) not in {junction, store[3][1]}
        return original(path)
    monkeypatch.setattr(os, 'scandir', guard)
    result = scan(store)
    assert result['candidates'] == [] and result['skipped']['reparse'] == 1


@pytest.mark.skipif(sys.platform != 'win32', reason='Actual Windows no-delete directory handle')
def test_directory_handle_prevents_name_replacement(store):
    root = store[3][0]
    with discovery._directory(root) as (path, _):
        assert path == str(root)
        with pytest.raises(PermissionError):
            root.rename(root.with_name('moved'))
    assert root.is_dir()


def test_entry_candidate_depth_and_directory_limits_never_recommend_incomplete_scan(store):
    for number in range(5):
        make_template(store, f'Fiche demande déclaration CE V10 copie {number}.docx')
    result = scan(store, limits=discovery.ScanLimits(candidates=2))
    assert len(result['candidates']) == 2 and result['bounds'] == ['candidates']
    assert result['ambiguous'] and result['recommended_path'] is None
    result = scan(store, limits=discovery.ScanLimits(entries=1))
    assert result['examined']['entries'] == 1 and 'entries' in result['bounds']
    result = scan(store, limits=discovery.ScanLimits(depth=1))
    assert result['candidates'] == [] and result['bounds'] == ['depth']
    result = scan(store, limits=discovery.ScanLimits(directories=1))
    assert result['examined']['directories'] == 1 and 'directories' in result['bounds']
    assert all(scan(store, limits=limits)['status'] == 'limited' for limits in (
        discovery.ScanLimits(candidates=1), discovery.ScanLimits(entries=1), discovery.ScanLimits(depth=1)))


def test_cancellation_deadline_and_unknown_total_progress(store, monkeypatch):
    make_template(store)
    result = scan(store, cancelled=lambda: True)
    assert result['status'] == 'cancelled' and not result['candidates'] and result['recommended_path'] is None
    ticks = iter(range(10000))
    monkeypatch.setattr(discovery.time, 'monotonic', lambda: next(ticks))
    result = scan(store, limits=discovery.ScanLimits(seconds=.5))
    assert result['status'] == 'limited' and result['bounds'] == ['time']
    monkeypatch.undo()
    for number in range(110):
        (store[3][0] / f'file-{number}.txt').write_text('a')
    events = []
    result = scan(store, on_progress=events.append)
    assert len(events) >= 2 and all(event['total'] is None for event in events)
    assert events[-1]['examined'] == result['examined']


def test_changed_link_during_progress_invalidates_result_on_fresh_connection(store):
    make_template(store)
    def change(event):
        with store[0]() as db:
            db.get(NetworkLink, store[2][0]).chemin = str(store[3][1])
            db.commit()
    with pytest.raises(HTTPException) as error:
        scan(store, on_progress=change)
    assert error.value.status_code == 409


def test_directory_change_during_enumeration_is_rejected(store, monkeypatch):
    make_template(store)
    def change(event):
        # A new entry changes its directory timestamp while the held handle
        # remains valid; final namespace checks must still reject the scan.
        (store[3][0] / 'concurrent.txt').write_text('changed')
    with pytest.raises(HTTPException) as error:
        scan(store, on_progress=change)
    assert error.value.status_code == 409


def test_disabled_and_outside_roots_and_missing_link_are_distinct(store):
    with store[0]() as db:
        for policy, expected in ((files.FilePolicy(()), 409), (files.FilePolicy((str(store[3][1]),)), 403)):
            with pytest.raises(HTTPException) as error:
                discovery.discover(db, store[1][0], link_id=store[2][0], document_id='ce_request', policy=policy)
            assert error.value.status_code == expected
        db.get(NetworkLink, store[2][0]).chemin = str(store[3][0] / 'unavailable')
        db.commit()
    with pytest.raises(HTTPException) as error:
        scan(store)
    assert error.value.status_code == 409


@pytest.mark.parametrize('changes', [dict(entries=0), dict(directories=2001), dict(depth=33),
    dict(candidates=201), dict(seconds=0), dict(seconds=float('nan')), dict(seconds=121)])
def test_limits_are_trusted_and_bounded(changes):
    with pytest.raises(ValueError):
        discovery.ScanLimits(**changes)


@pytest.mark.parametrize('paths,patterns,version', [
    ((), ('ce',), 10), (('04/../secret',), ('ce',), 10), (('/absolute',), ('ce',), 10),
    (('.',), ('***',), 10), (('.',), (), 10), (('.',), ('ce',), True), (('.',), ('ce',), 1000)])
def test_invalid_search_preferences_cannot_change_namespace(paths, patterns, version):
    with pytest.raises((ValueError, HTTPException)):
        discovery.SearchRule('ce_request', paths, patterns, preferred_version=version)


def test_reader_http_discovery_is_read_only_scoped_and_strict(api, monkeypatch):
    client, root, factory, ids, source = api
    target = source.parent / '04 Qualité' / '06 CE' / 'Fiche demande déclaration CE V10.docx'
    target.parent.mkdir(parents=True)
    target.write_bytes(source.read_bytes())
    before = capture_baseline(factory.kw['bind'].url.database)
    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'reader')
    command = {'document_id': 'ce_request', 'link_id': ids['link']}
    response = client.post(root + '/discover', json=command)
    assert response.status_code == 200, response.text
    assert response.json()['candidates'][0]['relative_path'] == target.relative_to(source.parent).as_posix()
    assert client.post(root + '/discover', json={**command, 'link_id': ids['other_link']}).status_code == 404
    for key, value in (('role', 'owner'), ('roots', [str(source.parent)]), ('relative_path', '..'),
                       ('limits', {'entries': 999999}), ('filename_patterns', ['*'])):
        assert client.post(root + '/discover', json={**command, key: value}).status_code == 422
    assert client.post(root + '/discover/extra', json=command).status_code == 403
    monkeypatch.delenv('AGENT_TESTING', raising=False)
    assert client.post(root + '/discover', json=command, headers={'Origin': 'https://foreign.invalid'}).status_code == 403
    assert capture_baseline(factory.kw['bind'].url.database) == before
    assert source.read_bytes() == target.read_bytes()


def test_explicit_drive_mapping_discovery(store):
    if os.name != 'nt':
        pytest.skip('Windows drive mapping')
    make_template(store)
    with store[0]() as db:
        db.get(NetworkLink, store[2][0]).chemin = 'V:\\project-A'
        db.commit()
    policy = files.FilePolicy(store[4].roots, (('V:', str(store[3][0].parent)),))
    with store[0]() as db:
        result = discovery.discover(db, store[1][0], link_id=store[2][0], document_id='ce_request', policy=policy)
    assert len(result['candidates']) == 1 and result['rule']['document_id'] == 'ce_request'
