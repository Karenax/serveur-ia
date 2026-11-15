"""Device state is independent of audio samples and PortAudio's cached inventory."""

from unittest.mock import Mock
import ctypes as ct
import queue
import sys
from types import SimpleNamespace

import pytest

from scripts.windows_audio_endpoints import (
    ACTIVE, EndpointMonitor, _Guid, _PropertyKey, _PropVariant, _checked,
)


def api():
    result = Mock()
    result.enumerate.side_effect = lambda flow: [
        {"id": f"opaque-{flow}-original", "name": "Casque (Test)"},
        {"id": f"opaque-{flow}-other", "name": "Another output"},
    ]
    result.state.return_value = ACTIVE
    return result


def test_windows_abi_guid_property_key_and_variant_offsets():
    assert ct.sizeof(_Guid) == 16
    assert ct.sizeof(_PropertyKey) == 20
    assert _PropVariant.value.offset == 8
    assert ct.sizeof(_PropVariant) >= 16
    assert bytes(_Guid.parse("a95664d2-9614-4f35-a746-de8db63617e6")) == bytes.fromhex(
        "d26456a91496354fa746de8db63617e6"
    )


@pytest.mark.parametrize("track,flow,name", [
    ("mic", 1, "Casque (Test)"),
    ("system", 0, "Casque (Test) [Loopback]"),
])
def test_binding_uses_selected_flow_and_exact_name(track, flow, name):
    backend = api()
    with EndpointMonitor(backend) as monitor:
        monitor.bind(track, name)
        monitor.check(0)
        backend.enumerate.assert_called_once_with(flow)
        backend.state.assert_called_once_with(f"opaque-{flow}-original")
    backend.close.assert_called_once()


@pytest.mark.parametrize("rows", [[], [
    {"id": "one", "name": "Casque (Test)"},
    {"id": "two", "name": "Casque (Test)"},
]])
def test_missing_or_ambiguous_endpoint_never_falls_back_to_default(rows):
    backend = api()
    backend.enumerate.side_effect = None
    backend.enumerate.return_value = rows
    with EndpointMonitor(backend) as monitor, pytest.raises(ValueError, match="absent ou ambigu"):
        monitor.bind("system", "Casque (Test) [Loopback]")
    backend.state.assert_not_called()
    backend.close.assert_called_once()


@pytest.mark.parametrize("state", [2, 4, 8, 0, 15])
def test_removed_disabled_or_unplugged_loopback_interrupts_even_without_audio(state):
    backend = api()
    with EndpointMonitor(backend) as monitor:
        monitor.bind("system", "Casque (Test) [Loopback]")
        monitor.check(1)
        backend.state.return_value = state
        with pytest.raises(ValueError, match="déconnecté"):
            monitor.check(2)


def test_endpoint_disappearance_is_reported_and_not_rebound_by_friendly_name():
    backend = api()
    with EndpointMonitor(backend) as monitor:
        monitor.bind("mic", "Casque (Test)")
        backend.state.side_effect = OSError("endpoint not found")
        with pytest.raises(ValueError, match="déconnecté ou inaccessible"):
            monitor.check(1)
        backend.enumerate.assert_called_once()


def test_endpoint_id_survives_default_changes_and_inventory_reordering():
    backend = api()
    with EndpointMonitor(backend) as monitor:
        monitor.bind("system", "Casque (Test) [Loopback]")
        backend.enumerate.side_effect = AssertionError("Must not enumerate again")
        monitor.check(1)
        monitor.check(2)
        assert [call.args for call in backend.state.call_args_list] == [
            ("opaque-0-original",), ("opaque-0-original",),
        ]


def test_idle_loopback_remains_valid_without_any_audio_callbacks():
    backend = api()
    with EndpointMonitor(backend) as monitor:
        monitor.bind("system", "Casque (Test) [Loopback]")
        for stamp in [0, 1, 10000, 100000]:
            monitor.check(stamp)
        assert backend.state.call_count == 4


def test_resume_checks_immediately_even_inside_poll_interval():
    backend = api()
    with EndpointMonitor(backend) as monitor:
        monitor.bind("mic", "Casque (Test)")
        monitor.check(10)
        monitor.check(10.5)
        assert backend.state.call_count == 1
        backend.state.return_value = 8
        with pytest.raises(ValueError, match="déconnecté"):
            monitor.check(10.6, force=True)


def test_com_lifetime_is_closed_on_bind_failure_and_close_is_idempotent():
    backend = api()
    with pytest.raises(ValueError), EndpointMonitor(backend) as monitor:
        monitor.bind("unknown", "Casque (Test)")
    monitor.close()
    backend.close.assert_called_once()
    with pytest.raises(RuntimeError, match="fermé"):
        monitor.check(1)


