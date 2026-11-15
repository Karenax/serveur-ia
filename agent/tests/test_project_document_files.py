"""Real Windows file handles on fictional links, with neutral project stores."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db import Base
from backend.app.models import NetworkLink, Project
from backend.app.services import document_file_access as files
from backend.app.services.document_publications import configured_write_policy
from backend.app.services.project_operator import Operator, operator_context
from tests.test_project_document_packages import package, parts_for


@pytest.fixture
def store(tmp_path):
    engine = create_engine(f'sqlite:///{tmp_path / "files.db"}')
    Base.metadata.create_all(engine, tables=[Project.__table__, NetworkLink.__table__])
    root = tmp_path / 'authorized'
    root.mkdir()
    folders = [root / 'project-A', root / 'project-B']
    for folder in folders:
        folder.mkdir()
        (folder / 'demande.docx').write_bytes(package(parts_for('ce_request')))
        (folder / 'notes.txt').write_text('Compte rendu fictif', encoding='utf-8')
    factory = sessionmaker(bind=engine)
    with factory() as db:
        projects = [Project(code=code, title=code) for code in ('A', 'B')]
        db.add_all(projects)
        db.flush()
        links = [NetworkLink(project_id=project.id, code='affaire', libelle='Dossier', chemin=str(folder))
                 for project, folder in zip(projects, folders)]
        db.add_all(links)
        db.commit()
        ids, link_ids = [row.id for row in projects], [row.id for row in links]
    yield factory, ids, link_ids, folders, files.FilePolicy((str(root),))
    engine.dispose()


def acquire(store, **kwargs):
    factory, ids, links, _, policy = store
    with factory() as db:
        return files.acquire_file(db, ids[0], link_id=links[0], policy=policy, **kwargs)


def test_reader_acquisition_and_preview_preserve_files_and_database(store):
    factory, ids, links, folders, policy = store
    before = {path: path.read_bytes() for folder in folders for path in folder.iterdir()}
    with factory() as db:
        baseline = [(row.id, row.chemin, row.code) for row in db.query(NetworkLink).all()]
        with operator_context(Operator('reader', 'reader', frozenset({ids[0]}))):
            data, source = files.acquire_file(db, ids[0], link_id=links[0], relative_path='demande.docx', policy=policy)
            report = files.preview_file(db, ids[0], link_id=links[0], relative_path='demande.docx',
                document_id='ce_request', values={'project_code': 'AIRB26LTH0205-A'}, policy=policy)
        assert source['sha256'] == hashlib.sha256(data).hexdigest()
        assert report['can_prepare'] and report['read_only']
        assert report['source']['link_id'] == links[0]
        assert not db.new and not db.dirty and not db.deleted
        assert [(row.id, row.chemin, row.code) for row in db.query(NetworkLink).all()] == baseline
    assert {path: path.read_bytes() for folder in folders for path in folder.iterdir()} == before


def test_foreign_project_and_link_refused_before_any_file_probe(store, monkeypatch):
    factory, ids, links, _, policy = store
    def forbidden(*args, **kwargs):
        pytest.fail('Filesystem/configuration probed before project/link authorization')
    monkeypatch.setattr(Path, 'resolve', forbidden)
    monkeypatch.setattr(files, 'configured_policy', forbidden)
    with factory() as db, operator_context(Operator('reader', 'reader', frozenset({ids[0]}))):
        for project, link in ((ids[1], links[1]), (ids[0], links[1])):
            with pytest.raises(HTTPException) as error:
                files.acquire_file(db, project, link_id=link, relative_path='notes.txt', policy=policy)
            assert error.value.status_code == 404


@pytest.mark.parametrize('path', ['../project-B/notes.txt', '..\\project-B\\notes.txt', 'V:\\secret.txt',
    '\\\\server\\share\\file', '/absolute', 'x:stream', 'a//b', 'a/./b', 'a\x00b', 'NUL', 'trailing.'])
def test_invalid_relative_paths_refused(store, path):
    with pytest.raises(HTTPException) as error:
        acquire(store, relative_path=path)
    assert error.value.status_code == 422


def test_missing_share_and_missing_document_are_distinct(store):
    factory, ids, links, folders, policy = store
    with pytest.raises(HTTPException) as error:
        acquire(store, relative_path='missing.txt')
    assert error.value.status_code == 404
    with factory() as db:
        db.get(NetworkLink, links[0]).chemin = str(folders[0] / 'missing-share')
        db.commit()
    with pytest.raises(HTTPException) as error:
        acquire(store, relative_path='missing.txt')
    assert error.value.status_code == 409


def test_file_link_never_authorizes_a_sibling(store):
    factory, ids, links, folders, policy = store
    with factory() as db:
        db.get(NetworkLink, links[0]).chemin = str(folders[0] / 'notes.txt')
        db.commit()
    assert acquire(store)[0].decode() == 'Compte rendu fictif'
    assert acquire(store, relative_path='notes.txt')[0].decode() == 'Compte rendu fictif'
    with pytest.raises(HTTPException) as error:
        acquire(store, relative_path='demande.docx')
    assert error.value.status_code == 403


def test_disallowed_root_refused_before_resolving_it(store, tmp_path, monkeypatch):
    factory, ids, links, _, policy = store
    with factory() as db:
        db.get(NetworkLink, links[0]).chemin = str(tmp_path / 'outside')
        db.commit()
    def forbidden(*args, **kwargs):
        pytest.fail('Disallowed root was resolved')
    monkeypatch.setattr(Path, 'resolve', forbidden)
    with pytest.raises(HTTPException) as error:
        acquire(store, relative_path='notes.txt')
    assert error.value.status_code == 403


def test_drive_mapping_is_explicit_and_remains_under_authorized_root(store):
    factory, ids, links, folders, policy = store
    with factory() as db:
        db.get(NetworkLink, links[0]).chemin = 'V:\\project-A'
        db.commit()
        mapped = files.FilePolicy(policy.roots, (('V:', str(folders[0].parent)),))
        data, source = files.acquire_file(db, ids[0], link_id=links[0], relative_path='notes.txt', policy=mapped)
    assert data.decode() == 'Compte rendu fictif' and source['drive_mapped']


def test_empty_policy_and_configuration_invalid_are_explicit(store, monkeypatch):
    factory, ids, links, _, policy = store
    with factory() as db:
        with pytest.raises(HTTPException) as error:
            files.acquire_file(db, ids[0], link_id=links[0], relative_path='notes.txt', policy=files.FilePolicy(()))
        assert error.value.status_code == 409
    monkeypatch.setenv('AGENT_DOCUMENT_ROOTS', json.dumps(list(policy.roots)))
    monkeypatch.setenv('AGENT_DOCUMENT_DRIVE_MAPPINGS', '{}')
    assert files.configured_policy() == policy
    monkeypatch.setenv('AGENT_DOCUMENT_ROOTS', '{bad json')
    with pytest.raises(HTTPException):
        files.configured_policy()


def test_managed_client_directory_is_scoped_in_read_and_write_policies(store, monkeypatch):
    factory, ids, links, folders, _ = store
    base = folders[0].parent
    for folder, project_id in zip(folders, ids):
        folder.rename(base / project_id)
    monkeypatch.setenv('AGENT_DOCUMENT_PROJECT_ROOT', json.dumps(str(base)))
    monkeypatch.setenv('AGENT_DOCUMENT_ROOTS', '[]')
    monkeypatch.setenv('AGENT_DOCUMENT_WRITE_ROOTS', '[]')
    assert configured_write_policy(ids[0]).roots == (str(base / ids[0]),)
    with factory() as db, operator_context(Operator('owner', 'owner', frozenset({ids[0]}))):
        link = db.get(NetworkLink, links[0])
        link.chemin = str(base / ids[0])
        data, _ = files.acquire_file(db, ids[0], link_id=link.id, relative_path='notes.txt')
        assert data.decode() == 'Compte rendu fictif'
        link.chemin = str(base / ids[1])
        with pytest.raises(HTTPException) as error:
            files.acquire_file(db, ids[0], link_id=link.id, relative_path='notes.txt')
        assert error.value.status_code == 403


def test_source_hash_empty_files_directory_and_limits_are_enforced(store, monkeypatch):
    with pytest.raises(HTTPException) as error:
        acquire(store, relative_path='notes.txt', expected_sha256='0' * 64)
    assert error.value.status_code == 409
    with pytest.raises(HTTPException) as error:
        acquire(store, relative_path='')
    assert error.value.status_code == 409
    store[3][0].joinpath('empty.txt').write_bytes(b'')
    with pytest.raises(HTTPException) as error:
        acquire(store, relative_path='empty.txt')
    assert error.value.status_code == 422
    monkeypatch.setattr(files, 'MAX_SOURCE_BYTES', 2)
    with pytest.raises(HTTPException) as error:
        acquire(store, relative_path='notes.txt')
    assert error.value.status_code == 413


def test_opened_handle_path_is_checked_before_read(store, monkeypatch):
    monkeypatch.setattr(files, '_handle_path', lambda stream: store[3][1] / 'notes.txt')
    with pytest.raises(HTTPException) as error:
        acquire(store, relative_path='notes.txt')
    assert error.value.status_code == 409


def test_preview_refuses_mismatched_extension_and_bad_office_package(store):
    factory, ids, links, folders, policy = store
    with factory() as db:
        with pytest.raises(HTTPException) as error:
            files.preview_file(db, ids[0], link_id=links[0], relative_path='notes.txt',
                document_id='ce_request', values={'project_code': '0205'}, policy=policy)
        assert error.value.status_code == 422
        (folders[0] / 'bad.docx').write_bytes(b'not a zip')
        with pytest.raises(HTTPException) as error:
            files.preview_file(db, ids[0], link_id=links[0], relative_path='bad.docx',
                document_id='ce_request', values={'project_code': '0205'}, policy=policy)
        assert error.value.status_code == 422


@pytest.mark.skipif(sys.platform != 'win32', reason='Real Windows junction qualification')
def test_real_windows_junction_to_another_project_is_refused(store):
    folders = store[3]
    junction = folders[0] / 'outside-junction'
    result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(junction), str(folders[1])],
                            capture_output=True, check=False)
    assert result.returncode == 0, result.stderr.decode(errors='replace')
    with pytest.raises(HTTPException) as error:
        acquire(store, relative_path='outside-junction/notes.txt')
    assert error.value.status_code == 403


def test_file_modified_during_read_is_refused(store, monkeypatch):
    source = store[3][0] / 'notes.txt'
    original_open = Path.open

    class ChangingStream:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.stream.close()

        def fileno(self):
            return self.stream.fileno()

        def read(self, length):
            data = self.stream.read(length)
            with original_open(source, 'wb') as output:
                output.write(b'Changed during acquisition, different size')
            return data

    def opening(path, *args, **kwargs):
        stream = original_open(path, *args, **kwargs)
        return ChangingStream(stream) if path == source and args == ('rb',) else stream

    monkeypatch.setattr(Path, 'open', opening)
    with pytest.raises(HTTPException) as error:
        acquire(store, relative_path='notes.txt')
    assert error.value.status_code == 409


def test_server_absolute_paths_refuse_alternate_stream_and_traversal(store):
    root = store[3][0]
    for value in (str(root / 'notes.txt:stream'), str(root / '..' / 'other'), str(root / 'alias.')):
        with pytest.raises(ValueError):
            files.FilePolicy((value,))
    with pytest.raises(HTTPException) as error:
        acquire(store, expected_sha256='not-a-sha256')
    assert error.value.status_code == 422


def test_unrelated_offline_root_is_never_probed_or_allowed_to_block_current_project(store, tmp_path, monkeypatch):
    inactive = tmp_path / 'unavailable-other-share'
    original = Path.resolve

    def resolve(path, *args, **kwargs):
        if path == inactive:
            pytest.fail('An unrelated root was probed')
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'resolve', resolve)
    factory, ids, links, _, policy = store
    policy = files.FilePolicy((str(inactive), *policy.roots))
    with factory() as db:
        data, source = files.acquire_file(db, ids[0], link_id=links[0], relative_path='notes.txt', policy=policy)
    assert data.decode() == 'Compte rendu fictif' and source['read_only']
