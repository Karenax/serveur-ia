"""Exercise the ordinary capture loop with fake devices and genuine WAV journals.

No microphone, PortAudio runtime or model is opened. Only the encoder is replaced
by the existing WAV journal codec so exact retained PCM can be inspected.
"""
import errno
import io
import sys
from types import SimpleNamespace
from unittest.mock import Mock
import wave

import pytest

from scripts import native_audio_capture as capture
from scripts import native_chunk_journal as journal


@pytest.fixture
def ordinary_capture(tmp_path, monkeypatch):
    events, closed, order = [], [], []
    pcm = b'\x12\x34' * 1600
    tail = b'\x56\x78' * 16
    failing_close = set()
    kernel = SimpleNamespace(OpenProcess=Mock(return_value=123),
                             WaitForSingleObject=Mock(return_value=258), CloseHandle=Mock())
    monkeypatch.setattr(capture.ctypes, 'WinDLL', lambda *a, **k: kernel)
    monkeypatch.setattr(capture, 'session_id', lambda *a: 1)
    monkeypatch.setattr(capture, 'emit', lambda **event: events.append(event))
    monkeypatch.setattr(capture.sys, 'stdin', io.StringIO('{"op":"start"}\n'))
    monkeypatch.setattr(capture.threading, 'Thread',
                        lambda target, **kwargs: SimpleNamespace(start=target))

    class Frame:
        def __init__(self, raw):
            self.raw = raw

        def to_ndarray(self):
            return SimpleNamespace(tobytes=lambda: self.raw)

    class Resampler:
        def __init__(self, **kwargs):
            self.used = False

        def resample(self, frame):
            if frame is None:
                return [Frame(tail)] if self.used else []
            self.used = True
            return [frame]

    monkeypatch.setitem(sys.modules, 'av', SimpleNamespace(
        AudioFrame=SimpleNamespace(from_ndarray=lambda array, **kwargs: Frame(array.tobytes())),
        AudioResampler=Resampler))

    class Stream:
        def __init__(self, track, callback):
            self.track, self.callback = track, callback

        def start_stream(self):
            self.callback(pcm, len(pcm)//2, None, 0)

        def close(self):
            order.append('close-'+self.track)
            if self.track in failing_close:
                raise OSError('Fake endpoint close failure')
            closed.append(self.track)

        def is_active(self):
            raise AssertionError('Cleanup must not depend on a device health query')

    class Audio:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            order.append('audio-exit')

        def get_host_api_info_by_type(self, *args):
            return {'index': 0, 'defaultInputDevice': 0}

        def get_device_info_by_index(self, index):
            return {'index': index, 'name': 'fake-'+str(index), 'hostApi': 0,
                    'maxInputChannels': 1, 'isLoopbackDevice': index == 1,
                    'defaultSampleRate': 16000}

        def open(self, **kwargs):
            return Stream('mic' if kwargs['input_device_index'] == 0 else 'system',
                          kwargs['stream_callback'])

    monkeypatch.setitem(sys.modules, 'pyaudiowpatch', SimpleNamespace(
        PyAudio=Audio, paWASAPI=13, paInt16=8, paContinue=0))

    class Endpoints:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def bind(self, *args):
            pass

        def check(self, *args, **kwargs):
            if not kwargs.get('force'):
                raise ValueError('Périphérique audio interrompu : system')

    from scripts import windows_audio_endpoints
    monkeypatch.setattr(windows_audio_endpoints, 'EndpointMonitor', Endpoints)
    original_commit = journal.commit_chunk

    def commit(directory, sid, track, sequence, raw, start_ms, *, codec):
        assert codec == 'opus'  # Production still requests compressed storage.
        assert set(closed) == {'mic', 'system'}
        assert 'audio-exit' not in order
        order.append('persist-'+track)
        return original_commit(directory, sid, track, sequence, raw, start_ms, codec='wav')

    monkeypatch.setattr(journal, 'commit_chunk', commit)
    request = {'session_id': 'ab432130-73e2-4c26-b546-a3966d274ffc',
               'storage': str(tmp_path), 'directory': str(tmp_path/'audio'),
               'tracks': ['mic', 'system'], 'devices': {'mic': 0, 'system': 1}}
    monkeypatch.setattr(capture, 'main', lambda: capture.capture(request, parent_pid=456))
    return SimpleNamespace(events=events, closed=closed, order=order, kernel=kernel,
                           pcm=pcm, tail=tail, request=request, failing_close=failing_close)


def test_unplug_drains_queue_and_resampler_before_reporting_interruption(ordinary_capture):
    fixture = ordinary_capture
    assert capture.cli_main() == 1
    packets = [event for event in fixture.events if event['kind'] == 'chunk']
    assert {p['track'] for p in packets} == {'mic', 'system'}
    for packet in packets:
        with wave.open(packet['path'], 'rb') as audio:
            assert audio.readframes(audio.getnframes()) == fixture.pcm + fixture.tail
    assert fixture.events[-1] == {'kind': 'error', 'error': 'Périphérique audio interrompu : system'}
    assert not any(e.get('state') == 'stopped' for e in fixture.events)
    assert fixture.order[:2] == ['close-mic', 'close-system']
    assert fixture.order[-1] == 'audio-exit'
    fixture.kernel.CloseHandle.assert_called_once_with(123)


def test_failed_close_attempts_other_track_and_never_claims_drain(ordinary_capture):
    fixture = ordinary_capture
    fixture.failing_close.add('mic')
    assert capture.cli_main() == 1
    assert 'system' in fixture.closed
    assert not any(e['kind'] == 'chunk' or e.get('state') == 'stopped' for e in fixture.events)
    assert fixture.events[-1] == {'kind': 'error', 'error': 'Fermeture audio non confirmée : mic'}
    fixture.kernel.CloseHandle.assert_called_once_with(123)


def test_disk_full_during_interruption_retains_storage_failure(ordinary_capture, monkeypatch):
    fixture = ordinary_capture

    def full(*args, **kwargs):
        raise OSError(errno.ENOSPC, 'fake full isolated storage')

    monkeypatch.setattr(journal, 'commit_chunk', full)
    assert capture.cli_main() == 1
    assert set(fixture.closed) == {'mic', 'system'}
    assert not any(e['kind'] == 'chunk' or e.get('state') == 'stopped' for e in fixture.events)
    assert 'Stockage audio saturé' in fixture.events[-1]['error']
    fixture.kernel.CloseHandle.assert_called_once_with(123)
