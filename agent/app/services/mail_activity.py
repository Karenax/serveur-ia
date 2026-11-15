"""Read-only mail pipeline status. Waiting work never implies active indexing."""
from datetime import datetime, timezone
from sqlalchemy import func
from sqlalchemy.orm import load_only

from app.db_support import utc_iso
from app.models import AppSetting, MemoryDatasetMapping, MemoryProjection, Source, ThunderbirdJob
from app.services.settings_service import get_section
from app.services.thunderbird import presence_connected
from app.workspace_models import MailEnrichmentJob, TriageJob


def snapshot(db):
    from app.services.auto_scan import AUTO_SCAN_STATE
    from app.services.triage import pending_triage_query
    from app.services.projections import active_mail_indexing

    config = get_section(db, "mail")
    presence = db.get(AppSetting, "thunderbird_status")
    tb = dict(presence.value or {}) if presence else {}
    tb["connected"] = presence_connected(tb.get("last_seen"))
    sync = tb.get("sync") or {}
    commands = db.query(ThunderbirdJob).filter(
        ThunderbirdJob.kind == "sync", ThunderbirdJob.status.in_(["queued", "running"])).count()
    if config["source"] == "thunderbird":
        state = ("offline" if not tb["connected"] else "running" if sync.get("running") else
                 "failed" if sync.get("last_error") else "queued" if commands or sync.get("more_pending") else "idle")
        queued_detail = ("Demande en attente" if commands else "Prochain passage automatique" if config["auto_scan"]
                         else "Relancer un passage manuel")
        detail = ("Thunderbird déconnecté" if state == "offline" else queued_detail if state == "queued"
                  else "Transfert en cours" if state == "running" else "Erreur de transfert" if state == "failed"
                  else "En veille" if config["auto_scan"] else "Automatisme désactivé")
        processed, total = sync.get("processed"), sync.get("total")
        if processed is not None and total is not None:
            detail = f"{processed} / {total} mails · " + detail
        elif state == "running":
            detail += " · compteur indisponible"
        transfer = {"state": state, "detail": detail, "processed": processed, "total": total,
                    "more_pending": bool(sync.get("more_pending"))}
    else:
        running = bool(AUTO_SCAN_STATE["running"] and AUTO_SCAN_STATE.get("phase") == "scan")
        transfer = {"state": "running" if running else "failed" if AUTO_SCAN_STATE.get("last_error") else "idle",
                    "detail": "Passage EML en cours" if running else "En veille" if config["auto_scan"] else "Automatisme désactivé",
                    "processed": None, "total": None, "more_pending": False}
    triage_query = db.query(TriageJob).options(load_only(
        TriageJob.status, TriageJob.processed, TriageJob.total, TriageJob.created_at))
    triage = (triage_query.filter(TriageJob.status.in_(["running", "queued"]))
              .order_by(TriageJob.created_at).first())
    if triage is None:
        triage = triage_query.order_by(TriageJob.created_at.desc()).first()
    enrichment = (db.query(MailEnrichmentJob.status, MailEnrichmentJob.stage, func.count())
                  .join(Source, Source.id == MailEnrichmentJob.source_id)
                  .filter(Source.status == "resolved", Source.project_id == MailEnrichmentJob.project_id)
                  .group_by(MailEnrichmentJob.status, MailEnrichmentJob.stage).all())

    def count(status, stage):
        return sum(n for s, step, n in enrichment if s == status and step == stage)

    pending = pending_triage_query(db).count()
    automatic = bool(AUTO_SCAN_STATE["running"] and AUTO_SCAN_STATE.get("phase") == "analysis")
    analysis_running = bool(triage and triage.status == "running") or automatic or count("running", "extraction") > 0
    analysis_state = ("running" if analysis_running else "failed" if (triage and triage.status == "failed")
                      or count("failed", "extraction") else "queued" if pending or (triage and triage.status == "queued")
                      or count("queued", "extraction") else "idle")
    analysis = {"state": analysis_state, "processed": triage.processed if triage else None,
                "total": triage.total if triage else None,
                "detail": "Analyse à reprendre" if analysis_state == "failed"
                else f"{triage.processed} / {triage.total} mails" if triage and triage.status in {"queued", "running"}
                else "Analyse automatique" if automatic else "Extraction des informations" if count("running", "extraction")
                else f"{pending} mail(s) à analyser" if pending else "Aucune analyse en cours"}
    projections = (db.query(MemoryProjection.status, func.count())
                   .join(Source, Source.id == MemoryProjection.source_id)
                   .join(MemoryDatasetMapping, MemoryDatasetMapping.id == MemoryProjection.dataset_mapping_id)
                   .filter(Source.source_type == "email", Source.status == "resolved",
                           Source.project_id == MemoryProjection.project_id, MemoryProjection.purpose == "evidence",
                           MemoryDatasetMapping.engine == get_section(db, "memory")["engine"])
                   .group_by(MemoryProjection.status).all())
    totals = dict(projections)
    indexed, waiting, failed = totals.get("indexed", 0), totals.get("pending", 0), totals.get("failed", 0)
    indexing = {"state": "running" if active_mail_indexing() or count("running", "memory") else "failed" if failed or count("failed", "memory")
                else "queued" if waiting or count("queued", "memory") else "idle",
                "processed": indexed, "total": indexed + waiting + failed,
                "detail": f"{indexed} indexé(s) · {waiting} en attente" + (f" · {failed} en erreur" if failed else "")}
    events = [{"key": label, "text": f"{label} : {step['detail']}", "state": step["state"]}
              for label, step in [("Synchro", transfer), ("Analyse", analysis), ("Mémoire", indexing)]]
    if transfer["more_pending"]:
        events.append({"key": "remaining", "text": "Transfert : suite au prochain passage", "state": "queued"})
    if config["source"] == "thunderbird" and sync.get("total") is None and tb.get("version") == "0.1.0":
        events.append({"key": "version", "text": "Compteur de transfert : liaison 0.2.0 requise", "state": "queued"})
    return {"source": config["source"], "transfer": transfer, "analysis": analysis, "indexing": indexing,
            "events": events, "checked_at": utc_iso(datetime.now(timezone.utc))}
