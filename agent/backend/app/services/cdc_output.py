"""Shared eligibility for technical BE outputs."""
from fastapi import HTTPException

from ..models import CdcItem
from .cdc_generation import run_deterministic_checks


def output_items(db, project_id: str, draft: bool = False):
    items = db.query(CdcItem).filter(
        CdcItem.project_id == project_id,
        CdcItem.knowledge_status.notin_(["rejected", "superseded"]),
    ).all()
    if not items:
        raise HTTPException(400, "Aucun élément actif à exporter")
    checks = run_deterministic_checks(db, project_id)
    pending = [i.id for i in items if i.knowledge_status != "confirmed"]
    blockers = [c for c in checks if c["severity"] == "blocker"]
    if not draft and (pending or blockers):
        raise HTTPException(409, detail={
            "message": "Revue incomplète ou contrôle bloquant : sortie finale interdite",
            "pending_items": pending, "blockers": blockers,
        })
    return items, checks
