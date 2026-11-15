"""Liaison locale authentifiée et commandes durables Thunderbird."""
import os
import secrets
from datetime import datetime, timezone

from ..db import SessionLocal
from ..models import AppSetting
from .secrets_store import protect, reveal

PRESENCE_GRACE_SECONDS = 180


def presence_connected(last_seen):
    try:
        seen = datetime.fromisoformat(last_seen)
        age = (datetime.now(timezone.utc) - seen.replace(tzinfo=seen.tzinfo or timezone.utc)).total_seconds()
        return 0 <= age < PRESENCE_GRACE_SECONDS
    except (TypeError, ValueError):
        return False


def pairing_token(create=False):
    configured = os.environ.get("PB_THUNDERBIRD_TOKEN")
    if configured:
        return configured
    with SessionLocal() as db:
        row = db.get(AppSetting, "thunderbird_pairing")
        if row:
            return reveal(row.value["token"])
        if create:
            token = secrets.token_urlsafe(32)
            db.add(AppSetting(key="thunderbird_pairing", value={"token": protect(token)}))
            db.commit()
            return token
    return ""


def heartbeat(db, payload):
    row = db.get(AppSetting, "thunderbird_status")
    value = {**payload, "last_seen": datetime.now(timezone.utc).isoformat()}
    if row:
        row.value = value
    else:
        db.add(AppSetting(key="thunderbird_status", value=value))
    db.commit()
    return {"status": "ok", "mail_config": mail_control(db)}


def mail_control(db):
    from .settings_service import get_section
    cfg = get_section(db, "mail")
    return {"source": cfg.get("source", "thunderbird"),
            "auto_scan": cfg.get("auto_scan", True),
            "folder_ids": cfg.get("thunderbird_folder_ids"),
            "interval_minutes": cfg.get("scan_interval_minutes", 5)}
