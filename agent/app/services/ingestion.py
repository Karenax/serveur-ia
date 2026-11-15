"""Ingestion: hash, idempotence, parsing .eml / audio."""
import hashlib
import email
import email.policy
from email.utils import getaddresses, parsedate_to_datetime
from datetime import timezone


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_eml(raw: bytes) -> dict:
    msg = email.message_from_bytes(raw, policy=email.policy.default)
    subject = str(msg.get("Subject", "") or "")
    sender = str(msg.get("From", "") or "")
    to = [a[1] for a in getaddresses(msg.get_all("To", []))]
    cc = [a[1] for a in getaddresses(msg.get_all("Cc", []))]
    msg_id = str(msg.get("Message-ID", "") or "")
    date_raw = msg.get("Date")
    captured = None
    if date_raw:
        try:
            captured = parsedate_to_datetime(str(date_raw))
            if captured.tzinfo is None:
                captured = captured.replace(tzinfo=timezone.utc)
        except Exception:
            captured = None
    body_text = ""
    body_html = ""
    attachments: list[dict] = []
    if msg.is_multipart():
        for part in msg.walk():
            if part.is_multipart():
                continue
            ctype = part.get_content_type()
            disp = part.get_content_disposition() or ""
            try:
                payload = part.get_content()
            except Exception:
                payload = None
            if disp == "attachment":
                attachments.append({"filename": part.get_filename() or "unnamed",
                                    "mime": ctype})
            elif ctype == "text/plain" and isinstance(payload, str) and not body_text:
                body_text = payload
            elif ctype == "text/html" and isinstance(payload, str) and not body_html:
                body_html = payload
    else:
        try:
            payload = msg.get_content()
            if isinstance(payload, str):
                if msg.get_content_type() == "text/html":
                    body_html = payload
                else:
                    body_text = payload
        except Exception:
            pass
    return {
        "subject": subject, "sender": sender, "to": to, "cc": cc,
        "message_id": msg_id, "captured_at": captured,
        "in_reply_to": str(msg.get("In-Reply-To", "") or ""),
        "references": str(msg.get("References", "") or ""),
        "body_text": body_text or body_html or "",
        "body_html present": bool(body_html),
        "attachments": attachments,
    }


def extract_candidates(body: str, subject: str) -> list[dict]:
    """Heuristique baseline sans LLM : actions, dates, décisions."""
    import re
    out: list[dict] = []
    text = f"{subject}\n{body}"
    # Action si impératif / TODO / verbe d'action
    if re.search(r"(?i)\b(todo|action|faire|envoyer|préparer|valider|rappeler|call|send|prepare)\b", text):
        out.append({"kind": "action", "subject": subject[:120] or "Action issue du mail",
                    "value": body[:500], "confidence": 0.55,
                    "reason": "mot-clé action détecté"})
    # Date / jalon : JJ/MM/AAAA ou YYYY-MM-DD
    m = re.search(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})\b", text)
    if m:
        out.append({"kind": "milestone", "subject": subject[:120] or "Échéance",
                    "value": f"Date détectée: {m.group(1)}", "confidence": 0.6,
                    "reason": "date explicite"})
    # Décision
    if re.search(r"(?i)\b(décid[ée]|valid[ée]|act[ée]|confirmé|approved|decision)\b", text):
        out.append({"kind": "decision", "subject": subject[:120] or "Décision possible",
                    "value": body[:500], "confidence": 0.5,
                    "reason": "mot-clé décision"})
    if not out:
        out.append({"kind": "free_information", "subject": subject[:120] or "Info mail",
                    "value": body[:800], "confidence": 0.4, "reason": "extraction baseline"})
    return out
