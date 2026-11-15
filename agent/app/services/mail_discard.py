"""Écarter un mail : sauvegarde, purge canonique et exclusion durable par hash."""
import asyncio
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import or_

from ..config import RAW_DIR
from ..db_support import backup_sqlite
from ..models import (AuditLog, KnowledgeItem, MemoryProjection, Proposal,
                      ProvenanceLink, Source, SourceArtifact, ValidationDecision)
from .projections import process


def discard_mail(db, mem, source_id):
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(404, "Mail introuvable")
    if source.source_type != "email":
        raise HTTPException(400, "Seuls les mails peuvent être écartés")
    # Ne toucher qu'aux copies Agent, jamais à original_uri/origin_path.
    raw_files = [p for p in RAW_DIR.glob(f"{source.sha256}.*")
                 if p.is_file() and not p.is_symlink()
                 and p.resolve().is_relative_to(RAW_DIR.resolve())]
    backup = None
    if source.status != "discarded":
        bind = db.get_bind()
        if bind.dialect.name != "sqlite" or not bind.url.database or bind.url.database == ":memory:":
            raise HTTPException(503, "Sauvegarde SQLite requise avant la purge")
        path = Path(bind.url.database).resolve()
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        backup = path.parent / "backups" / f"before-mail-discard-{stamp}"
        db.rollback()
        backup_sqlite(path, backup / "project_brain.db")
        for raw in raw_files:
            (backup / "raw").mkdir(exist_ok=True)
            shutil.copy2(raw, backup / "raw" / raw.name)
        # Prend le verrou d'écriture avant de lire les données à purger.
        db.query(Source).filter_by(id=source_id).update({Source.status: "discarded"})
        db.expire_all()
        source = db.get(Source, source_id)
        from .mail_discard_learning import remember_discard
        remember_discard(db, source)
        proposals = db.query(Proposal).filter_by(source_id=source_id).all()
        proposal_ids = [p.id for p in proposals]
        links = db.query(ProvenanceLink).filter_by(source_id=source_id).all()
        item_ids = {link.knowledge_item_id for link in links}
        exclusive_ids = {item_id for item_id in item_ids if not db.query(ProvenanceLink).filter(
            ProvenanceLink.knowledge_item_id == item_id, ProvenanceLink.source_id != source_id).first()}
        projections = db.query(MemoryProjection).filter(or_(
            MemoryProjection.source_id == source_id,
            MemoryProjection.knowledge_item_id.in_(exclusive_ids))).all()
        for projection in projections:
            projection.status = "obsolete"
            projection.source_id = source_id
            projection.last_error = None
        # Les preuves d'autres mails restent valables : seules les connaissances
        # exclusivement issues du mail écarté sont supprimées.
        db.query(ProvenanceLink).filter_by(source_id=source_id).delete(synchronize_session=False)
        if exclusive_ids:
            db.query(ValidationDecision).filter(ValidationDecision.resulting_knowledge_id.in_(exclusive_ids)).update(
                {ValidationDecision.resulting_knowledge_id: None}, synchronize_session=False)
            db.query(KnowledgeItem).filter(KnowledgeItem.supersedes_id.in_(exclusive_ids)).update(
                {KnowledgeItem.supersedes_id: None}, synchronize_session=False)
            db.query(KnowledgeItem).filter(KnowledgeItem.id.in_(exclusive_ids)).delete(synchronize_session=False)
        if proposal_ids:
            db.query(ValidationDecision).filter(ValidationDecision.proposal_id.in_(proposal_ids)).delete(synchronize_session=False)
            db.query(Proposal).filter(Proposal.id.in_(proposal_ids)).delete(synchronize_session=False)
        db.query(SourceArtifact).filter_by(source_id=source_id).delete(synchronize_session=False)
        from ..workspace_models import MailEnrichmentJob
        db.query(MailEnrichmentJob).filter_by(source_id=source_id).delete(synchronize_session=False)
        related_ids = {source_id, *proposal_ids, *exclusive_ids}
        for audit in db.query(AuditLog).all():
            if any(value in json.dumps(audit.payload or {}) for value in related_ids):
                audit.payload = {"source_id": source_id, "redacted": "mail-discarded"}
        source.project_id = None
        source.author = None
        source.participants = []
        source.captured_at = None
        source.original_uri = ""
        source.source_metadata = {}
        source.mime_type = None
        source.retention_policy = "hash-only"
        db.add(AuditLog(event_type="source.discarded.v1", actor="validator",
                        payload={"source_id": source_id}))
        db.commit()
    # La trace reste même si le disque ou EG2 sont momentanément indisponibles.
    raw_pending = False
    for raw in raw_files:
        try:
            raw.unlink(missing_ok=True)
        except OSError:
            raw_pending = True
    projects = {p.project_id for p in db.query(MemoryProjection).filter_by(source_id=source_id)}
    # process() conserve les tâches obsolètes en cas d'échec externe.
    for project_id in projects:
        asyncio.run(process(db, mem, project_id, limit=100000))
    memory_pending = db.query(MemoryProjection).filter_by(source_id=source_id, status="obsolete").count() > 0
    return {"source_id": source_id, "status": "discarded", "backup": str(backup) if backup else None,
            "raw_cleanup_pending": raw_pending, "memory_cleanup_pending": memory_pending}
