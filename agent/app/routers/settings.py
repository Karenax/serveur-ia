"""API paramétrage IA + dossier mails."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from typing import Literal
from sqlalchemy.orm import Session
from ..db import get_db
from ..services import settings_service as svc
from ..services import ai_client as ai

router = APIRouter(prefix="/v1/settings", tags=["settings"])


@router.get('/memory/recovery')
def memory_recovery_status(db: Session = Depends(get_db)):
    from ..services.memory_recovery import snapshot
    return snapshot(db)


@router.post('/memory/recovery', status_code=202)
def memory_recovery_start(db: Session = Depends(get_db)):
    from ..services.memory_recovery import start
    return start(db)


class AISettings(BaseModel):
    provider: Literal["none", "ollama", "openai_compatible"] = "ollama"
    base_url: str = "http://localhost:11434"
    model: str = "llama3.1"
    api_key: str | None = None
    clear_api_key: bool = False
    enabled: bool = False
    timeout_s: int = Field(default=600, ge=1, le=86400)
    fallback_enabled: bool = False
    fallback_base_url: str = "http://127.0.0.1:1234"
    fallback_model: str = Field(default="google/gemma-4-e4b", min_length=1, max_length=256)
    fallback_autostart: bool = False

    @field_validator("fallback_base_url")
    @classmethod
    def local_only(cls, value):
        from ..services.ai_routing import local_config
        local_config({"enabled": True, "fallback_enabled": True, "fallback_base_url": value})
        return value.rstrip("/")


class MailSettings(BaseModel):
    source: Literal["folder", "thunderbird"] = "thunderbird"
    thunderbird_folder_ids: list[str] | None = Field(default=None, max_length=1000)
    folder: str = ""
    auto_scan: bool = True
    scan_interval_minutes: int = Field(default=5, ge=1, le=1440)
    auto_classification_threshold: float = Field(default=0.75, ge=0.01, le=1.0, allow_inf_nan=False)


class MemorySettings(BaseModel):
    engine: Literal["eg2"] = "eg2"
    prefix: str = Field(default="pb", pattern=r"^[a-zA-Z0-9_-]{1,32}$")
    embedding_provider: Literal["openai_compatible"] = "openai_compatible"
    embedding_model: str = Field(default="text-embedding-embeddinggemma-2", max_length=256)
    embedding_endpoint: str = Field(default="http://192.9.110.115:1234", max_length=512)
    index_path: str = Field(default="", max_length=1024)
    timeout_s: int = Field(default=600, ge=1, le=86400)
    batch_size: int = Field(default=8, ge=1, le=32)


@router.get("")
def get_settings(db: Session = Depends(get_db)):
    data = svc.get_all(db)
    # masque partiellement la clé
    if data.get("ai", {}).get("api_key"):
        data["ai"]["api_key_set"] = True
    return data


@router.put("/ai")
def put_ai(body: AISettings, db: Session = Depends(get_db)):
    return svc.public_ai(svc.save_section(db, "ai", body.model_dump(exclude_unset=True)))


@router.put("/mail")
def put_mail(body: MailSettings, db: Session = Depends(get_db)):
    changes = body.model_dump(exclude_unset=True)
    # Historical clients submitting only an EML folder keep that explicit choice.
    if "source" not in changes and "folder" in changes:
        changes["source"] = "folder"
    return svc.save_section(db, "mail", changes)


@router.put("/memory")
def put_memory(body: MemorySettings, db: Session = Depends(get_db)):
    if body.engine not in ("eg2",):
        from fastapi import HTTPException
        raise HTTPException(400, "engine doit être eg2")
    return svc.save_section(db, "memory", body.model_dump())


@router.get("/memory/engines")
def engines(db: Session = Depends(get_db)):
    from ..services.memory_factory import get_memory_adapter
    from ..db import SessionLocal
    active = get_memory_adapter(SessionLocal)
    return {"configured": svc.get_section(db, "memory"),
            "active": {"engine": type(active).__name__,
                       "health": __import__("asyncio").run(active.health())}}


@router.post("/ai/test")
def test_ai(db: Session = Depends(get_db)):
    cfg = svc.get_section(db, "ai")
    outcome = ai.check_connection(cfg)
    from ..services.connection_health import record_llm_test
    record_llm_test(cfg, outcome)
    return outcome


@router.get("/ai/routing")
def ai_routing_status(db: Session = Depends(get_db)):
    from ..services.ai_routing import status
    return status(svc.get_section(db, "ai"))


class OfflineDecision(BaseModel):
    outage_id: str = Field(min_length=1, max_length=64)
    decision: Literal['offline', 'wait']


@router.post('/ai/offline-decision')
def offline_decision(body: OfflineDecision, db: Session = Depends(get_db)):
    from ..services.ai_routing import decide_offline
    try:
        return decide_offline(svc.get_section(db, 'ai'), body.outage_id, body.decision)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None


@router.post("/ai/fallback/test")
def test_ai_fallback(db: Session = Depends(get_db)):
    from ..services.ai_routing import local_config
    cfg = local_config(svc.get_section(db, "ai"))
    if cfg is None:
        return {"ok": False, "reason": "Secours local désactivé"}
    try:
        return {**ai.check_connection(cfg), "model": cfg["model"], "base_url": cfg["base_url"]}
    except Exception as exc:
        return {"ok": False, "reason": str(exc)}


@router.post("/memory/test")
def test_memory(db: Session = Depends(get_db)):
    """Sonde bout en bout sur un dataset jetable : remember → recall → forget.

    Ne touche à aucun projet. Premier appel potentiellement long
    (calcul des embeddings sur le serveur).
    """
    import asyncio
    from ..db import SessionLocal
    from ..services.memory_factory import resolve_engine
    if resolve_engine(SessionLocal) == "fake":
        return {"status": "skipped", "reason": "Adaptateur SQL réservé aux tests isolés"}
    from ..services.eg2_memory import EG2MemoryAdapter
    return asyncio.run(EG2MemoryAdapter(SessionLocal).probe())


@router.get("/ai/models")
def list_models(db: Session = Depends(get_db)):
    cfg = svc.get_section(db, "ai")
    res = ai.check_connection(cfg)
    return res
