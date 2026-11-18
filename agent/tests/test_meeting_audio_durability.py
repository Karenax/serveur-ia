"""Audio import retries must never acknowledge a damaged original."""
import hashlib
import os
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db import get_db
from app.models import MeetingRecording, Source
from app.operational_limits import AUDIO_IMPORT_BYTES, MIB
from app.services import meeting_audio as audio_service
from backend.app.routers import meeting_audio
from tests.test_meeting_sessions import stores


def client_for(brain):
    app = FastAPI()
    app.include_router(meeting_audio.router)

    def dependency():
        with brain() as db:
            yield db

    app.dependency_overrides[get_db] = dependency
    return TestClient(app)


def send(client, project_id, raw):
    return client.post(f'/api/v1/projects/{project_id}/recordings',
                       data={'title': 'Réunion fictive', 'date': '2026-11-18', 'num_speakers': '0'},
                       files={'file': ('reunion.wav', raw, 'audio/wav')})


def test_reported_audio_upload_limit_matches_the_server_limit(tmp_path):
    assert audio_service.runtime_status(models_dir=tmp_path)['max_upload_mb'] == AUDIO_IMPORT_BYTES // MIB


def test_integrity_reads_actual_original_and_rejects_damage(stores):
    brain, _, project_id, _ = stores
    raw = b'audio-fictif-a-verifier'
    with client_for(brain) as client:
        uploaded = send(client, project_id, raw)
        assert uploaded.status_code == 201
        row = uploaded.json()
        url = f"/api/v1/projects/{project_id}/recordings/{row['id']}/audio-integrity"
        response = client.get(url)
        assert response.status_code == 200
        assert response.headers['cache-control'] == 'no-store'
        assert response.json() == {'recording_id': row['id'], 'source_id': row['source_id'],
                                   'sha256': hashlib.sha256(raw).hexdigest(), 'size': len(raw)}
        with brain() as db:
            source = db.get(Source, row['source_id'])
            path = Path(source.original_uri)
        path.write_bytes(b'x' * len(raw))
        assert client.get(url).status_code == 409
        assert path.read_bytes() == b'x' * len(raw)
        assert client.get(f"/api/v1/projects/projet-inexistant/recordings/{row['id']}/audio-integrity").status_code == 404


def test_integrity_rejects_a_file_modified_during_read(stores, monkeypatch):
    brain, _, project_id, _ = stores
    raw = b'audio-fictif-concurrent'
    with client_for(brain) as client:
        uploaded = send(client, project_id, raw)
        assert uploaded.status_code == 201
        row = uploaded.json()
        with brain() as db:
            path = Path(db.get(Source, row['source_id']).original_uri)
        original_digest = hashlib.file_digest

        def mutate_after_digest(stream, algorithm):
            result = original_digest(stream, algorithm)
            path.write_bytes(b'x' * len(raw))
            return result

        monkeypatch.setattr(meeting_audio.hashlib, 'file_digest', mutate_after_digest)
        response = client.get(f"/api/v1/projects/{project_id}/recordings/{row['id']}/audio-integrity")
        assert response.status_code == 409
    assert path.read_bytes() == b'x' * len(raw)


def test_integrity_refuses_a_copy_that_cannot_be_synchronized(stores, monkeypatch):
    brain, _, project_id, _ = stores
    raw = b'audio-fictif-synchronisation'
    with client_for(brain) as client:
        uploaded = send(client, project_id, raw)
        assert uploaded.status_code == 201
        row = uploaded.json()
        with brain() as db:
            path = Path(db.get(Source, row['source_id']).original_uri)
        def interrupted(_descriptor):
            raise OSError('stockage indisponible')
        monkeypatch.setattr(meeting_audio.os, 'fsync', interrupted)
        response = client.get(f"/api/v1/projects/{project_id}/recordings/{row['id']}/audio-integrity")
        assert response.status_code == 503
    assert path.read_bytes() == raw


