"""Agent - serveur unique : coeur de connaissance Project Brain + MiniPilot absorbé.

- Brain : `/v1/*` (REST), `/ui` (validation), `/docs`.
- MiniPilot : `/api/v1/*` (ERP), `/` (React buildé), `/static`, `/assets`.
- Bases SQLite séparées, données préservées : Brain `./project_brain.db`,
  MiniPilot `MINIPILOT_HOME/minipilot.db` (défaut `~/.minipilot`).
"""
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import ExitStack, asynccontextmanager
import json
from pathlib import Path
from .config import settings
from sqlalchemy.orm import Session
from .db import init_db, get_db
from .security import local_guard, session
from .models import Project, Source, Proposal, KnowledgeItem
from .routers.sources import router as sources_router, project_router as project_sources_router
from .routers.ingest_folder import router as ingest_router
from .routers.settings import router as settings_router
from .routers.embedding_channel import router as embedding_channel_router
from .routers.triage import router as triage_router
from .routers.thunderbird import router as thunderbird_router
from .routers.mail_search import router as mail_search_router
from .routers.search import router as search_router
from .routers.workspace import router as workspace_router
from .routers.meeting_sessions import router as meeting_sessions_router
from .routers.kiara_admin import router as kiara_admin_router
from .routers.source_library import router as source_library_router
from .routers.session_assistant import router as session_assistant_router
from .routers.meeting_notes_publication import router as meeting_notes_publication_router
from .routers.fusion_insights import router as fusion_insights_router
from .routers.session_calendar import router as session_calendar_router
from .routers.source_search import router as source_search_router
from .routers.session_export import router as session_export_router
from .routers.native_capture import router as native_capture_router
from .routers.core import (projects_router, knowledge_router, resolution_router,
                           proposals_router, memory_router)

ROOT = Path(__file__).resolve().parent.parent
MP_WEB_DIST = ROOT / "web" / "dist"
MP_STATIC = ROOT / "backend" / "app" / "static"

from backend.app.routers import (  # noqa: E402
    ai as mp_ai, brain as mp_brain, cdc as mp_cdc, meetings as mp_meetings,
    network_links as mp_links, portfolio_tools as mp_portfolio,
    projects as mp_projects, sage as mp_sage, scan as mp_scan,
    workshop as mp_workshop,
    operations as mp_operations,
    meeting_audio as mp_meeting_audio,
    milestones as mp_milestones,
    project_identity as mp_identity,
    project_planning as mp_planning,
    project_deliverables as mp_deliverables,
    project_cockpit as mp_cockpit,
    project_reviews as mp_reviews,
    project_documents as mp_documents,
    project_document_jobs as mp_document_jobs,
    project_notes as mp_notes,
    project_note_files as mp_note_files,
    project_note_imports as mp_note_imports,
    project_note_network as mp_note_network,
    project_knowledge_analysis as mp_project_knowledge,
)
from backend.app.db import init_db as mp_init_db  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    import os
    if os.environ.get('AGENT_TESTING') != '1':
        from .services.child_process import protect_children, watch_kiara_parent
        protect_children()
        watch_kiara_parent()
    from .services.logging_setup import configure_logging
    from .services.workspace_jobs import (init_workspace_db, start_worker as start_mail_worker,
                                          stop_worker as stop_mail_worker)
    configure_logging()
    init_workspace_db()
    init_db()
    mp_init_db()
    from .services.source_library import init_library_db
    from .db import engine
    init_library_db(engine)
    if os.environ.get('AGENT_START_WORKERS') == '0':
        yield
        return
    enabled = None
    if 'AGENT_WORKER_GROUPS' in os.environ:
        from kiara_shared.agent_workers import validate_groups
        enabled = frozenset(validate_groups(json.loads(os.environ['AGENT_WORKER_GROUPS'])))
        if not enabled:
            yield
            return

    def allowed(group):
        return enabled is None or group in enabled

    from .db import SessionLocal
    if allowed('knowledge'):
        from .services.knowledge_defaults import promote_pending
        with SessionLocal() as db:
            promote_pending(db)
    # scan automatique périodique (nouveaux mails uniquement, toutes les N
    # minutes, Paramètres > mail). Premier passage immédiat au démarrage.
    from .services.auto_scan import start_auto_scan, stop_auto_scan
    from backend.app.services.cdc_jobs import start_worker, stop_worker
    from .services.meeting_audio import start_worker as start_audio, stop_worker as stop_audio
    from .services.mail_enrichment import start_worker as start_enrichment, stop_worker as stop_enrichment
    from backend.app.services.milestone_scan import start_worker as start_milestones, stop_worker as stop_milestones
    from backend.app.services.document_job_worker import start_worker as start_documents, stop_worker as stop_documents
    from backend.app.services.project_knowledge_analysis import start_worker as start_knowledge, stop_worker as stop_knowledge
    from .services.note_evidence_bridge import start_worker as start_note_bridge, stop_worker as stop_note_bridge
    from .services.live_speech import start_worker as start_live_speech, stop_worker as stop_live_speech
    from .services.meeting_sessions import recover_interrupted
    from .services.session_batch_transcription import recover_orphans as recover_batch, stop_all as stop_batch
    from .services.session_proactive import start_worker as start_proactive, stop_worker as stop_proactive
    if allowed('audio') and os.environ.get('AGENT_TESTING') != '1':
        with SessionLocal() as db:
            recover_interrupted(db)
            recover_batch(db, startup=True)
    with ExitStack() as workers:
        def start(group, run, stop):
            if allowed(group):
                workers.callback(stop)
                run()

        start('mail', start_auto_scan, stop_auto_scan)
        start('cdc', start_worker, stop_worker)
        start('audio', start_audio, stop_audio)
        start('mail', start_mail_worker, stop_mail_worker)
        start('mail', start_enrichment, stop_enrichment)
        start('planning', start_milestones, stop_milestones)
        start('documents', start_documents, stop_documents)
        start('knowledge', start_knowledge, stop_knowledge)
        start('knowledge', start_note_bridge, stop_note_bridge)
        from .services.native_audio import stop_all
        workers.callback(stop_all)
        workers.callback(stop_batch)
        if os.environ.get('AGENT_TESTING') != '1':
            if allowed('audio'):
                from .services.meeting_sessions import live_transcription_enabled
                with SessionLocal() as db:
                    enable_live = live_transcription_enabled(db)
                if enable_live:
                    start('audio', start_live_speech, stop_live_speech)
                start('audio', start_proactive, stop_proactive)
        from .services.memory_recovery import start_automatic, stop as stop_memory_recovery
        start('knowledge', start_automatic, stop_memory_recovery)
        yield


