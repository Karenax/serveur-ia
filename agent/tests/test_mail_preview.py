import hashlib
from email.message import EmailMessage

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import Source

client = TestClient(app)


@pytest.fixture
def mail(monkeypatch, tmp_path):
    monkeypatch.setattr("app.services.mail_preview.RAW_DIR", tmp_path)
    message = EmailMessage()
    message["From"] = "Alice <alice@example.com>"
    message["To"] = "Bob <bob@example.com>"
    message["Cc"] = "Carole <carole@example.com>"
    message.set_content("Bonjour")
    message.add_attachment(b"%PDF-1.4 test", maintype="application", subtype="pdf", filename="Plan été.pdf")
    message.add_attachment(b"<script>evil()</script>", maintype="text", subtype="html", filename="page.html")
    raw = message.as_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    (tmp_path/f"{sha}.eml").write_bytes(raw)
    with SessionLocal() as db:
        source = Source(source_type="email", status="resolution_pending", original_uri="", sha256=sha)
        db.add(source)
        db.commit()
        source_id = source.id
    yield source_id, tmp_path/f"{sha}.eml"
    with SessionLocal() as db:
        db.delete(db.get(Source, source_id))
        db.commit()


def test_detail_separates_to_cc_and_lists_previewable_attachments(mail):
    data = client.get(f"/v1/sources/{mail[0]}").json()
    assert data["sender"] == "Alice <alice@example.com>"
    assert data["recipients"] == {"to": ["Bob <bob@example.com>"], "cc": ["Carole <carole@example.com>"]}
    assert [part["previewable"] for part in data["attachments"]] == [True, False]


def test_preview_returns_exact_attachment_and_unicode_filename(mail):
    result = client.get(f"/v1/sources/{mail[0]}/attachments/0")
    assert result.status_code == 200
    assert result.content == b"%PDF-1.4 test"
    assert result.headers["content-type"] == "application/pdf"
    assert result.headers["content-disposition"].startswith("inline;")
    assert "%C3%A9" in result.headers["content-disposition"]
    assert result.headers["x-content-type-options"] == "nosniff"
    assert client.get(f"/v1/sources/{mail[0]}/attachments/0?download=true").headers["content-disposition"].startswith("attachment;")


def test_active_html_is_downloaded_and_invalid_indices_rejected(mail):
    assert client.get(f"/v1/sources/{mail[0]}/attachments/1").headers["content-disposition"].startswith("attachment;")
    for index in [-1, 2]:
        assert client.get(f"/v1/sources/{mail[0]}/attachments/{index}").status_code == 404


def test_absent_original_and_discarded_mail_are_not_accessible(mail):
    mail[1].unlink()
    assert client.get(f"/v1/sources/{mail[0]}/attachments/0").status_code == 404
    with SessionLocal() as db:
        db.get(Source, mail[0]).status = "discarded"
        db.commit()
    assert client.get(f"/v1/sources/{mail[0]}/attachments/0").status_code == 410


def test_preview_prefers_original_html_and_resolves_cid_without_altering_plain_text(mail):
    # Build an alternative/related HTML body with an unnamed inline logo.
    original=EmailMessage()
    original['From']='Alice <alice@example.com>'
    original.set_content('Plain alternative')
    original.add_alternative('<html><head><style>.brand{color:red}</style></head><body><table width="600"><tr><td>Présentation originale</td></tr></table><img src="cid:logo"></body></html>',subtype='html')
    original.get_payload()[1].add_related(b'embedded-image',maintype='image',subtype='png',cid='<logo>')
    mail[1].write_bytes(original.as_bytes())
    result=client.get(f'/v1/sources/{mail[0]}').json()
    assert '.brand{color:red}' in result['body_html']
    assert 'width="600"' in result['body_html']
    assert result['inline_images']['logo'].startswith('data:image/png;base64,')
    assert 'Plain alternative' not in result['body_html']
