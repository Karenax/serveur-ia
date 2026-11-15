"""Validate benchmark labels and strict multi-evidence scoring independently of models."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('long_benchmark', Path(__file__).parents[1] / 'scripts' / 'embedding_long_benchmark.py')
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)


def test_gold_is_complete_unique_and_hidden_from_questions():
    documents, passages, questions = benchmark.corpus()
    ids = [p['id'] for p in passages]
    assert len(ids) == len(set(ids))
    assert len(documents) == 6 and all(len(doc['text'].split()) > 2000 for doc in documents)
    assert all(len(p['text']) < 2000 for p in passages)
    for question in questions:
        assert set(question['expected']) <= set(ids)
        assert not benchmark.evidence_ids(question['query'])
    assert sum(len(q['expected']) > 1 for q in questions) >= 8


def test_partial_evidence_does_not_count_as_complete_success():
    query = {'expected': ['A11', 'A12']}
    lookup = {p['id']: p['text'] for p in benchmark.corpus()[1]}
    partial = benchmark.evaluate(query, [lookup['A11']], .1)
    assert partial['any_at_5'] and not partial['all_at_5']
    assert partial['coverage_at_5'] == .5
    complete = benchmark.evaluate(query, [lookup['A11'], lookup['A12']], .1)
    assert complete['all_at_5']
    later = benchmark.evaluate(query, [*[f'[PREUVE:N{i:03}]' for i in range(5)], lookup['A11'], lookup['A12']], .1)
    assert not later['all_at_5'] and later['all_at_10']
    aggregated = benchmark.evaluate(query, ['[PREUVE:N000] ' + lookup['A11'] + ' ' + lookup['A12']], .1)
    assert aggregated['all_at_5'] and aggregated['all_at_context']
    cut = benchmark.evaluate(query, ['x' * 6000 + lookup['A11'] + lookup['A12']], .1)
    assert cut['all_at_5'] and cut['all_at_context']
    assert not benchmark.evaluate(query, [lookup['A11'][:30], lookup['A12']], .1)['all_at_5']
    assert benchmark.evidence_ids('[PREUVE:A1] tronqué') == []
