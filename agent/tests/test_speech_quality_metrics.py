"""Reported accuracy must distinguish format equivalence from wrong values."""
import re

from scripts.qualify_speech_corpus import INDUSTRIAL, fold, wer, words


def test_equivalent_numeric_unit_formats_have_identical_words():
    assert words('16A et 80°C') == words('seize ampères et quatre-vingts degrés Celsius')
    assert words('2 400 €') == words('deux mille quatre cents euros')
    assert words('1 250W') == words('mille deux cent cinquante watts')
    assert words('2,5mm2') == words('deux virgule cinq millimètres carrés')


def test_wrong_industrial_value_and_unit_remain_failures():
    pattern = INDUSTRIAL[2][1]['power']
    assert re.search(pattern, fold('puissance de 1 250W'))
    assert not re.search(pattern, fold('puissance de 2250W'))
    assert wer('mille deux cent cinquante watts', '2250W')['errors'] > 0
    assert not re.search(INDUSTRIAL[0][1]['section_mm2'], fold('2,5 mètres'))


def test_loss_of_negation_and_tax_basis_are_not_normalized_away():
    assert not re.search(INDUSTRIAL[3][1]['negation'], fold('Démarrez la machine'))
    assert re.search(INDUSTRIAL[3][1]['negation'], fold('Ne démarrer pas la machine'))
    assert not re.search(INDUSTRIAL[7][1]['tax_basis'], fold('au Ortax'))