app = FastAPI(title="Agent (Brain + MiniPilot)", version="0.4.0", lifespan=lifespan)
app.middleware("http")(local_guard)
from .http_protection import HTTPProtection  # noqa: E402
app.add_middleware(HTTPProtection)
app.get("/api/v1/session")(session)

templates = Jinja2Templates(directory=str(ROOT / "app" / "templates"))

app.include_router(sources_router)
app.include_router(project_sources_router)
app.include_router(ingest_router)
app.include_router(settings_router)
app.include_router(embedding_channel_router)
app.include_router(triage_router)
app.include_router(thunderbird_router)
app.include_router(mail_search_router)
app.include_router(search_router)
app.include_router(workspace_router)
app.include_router(meeting_sessions_router)
app.include_router(kiara_admin_router)
app.include_router(source_library_router)
app.include_router(session_assistant_router)
app.include_router(meeting_notes_publication_router)
app.include_router(fusion_insights_router)
app.include_router(session_calendar_router)
app.include_router(source_search_router)
app.include_router(session_export_router)
app.include_router(native_capture_router)
app.include_router(projects_router)
app.include_router(knowledge_router)
app.include_router(resolution_router)
app.include_router(proposals_router)
app.include_router(memory_router)

# MiniPilot absorbé : routers ERP sous /api/v1
app.include_router(mp_projects.router)
app.include_router(mp_brain.router)
app.include_router(mp_cdc.router)
app.include_router(mp_links.router)
app.include_router(mp_scan.router)
app.include_router(mp_meetings.router)
app.include_router(mp_ai.router)
app.include_router(mp_portfolio.router)
app.include_router(mp_sage.router)
app.include_router(mp_workshop.router)
app.include_router(mp_operations.router)
app.include_router(mp_meeting_audio.router)
app.include_router(mp_milestones.router)
app.include_router(mp_identity.router)
app.include_router(mp_planning.router)
app.include_router(mp_planning.catalog_router)
app.include_router(mp_deliverables.router)
app.include_router(mp_deliverables.catalog_router)
app.include_router(mp_deliverables.typology_router)
app.include_router(mp_cockpit.router)
app.include_router(mp_project_knowledge.router)
app.include_router(mp_reviews.router)
app.include_router(mp_reviews.catalogue_router)
app.include_router(mp_documents.router)
app.include_router(mp_documents.settings_router)
app.include_router(mp_document_jobs.router)
# Static import paths precede the dynamic note identity path.
app.include_router(mp_note_network.router)
app.include_router(mp_note_imports.router)
app.include_router(mp_note_files.router)
app.include_router(mp_notes.router)


