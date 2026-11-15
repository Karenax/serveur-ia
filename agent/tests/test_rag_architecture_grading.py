"""Prevent fabricated quotes or model-only guesses from passing the comparison."""
import importlib.util
from pathlib import Path


def load(monkeypatch):
    scripts = Path(__file__).parents[1] / 'scripts'
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location('rag_benchmark', scripts / 'rag_architecture_benchmark.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def row(reference='P1', quote='La passerelle exige un inox 316L.'):
    return {'patterns': ['316l'], 'unknown': False,
            'context': [{'reference': 'P1', 'text': 'La passerelle exige un inox 316L.'}],
            'response': {'answer': 'Inox 316L', 'answerable': True,
                         'citations': [{'reference': reference, 'quote': quote}]}}


def test_grounding_requires_real_reference_and_verbatim_quote(monkeypatch):
    grade = load(monkeypatch).grade
    assert grade(row())['success']
    assert not grade(row(reference='P99'))['success']
    assert not grade(row(quote='Le constructeur valide un inox 316L.'))['success']


def test_audit_annotation_is_distinct_from_wrong_reference(monkeypatch):
    result = load(monkeypatch).grade(row(reference='P1 [PREUVE:A02]'))
    assert result['success'] and not result['references_strict_format']


def test_correct_refusal_is_not_confused_with_boolean_label(monkeypatch):
    entry = row()
    entry['response']['answerable'] = False
    result = load(monkeypatch).grade(entry)
    assert not result['success'] and result['concepts_and_quotes']
