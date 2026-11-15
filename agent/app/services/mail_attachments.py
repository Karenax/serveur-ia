"""Attach extracted evidence to the parent mail, with its existing project boundary."""
import asyncio
from collections import Counter
from email import policy
from email.parser import BytesParser
import hashlib
from pathlib import Path
import re
import uuid

from sqlalchemy import update

from ..models import Source, SourceArtifact
from .current_evidence import is_current_evidence
from .mail_attachment_extraction import VERSION, INTERPRETATION_REVISION, MAX_BYTES, extract_attachment
from .mail_preview import attachment_parts


def _scan(sha256, storage):
    path = Path(storage) / 'raw' / (sha256 + '.eml')
    root = (Path(storage) / 'raw').resolve()
    if not path.is_file() or not path.resolve().is_relative_to(root) or path.is_symlink():
        raise ValueError('Original du mail indisponible ; pièces jointes à reprendre')
    if path.stat().st_size > MAX_BYTES:
        raise ValueError('Original du mail trop volumineux')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha256:
        raise ValueError('Empreinte de l’original incompatible')
    message = BytesParser(policy=policy.default).parsebytes(raw)
    records = []
    for index, part in enumerate(attachment_parts(message)):
        filename = part.get_filename() or 'Pièce jointe'
        data = part.get_payload(decode=True) or b''
        digest = hashlib.sha256(data).hexdigest()
        try:
            items = extract_attachment(data, filename, part.get_content_type(), storage)
        except Exception as exc:
            error = str(exc)[:300]
            state = ('too_large' if any(term in error.casefold() for term in ('trop volumineux', 'supérieur à'))
                     else 'encrypted' if any(term in error.casefold() for term in ('chiffr', 'encrypted')) else 'failed')
            items = [{'text': '', 'status': state, 'locator': {
                'error_type': type(exc).__name__, 'extraction_error': error}}]
        records.append({'index': index, 'filename': filename, 'mime': part.get_content_type(),
                        'sha256': digest, 'size_bytes': len(data), 'items': items})
    if sum(len(item['text']) for record in records for item in record['items']) > 10_000_000:
        raise ValueError('Texte des pièces jointes supérieur à 10 millions de caractères par mail')
    return records


async def prepare(db, source, *, retry=False):
    """Parse outside the SQL transaction, then recheck classification before writing."""
    if source.source_type != 'email' or not is_current_evidence(source):
        return False
    previous = (source.source_metadata or {}).get('attachment_extraction') or {}
    if (previous.get('version') == VERSION and previous.get('revision') == INTERPRETATION_REVISION
            and previous.get('complete') and not retry):
        return False
    if not re.fullmatch(r'[a-fA-F0-9]{64}', source.sha256 or ''):
        return False  # Legacy/test source without a managed original.
    from ..config import settings
    # Old text-only fixtures have no original; actual declared attachments must fail visibly.
    path = Path(settings.storage_dir) / 'raw' / (source.sha256 + '.eml')
    if not path.is_file() and not (source.source_metadata or {}).get('attachments'):
        return False
    source_id, project_id, original_hash = source.id, source.project_id, source.sha256
    db.commit()
    records = await asyncio.to_thread(_scan, original_hash, settings.storage_dir)
    # Short write lock serializes competing extraction/classification/discard commits.
    valid = db.execute(update(Source).where(Source.id == source_id, Source.status == 'resolved',
        Source.project_id == project_id, Source.sha256 == original_hash).values(status='resolved'))
    db.expire_all()
    source = db.get(Source, source_id)
    if valid.rowcount != 1 or not is_current_evidence(source):
        db.rollback()
        return False
    existing = {row.id: row for row in db.query(SourceArtifact).filter_by(source_id=source_id)}
    active = set()
    statuses = Counter()
    summary = []
    changed = False
    for record in records:
        states = Counter()
        for ordinal, item in enumerate(record['items']):
            states[item['status']] += 1
            artifact_id = str(uuid.uuid5(uuid.NAMESPACE_URL,
                f"{VERSION}:{source_id}:{record['index']}:{record['sha256']}:{ordinal}"))
            active.add(artifact_id)
            locator = {**item['locator'], 'attachment_index': record['index'],
                'filename': record['filename'], 'attachment_sha256': record['sha256'],
                'extraction_version': VERSION, 'extraction_status': item['status'], 'ordinal': ordinal}
            label = record['filename'] + (' / ' + locator['archive_member'] if locator.get('archive_member') else '')
            text = '\n\nPièce jointe : ' + label + '\n' + item['text'] if item['text'].strip() else ''
            kind = 'attachment_text' if text else 'attachment_status'
            old = existing.get(artifact_id)
            if old is None:
                db.add(SourceArtifact(id=artifact_id, source_id=source_id, kind=kind,
                                      content_text=text, content_json=locator))
                changed = changed or bool(text)
            elif old.content_text != text or old.content_json != locator:
                changed = changed or old.content_text != text
                old.kind, old.content_text, old.content_json = kind, text, locator
        statuses.update(states)
        summary.append({k: v for k, v in record.items() if k != 'items'} | {'states': dict(states)})
    for old in existing.values():
        if old.kind in {'attachment_text', 'attachment_status'} and old.id not in active:
            if not (old.content_json or {}).get('superseded'):
                old.content_json = {**old.content_json, 'superseded': True}
                changed = changed or bool(old.content_text)
    source.source_metadata = {**source.source_metadata, 'attachment_extraction': {
        'version': VERSION, 'revision': INTERPRETATION_REVISION,
        'complete': not any(statuses[s] for s in ('failed', 'ocr_required')),
        'parts': summary, 'states': dict(statuses)}}
    db.commit()
    return changed
