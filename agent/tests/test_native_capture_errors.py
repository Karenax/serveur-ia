"""Exercise the native CLI error boundary without opening any device."""
import errno
import json
from pathlib import Path

import pytest

from scripts import native_audio_capture as capture


@pytest.mark.parametrize('native_code', [None, 39, 112])
def test_storage_failure_has_actionable_message_without_path(monkeypatch, native_code):
    failure = OSError(errno.ENOSPC if native_code is None else errno.EIO, 'C:/private/fixture.wav')
    if native_code is not None:
        failure.winerror = native_code
    messages = []

    def fail():
        raise failure

    monkeypatch.setattr(capture, 'main', fail)
    monkeypatch.setattr(capture, 'emit', lambda **event: messages.append(event))
    assert capture.cli_main() == 1
    assert len(messages) == 1 and messages[0]['kind'] == 'error'
    message = messages[0]['error']
    assert 'Stockage audio saturé' in message and 'Libérez' in message
    assert 'acquittés sont conservés' in message and 'private' not in message


def test_device_permission_failure_is_not_reported_as_full_storage(monkeypatch):
    def fail():
        raise PermissionError(errno.EACCES, 'C:/private/device')

    messages = []
    monkeypatch.setattr(capture, 'main', fail)
    monkeypatch.setattr(capture, 'emit', lambda **event: messages.append(event))
    assert capture.cli_main() == 1
    assert 'permission Windows' in messages[0]['error']
    assert 'saturé' not in messages[0]['error'] and 'private' not in messages[0]['error']


def test_request_validation_detail_is_preserved(monkeypatch):
    def fail():
        raise ValueError('Choix explicite des pistes mic/system requis')

    messages = []
    monkeypatch.setattr(capture, 'main', fail)
    monkeypatch.setattr(capture, 'emit', lambda **event: messages.append(event))
    assert capture.cli_main() == 1
    assert messages == [{'kind': 'error', 'error': 'Choix explicite des pistes mic/system requis'}]


def test_success_does_not_invent_an_error(monkeypatch):
    monkeypatch.setattr(capture, 'main', lambda: None)
    monkeypatch.setattr(capture, 'emit', lambda **event: pytest.fail('unexpected error'))
    assert capture.cli_main() == 0


def test_local_diagnostic_keeps_original_and_cleanup_causes_without_locals(tmp_path):
    try:
        try:
            raise ValueError('Fictitious endpoint removed')
        except ValueError:
            raise OSError(errno.EIO, 'Fictitious resampler drain failed') from None
    except OSError as error:
        first = capture.record_capture_failure(tmp_path, error)
        second = capture.record_capture_failure(tmp_path, error)
    assert first != second and first.is_file() and second.is_file()
    diagnostic = json.loads(first.read_text(encoding='utf-8'))
    assert diagnostic['kind'] == 'capture.failure'
    assert [cause['type'] for cause in diagnostic['causes']] == ['OSError', 'ValueError']
    assert diagnostic['causes'][0]['errno'] == errno.EIO
    assert all(set(frame) == {'file', 'line', 'function'}
               for cause in diagnostic['causes'] for frame in cause['frames'])


def test_local_diagnostic_does_not_replace_failure_when_storage_is_full(tmp_path, monkeypatch):
    def full(*_args, **_kwargs):
        raise OSError(errno.ENOSPC, 'Fictitious full disk')
    monkeypatch.setattr(Path, 'open', full)
    assert capture.record_capture_failure(tmp_path, ValueError('Original interruption')) is None