def test_incomplete_orphan_is_preserved_and_never_acknowledged(stores, tmp_path):
    brain, _, project_id, _ = stores
    raw = b'reunion-fictive-originale'
    target = tmp_path / 'raw' / (hashlib.sha256(raw).hexdigest() + '.wav')
    target.write_bytes(b'ecriture interrompue')
    with client_for(brain) as client:
        response = send(client, project_id, raw)
    assert response.status_code == 409
    assert target.read_bytes() == b'ecriture interrompue'
    with brain() as db:
        assert db.scalar(select(func.count()).select_from(Source)) == 0
        assert db.scalar(select(func.count()).select_from(MeetingRecording)) == 0


def test_duplicate_is_not_acknowledged_if_the_original_was_modified(stores):
    brain, _, project_id, _ = stores
    raw = b'reunion-fictive-a-conserver'
    with client_for(brain) as client:
        first = send(client, project_id, raw)
        assert first.status_code == 201
        with brain() as db:
            source = db.get(Source, first.json()['source_id'])
            path = Path(source.original_uri)
        path.write_bytes(b'fichier modifie')
        response = send(client, project_id, raw)
    assert response.status_code == 409
    assert path.read_bytes() == b'fichier modifie'
    with brain() as db:
        assert db.scalar(select(func.count()).select_from(Source)) == 1
        assert db.scalar(select(func.count()).select_from(MeetingRecording)) == 1


def test_existing_identical_orphan_can_be_adopted_without_modification(stores, tmp_path):
    brain, _, project_id, _ = stores
    raw = b'reunion-fictive-deja-ecrite'
    target = tmp_path / 'raw' / (hashlib.sha256(raw).hexdigest() + '.wav')
    target.write_bytes(raw)
    with client_for(brain) as client:
        response = send(client, project_id, raw)
        assert response.status_code == 201
        again = send(client, project_id, raw)
        assert again.status_code == 201 and again.json()['id'] == response.json()['id']
        assert client.get(f"/api/v1/projects/{project_id}/recordings/{response.json()['id']}/audio").content == raw
    assert target.read_bytes() == raw


def test_identical_orphan_is_not_acknowledged_if_disk_sync_fails(stores, tmp_path, monkeypatch):
    brain, _, project_id, _ = stores
    raw = b'reprise-sans-synchronisation'
    target = tmp_path / 'raw' / (hashlib.sha256(raw).hexdigest() + '.wav')
    target.write_bytes(raw)

    def interrupted(_descriptor):
        raise OSError('synchronisation impossible')

    with client_for(brain) as client:
        monkeypatch.setattr(meeting_audio.os, 'fsync', interrupted)
        assert send(client, project_id, raw).status_code == 503
    assert target.read_bytes() == raw
    with brain() as db:
        assert db.scalar(select(func.count()).select_from(Source)) == 0


def test_same_length_orphan_with_different_content_is_preserved(stores, tmp_path):
    brain, _, project_id, _ = stores
    raw = b'original'
    target = tmp_path / 'raw' / (hashlib.sha256(raw).hexdigest() + '.wav')
    target.write_bytes(b'different'[:len(raw)])
    with client_for(brain) as client:
        assert send(client, project_id, raw).status_code == 409
    assert target.read_bytes() == b'different'[:len(raw)]


def test_racing_conflicting_file_is_not_overwritten(stores, tmp_path, monkeypatch):
    brain, _, project_id, _ = stores
    raw = b'enregistrement-fictif'
    target = tmp_path / 'raw' / (hashlib.sha256(raw).hexdigest() + '.wav')

    def competing_writer(_staged, destination):
        Path(destination).write_bytes(b'autre copie')
        raise FileExistsError('concurrent writer')

    monkeypatch.setattr(meeting_audio.os, 'link', competing_writer)
    with client_for(brain) as client:
        assert send(client, project_id, raw).status_code == 409
    assert target.read_bytes() == b'autre copie'
    assert any(path.read_bytes() == raw for path in (tmp_path / 'raw').glob('*.pending'))
    with brain() as db:
        assert db.scalar(select(func.count()).select_from(Source)) == 0


