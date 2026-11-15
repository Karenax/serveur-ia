"""Qualification timecodes stay those of the decoder, without audio/model load."""
from types import SimpleNamespace

import pytest

from scripts.qualify_speech_segments import segment_row


def test_segment_timecodes_preserve_real_decoder_boundaries():
    row = segment_row(SimpleNamespace(start=1.24, end=3.88, text=" Valeur fictive. "))
    assert (row["start_ms"], row["end_ms"]) == (1240, 3880)
    assert (row["raw_start_s"], row["raw_end_s"]) == (1.24, 3.88)
    assert row["text"] == "Valeur fictive."
    assert row["timestamp_origin"] == "decoder_segment_restored_by_vad"


def test_out_of_audio_boundary_is_preserved_for_report_rejection_not_clamped():
    row = segment_row(SimpleNamespace(start=-.02, end=.8, text="Fictif"))
    assert row["start_ms"] == -20
    assert row["raw_start_s"] == -.02


@pytest.mark.parametrize("begin,end", [(float("nan"), 1), (0, float("inf")), (2, 1)])
def test_invalid_decoder_timestamps_cannot_be_replaced_with_invented_locators(begin, end):
    with pytest.raises(ValueError):
        segment_row(SimpleNamespace(start=begin, end=end, text="Fictif"))
