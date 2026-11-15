"""Intégration extension Infomaniak : les .eml produits (Infomaniak-IA/*) doivent parser."""
import os
from pathlib import Path

from app.services.ingestion import parse_eml
from app.services.mail_ingest import DEFAULT_WATCH_DIR


def test_infomaniak_eml_parses():
    folder = Path(os.environ.get("PB_INFOMANIAK_DIR", DEFAULT_WATCH_DIR))
    files = sorted(folder.glob("*.eml"))
    if not files:
        import pytest
        pytest.skip("dossier Infomaniak-IA absent")
    ok = 0
    for f in files[:10]:
        d = parse_eml(f.read_bytes())
        assert d["subject"], f.name
        assert d["body_text"], f.name
        ok += 1
    assert ok > 0
