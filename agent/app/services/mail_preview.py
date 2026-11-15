"""Read recipients and attachments directly from the preserved original mail."""
from app.operational_limits import DOCUMENT_IMPORT_BYTES
import re
import base64
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses

from fastapi import HTTPException

from ..config import RAW_DIR

PREVIEW_TYPES = {"application/pdf", "image/png", "image/jpeg", "image/gif", "image/webp", "text/plain"}


def original_message(source):
    if source.status == "discarded":
        raise HTTPException(410, "Mail écarté : contenu purgé")
    if source.source_type != "email" or not re.fullmatch(r"[a-fA-F0-9]{64}", source.sha256 or ""):
        return None
    path = RAW_DIR / f"{source.sha256}.eml"
    if not path.is_file() or not path.resolve().is_relative_to(RAW_DIR.resolve()):
        return None
    if path.stat().st_size > DOCUMENT_IMPORT_BYTES:
        raise HTTPException(413, "Mail trop volumineux")
    return BytesParser(policy=policy.default).parsebytes(path.read_bytes())


def attachment_parts(message):
    return [part for part in message.walk() if not part.is_multipart()
            and (part.get_content_disposition() == "attachment" or part.get_filename())]


def mail_preview(source):
    message = original_message(source)
    if message is None:
        return {}
    body = message.get_body(preferencelist=('html',))
    html = None
    if body is not None:
        try:
            html = body.get_content()
        except (LookupError, UnicodeError):
            html = (body.get_payload(decode=True) or b'').decode('utf-8', errors='replace')
    inline_images, total = {}, 0
    for part in message.walk():
        cid = str(part.get('Content-ID', '')).strip().strip('<>')
        if not cid or part.get_content_type() not in {'image/png', 'image/jpeg', 'image/gif', 'image/webp'}:
            continue
        content = part.get_payload(decode=True) or b''
        if len(content) > 2 * 1024**2 or total + len(content) > 8 * 1024**2:
            continue
        total += len(content)
        inline_images[cid] = 'data:' + part.get_content_type() + ';base64,' + base64.b64encode(content).decode('ascii')
    return {
        'body_html': html,
        'inline_images': inline_images,
        "sender": str(message.get("From", "")),
        "recipients": {name.lower(): [f"{label} <{address}>" if label else address
                                       for label, address in getaddresses(message.get_all(name, [])) if address]
                       for name in ("To", "Cc")},
        "attachments": [{"index": index, "filename": part.get_filename() or "Pièce jointe",
                         "mime": part.get_content_type(), "previewable": part.get_content_type() in PREVIEW_TYPES}
                        for index, part in enumerate(attachment_parts(message))],
    }
