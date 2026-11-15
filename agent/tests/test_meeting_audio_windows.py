"""Long recording primitives: no model, microphone or business database."""
from types import SimpleNamespace as NS
from contextlib import nullcontext

import numpy as np
import pytest

from scripts.meeting_audio_windows import (
    AudioWindow, cluster_speakers, owned_words, speaker_prototypes, windows_from_blocks,
)


@pytest.mark.parametrize('length', [1, 8, 9, 14, 15, 20, 21, 80])
def test_streamed_windows_preserve_samples_and_partition_the_timeline(length):
    source = np.arange(length, dtype=np.float32)
    blocks = (source[start:start + 3] for start in range(0, length, 3))
    rows = list(windows_from_blocks(blocks, sample_rate=1, window_seconds=8,
                                   overlap_seconds=2, maximum_seconds=80))
    assert all(len(row.samples) <= 8 for row in rows)
    assert sum(row.last for row in rows) == 1 and rows[-1].last
    assert rows[0].bounds[0] == 0 and rows[-1].bounds[1] == length
    for left, right in zip(rows, rows[1:]):
        assert left.bounds[1] == right.bounds[0]
        assert np.array_equal(left.samples[-2:], right.samples[:2])
    for row in rows:
        start = round(row.offset)
        assert np.array_equal(row.samples, source[start:start + len(row.samples)])


def test_maximum_uses_actual_decoded_samples_even_when_metadata_is_absent():
    with pytest.raises(ValueError, match='capacité'):
        list(windows_from_blocks([np.zeros(81)], sample_rate=1,
            window_seconds=8, overlap_seconds=2, maximum_seconds=80))


def test_empty_and_non_mono_streams_fail_before_inference():
    for blocks in ([], [np.zeros((2, 4))], [np.array([np.nan])]):
        with pytest.raises(ValueError):
            list(windows_from_blocks(blocks))


def test_overlap_word_belongs_to_exactly_one_window_and_keeps_its_text():
    left = AudioWindow(np.zeros(8), 0, False, 1, 2)
    right = AudioWindow(np.zeros(8), 6, True, 1, 2)
    word = NS(start=6.5, end=7.5, word=' négation')
    assert owned_words([word], left) == []
    kept = owned_words([NS(start=.5, end=1.5, word=word.word)], right)
    assert len(kept) == 1 and kept[0].word == word.word
    assert kept[0].start == 1 and kept[0].end == 1.5


def test_representative_audio_is_bounded_and_insufficient_voice_stays_unknown():
    seen = []
    class Stream:
        def accept_waveform(self, rate, samples):
            seen.append((rate, samples.copy()))
        def input_finished(self):
            pass
    extractor = NS(create_stream=Stream, is_ready=lambda stream: True,
                   compute=lambda stream: [1., 0.])
    samples = np.arange(100, dtype=np.float32)
    turns = [NS(start=0, end=4, speaker=0), NS(start=5, end=9, speaker=0)]
    result = speaker_prototypes(samples, turns, extractor, sample_rate=10,
                                representative_seconds=2)
    assert list(result) == [0] and len(seen[0][1]) == 20
    extractor.is_ready = lambda stream: False
    assert speaker_prototypes(samples, turns, extractor) == {}


def test_global_native_clustering_maps_repeated_voice_across_windows():
    calls = []
    def construct(config):
        calls.append(config)
        return lambda matrix: [8, 3, 8]
    sherpa = NS(FastClusteringConfig=lambda **kw: kw, FastClustering=construct)
    result = cluster_speakers([[1, 0], [0, 1], [.99, .01]], sherpa, num_speakers=2)
    assert result == ['SPEAKER_01', 'SPEAKER_02', 'SPEAKER_01']
    assert calls == [{'num_clusters': 2, 'threshold': .5}]
    assert cluster_speakers([], sherpa) == []


@pytest.fixture
def candidate():
    from scripts import transcribe_meeting
    return transcribe_meeting


@pytest.mark.parametrize('duration', [7201, None])
def test_long_or_unknown_input_routes_to_streaming_without_whole_file_decode(candidate, monkeypatch, duration):
    calls = []
    av = NS(open=lambda path: nullcontext(NS(duration=duration)), time_base=1)
    monkeypatch.setattr(candidate, 'transcribe_windowed', lambda *a, **kw: calls.append(kw))
    candidate.transcribe_meeting(NS(audio='private.ogg'), {}, av, None, None,
                                 lambda *a, **kw: pytest.fail('whole decode'), None)
    assert calls == [{'duration_hint': duration}]


