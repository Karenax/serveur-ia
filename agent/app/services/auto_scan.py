"""Scan automatique périodique : **nouveaux mails uniquement**, toutes les N minutes.

- `run_auto_scan_once()` : reprise des suggestions au seuil, scan du dossier
  puis tri non-forcé des nouveaux. Testable unitairement, sans boucle.
- `start_auto_scan()` / `stop_auto_scan()` : boucle en thread démon lancée
  par le lifespan. Chaque passage ouvre ses propres sessions ; une passe en
  échec n'arrête jamais la boucle (erreur journalisée dans l'état).
- `AUTO_SCAN_STATE` : dernier passage (horodatage, résultat ou erreur),
  exposé par `GET /v1/ingest/auto-status`.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Nombre max de mails triés par passage auto : l'arriéré se résorbe
# progressivement au lieu de bloquer la boucle pendant des heures.
AUTO_TRIAGE_LIMIT = 20

AUTO_SCAN_STATE: dict = {
    "enabled": False,
    "interval_minutes": 5,
    "running": False,
    "phase": None,
    "pass_started_at": None,
    "last_run_at": None,
    "last_result": None,
    "last_error": None,
    "runs": 0,
}

_stop_event = threading.Event()
_thread: threading.Thread | None = None


def run_auto_scan_once() -> dict:
    """Reprend les classements éligibles, puis importe et analyse les nouveaux."""
    from ..db import SessionLocal
    from ..services.mail_ingest import DEFAULT_WATCH_DIR, scan_folder
    from ..services.memory_factory import get_memory_adapter
    from ..services.settings_service import get_section
    from ..services.triage import TRIAGE_LOCK, auto_classify_pending, triage_pending
    from .workspace_jobs import active_job

    started = datetime.now(timezone.utc).isoformat()
    AUTO_SCAN_STATE.update(running=True, pass_started_at=started)
    try:
        db = SessionLocal()
        try:
            mail_cfg = get_section(db, "mail")
            folder = mail_cfg.get("folder") or DEFAULT_WATCH_DIR
            ai_cfg = get_section(db, "ai")
        finally:
            db.close()
        # Les suggestions déjà analysées sont exclues du tri non forcé.
        # Reprendre leur classement avant tout scan/inférence : ni un dossier
        # indisponible ni un LLM hors ligne ne doivent retenir un score acquis.
        AUTO_SCAN_STATE.update(phase="classification")
        with TRIAGE_LOCK, SessionLocal() as db:
            classification = ({"eligible": 0, "auto_classified": 0, "skipped": 0,
                               "errors": [], "busy": True} if active_job(db)
                              else auto_classify_pending(db, ai_cfg))
        mem = get_memory_adapter(SessionLocal)
        if mail_cfg.get("source") == "thunderbird":
            scan_stats = {"source": "thunderbird", "scanned": 0, "imported": 0,
                          "status": "Synchronisation assurée par la liaison Thunderbird"}
        else:
            AUTO_SCAN_STATE.update(phase="scan")
            scan_stats = scan_folder(folder, SessionLocal, mem, limit=500)
        AUTO_SCAN_STATE.update(phase="analysis")
        db2 = SessionLocal()
        try:
            busy = {"scanned": 0, "triaged": 0, "skipped": 0, "divers": 0,
                    "errors": [], "force": False, "busy": True}
            if active_job(db2):
                tri_stats = busy
            else:
                with TRIAGE_LOCK:
                    tri_stats = busy if active_job(db2) else triage_pending(
                        db2, mem, ai_cfg, limit=AUTO_TRIAGE_LIMIT, force=False)
        finally:
            db2.close()
        result = {"at": started, "scan": scan_stats, "triage": tri_stats,
                  "auto_classification": classification}
        AUTO_SCAN_STATE.update(last_run_at=started, last_result=result,
                               last_error=None, runs=AUTO_SCAN_STATE["runs"] + 1)
        return result
    finally:
        AUTO_SCAN_STATE.update(running=False, phase=None, pass_started_at=None)


def _loop() -> None:
    from ..db import SessionLocal
    from ..services.settings_service import get_section
    interval = 5
    while not _stop_event.is_set():
        try:
            db = SessionLocal()
            try:
                mail_cfg = get_section(db, "mail")
                enabled = mail_cfg.get("auto_scan", True)
                interval = max(1, int(mail_cfg.get("scan_interval_minutes", 5)))
            finally:
                db.close()
            AUTO_SCAN_STATE.update(enabled=enabled, interval_minutes=interval)
            if enabled:
                try:
                    run_auto_scan_once()
                except Exception:
                    AUTO_SCAN_STATE["last_error"] = "échec du passage (voir logs serveur)"
                    logger.exception("Échec du scan automatique")
        except Exception:
            logger.exception("Échec de configuration du scan automatique")
        _stop_event.wait(timeout=interval * 60)


def start_auto_scan() -> None:
    import os
    if os.environ.get("AGENT_TESTING") == "1":
        return
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop_event.clear()
    _thread = threading.Thread(target=_loop, name="auto-scan", daemon=True)
    _thread.start()


def stop_auto_scan() -> None:
    _stop_event.set()
    if _thread and _thread is not threading.current_thread():
        _thread.join(timeout=5)