def test_filesystem_without_hard_links_uses_exclusive_creation(stores, tmp_path, monkeypatch):
    brain, _, project_id, _ = stores
    raw = b'enregistrement-sans-liens'

    def unsupported(*_args):
        raise OSError('hard links unavailable')

    monkeypatch.setattr(meeting_audio.os, 'link', unsupported)
    with client_for(brain) as client:
        response = send(client, project_id, raw)
        assert response.status_code == 201
        assert client.get(f"/api/v1/projects/{project_id}/recordings/{response.json()['id']}/audio").content == raw
    assert not list((tmp_path / 'raw').glob('*.pending'))


def test_interrupted_staging_remains_available_and_retry_succeeds(stores, tmp_path, monkeypatch):
    brain, _, project_id, _ = stores
    raw = b'enregistrement-interrompu'
    target = tmp_path / 'raw' / (hashlib.sha256(raw).hexdigest() + '.wav')
    original_fsync = os.fsync

    def interrupted(_descriptor):
        raise OSError('interruption de recette')

    with client_for(brain) as client:
        monkeypatch.setattr(meeting_audio.os, 'fsync', interrupted)
        assert send(client, project_id, raw).status_code == 503
        assert not target.exists()
        assert any(path.read_bytes() == raw for path in (tmp_path / 'raw').glob('*.pending'))
        with brain() as db:
            assert db.scalar(select(func.count()).select_from(Source)) == 0
        monkeypatch.setattr(meeting_audio.os, 'fsync', original_fsync)
        response = send(client, project_id, raw)
        assert response.status_code == 201
        assert client.get(f"/api/v1/projects/{project_id}/recordings/{response.json()['id']}/audio").content == raw
    assert target.read_bytes() == raw


def test_failed_database_commit_reuses_verified_orphan_on_retry(stores, tmp_path, monkeypatch):
    brain, _, project_id, _ = stores
    raw = b'import-transaction-interrompue'
    target = tmp_path / 'raw' / (hashlib.sha256(raw).hexdigest() + '.wav')

    def failing_session():
        db = brain()
        def fail():
            raise RuntimeError('transaction interrompue')
        db.commit = fail
        return db

    with client_for(brain) as client:
        monkeypatch.setattr(meeting_audio, 'BrainSession', failing_session)
        with pytest.raises(RuntimeError, match='transaction interrompue'):
            send(client, project_id, raw)
        assert target.read_bytes() == raw
        with brain() as db:
            assert db.scalar(select(func.count()).select_from(Source)) == 0
        monkeypatch.setattr(meeting_audio, 'BrainSession', brain)
        result = send(client, project_id, raw)
        assert result.status_code == 201
        assert send(client, project_id, raw).json()['id'] == result.json()['id']
    assert target.read_bytes() == raw


def test_interrupted_fallback_does_not_acknowledge_until_rechecked(stores, tmp_path, monkeypatch):
    brain, _, project_id, _ = stores
    raw = b'enregistrement-fallback-interrompu'
    target = tmp_path / 'raw' / (hashlib.sha256(raw).hexdigest() + '.wav')
    original_fsync = os.fsync
    calls = 0

    def unsupported(*_args):
        raise OSError('hard links unavailable')

    def fail_on_publication(descriptor):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError('publication interrompue')
        return original_fsync(descriptor)

    with client_for(brain) as client:
        monkeypatch.setattr(meeting_audio.os, 'link', unsupported)
        monkeypatch.setattr(meeting_audio.os, 'fsync', fail_on_publication)
        assert send(client, project_id, raw).status_code == 503
        assert target.read_bytes() == raw
        assert any(path.read_bytes() == raw for path in (tmp_path / 'raw').glob('*.pending'))
        with brain() as db:
            assert db.scalar(select(func.count()).select_from(Source)) == 0
        monkeypatch.setattr(meeting_audio.os, 'fsync', original_fsync)
        result = send(client, project_id, raw)
        assert result.status_code == 201
        assert client.get(f"/api/v1/projects/{project_id}/recordings/{result.json()['id']}/audio").content == raw
