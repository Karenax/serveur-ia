"""Références explicites et alias métier : suggestion sans affectation."""
from types import SimpleNamespace

import pytest

from app.services.resolution import resolve_project


def project(code="AIRB25LTH0806-A", aliases=None):
    return SimpleNamespace(id=code, code=code, aliases=aliases or [], customer_id=None)


@pytest.mark.parametrize("field", ["subject", "body_text"])
@pytest.mark.parametrize("reference,reason", [
    ("AIRB25LTH0806-A", "explicit_code"),
    ("AIRB26LTH0806-A", "explicit_alias"),
])
def test_declared_reference_in_subject_or_body(field, reference, reason):
    p = project(aliases=["AIRB26LTH0806-A"])
    result = resolve_project({field: f"Livrables {reference.lower()} zone ajustage T et x"}, [p])
    assert result["auto"] is False
    assert result["candidates"][0]["project_id"] == p.id
    assert result["candidates"][0]["score"] >= 0.9
    assert reason in result["candidates"][0]["reasons"]


@pytest.mark.parametrize("reference", [
    "AIRB26LTH0806-A", "XAIRB25LTH0806-A", "AIRB25LTH0806-A-4",
    "AIRB25LTH0806-A-AB", "AIRB25LTH0806-A-4bis", "AIRB25LTH0806-A9",
])
def test_no_inferred_alias_or_partial_code(reference):
    assert resolve_project({"subject": reference}, [project()])["candidates"] == []


@pytest.mark.parametrize("subject", [
    "PO-26-01872-AIRB25LTH0806-A SETAP",
    "PO-26-01872-AIRB25LTH0806-A-Votre colis est en livraison",
    "PO-26-01872-AIRB25LTH0806-A-AFC-STAB 021225",
    "AIRB25LTH0806-A-AMAZON BUSINESS",
    "AIRB25LTH0806-A- Stickers",
    "AIRB25LTH0806-A_CORRECTION CHARIOT",
])
def test_reference_in_purchase_order_and_hyphenated_subjects(subject):
    result = resolve_project({"subject": subject}, [project()])
    assert result["candidates"][0]["reasons"] == ["explicit_code"]


def test_alias_boundaries_and_duplicate_aliases():
    p = project(aliases=["AIRB26LTH0806-A", "airb26lth0806-a", ""])
    assert resolve_project({"body_text": "AIRB26LTH0806-A-4"}, [p])["candidates"] == []
    result = resolve_project({"body_text": "AIRB26LTH0806-A"}, [p])
    assert result["candidates"][0]["score"] == 0.9


def test_reference_has_priority_over_accumulated_context():
    explicit = project(aliases=["AIRB26LTH0806-A"])
    other = project("OTHER-123", ["ajustage", "zone", "livrables"])
    result = resolve_project({"subject": "Livrables AIRB26LTH0806-A zone ajustage"}, [other, explicit])
    assert result["candidates"][0]["project_id"] == explicit.id


def test_textual_alias_remains_a_contextual_hint():
    result = resolve_project({"body_text": "Monte et baisse ATEX"}, [project(aliases=["Monte et baisse"])])
    assert result["candidates"][0]["score"] == 0.4
    assert result["candidates"][0]["reasons"] == ["alias"]