def test_declared_over_capacity_is_refused_before_loading_a_model(candidate):
    av = NS(open=lambda path: nullcontext(NS(duration=43201)), time_base=1)
    with pytest.raises(ValueError, match='12 heures'):
        candidate.transcribe_meeting(NS(audio='private.ogg'), {}, av, None, None, None, None)


def test_windowed_worker_joins_speakers_and_keeps_boundary_words_once(candidate, monkeypatch):
    from scripts import meeting_audio_windows as windows
    audio = np.zeros(8 * 16000, dtype=np.float32)
    def source(*args, **kwargs):
        yield AudioWindow(audio, 0, False, 16000, 2)
        yield AudioWindow(audio, 6, True, 16000, 2)
    monkeypatch.setattr(windows, 'decode_windows', source)
    class Stream:
        def accept_waveform(self, *args):
            pass
        def input_finished(self):
            pass
    config_types = {name: lambda **kw: NS(**kw) for name in (
        'SpeakerEmbeddingExtractorConfig', 'OfflineSpeakerSegmentationModelConfig',
        'OfflineSpeakerSegmentationPyannoteModelConfig', 'FastClusteringConfig')}
    sherpa = NS(**config_types,
        OfflineSpeakerDiarizationConfig=lambda **kw: NS(validate=lambda: True),
        OfflineSpeakerDiarization=lambda config: NS(process=lambda samples: NS(
            sort_by_start_time=lambda: [NS(start=0, end=8, speaker=0)])),
        SpeakerEmbeddingExtractor=lambda config: NS(create_stream=Stream,
            is_ready=lambda stream: True, compute=lambda stream: [1., 0.]),
        FastClustering=lambda config: lambda features: [0] * len(features))
    calls = []
    def transcribe(samples, **options):
        calls.append(options)
        values = [(0., 1., ' début'), (6.5, 7.5, ' mot')] if len(calls) == 1 else [
            (.5, 1.5, ' mot'), (6., 7., ' fin')]
        words = [NS(start=start, end=end, word=text) for start, end, text in values]
        return [NS(words=words, end=words[-1].end)], NS(language='fr')
    monkeypatch.setattr(candidate, 'load_whisper', lambda *args: NS(transcribe=transcribe))
    events = []
    monkeypatch.setattr(candidate, 'emit', lambda **event: events.append(event))
    candidate.transcribe_windowed(NS(audio='private.ogg', speakers=0),
        {'embedding': 'private.onnx', 'segmentation': 'private.onnx'}, None, sherpa,
        None, None, window_seconds=8, overlap_seconds=2)
    final = events[-1]
    assert final['duration_seconds'] == 14
    rows = final['result']['segments']
    assert [r['text'] for r in rows] == ['début', 'mot', 'fin']
    assert [r['speaker'] for r in rows] == ['SPEAKER_01'] * 3
    assert [r['start'] for r in rows] == [0, 7, 12]
    assert final['result']['decode_windows'] == 2


@pytest.mark.parametrize('start,end', [(7199, 7201), (9000, 9000.2), (43199, 43200)])
def test_review_schema_accepts_late_transcript_without_cutting_the_meeting(start, end):
    from app.services.meeting_audio import TranscriptSegment
    segment = TranscriptSegment(id='late', start=start, end=end,
                                speaker='SPEAKER_01', text='Réserve conservée.')
    assert segment.start == start and segment.end == end


def test_review_schema_keeps_the_shared_capture_capacity():
    from app.services.meeting_audio import TranscriptSegment
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        TranscriptSegment(id='outside', start=43200, end=43200.1,
                          speaker='UNKNOWN', text='Hors capacité.')


def test_default_join_preserves_thirty_seconds_of_context_in_both_decodes():
    # A short speech turn straddling ownership must be wholly available in both
    # contexts; a five-second overlap lost a real fictitious turn in qualification.
    source = np.zeros(1000, dtype=np.float32)
    source[865:872] = 1
    left, right = list(windows_from_blocks([source], sample_rate=1))
    join = left.bounds[1]
    assert join == right.bounds[0]
    assert left.offset + left.duration - join >= 30
    assert join - right.offset >= 30
    assert left.samples[865:872].sum() == right.samples[25:32].sum() == 7
