"""Real file publication interleavings, complete quota admission and fail-closed edges."""
import errno
import os
from pathlib import Path
from uuid import uuid4

import pytest
from scripts.native_chunk_journal import Limits, inventory


def rename_during_stat(monkeypatch, pending, destination):
    real = Path.lstat
    moved = []

    def lstat(path, *args, **kwargs):
        if path == pending and not moved:
            os.replace(pending, destination)
            moved.append(True)
        return real(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'lstat', lstat)
    return moved


@pytest.mark.parametrize('phase', ['manifest', 'receipt'])
def test_normal_atomic_publication_is_reinventoried_with_destination(monkeypatch, tmp_path, phase):
    pending = tmp_path / (phase + '-' + uuid4().hex + '.pending')
    destination = tmp_path / 'mic-00000000.json'
    pending.write_bytes(b'{}')
    moved = rename_during_stat(monkeypatch, pending, destination)
    result = inventory(tmp_path, Limits(file_count=1, storage_bytes=2))
    assert moved == [True] and result['paths'] == [destination]
    assert result['bytes'] == 2 and destination.read_bytes() == b'{}'


def test_publication_does_not_hide_destination_bytes_from_quota(monkeypatch, tmp_path):
    pending = tmp_path / ('receipt-' + uuid4().hex + '.pending')
    destination = tmp_path / 'mic-00000000.receipt.json'
    pending.write_bytes(b'{}')
    rename_during_stat(monkeypatch, pending, destination)
    with pytest.raises(ValueError, match='cumulative storage'):
        inventory(tmp_path, Limits(storage_bytes=1))
    assert destination.read_bytes() == b'{}'


@pytest.mark.parametrize('name', ['mic-00000000.ogg', 'other.pending', 'manifest-invalid.pending'])
def test_unexpected_disappearance_still_fails(monkeypatch, tmp_path, name):
    pending = tmp_path / name
    destination = tmp_path / 'retained.original'
    pending.write_bytes(b'original')
    rename_during_stat(monkeypatch, pending, destination)
    with pytest.raises(FileNotFoundError):
        inventory(tmp_path, Limits())
    assert destination.read_bytes() == b'original'


def test_permission_failure_not_retried_or_hidden(monkeypatch, tmp_path):
    pending = tmp_path / ('receipt-' + uuid4().hex + '.pending')
    pending.write_bytes(b'{}')
    real = Path.lstat
    denied = []

    def lstat(path, *args, **kwargs):
        if path == pending:
            denied.append(True)
            raise PermissionError(errno.EACCES, 'controlled denied metadata', str(path))
        return real(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'lstat', lstat)
    with pytest.raises(PermissionError):
        inventory(tmp_path, Limits())
    assert len(denied) == 1


def test_persistent_publication_churn_remains_an_error_and_preserves_bytes(monkeypatch, tmp_path):
    initial = tmp_path / ('manifest-' + uuid4().hex + '.pending')
    initial.write_bytes(b'original')
    current = [initial]
    real = Path.lstat

    def lstat(path, *args, **kwargs):
        if path == current[0]:
            destination = tmp_path / ('manifest-' + uuid4().hex + '.pending')
            os.replace(path, destination)
            current[0] = destination
        return real(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'lstat', lstat)
    with pytest.raises(FileNotFoundError):
        inventory(tmp_path, Limits())
    assert current[0].read_bytes() == b'original'
