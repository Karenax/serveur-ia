"""Pont MiniPilot <-> Project Brain (coeur de connaissance, même serveur).

MiniPilot ne duplique jamais la vérité : mapping explicite par projet
(`BrainLink`), lecture seule via REST Project Brain. La validation des
informations se fait dans l'UI Project Brain (/ui).
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.routers.settings import AISettings, MailSettings

from ..db import get_db
from ..models import BrainLink, Project

router = APIRouter(prefix="/api/v1", tags=["brain"])


def brain_base() -> str:
    return os.environ.get("MINIPILOT_BRAIN_URL", "http://127.0.0.1:8001").rstrip("/")


def _call(method: str, path: str, body: object = None, timeout: int = 20):
    if os.environ.get("AGENT_BRAIN_TRANSPORT", "internal") == "internal":
        from app.services.local_dispatch import call
        return call(method, path, body)
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        brain_base() + path, data=data,
        headers={"Content-Type": "application/json"}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else None
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8")[:300]
        except Exception:
            detail = ""
        if exc.code == 404:
            raise HTTPException(404, f"Project Brain : introuvable ({detail})") from exc
        raise HTTPException(502, f"Project Brain erreur {exc.code} : {detail}") from exc
    except Exception as exc:
        raise HTTPException(
            502, f"Project Brain injoignable ({brain_base()}) : {exc}.") from exc


@router.get("/brain/status")
def brain_status():
    try:
        health = _call("GET", "/health", timeout=5)
        return {"reachable": True, "brain": health, "url": brain_base()}
    except HTTPException as exc:
        return {"reachable": False, "detail": exc.detail, "url": brain_base()}


@router.get("/brain/projects")
def brain_projects():
    """Projets connus du coeur de connaissance (pour le rattachement)."""
    return _call("GET", "/v1/projects")


@router.get("/brain/overview")
def brain_overview():
    """Pilotage Brain : IA, dossier mails, compteurs (tout ce que l'ancien /ui affichait)."""
    settings = _call("GET", "/v1/settings", timeout=10) or {}
    ai = dict((settings.get("ai") or {}))
    ai.pop("api_key", None)
    folder = _call("GET", "/v1/ingest/default-folder", timeout=10)
    counts = _call("GET", "/v1/stats", timeout=10)
    return {
        "url": brain_base(),
        "ai": {"provider": ai.get("provider"), "model": ai.get("model"),
               "enabled": ai.get("enabled"), "base_url": ai.get("base_url")},
        "mail": {"folder": (settings.get("mail") or {}).get("folder"),
                 "auto_scan": (settings.get("mail") or {}).get("auto_scan"),
                 "eml_count": (folder or {}).get("eml_count"),
                 "exists": (folder or {}).get("exists")},
        "memory": settings.get("memory"),
        "pending_count": counts["pending_count"],
        "proposals_count": counts["proposals_count"],
    }


@router.get("/brain/proposals")
def brain_proposals():
    """Propositions en attente côté Brain (validation dans son UI)."""
    return _call("GET", "/v1/proposals?status=pending", timeout=20)


@router.post("/brain/scan")
def brain_scan_global():
    """Scan du dossier mails configuré côté Brain (global, sans rattachement)."""
    return _call("POST", "/v1/ingest/scan", {"folder": None, "limit": 500}, timeout=180)


# --- Tri des mails (classement IA à valider, projet DIVERS) ---
@router.get("/brain/triage/stats")
def brain_triage_stats():
    return _call("GET", "/v1/triage/stats", timeout=15)


@router.get("/brain/triage/queue")
def brain_triage_queue(offset: int = 0, limit: int = 200):
    return _call("GET", f"/v1/triage/queue?offset={offset}&limit={limit}", timeout=20)


@router.get("/brain/triage/learning")
def brain_triage_learning():
    return _call("GET", "/v1/triage/learning")


@router.get("/brain/sources")
def brain_sources(status: str = "all", offset: int = 0, project_id: str | None = None):
    from urllib.parse import urlencode
    params = {"status": status, "offset": offset, "limit": 100, "source_type": "email"}
    if project_id:
        params["project_id"] = project_id
    return _call("GET", "/v1/sources?" + urlencode(params))


class SourceReassignment(BaseModel):
    project_id: str = Field(min_length=1, max_length=36)


@router.post("/brain/sources/{source_id}/reassign")
def reassign_source(source_id: str, body: SourceReassignment):
    return _call("POST", f"/v1/resolution/{source_id}/confirm", {**body.model_dump(), "defer_enrichment": True})


@router.post("/brain/sources/{source_id}/discard")
def discard_source(source_id: str):
    return _call("POST", f"/v1/sources/{source_id}/discard", timeout=600)


@router.post("/brain/triage/run")
def brain_triage_run(limit: int = 50, offset: int = 0, force: bool = False):
    return _call(
        "POST",
        f"/v1/triage/run?limit={limit}&offset={offset}&force={str(force).lower()}",
        timeout=600)


class BrainTriageDecision(BaseModel):
    actor: str = "validator"
    comment: str | None = None


@router.post("/brain/triage/{proposal_id}/accept")
def brain_triage_accept(proposal_id: str, body: BrainTriageDecision):
    return _call("POST", f"/v1/triage/{proposal_id}/accept",
                 {"actor": body.actor, "comment": body.comment}, timeout=120)


class BrainTriageAssign(BaseModel):
    project_id: str = Field(min_length=1, max_length=36)
    actor: str = "validator"
    comment: str | None = None


@router.post("/brain/triage/{proposal_id}/assign")
def brain_triage_assign(proposal_id: str, body: BrainTriageAssign):
    return _call("POST", f"/v1/triage/{proposal_id}/assign",
                 body.model_dump(), timeout=120)


class BrainAiSettings(AISettings):
    provider: str = Field(min_length=1, max_length=32)
    base_url: str = Field(min_length=1, max_length=512)
    model: str = Field(min_length=1, max_length=256)
    api_key: str | None = Field(default=None, max_length=512)
    clear_api_key: bool = False
    enabled: bool = False


class BrainMailSettings(MailSettings):
    folder: str = Field(default="", max_length=1024)

    @model_validator(mode="after")
    def validate_eml_folder(self):
        if ("folder" in self.model_fields_set and not self.folder.strip()
                and ("source" not in self.model_fields_set or self.source == "folder")):
            raise ValueError("Sélectionnez un dossier EML, ou choisissez Thunderbird comme source")
        return self


@router.get("/brain/ingest/auto-status")
def brain_auto_status():
    return _call("GET", "/v1/ingest/auto-status", timeout=15)


class BrainMemorySettings(BaseModel):
    engine: str = "eg2"
    prefix: str = Field(default="pb", min_length=1, max_length=32)
    embedding_provider: str = Field(default="openai_compatible", max_length=32)
    embedding_model: str = Field(default="text-embedding-embeddinggemma-2", max_length=256)
    embedding_endpoint: str = Field(default="http://192.9.110.115:1234", max_length=512)
    index_path: str = Field(default="", max_length=1024)
    timeout_s: int = Field(default=600, ge=1, le=86400)
    batch_size: int = Field(default=8, ge=1, le=32)


@router.get("/brain/ai-settings")
def brain_ai_settings():
    """Réglage IA (clé API jamais renvoyée en clair : `api_key_set` booléen)."""
    settings = _call("GET", "/v1/settings", timeout=10) or {}
    ai = dict((settings.get("ai") or {}))
    out = {k: ai.get(k) for k in ("provider", "base_url", "model", "enabled", "timeout_s",
                                 "fallback_enabled", "fallback_base_url", "fallback_model", "fallback_autostart")}
    out["api_key_set"] = bool(ai.get("api_key_set"))
    return out


@router.get("/brain/mail-settings")
def brain_mail_settings():
    settings = _call("GET", "/v1/settings", timeout=10) or {}
    mail = dict((settings.get("mail") or {}))
    folder = {}
    if mail.get("source", "folder") == "folder":
        try:
            folder = _call("GET", "/v1/ingest/default-folder", timeout=10) or {}
        except HTTPException:
            pass
    return {**mail, "eml_count": folder.get("eml_count"), "exists": folder.get("exists")}


@router.put("/brain/mail-settings")
def save_brain_mail_settings(payload: BrainMailSettings):
    return _call("PUT", "/v1/settings/mail", payload.model_dump(exclude_unset=True), timeout=15)


@router.get("/brain/memory-settings")
def brain_memory_settings():
    settings = _call("GET", "/v1/settings", timeout=10) or {}
    active = _call("GET", "/v1/settings/memory/engines", timeout=15) or {}
    # la forme utile côté UI : adaptateur actif + sa santé
    return {"configured": settings.get("memory") or (active.get("configured") if isinstance(active, dict) else None),
            "active": active.get("active") if isinstance(active, dict) and "active" in active else active}


@router.put("/brain/memory-settings")
def save_brain_memory_settings(payload: BrainMemorySettings):
    if payload.engine not in ("eg2",):
        raise HTTPException(400, "Moteur : eg2")
    if payload.embedding_provider not in ("openai_compatible",):
        raise HTTPException(400, "Embeddings : openai_compatible (EG2)")
    return _call("PUT", "/v1/settings/memory", payload.model_dump(), timeout=15)


@router.post("/brain/memory-test")
def brain_memory_test():
    """Sonde EG2 indexation, rappel et purge dans un index temporaire."""
    return _call("POST", "/v1/settings/memory/test", timeout=900)


from app.schemas import ChatQuery as BrainChatQuery  # noqa: E402


@router.post("/brain/chat")
def brain_chat(body: BrainChatQuery):
    """Assistant : réponse synthétisée depuis la mémoire, sources qualifiées."""
    return _call("POST", "/v1/projects/chat", body.model_dump(), timeout=300)


@router.put("/brain/ai-settings")
def save_brain_ai_settings(payload: BrainAiSettings):
    if payload.provider not in ("none", "ollama", "openai_compatible"):
        raise HTTPException(400, "Fournisseur : none, ollama ou openai_compatible")
    body = payload.model_dump(exclude_unset=True)
    if not body.get("api_key"):
        body.pop("api_key", None)  # ne pas écraser la clé enregistrée
    return _call("PUT", "/v1/settings/ai", body, timeout=15)


@router.post("/brain/ai-test")
def brain_ai_test():
    return _call("POST", "/v1/settings/ai/test", {}, timeout=90)


def _project_or_404(db: Session, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Projet introuvable")
    return project


def _link_or_409(db: Session, project_id: str) -> BrainLink:
    link = db.get(BrainLink, project_id)
    if not link:
        raise HTTPException(409, "Projet non relié au coeur de connaissance : "
                                 "rattache-le d'abord (suggestion par code).")
    return link


@router.get("/projects/{project_id}/brain")
def brain_link(project_id: str, db: Session = Depends(get_db)):
    project = _project_or_404(db, project_id)
    link = db.get(BrainLink, project_id)
    out: dict = {"linked": link is not None, "minipilot_code": project.code}
    if link:
        out.update({"brain_project_id": link.brain_project_id, "brain_code": link.brain_code})
        try:
            status = _call("GET", f"/v1/projects/{link.brain_project_id}/memory/status", timeout=10)
            out["memory"] = status
        except HTTPException as exc:
            out["memory_error"] = exc.detail
        try:
            out["pending"] = _call("GET", "/v1/resolution/pending", timeout=10)
        except HTTPException:
            out["pending"] = []
    else:
        # Suggestion automatique par égalité de code
        try:
            candidates = _call("GET", "/v1/projects", timeout=10) or []
            code = (project.code or "").strip().upper()
            out["suggested"] = next(
                (c for c in candidates if str(c.get("code", "")).strip().upper() == code),
                None)
            out["brain_projects"] = candidates
        except HTTPException as exc:
            out["brain_error"] = exc.detail
            out["brain_projects"] = []
    return out


class BrainLinkSave(BaseModel):
    brain_project_id: str = Field(min_length=1, max_length=36)


@router.post("/projects/{project_id}/brain/ensure")
def ensure_brain_link(project_id: str, db: Session = Depends(get_db)):
    """Make an ERP project usable for explicit mail classification, idempotently."""
    project = _project_or_404(db, project_id)
    link = db.get(BrainLink, project_id)
    candidates = _call("GET", "/v1/projects", timeout=10) or []
    if link:
        target = next((p for p in candidates if p["id"] == link.brain_project_id), None)
        if not target:
            raise HTTPException(409, "Le projet de connaissance associé est introuvable")
    else:
        code = (project.code or "").strip() or f"ERP-{project.id}"

        def matching(rows):
            matches = [p for p in rows if str(p.get("code", "")).strip().casefold() == code.casefold()]
            if len(matches) > 1:
                raise HTTPException(409, "Plusieurs projets portent ce code : choisissez le lien dans Connaissance")
            return matches[0] if matches else None

        target = matching(candidates)
        if target is None:
            try:
                target = _call("POST", "/v1/projects", {"code": code, "name": project.title}, timeout=15)
            except HTTPException as exc:
                if exc.status_code != 409:
                    raise
                target = matching(_call("GET", "/v1/projects", timeout=10) or [])
                if target is None:
                    raise
        db.add(BrainLink(project_id=project_id, brain_project_id=target["id"], brain_code=target["code"]))
        db.commit()
    return {"linked": True, "brain_project_id": target["id"], "brain_code": target["code"]}


@router.put("/projects/{project_id}/brain")
def save_brain_link(project_id: str, payload: BrainLinkSave, db: Session = Depends(get_db)):
    _project_or_404(db, project_id)
    # Vérifie l'existence côté Brain (ses projets exposent id/code/name).
    candidates = _call("GET", "/v1/projects", timeout=10) or []
    target = next((c for c in candidates if c.get("id") == payload.brain_project_id), None)
    if not target:
        raise HTTPException(404, "Projet Brain introuvable : crée-le d'abord dans le coeur.")
    link = db.get(BrainLink, project_id)
    if link:
        link.brain_project_id = target["id"]
        link.brain_code = str(target.get("code", ""))
    else:
        db.add(BrainLink(project_id=project_id, brain_project_id=target["id"],
                         brain_code=str(target.get("code", ""))))
    db.commit()
    return {"linked": True, "brain_project_id": target["id"], "brain_code": target.get("code")}


@router.delete("/projects/{project_id}/brain")
def delete_brain_link(project_id: str, db: Session = Depends(get_db)):
    _project_or_404(db, project_id)
    link = db.get(BrainLink, project_id)
    if link:
        db.delete(link)
        db.commit()
    return {"linked": False}


@router.get("/projects/{project_id}/brain/knowledge")
def brain_knowledge(project_id: str, kind: str | None = None, status: str = 'validated', offset: int = 0, limit: int = 200, db: Session = Depends(get_db)):
    link = _link_or_409(db, project_id)
    from urllib.parse import urlencode
    path = f"/v1/projects/{link.brain_project_id}/knowledge?" + urlencode({'status': status, 'offset': max(0, offset), 'limit': min(max(1, limit), 1000), **({'kind': kind} if kind else {})})
    return _call("GET", path)


@router.post('/projects/{project_id}/brain/knowledge/{knowledge_id}/{action}')
def change_brain_knowledge(project_id: str, knowledge_id: str, action: str,
                           body: BrainTriageDecision, db: Session = Depends(get_db)):
    link = _link_or_409(db, project_id)
    return _call('POST', f'/v1/projects/{link.brain_project_id}/knowledge/{knowledge_id}/{action}', body.model_dump())


@router.get("/projects/{project_id}/brain/actions")
def brain_actions(project_id: str, db: Session = Depends(get_db)):
    link = _link_or_409(db, project_id)
    return _call("GET", f"/v1/projects/{link.brain_project_id}/open-actions")


@router.get("/projects/{project_id}/brain/risks")
def brain_risks(project_id: str, db: Session = Depends(get_db)):
    link = _link_or_409(db, project_id)
    return _call("GET", f"/v1/projects/{link.brain_project_id}/risks")


@router.get("/projects/{project_id}/brain/timeline")
def brain_timeline(project_id: str, db: Session = Depends(get_db)):
    link = _link_or_409(db, project_id)
    return _call("GET", f"/v1/projects/{link.brain_project_id}/timeline")


@router.post("/projects/{project_id}/brain/scan")
def brain_scan(project_id: str, db: Session = Depends(get_db)):
    """Déclenche un scan du dossier mails côté Brain (réutilise son dossier configuré)."""
    _link_or_409(db, project_id)
    return _call("POST", "/v1/ingest/scan", {"folder": None, "limit": 500}, timeout=120)


@router.post("/projects/{project_id}/brain/memory/retry")
def brain_retry_memory(project_id: str, db: Session = Depends(get_db)):
    link = _link_or_409(db, project_id)
    return _call("POST", f"/v1/projects/{link.brain_project_id}/memory/retry", {}, timeout=300)