@app.get("/health")
def health():
    from fastapi.responses import JSONResponse
    from sqlalchemy import text
    from .db import engine
    from backend.app.db import engine as erp_engine
    states = {}
    for name, target in (("brain", engine), ("erp", erp_engine)):
        try:
            with target.connect() as conn:
                conn.execute(text("SELECT 1 FROM projects LIMIT 1"))
                invalid = conn.execute(text("PRAGMA foreign_key_check")).first()
            if invalid:
                states[name] = "integrity_error"
                continue
            states[name] = "ok"
        except Exception:
            states[name] = "unavailable"
    ready = all(v == "ok" for v in states.values())
    return JSONResponse({"status": "ok" if ready else "degraded", "service": "agent",
                         "app": "agent", "databases": states}, status_code=200 if ready else 503)


@app.get("/ui", response_class=HTMLResponse)
def ui_home(request: Request, db: Session = Depends(get_db)):
    n_proj = db.query(Project).count()
    n_pending = db.query(Source).filter_by(status="resolution_pending").count()
    n_prop = db.query(Proposal).filter_by(status="pending").count()
    n_know = db.query(KnowledgeItem).filter_by(status="validated").count()
    projects = db.query(Project).all()
    return templates.TemplateResponse(request=request, name="home.html", context={"request": request, "n_proj": n_proj,
                                                    "n_pending": n_pending, "n_prop": n_prop,
                                                    "n_know": n_know, "projects": projects})


@app.get("/ui/pending", response_class=HTMLResponse)
def ui_pending(request: Request, db: Session = Depends(get_db)):
    rows = db.query(Source).filter_by(status="resolution_pending").all()
    projects = db.query(Project).all()
    return templates.TemplateResponse(request=request, name="pending.html", context={"request": request, "rows": rows, "projects": projects})


@app.get("/ui/proposals", response_class=HTMLResponse)
def ui_proposals(request: Request, offset: int = 0, db: Session = Depends(get_db)):
    rows = db.query(Proposal).filter(Proposal.status == "pending", Proposal.kind != "project_attach").order_by(Proposal.created_at.desc()).offset(max(0, offset)).limit(200).all()
    return templates.TemplateResponse(request=request, name="proposals.html", context={"request": request, "rows": rows, "offset": max(0, offset)})


@app.get("/ui/projects/{pid}", response_class=HTMLResponse)
def ui_project(request: Request, pid: str, db: Session = Depends(get_db)):
    p = db.query(Project).filter_by(id=pid).first()
    know = db.query(KnowledgeItem).filter_by(project_id=pid, status="validated").all() if p else []
    srcs = db.query(Source).filter_by(project_id=pid).all() if p else []
    return templates.TemplateResponse(request=request, name="project.html", context={"request": request, "project": p,
                                                       "know": know, "srcs": srcs})


@app.get("/ui/settings", response_class=HTMLResponse)
def ui_settings(request: Request, db: Session = Depends(get_db)):
    from .services.settings_service import get_all
    data = get_all(db)
    return templates.TemplateResponse(request=request, name="settings.html", context={"request": request, "data": data})


# --- MiniPilot absorbé : frontend React + statiques ---
@app.get("/", response_class=HTMLResponse)
@app.get("/app", response_class=HTMLResponse, include_in_schema=False)
@app.get("/app/{path:path}", response_class=HTMLResponse, include_in_schema=False)
def mp_index() -> str:
    dist_index = MP_WEB_DIST / "index.html"
    if dist_index.exists():
        return dist_index.read_text(encoding="utf-8")
    fallback = MP_STATIC / "index.html"
    return fallback.read_text(encoding="utf-8")


if MP_STATIC.exists():
    app.mount("/static", StaticFiles(directory=str(MP_STATIC)), name="mp-static")
if (MP_WEB_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(MP_WEB_DIST / "assets")), name="mp-assets")
