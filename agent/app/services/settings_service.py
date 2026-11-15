"""Settings persistés (IA + dossier mails)."""
import os
from sqlalchemy.orm import Session
from .secrets_store import protect, reveal
from ..models import AppSetting
from ..config import settings
from .ai_client import DEFAULTS as AI_DEFAULTS
from .mail_ingest import DEFAULT_WATCH_DIR

DEFAULTS = {
    "ai": {**AI_DEFAULTS},
    "mail": {"source": "thunderbird", "thunderbird_folder_ids": None,
             "folder": DEFAULT_WATCH_DIR, "auto_scan": True,
             "scan_interval_minutes": 5, "auto_classification_threshold": 0.75},
    "memory": {"engine": settings.memory_engine, "prefix": "pb",
               "embedding_provider": "openai_compatible",
               "embedding_model": "text-embedding-embeddinggemma-2",
               "embedding_endpoint": "http://192.9.110.115:1234",
               "index_path": "", "timeout_s": 600, "batch_size": 8},
}


def get_all(db: Session) -> dict:
    out = {k: dict(v) for k, v in DEFAULTS.items()}
    for row in db.query(AppSetting).all():
        if row.key.startswith("thunderbird_"):
            continue
        out[row.key] = row.value
    out["ai"] = public_ai(get_section(db, 'ai') if os.environ.get('AGENT_KIARA_INFERENCE_URL') else out["ai"])
    out["mail"] = get_section(db, "mail")
    out["memory"] = get_section(db, "memory")
    return public_settings(out)


def public_settings(value):
    """All sections are public DTOs; encrypted blobs are still secret material."""
    if isinstance(value, list):
        return [public_settings(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {}
    for name, item in value.items():
        if name in {'api_key', 'access_token', 'refresh_token', 'client_secret', 'password', 'secret'}:
            result[name + '_set'] = bool(item)
        else:
            result[name] = public_settings(item)
    return result


def get_section(db: Session, key: str) -> dict:
    kiara_endpoint = os.environ.get('AGENT_KIARA_INFERENCE_URL')
    row = db.query(AppSetting).filter_by(key=key).first()
    if row:
        merged = dict(DEFAULTS.get(key, {}))
        merged.update(row.value or {})
        if key == "memory":
            merged = {k: merged[k] for k in DEFAULTS["memory"]}
            merged["engine"] = settings.memory_engine if os.environ.get("AGENT_TESTING") == "1" else "eg2"
            if kiara_endpoint:
                merged.update(embedding_provider='openai_compatible', embedding_endpoint=kiara_endpoint,
                              embedding_model='google/embeddinggemma-2')
        if key == "ai":
            try:
                merged["api_key"] = os.environ.get("PB_API_KEY") or reveal(merged.get("api_key", ""))
            except (OSError, ValueError):
                merged.update(api_key="", api_key_unavailable=True, enabled=False)
            if kiara_endpoint and os.environ.get('PB_API_KEY'):
                merged.update(provider='openai_compatible', base_url=kiara_endpoint, model='fred-qwen', enabled=True)
        return merged
    defaults = dict(DEFAULTS.get(key, {}))
    if key == "ai" and os.environ.get("PB_API_KEY"):
        defaults["api_key"] = os.environ["PB_API_KEY"]
    if kiara_endpoint and key == 'ai' and os.environ.get('PB_API_KEY'):
        defaults.update(provider='openai_compatible', base_url=kiara_endpoint, model='fred-qwen', enabled=True)
    if kiara_endpoint and key == 'memory':
        defaults.update(embedding_provider='openai_compatible', embedding_endpoint=kiara_endpoint,
                        embedding_model='google/embeddinggemma-2')
    return defaults


def save_section(db: Session, key: str, value: dict) -> dict:
    row = db.query(AppSetting).filter_by(key=key).first()
    merged = {**DEFAULTS.get(key, {}), **(row.value or {} if row else {})}
    updates = dict(value or {})
    if key == "ai":
        if updates.pop("clear_api_key", False):
            updates["api_key"] = ""
        elif not updates.get("api_key"):
            updates.pop("api_key", None)
    merged.update(updates)
    if key == "memory":
        merged = {k: merged[k] for k in DEFAULTS["memory"]}
    stored = dict(merged)
    if key == "ai":
        stored["api_key"] = protect(stored.get("api_key", ""))
    if not row:
        row = AppSetting(key=key, value=stored)
        db.add(row)
    else:
        row.value = stored
    if key == 'ai':
        from .ai_routing import settings_update
        with settings_update(merged):
            db.commit()
    else:
        db.commit()
    return merged


def public_ai(value: dict) -> dict:
    out = dict(value)
    raw = out.pop("api_key", "")
    out["api_key_set"] = bool(os.environ.get("PB_API_KEY") or raw)
    if raw.startswith("dpapi:") and not os.environ.get("PB_API_KEY"):
        try:
            reveal(raw)
        except (OSError, ValueError):
            out["api_key_unavailable"] = True
    return out
