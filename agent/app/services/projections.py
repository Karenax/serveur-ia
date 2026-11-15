"""Durable projection queue: canonical commits survive memory failures."""
import hashlib
import logging
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from sqlalchemy import case

from ..models import MemoryDatasetMapping, MemoryProjection, KnowledgeItem, Source, SourceArtifact
from .eg2_memory import dataset_name_for
from .current_evidence import is_current_evidence

_mail_indexing_lock = threading.Lock()
_mail_indexing = 0


def active_mail_indexing():
    with _mail_indexing_lock:
        return _mail_indexing


@contextmanager
def track_mail_indexing():
    global _mail_indexing
    with _mail_indexing_lock:
        _mail_indexing += 1
    try:
        yield
    finally:
        with _mail_indexing_lock:
            _mail_indexing -= 1


def enqueue(db, project_id, purpose, source_id=None, knowledge_id=None):
    from .settings_service import get_section
    from ..config import settings
    engine = get_section(db, "memory").get("engine") or settings.memory_engine
    prefix = get_section(db, "memory").get("prefix", "pb")
    mapping = db.query(MemoryDatasetMapping).filter_by(
        project_id=project_id, purpose=purpose, engine=engine).first()
    name = dataset_name_for(project_id, purpose, prefix)
    if mapping and mapping.dataset_name != name:
        mapping.dataset_name = name
        for previous in db.query(MemoryProjection).filter_by(dataset_mapping_id=mapping.id, status="indexed"):
            previous.status = "pending"
    if mapping is None:
        mapping = MemoryDatasetMapping(project_id=project_id, purpose=purpose, engine=engine,
                                       dataset_name=dataset_name_for(project_id, purpose, prefix))
        db.add(mapping)
        db.flush()
    row = db.query(MemoryProjection).filter_by(project_id=project_id, purpose=purpose,
                                               source_id=source_id, knowledge_item_id=knowledge_id,
                                               dataset_mapping_id=mapping.id).first()
    if row is None:
        row = MemoryProjection(project_id=project_id, purpose=purpose, source_id=source_id,
                               knowledge_item_id=knowledge_id, dataset_mapping_id=mapping.id,
                               status="pending", content_hash="")
        db.add(row)
    elif row.status not in ("indexed", "pending"):
        row.status = "pending"
    return row


async def process(db, mem, project_id=None, limit=100, projection_ids=None):
    try:
        active = (await mem.health()).get("engine")
    except Exception:
        return {"indexed": 0, "failed": 1, "forgotten": 0}
    query = db.query(MemoryProjection).filter(MemoryProjection.status.in_(["pending", "failed", "obsolete"]))
    if project_id:
        query = query.filter_by(project_id=project_id)
    if projection_ids is not None:
        query = query.filter(MemoryProjection.id.in_(projection_ids))
    rows = query.order_by(case((MemoryProjection.status == "obsolete", 0), else_=1), MemoryProjection.projected_at).limit(limit).all()
    counts = {"indexed": 0, "failed": 0, "forgotten": 0}
    for row in rows:
        try:
            mapping = db.get(MemoryDatasetMapping, row.dataset_mapping_id) if row.dataset_mapping_id else None
            if mapping and mapping.engine != active:
                row.last_error = "Moteur différent ; projection conservée pour reprise avec le moteur d’origine"
                counts["failed"] += 1
                db.commit()
                continue
            if row.status == "obsolete":
                if row.external_ref and not await mem.forget_projection(row.project_id, row.external_ref):
                    raise RuntimeError("Suppression externe non confirmée")
                row.status = "forgotten"
                counts["forgotten"] += 1
            elif row.purpose == "truth":
                item = db.get(KnowledgeItem, row.knowledge_item_id)
                if item is None or item.status != "validated" or item.project_id != row.project_id:
                    row.status = "obsolete"
                    continue
                payload = {"id": item.id, "kind": item.kind, "subject": item.subject,
                           "value": item.value, "version": item.version, "status": item.status}
                row_id, project, owner, version, value = row.id, row.project_id, item.id, item.version, item.value
                if row.external_ref and not await mem.forget_projection(row.project_id, row.external_ref):
                    raise RuntimeError("Ancienne projection non purgée")
                db.commit()
                ref = await mem.remember_truth(project, payload)
                row = await _remembered(db, mem, row_id, project, ref, "truth", owner, version)
                if row is None:
                    continue
                row.content_hash = hashlib.sha256(value.encode()).hexdigest()
                row.projection_version = version
                row.status = "indexed"
                counts["indexed"] += 1
            else:
                source = db.get(Source, row.source_id) if row.source_id else None
                if source is None or source.project_id != row.project_id or not is_current_evidence(source):
                    row.status = "obsolete"
                    continue
                if source.source_type == 'email':
                    from .mail_attachments import prepare
                    await prepare(db, source)
                    db.expire_all()
                    source = db.get(Source, row.source_id)
                    if source is None or source.project_id != row.project_id or not is_current_evidence(source):
                        row.status = 'obsolete'
                        continue
                arts = db.query(SourceArtifact).filter_by(source_id=source.id).all()
                content = "\n".join(a.content_text or "" for a in arts if not (a.content_json or {}).get("superseded")
                                    and a.kind not in {"audio_pending", "attachment_status"})
                row_id, project, owner = row.id, row.project_id, source.id
                is_mail = source.source_type == "email"
                previous_ref = row.external_ref
                db.commit()
                if is_mail:
                    with track_mail_indexing():
                        ref = await mem.remember_evidence(project, content, {"source_id": owner})
                else:
                    ref = await mem.remember_evidence(project, content, {"source_id": owner})
                if previous_ref and previous_ref != ref and not await mem.forget_projection(project, previous_ref):
                    raise RuntimeError("Ancienne projection non purgée")
                row = await _remembered(db, mem, row_id, project, ref, "evidence", owner,
                                       content_hash=hashlib.sha256(content.encode()).hexdigest())
                if row is None:
                    continue
                row.content_hash = hashlib.sha256(content.encode()).hexdigest()
                row.status = "indexed"
                counts["indexed"] += 1
            row.last_error = None
            row.projected_at = datetime.now(timezone.utc)
        except Exception as exc:
            if row.status != "obsolete":
                row.status = "failed"
            row.last_error = type(exc).__name__ + ": projection à reprendre"
            row.projected_at = datetime.now(timezone.utc)
            logging.getLogger(__name__).exception("Échec projection mémoire %s", row.id)
            counts["failed"] += 1
        db.commit()
    return counts


