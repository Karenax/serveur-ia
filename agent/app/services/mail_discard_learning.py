"""Explainable discard estimates from human decisions; never auto-discard."""
import hashlib
import re
from dataclasses import dataclass

from sqlalchemy.orm import selectinload

from ..models import AuditLog, Source
from .mail_learning import addresses, authored_text, subject_key, terms

EVENT = "mail.discard_learning.v2"


def _hash(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def fingerprint(sender, subject, body):
    body = authored_text(body)
    body = re.split(r"(?im)^\s*(?:bien\s+cordialement|cordialement|best\s+regards|kind\s+regards|sincerely)\b", body)[0]
    return {"version": 1, "sender": sorted(_hash(s) for s in addresses(sender)),
            "subject": _hash(subject_key(subject)) if subject_key(subject) else None,
            "subject_terms": sorted(_hash(t) for t in terms(subject)),
            "body_terms": sorted(_hash(t) for t in terms(body))}


def source_fingerprint(source):
    body = "\n".join(a.content_text or "" for a in source.artifacts if a.kind == "body_text")
    return fingerprint(source.author or "", (source.source_metadata or {}).get("subject", ""), body)


def remember_discard(db, source):
    if not db.query(AuditLog.id).filter_by(event_type=EVENT, correlation_id=source.id).first():
        db.add(AuditLog(event_type=EVENT, actor="validator", correlation_id=source.id,
                        payload={"fingerprint": source_fingerprint(source)}))


def _jaccard(a, b):
    left, right = set(a), set(b)
    return len(left & right) / len(left | right) if left and right else 0.0


def similarity(a, b):
    sender = bool(set(a["sender"]) & set(b["sender"]))
    same_subject = bool(a["subject"] and a["subject"] == b["subject"])
    subject = _jaccard(a["subject_terms"], b["subject_terms"])
    body = _jaccard(a["body_terms"], b["body_terms"])
    # A shared sender or footer alone must never qualify a message.
    if same_subject:
        return (0.95 if sender else 0.8), "Même objet" + (" et même expéditeur" if sender else "")
    if subject >= 0.5 and (sender or body >= 0.5):
        return min(0.9, 0.45 * subject + 0.35 * body + 0.1 * sender), "Objet et contenu similaires"
    if body >= 0.7 and len(set(a["body_terms"]) & set(b["body_terms"])) >= 5:
        return min(0.8, body * 0.8), "Contenu similaire"
    return 0.0, ""


@dataclass
class DiscardContext:
    discarded: list
    retained: list

    def estimate(self, source):
        current = source_fingerprint(source)
        matches = [similarity(current, saved) for saved in self.discarded]
        matches = [(score, reason) for score, reason in matches if score > 0]
        if not matches:
            return {"probability": None, "discarded_samples": 0, "retained_samples": 0,
                    "reason": "Aucun mail écarté suffisamment similaire", "estimated": True}
        kept = [similarity(current, saved)[0] for source_id, saved in self.retained if source_id != source.id]
        kept = [score for score in kept if score > 0]
        weight = sum(score for score, _ in matches)
        strongest, reason = max(matches)
        probability = strongest * (weight + 0.5) / (weight + sum(kept) + 1)
        return {"probability": round(min(0.99, probability), 3), "discarded_samples": len(matches),
                "retained_samples": len(kept), "reason": reason, "estimated": True}


def build_discard_context(db):
    discarded_ids = {s.id for s in db.query(Source.id).filter_by(source_type="email", status="discarded")}
    discarded = []
    seen = set()
    for audit in db.query(AuditLog).filter_by(event_type=EVENT):
        fp = (audit.payload or {}).get("fingerprint", {})
        if audit.correlation_id in discarded_ids and audit.correlation_id not in seen and fp.get("version") == 1:
            discarded.append(fp)
            seen.add(audit.correlation_id)
    retained = [(s.id, source_fingerprint(s)) for s in db.query(Source).options(selectinload(Source.artifacts))
                .filter_by(source_type="email", status="resolved")] if discarded else []
    return DiscardContext(discarded, retained)
