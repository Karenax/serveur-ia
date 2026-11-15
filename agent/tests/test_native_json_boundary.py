"""Four prepared pure regressions: exact fictitious response, no model or SQL."""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import unittest

from scripts.grouped_pcm_core import GroupRefused,group_from_manifest,map_words
from scripts.grouped_pcm_worker import native_json_number
from scripts.grouped_response_evidence import validate_native_evidence

FIXTURES=Path(__file__).parent/'fixtures/grouped-native-json'


class NativeFloatFixture(float):
    """FICTITIOUS raw float subclass; not a claim about actual FW runtime type."""
    def __repr__(self):return 'FICTITIOUS-repr-different-from-JSON'
    def __str__(self):return 'FICTITIOUS-str-different-from-JSON'
    def __float__(self):return -999.0 # Base numeric payload remains unchanged.


def actual_fictitious():
    request=json.loads((FIXTURES/'actual-fictitious-request.jsonl').read_text(encoding='utf-8'))
    event=json.loads((FIXTURES/'actual-fictitious-responses.jsonl').read_text(encoding='utf-8').splitlines()[1])
    return group_from_manifest(request['manifest']),event


class NativeJSONBoundary(unittest.TestCase):
    def test_01_actual_42_word_regression_same_values_and_five_slices(self):
        group,event=actual_fictitious()
        self.assertEqual((event['mapping_status'],event['mapping_refusal'],event['segments']),
            ('refused','nonfinite_native_timestamp',[]))
        raw=[{**w,'start':NativeFloatFixture(w['start']),'end':NativeFloatFixture(w['end'])}
             for w in event['retained_words']]
        with self.assertRaisesRegex(GroupRefused,'nonfinite_native_timestamp'):
            map_words(group,raw)
        normalized=[{**w,'start':native_json_number(w['start']),'end':native_json_number(w['end'])} for w in raw]
        self.assertEqual(normalized,event['retained_words'])
        self.assertEqual(json.loads(json.dumps(raw)),normalized)
        self.assertTrue(all(type(w[k]) is float for w in normalized for k in ('start','end')))
        mapped=map_words(group,normalized)
        expected=json.loads((FIXTURES/'independently-derived-mapping.json').read_text(encoding='utf-8'))
        self.assertEqual(mapped,expected['segments'])
        self.assertEqual(len(normalized),42)
        self.assertEqual([(s['chunk_id'],s['start_ms'],s['end_ms']) for s in mapped],
            [('clean-02',0,4400),('clean-02',4400,5600),('clean-03',6020,11200),
             ('clean-09',12130,12950),('clean-09',12950,17850)])

    def test_02_native_parts_and_words_keep_original_filter_text_and_values(self):
        group,event=actual_fictitious()
        normalized=deepcopy(event)
        for key in ('native_words','retained_words','native_segments'):
            for row in normalized[key]:
                for field in ('start','end','no_speech_prob'):
                    if field in row:
                        row[field]=native_json_number(NativeFloatFixture(row[field]))
        self.assertEqual(normalized,event)
        self.assertTrue(validate_native_evidence(group,normalized))
        self.assertEqual(normalized['canonical_segments'],event['canonical_segments'])

    def test_03_bool_nonfinite_and_non_JSON_numeric_types_still_refused(self):
        for value in (True,False,float('nan'),float('inf'),-float('inf'),'0.3',Decimal('0.3'),None):
            with self.subTest(value=repr(value)),self.assertRaisesRegex(GroupRefused,'nonfinite_native_timestamp'):
                native_json_number(value)
        self.assertEqual(native_json_number(2),2)
        self.assertEqual(type(native_json_number(2)),int)

    def test_04_normalization_does_not_clip_crossing_or_overlap(self):
        group,event=actual_fictitious()
        for changed,reason in (({'start':5.6,'end':6.02},'word_crosses_source_boundary'),
                ({'start':0.2,'end':1.1},'word_out_of_range_or_nonpositive_or_overlapping')):
            words=deepcopy(event['retained_words'])
            index=12 if reason=='word_crosses_source_boundary' else 1
            words[index].update({k:native_json_number(NativeFloatFixture(v)) for k,v in changed.items()})
            with self.subTest(reason=reason),self.assertRaisesRegex(GroupRefused,reason):
                map_words(group,words)


if __name__=='__main__':
    unittest.main()
