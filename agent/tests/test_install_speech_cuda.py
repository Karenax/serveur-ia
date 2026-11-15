"""Real file-copy/RECORD checks with tiny inert fixtures; never load DLLs."""
import base64
import csv
import hashlib
import json
import os

import pytest

from scripts.install_speech_cuda import PACKAGES, install
from scripts import install_speech_cuda as installer


@pytest.fixture
def packages(tmp_path):
    source = tmp_path / 'source'
    for package, metadata in PACKAGES.items():
        names = ['cublas64_12.dll', 'cublasLt64_12.dll'] if package == 'cublas' else ['cudnn64_9.dll']
        values = {f'nvidia/{package}/bin/{name}': b'FICTITIOUS DLL, NEVER LOAD' for name in names}
        license_path = metadata + ('/licenses/License.txt' if package == 'cublas' else '/License.txt')
        values[license_path] = b'Fictitious license fixture'
        rows = []
        for relative, data in values.items():
            path = source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip('=')
            rows.append([relative, 'sha256=' + digest, str(len(data))])
        with (source / metadata / 'RECORD').open('w', encoding='utf-8', newline='') as output:
            csv.writer(output).writerows(rows)
    return source


def test_real_copy_readback_preserves_both_license_layouts_and_source(packages, tmp_path):
    target = tmp_path / 'runtime'
    before = {str(p): p.read_bytes() for p in packages.rglob('*') if p.is_file()}
    manifest = install(packages, target)
    assert len(manifest['files']) == 3 and len(manifest['licenses']) == 2
    assert json.loads((target / 'manifest.json').read_text()) == manifest
    for row in manifest['files'] + manifest['licenses']:
        assert hashlib.sha256((target / row['relative_path']).read_bytes()).hexdigest() == row['sha256']
    assert all(path.read_bytes() == before[str(path)] for path in packages.rglob('*') if path.is_file())


def test_changed_source_refused_before_any_installation(packages, tmp_path):
    (packages / 'nvidia/cublas/bin/cublas64_12.dll').write_bytes(b'CORRUPTED, NEVER LOAD')
    target = tmp_path / 'runtime'
    with pytest.raises(ValueError, match='RECORD'):
        install(packages, target)
    assert not target.exists()


def test_existing_runtime_is_not_overwritten(packages, tmp_path):
    target = tmp_path / 'runtime'
    target.mkdir()
    original = target / 'retained.txt'
    original.write_text('Must remain unchanged')
    with pytest.raises(FileExistsError):
        install(packages, target)
    assert original.read_text() == 'Must remain unchanged'


def windows_refusal(code):
    error = PermissionError('Fictitious Windows publication refusal')
    error.winerror = code
    return error


@pytest.mark.parametrize('code', [5, 32, 33])
def test_transient_windows_publication_refusal_retries_only_rename(packages, tmp_path, monkeypatch, code):
    rename = installer.os.rename
    calls = []
    def once(source, target):
        calls.append((source, target))
        if len(calls) == 1:
            raise windows_refusal(code)
        return rename(source, target)
    monkeypatch.setattr(installer.os, 'rename', once)
    monkeypatch.setattr(installer.time, 'sleep', lambda _: None)
    result = install(packages, tmp_path / 'runtime')
    assert len(calls) == 2 and calls[0] == calls[1]
    assert len(result['files']) == 3 and len(result['licenses']) == 2


def test_persistent_windows_refusal_preserves_preparation_and_original_exception(tmp_path, monkeypatch):
    stage = tmp_path / 'prepared'
    stage.mkdir()
    (stage / 'retained.txt').write_text('Verified preparation')
    failure = windows_refusal(5)
    calls = []
    def denied(*args):
        calls.append(args)
        raise failure
    clock = iter([0.0, 0.1, 2.1])
    monkeypatch.setattr(installer.time, 'monotonic', lambda: next(clock))
    monkeypatch.setattr(installer.time, 'sleep', lambda _: None)
    monkeypatch.setattr(installer.os, 'rename', denied)
    with pytest.raises(PermissionError) as refused:
        installer._publish(stage, tmp_path / 'runtime')
    assert refused.value is failure and len(calls) == 2
    assert (stage / 'retained.txt').read_text() == 'Verified preparation'
    assert not (tmp_path / 'runtime').exists()


def test_destination_arriving_during_retry_is_never_replaced(tmp_path, monkeypatch):
    stage, target = tmp_path / 'prepared', tmp_path / 'runtime'
    stage.mkdir()
    def concurrent_install(*args):
        target.mkdir()
        (target / 'retained.txt').write_text('Other installation')
        raise windows_refusal(5)
    monkeypatch.setattr(installer.os, 'rename', concurrent_install)
    monkeypatch.setattr(installer.time, 'sleep', lambda _: None)
    with pytest.raises(FileExistsError):
        installer._publish(stage, target)
    assert stage.exists() and (target / 'retained.txt').read_text() == 'Other installation'


def test_non_windows_IO_error_is_not_retried(tmp_path, monkeypatch):
    failure = OSError('Fictitious disk error')
    def denied(*args):
        raise failure
    monkeypatch.setattr(installer.os, 'rename', denied)
    monkeypatch.setattr(installer.time, 'sleep', lambda _: pytest.fail('No retry for unrelated errors'))
    with pytest.raises(OSError) as refused:
        installer._publish(tmp_path / 'prepared', tmp_path / 'runtime')
    assert refused.value is failure


@pytest.mark.skipif(os.name != 'nt', reason='Real Windows file-sharing semantics')
def test_real_windows_locked_file_is_preserved_then_directory_published(tmp_path, monkeypatch):
    import ctypes
    from ctypes import wintypes
    stage, target = tmp_path / 'prepared', tmp_path / 'runtime'
    stage.mkdir()
    retained = stage / 'manifest.json'
    retained.write_text('{"fictitious":true}')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                  wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.CreateFileW(str(retained), 0x80000000, 3, None, 3, 0x80, None)
    assert handle != ctypes.c_void_p(-1).value
    opened = True
    observed = []
    rename = installer.os.rename
    def release_after_real_refusal(source, destination):
        nonlocal opened
        try:
            return rename(source, destination)
        except OSError as exc:
            observed.append(exc.winerror)
            assert kernel.CloseHandle(handle)
            opened = False
            raise
    monkeypatch.setattr(installer.os, 'rename', release_after_real_refusal)
    try:
        installer._publish(stage, target)
    finally:
        if opened:
            assert kernel.CloseHandle(handle)
    assert len(observed) == 1 and observed[0] in {5, 32, 33}
    assert not stage.exists()
    assert (target / 'manifest.json').read_text() == '{"fictitious":true}'