async def _remembered(db, mem, row_id, project_id, ref, purpose, owner_id, version=None, content_hash=None):
    """Recheck canonical ownership after slow indexing; never resurrect old evidence."""
    db.expire_all()
    row = db.get(MemoryProjection, row_id)
    owner = db.get(KnowledgeItem if purpose == "truth" else Source, owner_id)
    valid = (row is not None and row.status in {"pending", "failed", "indexed"}
             and owner is not None and owner.project_id == project_id
             and owner.status == ("validated" if purpose == "truth" else "resolved")
             and (purpose != "truth" or owner.version == version))
    if valid and purpose == "evidence":
        valid = is_current_evidence(owner)
        if valid and content_hash is not None:
            content = "\n".join(a.content_text or "" for a in db.query(SourceArtifact).filter_by(source_id=owner.id)
                                if a.kind not in {"audio_pending", "attachment_status"} and not (a.content_json or {}).get("superseded"))
            valid = hashlib.sha256(content.encode()).hexdigest() == content_hash
    if valid:
        row.external_ref = ref
        return row
    if row is not None:
        row.external_ref, row.status = ref, "obsolete"
        db.commit()  # Preserve cleanup work if the external engine is unavailable.
    else:
        db.rollback()
    forgotten = await mem.forget_projection(project_id, ref)
    db.expire_all()
    row = db.get(MemoryProjection, row_id)
    if row is not None and row.status == "obsolete" and row.external_ref == ref:
        row.status = "forgotten" if forgotten else "obsolete"
        row.last_error = None if forgotten else "Suppression externe à reprendre"
        db.commit()
    return None


async def rebuild_from_canon(db_factory, mem, project_id):
    with db_factory() as db:
        for row in db.query(MemoryProjection).filter_by(project_id=project_id).all():
            if row.status in ("obsolete", "forgotten"):
                row.status = "forgotten"
            else:
                row.status = "pending"
            row.external_ref = None
        truth = db.query(KnowledgeItem).filter_by(project_id=project_id, status="validated").all()
        evidence = db.query(Source).filter_by(project_id=project_id, status="resolved").all()
        for item in truth:
            enqueue(db, project_id, "truth", knowledge_id=item.id)
        for source in evidence:
            enqueue(db, project_id, "evidence", source_id=source.id)
        db.commit()
        result = await process(db, mem, project_id, limit=100000)
        if not result['failed']:
            for mapping in db.query(MemoryDatasetMapping).filter_by(project_id=project_id).all():
                mapping.last_rebuilt_at = datetime.now(timezone.utc)
        db.commit()
        return {"project_id": project_id, "engine": (await mem.health()).get("engine"),
                "status": "rebuilt" if not result["failed"] else "failed",
                "truth": len(truth), "evidence": len(evidence), "projections": result}
