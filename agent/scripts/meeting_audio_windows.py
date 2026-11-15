"""Bounded audio windows and global anonymous speaker grouping.

Decoding stays in memory; the source remains compressed and no PCM file is made.
This module is used by the isolated speech runtime, never by microphone capture.
"""
from contextlib import closing
from dataclasses import dataclass
import math
from types import SimpleNamespace


@dataclass
class AudioWindow:
    samples: object
    offset: float
    last: bool
    sample_rate: int
    overlap_seconds: float

    @property
    def duration(self):
        return len(self.samples) / self.sample_rate

    @property
    def bounds(self):
        return (
            self.offset + (self.overlap_seconds / 2 if self.offset else 0),
            self.offset + self.duration - (0 if self.last else self.overlap_seconds / 2),
        )


def windows_from_blocks(blocks, *, sample_rate=16000, window_seconds=900,
                        overlap_seconds=60, maximum_seconds=None):
    """Retain one decode window, with one owner for each overlap midpoint."""
    import numpy as np

    if (sample_rate <= 0 or not math.isfinite(window_seconds)
            or not 0 < overlap_seconds * 2 < window_seconds):
        raise ValueError('Fenêtre de décodage incohérente')
    size = round(window_seconds * sample_rate)
    overlap = round(overlap_seconds * sample_rate)
    stride = size - overlap
    if overlap <= 0 or stride <= overlap:
        raise ValueError('Recouvrement audio incohérent')
    maximum = None if maximum_seconds is None else round(maximum_seconds * sample_rate)
    parts, count, total, offset = [], 0, 0, 0
    for block in blocks:
        block = np.asarray(block, dtype=np.float32)
        if block.ndim != 1 or not np.isfinite(block).all():
            raise ValueError('Bloc audio mono invalide')
        if not len(block):
            continue
        total += len(block)
        if maximum is not None and total > maximum:
            raise ValueError('Durée audio supérieure à la capacité de capture')
        parts.append(block)
        count += len(block)
        # Wait for one more sample to distinguish an exact full final window.
        while count > size:
            joined = np.concatenate(parts)
            tail = joined[stride:].copy()
            parts, count = [tail], len(tail)
            yield AudioWindow(joined[:size], offset / sample_rate, False,
                              sample_rate, overlap / sample_rate)
            offset += stride
            del joined
    if not total:
        raise ValueError('Audio vide')
    yield AudioWindow(np.concatenate(parts), offset / sample_rate, True,
                      sample_rate, overlap / sample_rate)


def _decoded_blocks(path, av, sample_rate):
    with av.open(str(path)) as source:
        resampler = av.AudioResampler(format='fltp', layout='mono', rate=sample_rate)
        for frame in source.decode(audio=0):
            for converted in resampler.resample(frame):
                yield converted.to_ndarray().reshape(-1)
        for converted in resampler.resample(None):
            yield converted.to_ndarray().reshape(-1)


def decode_windows(path, av, **options):
    rate = options.get('sample_rate', 16000)
    with closing(_decoded_blocks(path, av, rate)) as blocks:
        yield from windows_from_blocks(blocks, **options)


def owned_words(words, window):
    """Keep words by midpoint, then clip their times to the owned interval."""
    begin, end = window.bounds
    result = []
    for word in words:
        start, finish = float(word.start), float(word.end)
        if not math.isfinite(start + finish) or finish < start:
            raise ValueError('Horodatage de mot invalide')
        midpoint = window.offset + (start + finish) / 2
        if begin <= midpoint < end:
            result.append(SimpleNamespace(
                start=max(start, begin - window.offset),
                end=min(finish, end - window.offset), word=word.word))
    return result


def speaker_prototypes(samples, turns, extractor, *, sample_rate=16000,
                       representative_seconds=30):
    """Bound representative speech per local cluster; no voice name is inferred."""
    import numpy as np

    groups = {}
    for turn in sorted(turns, key=lambda item: item.start):
        if turn.speaker >= 0:
            groups.setdefault(turn.speaker, []).append(turn)
    result = {}
    limit = round(representative_seconds * sample_rate)
    for speaker, items in groups.items():
        parts, count = [], 0
        for turn in items:
            start = max(0, round(turn.start * sample_rate))
            end = min(len(samples), round(turn.end * sample_rate), start + limit - count)
            if end > start:
                parts.append(samples[start:end])
                count += end - start
            if count >= limit:
                break
        if not parts:
            continue
        stream = extractor.create_stream()
        stream.accept_waveform(sample_rate, np.concatenate(parts))
        stream.input_finished()
        if not extractor.is_ready(stream):
            continue
        vector = np.asarray(extractor.compute(stream), dtype=np.float32)
        if vector.ndim != 1 or not np.isfinite(vector).all():
            raise ValueError('Empreinte de voix invalide')
        if np.linalg.norm(vector) > 0:
            result[speaker] = vector
    return result


def cluster_speakers(features, sherpa, *, num_speakers=0):
    """Use the installed Sherpa clusterer across all window prototypes."""
    import numpy as np

    if not features:
        return []
    vectors = np.stack(features).astype(np.float32)
    if not np.isfinite(vectors).all() or num_speakers < 0:
        raise ValueError('Empreintes ou nombre de voix invalides')
    if len(features) == 1:
        return ['SPEAKER_01']
    config = sherpa.FastClusteringConfig(
        num_clusters=min(num_speakers, len(features)) if num_speakers else -1,
        threshold=0.5)
    labels = sherpa.FastClustering(config)(vectors)
    if len(labels) != len(features) or any(label < 0 for label in labels):
        raise ValueError('Regroupement des voix invalide')
    names = {}
    return [names.setdefault(label, f'SPEAKER_{len(names) + 1:02d}') for label in labels]
