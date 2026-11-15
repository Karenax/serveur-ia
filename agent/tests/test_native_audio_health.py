from unittest.mock import Mock
import pytest
from scripts.native_audio_capture import check_stream_health


def stream(active=True):
    return Mock(is_active=Mock(return_value=active))


def test_idle_loopback_is_allowed_indefinitely():
    check_stream_health({"system": stream()}, {}, now=100000, active_since=0)


def test_silent_mic_with_regular_callbacks_is_healthy():
    check_stream_health({"mic": stream()}, {"mic": 99999.9}, now=100000, active_since=0)


def test_removed_mic_without_callbacks_is_interrupted():
    with pytest.raises(ValueError, match="aucune donnée"):
        check_stream_health({"mic": stream()}, {"mic": 102}, now=112, active_since=100)


@pytest.mark.parametrize("track", ["mic", "system"])
def test_stopped_stream_is_not_reported_as_recording(track):
    with pytest.raises(ValueError, match="interrompu"):
        check_stream_health({track: stream(False)}, {}, now=101, active_since=100)


def test_startup_and_resume_have_their_own_callback_grace():
    check_stream_health({"mic": stream()}, {}, now=109.9, active_since=100)
    check_stream_health({"mic": stream()}, {"mic": 101}, now=5009.9, active_since=5000)
    with pytest.raises(ValueError):
        check_stream_health({"mic": stream()}, {}, now=110, active_since=100)


def test_real_device_query_error_is_propagated():
    broken = stream()
    broken.is_active.side_effect = OSError("device invalidated")
    with pytest.raises(OSError, match="invalidated"):
        check_stream_health({"system": broken}, {}, now=101, active_since=100)
