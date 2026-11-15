"""Validate complete native observations before mapping or SQL publication."""
import math

EXPECTED_OPTIONS = {'language': 'fr', 'beam_size': 1, 'word_timestamps': True,
    'vad_filter': True, 'condition_on_previous_text': False, 'no_speech_threshold': .6,
    'compression_ratio_threshold': 2.4, 'vad_parameters': {'min_silence_duration_ms': 250}}
NATIVE_OPTIONS = {key: EXPECTED_OPTIONS[key] for key in ('beam_size', 'word_timestamps',
    'condition_on_previous_text', 'no_speech_threshold', 'compression_ratio_threshold')}


def _number(value):
    return type(value) in {int, float} and math.isfinite(value)


def _same(actual, expected):
    if isinstance(expected, dict):
        return (isinstance(actual, dict) and set(actual) == set(expected)
                and all(_same(actual[key], value) for key, value in expected.items()))
    return type(actual) is type(expected) and actual == expected


def validate_native_evidence(group, event):
    if event.get('language') != 'fr' or not _same(event.get('effective_transcribe_options'), EXPECTED_OPTIONS):
        raise ValueError('Grouped explicit language or options differ')
    options = event.get('native_transcription_options')
    if not isinstance(options, dict) or any(not _same(options.get(key), value) for key, value in NATIVE_OPTIONS.items()):
        raise ValueError('Grouped native options missing or differ')
    parts, words = event.get('native_segments'), event.get('native_words')
    if (not isinstance(parts, list) or not isinstance(words, list)
            or len(parts) > 20000 or len(words) > 20000):
        raise ValueError('Complete bounded native observations required')
    by_segment = {ordinal: [] for ordinal in range(len(parts))}
    previous = None
    for word in words:
        if not isinstance(word, dict) or set(word) != {'segment_ordinal', 'word_ordinal', 'start', 'end',
                                                       'word', 'retained_by_canonical_filter'}:
            raise ValueError('Native word evidence shape differs')
        segment, ordinal = word['segment_ordinal'], word['word_ordinal']
        if (type(segment) is not int or segment not in by_segment or type(ordinal) is not int
                or ordinal != len(by_segment[segment]) or (previous is not None and (segment, ordinal) <= previous)):
            raise ValueError('Native word ordinals not observed in original order')
        if (not _number(word['start']) or not _number(word['end']) or word['end'] < word['start']
                or not isinstance(word['word'], str) or len(word['word']) > 10000
                or type(word['retained_by_canonical_filter']) is not bool):
            raise ValueError('Invalid native word observation')
        by_segment[segment].append(word)
        previous = segment, ordinal
    retained, canonical = [], []
    for ordinal, part in enumerate(parts):
        if not isinstance(part, dict) or set(part) != {'segment_ordinal', 'start', 'end', 'text',
                                                     'no_speech_prob', 'retained_by_canonical_filter'}:
            raise ValueError('Native segment evidence shape differs')
        if (type(part['segment_ordinal']) is not int or part['segment_ordinal'] != ordinal
                or not _number(part['start']) or not _number(part['end']) or part['end'] < part['start']
                or not isinstance(part['text'], str) or len(part['text']) > 10000
                or not _number(part['no_speech_prob']) or not 0 <= part['no_speech_prob'] <= 1
                or type(part['retained_by_canonical_filter']) is not bool):
            raise ValueError('Invalid native segment observation')
        emitted = [word for word in by_segment[ordinal] if (word['start'] + word['end']) * 500 >= 0]
        text = ''.join(word['word'] for word in emitted).strip()
        keep = bool(text and part['no_speech_prob'] <= .85)
        if part['retained_by_canonical_filter'] != keep:
            raise ValueError('Native segment filter contradicts observed words')
        for word in by_segment[ordinal]:
            if word['retained_by_canonical_filter'] != (keep and word in emitted):
                raise ValueError('Native word filter contradicts observed segment')
            if word['retained_by_canonical_filter']:
                retained.append({key: value for key, value in word.items() if key != 'retained_by_canonical_filter'})
        if keep:
            canonical.append({'start_ms': max(group.offset_ms, group.offset_ms + round(emitted[0]['start'] * 1000)),
                'end_ms': min(group.offset_ms + event['duration_ms'], group.offset_ms + round(emitted[-1]['end'] * 1000)),
                'text': text, 'speaker': group.members[0].track})
    if event.get('retained_words') != retained or event.get('canonical_segments') != canonical:
        raise ValueError('Retained words or canonical segments contradict native evidence')
    return True
