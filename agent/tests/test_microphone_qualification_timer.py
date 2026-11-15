"""Simulated deadline regressions only; no microphone or subprocess is opened."""
import pytest

from scripts.qualify_microphone_30s import ActiveCaptureWindow, CaptureDeadline


class Clock:
    def __init__(self):
        self.value = 0

    def __call__(self):
        return self.value


def test_slow_open_does_not_consume_thirty_second_capture_window():
    clock = Clock()
    budget = CaptureDeadline(clock)
    clock.value = 13.13
    budget.on_ready()
    clock.value += 30.27
    assert budget.remaining() == pytest.approx(4.73)


def test_almost_expired_open_still_receives_full_capture_and_flush_budget():
    clock = Clock()
    budget = CaptureDeadline(clock)
    clock.value = 44.9
    budget.on_ready()
    assert budget.remaining() == pytest.approx(35)


def test_open_timeout_never_authorizes_start():
    clock = Clock()
    budget = CaptureDeadline(clock)
    clock.value = 45
    with pytest.raises(TimeoutError):
        budget.on_ready()
    assert budget.phase == "opening"


def test_duplicate_ready_cannot_extend_an_active_capture_deadline():
    clock = Clock()
    budget = CaptureDeadline(clock)
    budget.on_ready()
    clock.value = 29
    with pytest.raises(RuntimeError):
        budget.on_ready()
    assert budget.remaining() == 6


def test_flush_grace_is_finite_and_does_not_add_audio_duration():
    clock = Clock()
    budget = CaptureDeadline(clock)
    budget.on_ready()
    clock.value = 35
    assert budget.remaining() == 0


def test_active_window_requires_the_single_start_authorization():
    window = ActiveCaptureWindow(1000, Clock())
    with pytest.raises(RuntimeError):
        window.remaining()


def test_first_packet_late_in_window_cannot_renew_active_capture():
    clock = Clock()
    window = ActiveCaptureWindow(1000, clock)
    window.start(100)
    clock.value = 29
    assert window.accepted_range(128.9, 100, 0) == (0, 100)
    with pytest.raises(RuntimeError):
        window.start(129)
    assert window.remaining() == 1
    clock.value = 30
    assert window.remaining() == 0


def test_buffer_acquired_before_deadline_can_be_drained_after_stop():
    clock = Clock()
    window = ActiveCaptureWindow(1000, clock)
    window.start(100)
    clock.value = 31
    assert window.remaining() == 0
    assert window.accepted_range(129.9, 100, 29_900) == (0, 100)


def test_buffer_acquired_after_deadline_is_not_retained():
    window = ActiveCaptureWindow(1000, Clock())
    window.start(100)
    assert window.accepted_range(130, 100, 29_900) == (0, 0)


def test_buffer_straddling_adc_end_is_clipped_to_authorized_interval():
    window = ActiveCaptureWindow(1000, Clock())
    window.start(100)
    assert window.accepted_range(129.95, 100, 29_900) == (0, 50)


def test_buffer_straddling_adc_start_discards_earlier_samples():
    window = ActiveCaptureWindow(1000, Clock())
    window.start(100)
    assert window.accepted_range(99.95, 100, 0) == (50, 100)


def test_final_buffer_never_exceeds_thirty_second_frame_quota():
    window = ActiveCaptureWindow(1000, Clock())
    window.start(100)
    assert window.accepted_range(129.9, 100, 29_975) == (0, 25)


def test_invalid_adc_clock_cannot_authorize_samples():
    window = ActiveCaptureWindow(1000, Clock())
    with pytest.raises(ValueError):
        window.start(float("nan"))
    window.start(100)
    with pytest.raises(ValueError):
        window.accepted_range(float("inf"), 100, 0)