def test_negative_hresult_is_an_error_but_success_codes_are_not():
    _checked(0)
    _checked(1)
    with pytest.raises(OSError, match="80004005"):
        _checked(-2147467259)


@pytest.mark.parametrize('close_fails', [False, True])
def test_ordinary_capture_interrupts_removed_silent_loopback_and_closes_resources(
    monkeypatch, tmp_path, close_fails,
):
    """Exercise the real capture loop while PortAudio still reports active."""
    from scripts import native_audio_capture as capture
    from scripts import windows_audio_endpoints as endpoints

    backend = api()
    backend.state.side_effect = [ACTIVE, 8]
    monkeypatch.setattr(endpoints, "EndpointMonitor", lambda: EndpointMonitor(backend))
    stream = Mock()
    stream.is_active.return_value = True
    if close_fails:
        stream.close.side_effect = OSError('Périphérique retiré')
    audio = Mock()
    audio.get_host_api_info_by_type.return_value = {"index": 42}
    audio.get_device_info_by_index.return_value = {
        "index": 7, "hostApi": 42, "name": "Casque (Test) [Loopback]",
        "maxInputChannels": 2, "defaultSampleRate": 48000,
        "isLoopbackDevice": True,
    }
    audio.open.return_value = stream
    audio_context = Mock()
    audio_context.__enter__ = Mock(return_value=audio)
    audio_context.__exit__ = Mock(return_value=False)
    monkeypatch.setitem(sys.modules, "pyaudiowpatch", SimpleNamespace(
        PyAudio=lambda: audio_context, paWASAPI=13, paInt16=8, paContinue=0,
    ))
    resampler = Mock()
    tail = Mock()
    tail.to_ndarray.return_value.tobytes.return_value = bytes(320)
    resampler.resample.side_effect = lambda frame: [tail] if close_fails and frame is None else []
    monkeypatch.setitem(sys.modules, "av", SimpleNamespace(
        AudioResampler=Mock(return_value=resampler),
        AudioFrame=Mock(),
    ))
    monkeypatch.setitem(sys.modules, "numpy", SimpleNamespace(frombuffer=Mock(), int16=int))
    kernel = Mock()
    kernel.OpenProcess.return_value = 1
    kernel.WaitForSingleObject.side_effect = [258] * 10 + [0]
    monkeypatch.setattr(capture.ctypes, "WinDLL", lambda *a, **k: kernel, raising=False)
    monkeypatch.setattr(capture, "session_id", lambda pid: 1)
    controls, incoming = queue.Queue(), queue.Queue()
    controls.put({"op": "start"})
    if close_fails:
        stream.start_stream.side_effect = lambda: incoming.put(('system', bytes(320), 80, 1))
    monkeypatch.setattr(capture, "queue", SimpleNamespace(
        Queue=Mock(side_effect=[controls, incoming]), Empty=queue.Empty, Full=queue.Full,
    ))
    monkeypatch.setattr(capture, "threading", SimpleNamespace(Thread=Mock(), Event=Mock()))
    capture.threading.Event.return_value.is_set.return_value = False
    stamps = iter(index * .6 for index in range(100))
    monkeypatch.setattr(capture, "time", SimpleNamespace(
        monotonic=lambda: next(stamps), sleep=lambda _: None,
    ))
    messages = []
    monkeypatch.setattr(capture, "emit", lambda **message: messages.append(message))
    from scripts import native_chunk_journal

    def commit(directory, session, track, sequence, raw, start, *, codec):
        assert directory == tmp_path / 'native'
        assert (session, raw, codec) == ('fake', bytes(320), 'opus')
        return {'kind': 'chunk', 'track': track, 'sequence': sequence,
                'start_ms': start, 'duration_ms': 10, 'size_bytes': 320}

    if close_fails:
        monkeypatch.setattr(native_chunk_journal, 'commit_chunk', commit)

    expected = 'Fermeture audio non confirmée' if close_fails else 'déconnecté.*Casque'
    with pytest.raises(ValueError, match=expected):
        capture.capture({
            "storage": str(tmp_path), "directory": str(tmp_path / "native"),
            "tracks": ["system"], "devices": {"system": 7}, "session_id": "fake",
        }, parent_pid=123)

    assert any(message.get("state") == "recording" for message in messages)
    assert not any(message.get("kind") == "chunk" for message in messages)
    assert backend.state.call_count == 2
    assert all(call.args == ("opaque-0-original",) for call in backend.state.call_args_list)
    stream.stop_stream.assert_not_called()
    if close_fails:
        assert all(call.args != (None,) for call in resampler.resample.call_args_list)
    else:
        assert resampler.resample.call_args.args == (None,)
    stream.close.assert_called_once()
    backend.close.assert_called_once()
    kernel.CloseHandle.assert_called_once_with(1)
