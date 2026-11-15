"""Identité MIME stable malgré les en-têtes d'état Thunderbird et les frontières."""
import hashlib
import json
from email import policy
from email.parser import BytesParser

from ..models import MailIdentity, Source


def fingerprint(raw):
    mail = BytesParser(policy=policy.default).parsebytes(raw)
    headers = {name: " ".join(str(mail.get(name, "")).split()) for name in
               ("Message-ID", "From", "To", "Cc", "Date", "Subject", "In-Reply-To", "References")}
    parts = []
    for part in mail.walk():
        if part.is_multipart():
            continue
        data = part.get_payload(decode=True) or b""
        if part.get_content_maintype() == "text":
            try:
                data = data.decode(part.get_content_charset() or "utf-8", errors="replace").replace("\r\n", "\n").encode()
            except LookupError:
                data = data.replace(b"\r\n", b"\n")
        parts.append([part.get_content_type(), part.get_filename(), hashlib.sha256(data).hexdigest()])
    return hashlib.sha256(json.dumps([headers, parts], sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def remember_identity(db, source_id, raw):
    key = fingerprint(raw)
    if not db.get(MailIdentity, key):
        db.add(MailIdentity(fingerprint=key, source_id=source_id))
    return key


def backfill(db, raw_dir, backup_dir):
    """Migration additive ; les anciens mails écartés restent exclus."""
    count = 0
    for source in db.query(Source).filter_by(source_type="email").all():
        paths = list(raw_dir.glob(f"{source.sha256}.eml"))
        if not paths and source.status == "discarded":
            paths = list(backup_dir.glob(f"before-mail-discard-*/raw/{source.sha256}.eml"))
        if paths:
            remember_identity(db, source.id, paths[0].read_bytes())
            count += 1
    db.commit()
    return count
