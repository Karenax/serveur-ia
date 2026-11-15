"""Global workspace views with explicit Brain/ERP scopes and durable UI state."""
import json
import unicodedata
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, or_, update
from sqlalchemy.orm import Session, load_only

from app.db import get_db
from app.db_support import utc_iso
from app.models import KnowledgeItem, MeetingRecording, Project, Proposal, ProvenanceLink, Source, SourceArtifact
from app.services import workspace_jobs
from app.workspace_models import AssistantThread, TriageJob, MailEnrichmentJob
from app.services.project_access import erp_ids, filter_erp, filter_brain, filter_proposals, require_brain, require_erp
from backend.app.db import get_db as get_erp_db
from backend.app.models import BrainLink, CdcAnalysisJob, CdcSource, Meeting, MeetingAction, MilestoneScanJob, Project as ERPProject

router = APIRouter(prefix="/api/v1/workspace", tags=["workspace"])


@router.get("/mail-activity")
def mail_activity(db: Session = Depends(get_db)):
    from app.services.mail_activity import snapshot
    return snapshot(db)


def _fold(value):
    return "".join(c for c in unicodedata.normalize("NFKD", value.casefold()) if not unicodedata.combining(c))


def _search(query, text, *columns):
    if text.strip():
        query = query.filter(or_(*(func.agent_fold(column).contains(_fold(text.strip()), autoescape=True)
                                  for column in columns)))
    return query


def _brain_scope(db, project_id):
    if project_id:
        require_brain(project_id)
    if project_id and not db.get(Project, project_id):
        raise HTTPException(404, "Projet de connaissance introuvable")


def _erp_scope(db, project_id):
    if project_id:
        require_erp(project_id)
    if project_id and not db.get(ERPProject, project_id):
        raise HTTPException(404, "Projet introuvable")


def _erp_contexts(erp, brain_ids):
    contexts = {}
    if not brain_ids:
        return contexts
    rows = (erp.query(BrainLink, ERPProject).join(ERPProject, ERPProject.id == BrainLink.project_id)
            .filter(BrainLink.brain_project_id.in_(brain_ids)))
    rows = filter_erp(rows, ERPProject.id).all()
    for link, project in rows:
        contexts.setdefault(link.brain_project_id, []).append(
            {"id": project.id, "code": project.code, "title": project.title})
    return contexts


def _source_citation(db, source_id, project_id, locator=None, excerpt=None):
    source = db.get(Source, source_id) if source_id else None
    # A mismatched provenance remains in the canonical history, but must never
    # appear as supporting evidence in a different project's workspace.
    if not source or source.status == "discarded" or source.project_id != project_id:
        return None
    locator = locator or {}
    artifact = db.get(SourceArtifact, locator.get("artifact_id")) if locator.get("artifact_id") else None
    if artifact and (artifact.source_id != source.id or (artifact.content_json or {}).get("superseded")):
        artifact = None
    if not artifact:
        artifact = next((row for row in db.query(SourceArtifact).filter_by(source_id=source.id)
                         .order_by(SourceArtifact.created_at.desc()).all()
                         if row.content_text and row.kind != "audio_pending" and
                         not (row.content_json or {}).get("superseded")), None)
    text = artifact.content_text or "" if artifact else ""
    if excerpt is None:
        excerpt = str(locator.get("quote") or "")
        if not excerpt and locator.get("mode") == "exact":
            start, end = locator.get("start"), locator.get("end")
            if isinstance(start, int) and isinstance(end, int) and 0 <= start <= end <= len(text):
                excerpt = text[start:end]
        excerpt = excerpt or text[:1800]
    meta = source.source_metadata or {}
    recording = None
    if locator.get("recording_id"):
        candidate = db.get(MeetingRecording, str(locator["recording_id"]))
        if candidate and candidate.project_id == project_id and candidate.source_id == source.id:
            recording = candidate
    return {"source_id": source.id, "source_type": source.source_type,
            "title": str(meta.get("subject") or meta.get("filename") or "Source")[:512],
            "author": source.author or "", "excerpt": str(excerpt)[:1800], "locator": locator,
            "source_url": f"/v1/sources/{source.id}",
            "recording_id": recording.id if recording else None,
            "erp_project_id": recording.erp_project_id if recording else None,
            "audio_url": f"/api/v1/projects/{recording.erp_project_id}/recordings/{recording.id}/audio" if recording else None}


@router.get("/proposals")
def proposals(project_id: str | None = None, status: str = "pending", q: str = Query("", max_length=300),
              offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
              db: Session = Depends(get_db), erp: Session = Depends(get_erp_db)):
    _brain_scope(db, project_id)
    query = filter_proposals(db.query(Proposal)).filter(Proposal.kind != "project_attach")
    if project_id:
        query = query.filter(Proposal.project_id == project_id)
    if status != "all":
        query = query.filter(Proposal.status == status)
    query = _search(query, q, Proposal.subject, Proposal.value, Proposal.reason)
    total = query.count()
    rows = query.order_by(Proposal.created_at.desc(), Proposal.id).offset(offset).limit(limit).all()
    contexts = _erp_contexts(erp, {row.project_id for row in rows if row.project_id})
    result = []
    for row in rows:
        project = db.get(Project, row.project_id) if row.project_id else None
        citation = _source_citation(db, row.source_id, row.project_id, row.locator)
        result.append({"id": row.id, "project_id": row.project_id, "brain_project_id": row.project_id,
                       "project_code": project.code if project else "", "project_name": project.name if project else "",
                       "erp_projects": contexts.get(row.project_id, []), "source_id": row.source_id,
                       "kind": row.kind, "operation": row.operation, "subject": row.subject, "value": row.value,
                       "confidence": row.confidence, "status": row.status, "reason": row.reason,
                       "created_at": utc_iso(row.created_at), "citations": [citation] if citation else []})
    return {"items": result, "total": total}


@router.get("/knowledge")
def knowledge(project_id: str | None = None, status: str = "validated", q: str = Query("", max_length=300),
              kind: str | None = None, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
              review_only: bool = False,
              db: Session = Depends(get_db), erp: Session = Depends(get_erp_db)):
    _brain_scope(db, project_id)
    query = filter_brain(db.query(KnowledgeItem), KnowledgeItem.project_id)
    if project_id:
        query = query.filter(KnowledgeItem.project_id == project_id)
    if status != "all":
        query = query.filter(KnowledgeItem.status == status)
    if kind:
        query = query.filter(KnowledgeItem.kind == kind)
    query = _search(query, q, KnowledgeItem.subject, KnowledgeItem.value)
    from ..services.knowledge_context import contexts as knowledge_contexts
    ordered = query.order_by(KnowledgeItem.created_at.desc(), KnowledgeItem.id)
    if review_only:
        candidates = ordered.all()
        qualifications = knowledge_contexts(db, candidates)
        candidates = [item for item in candidates if qualifications[item.id]['needs_review']]
        total, rows = len(candidates), candidates[offset:offset + limit]
    else:
        total = query.count()
        rows = ordered.offset(offset).limit(limit).all()
        qualifications = knowledge_contexts(db, rows)
    contexts = _erp_contexts(erp, {row.project_id for row in rows})
    result = []
    for row in rows:
        project = db.get(Project, row.project_id)
        citations = []
        for link in db.query(ProvenanceLink).filter_by(knowledge_item_id=row.id).all():
            citation = _source_citation(db, link.source_id, row.project_id, link.locator)
            if citation:
                citations.append(citation)
        result.append({"id": row.id, "project_id": row.project_id, "brain_project_id": row.project_id,
                       "project_code": project.code if project else "", "project_name": project.name if project else "",
                       "erp_projects": contexts.get(row.project_id, []), "kind": row.kind,
                       "subject": row.subject, "value": row.value, "status": row.status,
                       "confidence": row.confidence, "unit": row.unit, "version": row.version,
                       "validated_by": row.validated_by, "validated_at": utc_iso(row.validated_at) if row.validated_at else None,
                       "validation_mode": "default" if row.validated_by == "auto-default" else "human",
                       "context": qualifications[row.id],
                       "created_at": utc_iso(row.created_at), "citations": citations})
    return {"items": result, "total": total}


@router.get("/meetings")
def meetings(project_id: str | None = None, q: str = Query("", max_length=300),
             offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
             db: Session = Depends(get_db), erp: Session = Depends(get_erp_db)):
    _erp_scope(erp, project_id)
    report_query = filter_erp(erp.query(Meeting), Meeting.project_id)
    audio_query = db.query(MeetingRecording).options(load_only(
        MeetingRecording.id, MeetingRecording.erp_project_id, MeetingRecording.project_id,
        MeetingRecording.published_meeting_id, MeetingRecording.title, MeetingRecording.date,
        MeetingRecording.created_at, MeetingRecording.job_status, MeetingRecording.stage,
        MeetingRecording.progress, MeetingRecording.revision, MeetingRecording.reviewed_revision))
    if project_id:
        report_query = report_query.filter(Meeting.project_id == project_id)
        audio_query = audio_query.filter(MeetingRecording.erp_project_id == project_id)
    reports = {row.id: row for row in report_query.all()}
    recordings = filter_erp(audio_query, MeetingRecording.erp_project_id).all()
    from sqlalchemy import inspect
    from ..meeting_session_models import MeetingSession, MeetingSessionCommand
    session_by_audio, session_by_report = {}, {}
    if inspect(db.connection()).has_table('meeting_sessions'):
        visible_sessions = filter_erp(db.query(MeetingSession), MeetingSession.project_id)
        if project_id:
            visible_sessions = visible_sessions.filter(MeetingSession.project_id == project_id)
        allowed_sessions = {row.id: row for row in visible_sessions}
        session_by_audio = {row.recording_id: row.id for row in allowed_sessions.values() if row.recording_id}
        for command in db.query(MeetingSessionCommand).filter(MeetingSessionCommand.session_id.in_(allowed_sessions),
                MeetingSessionCommand.kind == 'publish-notes', MeetingSessionCommand.status == 'completed'):
            if command.result.get('meeting_id'):
                session_by_report[command.result['meeting_id']] = command.session_id
    audio_by_report = {row.published_meeting_id: row for row in recordings if row.published_meeting_id}
    entries = [(row, audio_by_report.get(row.id)) for row in reports.values()]
    entries.extend((None, row) for row in recordings if row.published_meeting_id not in reports)
    term = _fold(q.strip())
    items = []
    for report, audio in entries:
        pid = report.project_id if report else audio.erp_project_id
        project = erp.get(ERPProject, pid)
        if not project or (audio and (audio.erp_project_id != pid or
            not (link := erp.get(BrainLink, pid)) or link.brain_project_id != audio.project_id)):
            # An obsolete/mismatched recording mapping cannot imply project context.
            if not report:
                continue
            audio = None
        link = erp.get(BrainLink, pid)
        title = report.title if report else audio.title
        if term and term not in _fold(" ".join((title, project.code, project.title, report.decisions if report else ""))):
            continue
        items.append({"id": report.id if report else audio.id, "meeting_id": report.id if report else None,
                      "recording_id": audio.id if audio else None, "project_id": pid,
                      "session_id": session_by_audio.get(audio.id) if audio else session_by_report.get(report.id),
                      "brain_project_id": link.brain_project_id if link else None,
                      "project_code": project.code, "project_title": project.title,
                      "title": title, "date": report.date if report else audio.date,
                      "participants": report.participants if report else "", "decisions": report.decisions if report else "",
                      "stage": audio.stage if audio else "published",
                      "status": "published" if report else audio.job_status,
                      "created_at": utc_iso(report.created_at if report else audio.created_at),
                      "recording": {"id": audio.id, "job_status": audio.job_status, "stage": audio.stage,
                                    "progress": audio.progress, "revision": audio.revision,
                                    "reviewed_revision": audio.reviewed_revision} if audio else None})
    items.sort(key=lambda row: (row["created_at"], row["id"]), reverse=True)
    total = len(items)
    selected = items[offset:offset + limit]
    ids = [row["meeting_id"] for row in selected if row["meeting_id"]]
    actions = erp.query(MeetingAction).filter(MeetingAction.meeting_id.in_(ids)).all() if ids else []
    for item in selected:
        item["actions"] = [{"id": action.id, "title": action.title, "owner": action.owner,
                            "due_date": action.due_date, "task_id": action.task_id}
                           for action in actions if action.meeting_id == item["meeting_id"] and action.project_id == item["project_id"]]
    return {"items": selected, "total": total}


@router.get("/jobs")
def jobs(project_id: str | None = None, status: str = "all", offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
         db: Session = Depends(get_db), erp: Session = Depends(get_erp_db)):
    _erp_scope(erp, project_id)
    cdc = filter_erp(erp.query(CdcAnalysisJob), CdcAnalysisJob.project_id)
    audio = db.query(MeetingRecording).filter(MeetingRecording.job_status != "idle").options(load_only(
        MeetingRecording.id, MeetingRecording.erp_project_id, MeetingRecording.project_id, MeetingRecording.source_id,
        MeetingRecording.title, MeetingRecording.job_kind, MeetingRecording.job_status, MeetingRecording.stage,
        MeetingRecording.progress, MeetingRecording.processed_seconds, MeetingRecording.duration_seconds,
        MeetingRecording.cancel_requested, MeetingRecording.error, MeetingRecording.created_at, MeetingRecording.updated_at))
    if project_id:
        cdc = cdc.filter(CdcAnalysisJob.project_id == project_id)
        audio = audio.filter(MeetingRecording.erp_project_id == project_id)
    result = []
    scans = filter_erp(erp.query(MilestoneScanJob), MilestoneScanJob.project_id)
    if project_id:
        scans = scans.filter_by(project_id=project_id)
    for row in scans:
        project = erp.get(ERPProject, row.project_id)
        link = erp.get(BrainLink, row.project_id)
        result.append({"id": row.id, "engine": "milestones", "kind": "dates", "title": "Recherche des dates de jalons",
                       "project_id": row.project_id, "brain_project_id": link.brain_project_id if link else None,
                       "project_code": project.code if project else "", "project_title": project.title if project else "",
                       "source_id": None, "status": row.status, "stage": "Recherche des dates",
                       "progress": 100 if row.status == "completed" else round(row.processed / row.total * 100) if row.total else 0,
                       "processed": row.processed, "total": row.total, "unit": "passages", "can_cancel": False,
                       "can_retry": row.status == "failed", "cancel_url": None,
                       "retry_url": f"/api/v1/projects/{row.project_id}/milestones/scan", "error": row.error,
                       "created_at": utc_iso(row.created_at), "updated_at": utc_iso(row.updated_at)})
    for row in cdc.all():
        project = erp.get(ERPProject, row.project_id)
        link = erp.get(BrainLink, row.project_id)
        source = erp.get(CdcSource, row.source_id)
        result.append({"id": row.id, "engine": "cdc", "kind": "analyse", "title": source.filename if source else "Analyse CDC",
                       "project_id": row.project_id, "brain_project_id": link.brain_project_id if link else None,
                       "project_code": project.code if project else "", "project_title": project.title if project else "",
                       "source_id": row.source_id, "status": row.status, "stage": "analyse",
                       "progress": 100 if row.status == "completed" else round(row.completed_batches / row.total_batches * 95, 1) if row.total_batches else 0,
                       "processed": row.completed_batches, "total": row.total_batches, "unit": "batches",
                       "can_cancel": row.status in {"queued", "running"} and not row.cancel_requested,
                       "can_retry": row.status in {"failed", "cancelled", "interrupted"},
                       "cancel_url": f"/api/v1/projects/{row.project_id}/cdc/jobs/{row.id}/cancel",
                       "retry_url": f"/api/v1/projects/{row.project_id}/cdc/jobs/{row.id}/retry",
                       "error": row.error, "created_at": utc_iso(row.created_at), "updated_at": utc_iso(row.updated_at)})
    for row in filter_erp(audio, MeetingRecording.erp_project_id).all():
        project = erp.get(ERPProject, row.erp_project_id)
        link = erp.get(BrainLink, row.erp_project_id)
        if not project or not link or link.brain_project_id != row.project_id:
            continue
        result.append({"id": row.id, "engine": "audio", "kind": row.job_kind, "title": row.title,
                       "project_id": project.id, "brain_project_id": row.project_id,
                       "project_code": project.code, "project_title": project.title, "source_id": row.source_id,
                       "status": row.job_status, "stage": row.stage, "progress": row.progress,
                       "processed": row.processed_seconds, "total": row.duration_seconds, "unit": "seconds",
                       "can_cancel": row.job_status in {"queued", "running"} and not row.cancel_requested,
                       "can_retry": row.job_status in {"failed", "cancelled", "interrupted"},
                       "cancel_url": f"/api/v1/projects/{project.id}/recordings/{row.id}/cancel",
                       "retry_url": f"/api/v1/projects/{project.id}/recordings/{row.id}/{'synthesize' if row.job_kind == 'synthesis' else 'transcribe'}",
                       "error": row.error, "created_at": utc_iso(row.created_at), "updated_at": utc_iso(row.updated_at)})
    if not project_id and erp_ids() is None:
        for row in db.query(TriageJob).all():
            result.append({**workspace_jobs.describe(row), "engine": "triage", "kind": "reanalyse" if row.force else "analyse",
                           "title": "Tout ré-analyser" if row.force else "Analyser les nouveaux mails",
                           "project_id": None, "brain_project_id": None, "project_code": "", "project_title": "Tous les mails",
                           "source_id": None, "stage": "classement", "unit": "mails",
                           "cancel_url": f"/api/v1/workspace/triage-jobs/{row.id}/cancel",
                           "retry_url": f"/api/v1/workspace/triage-jobs/{row.id}/retry"})
    links = {link.brain_project_id: link.project_id for link in erp.query(BrainLink)}
    for row in filter_brain(db.query(MailEnrichmentJob), MailEnrichmentJob.project_id):
        erp_id = links.get(row.project_id)
        if project_id and erp_id != project_id:
            continue
        source = db.get(Source, row.source_id)
        if not source or source.status != "resolved" or source.project_id != row.project_id:
            continue
        project = erp.get(ERPProject, erp_id) if erp_id else None
        brain = db.get(Project, row.project_id)
        result.append({"id": row.id, "engine": "mail", "kind": "enrichment",
                       "title": (source.source_metadata or {}).get("subject") or "Connaissance du mail",
                       "project_id": erp_id, "brain_project_id": row.project_id,
                       "project_code": project.code if project else brain.code if brain else "",
                       "project_title": project.title if project else brain.name if brain else "",
                       "source_id": row.source_id, "status": row.status,
                       "stage": {"extraction": "Extraction des informations", "memory": "Indexation mémoire", "completed": "Terminé"}.get(row.stage, row.stage),
                       "progress": 100 if row.status == "completed" else 50 if row.stage == "memory" else 0,
                       "processed": 2 if row.status == "completed" else 1 if row.stage == "memory" else 0,
                       "total": 2, "unit": "steps", "can_cancel": False,
                       "can_retry": row.status == "failed", "cancel_url": "",
                       "retry_url": f"/api/v1/workspace/mail-enrichments/{row.id}/retry",
                       "error": row.error, "created_at": utc_iso(row.created_at), "updated_at": utc_iso(row.updated_at)})
    if status != "all":
        result = [row for row in result if row["status"] == status]
    result.sort(key=lambda row: (row["created_at"], row["id"]), reverse=True)
    return {"items": result[offset:offset + limit], "total": len(result)}


class TriageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    force: bool = False


@router.post("/mail-enrichments/{job_id}/retry")
def retry_mail_enrichment(job_id: str, db: Session = Depends(get_db)):
    from app.services.mail_enrichment import retry
    return retry(db, job_id)


@router.get("/triage-jobs")
def triage_jobs(offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    query = db.query(TriageJob)
    total = query.count()
    rows = query.order_by(TriageJob.created_at.desc(), TriageJob.id).offset(offset).limit(limit).all()
    return {"items": [workspace_jobs.describe(row) for row in rows], "total": total}


@router.post("/triage-jobs", status_code=202)
def enqueue_triage(body: TriageRequest, db: Session = Depends(get_db)):
    return workspace_jobs.enqueue(db, body.force)


@router.get("/triage-jobs/latest")
def latest_triage_job(db: Session = Depends(get_db)):
    row = workspace_jobs.active_job(db) or db.query(TriageJob).order_by(TriageJob.created_at.desc(), TriageJob.id).first()
    return {"job": workspace_jobs.describe(row) if row else None}


@router.get("/triage-jobs/{job_id}")
def triage_job(job_id: str, db: Session = Depends(get_db)):
    row = db.get(TriageJob, job_id)
    if not row:
        raise HTTPException(404, "Analyse des mails introuvable")
    return workspace_jobs.describe(row)


@router.post("/triage-jobs/{job_id}/cancel")
def cancel_triage(job_id: str, db: Session = Depends(get_db)):
    return workspace_jobs.change_state(db, job_id, "cancel")


@router.post("/triage-jobs/{job_id}/retry", status_code=202)
def retry_triage(job_id: str, db: Session = Depends(get_db)):
    return workspace_jobs.change_state(db, job_id, "retry")


class ThreadWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field("Nouvelle conversation", min_length=1, max_length=180)
    messages: list[dict] = Field(default_factory=list, max_length=200)

    @field_validator("messages")
    @classmethod
    def bounded_messages(cls, messages):
        if messages is None:
            return messages
        for message in messages:
            if set(message) - {"role", "text", "project", "citations"}:
                raise ValueError("Champs de message non autorisés")
            if message.get("role") not in {"user", "assistant"}:
                raise ValueError("Rôle de message invalide")
            if not isinstance(message.get("text"), str) or len(message["text"]) > 12000:
                raise ValueError("Texte de message invalide ou trop long")
            if "project" in message and (not isinstance(message["project"], str) or len(message["project"]) > 256):
                raise ValueError("Libellé projet invalide")
            if "citations" in message:
                citations = message["citations"]
                if not isinstance(citations, list) or len(citations) > 30 or any(not isinstance(c, dict) for c in citations):
                    raise ValueError("Citations invalides")
                if len(json.dumps(citations, ensure_ascii=False).encode()) > 30000:
                    raise ValueError("Citations trop volumineuses")
        if len(json.dumps(messages, ensure_ascii=False).encode()) > 300000:
            raise ValueError("Conversation trop volumineuse")
        return messages


class ThreadCreate(ThreadWrite):
    project_id: str | None = Field(None, max_length=36)


class ThreadUpdate(ThreadWrite):
    title: str | None = Field(None, min_length=1, max_length=180)
    messages: list[dict] | None = Field(None, max_length=200)
    expected_revision: int = Field(ge=1)


def _describe_thread(row, include_messages=True):
    result = {"id": row.id, "title": row.title, "project_id": row.project_id, "revision": row.revision,
              "message_count": len(row.messages or []), "created_at": utc_iso(row.created_at), "updated_at": utc_iso(row.updated_at)}
    if include_messages:
        result["messages"] = row.messages or []
    return result


@router.get("/assistant-threads")
def assistant_threads(project_id: str | None = None, offset: int = Query(0, ge=0), limit: int = Query(30, ge=1, le=100),
                      db: Session = Depends(get_db)):
    _brain_scope(db, project_id)
    query = filter_brain(db.query(AssistantThread), AssistantThread.project_id)
    if project_id:
        query = query.filter(AssistantThread.project_id == project_id)
    total = query.count()
    rows = query.order_by(AssistantThread.updated_at.desc(), AssistantThread.id).offset(offset).limit(limit).all()
    return {"items": [_describe_thread(row, False) for row in rows], "total": total}


@router.post("/assistant-threads", status_code=201)
def create_thread(body: ThreadCreate, db: Session = Depends(get_db)):
    _brain_scope(db, body.project_id)
    row = AssistantThread(project_id=body.project_id, title=body.title, messages=body.messages)
    db.add(row)
    db.commit()
    return _describe_thread(row)


@router.get("/assistant-threads/{thread_id}")
def assistant_thread(thread_id: str, project_id: str | None = None, db: Session = Depends(get_db)):
    row = db.get(AssistantThread, thread_id)
    if not row or (project_id and row.project_id != project_id):
        raise HTTPException(404, "Conversation introuvable dans ce contexte")
    return _describe_thread(row)


@router.put("/assistant-threads/{thread_id}")
def update_thread(thread_id: str, body: ThreadUpdate, project_id: str | None = None, db: Session = Depends(get_db)):
    row = db.get(AssistantThread, thread_id)
    if not row or (project_id and row.project_id != project_id):
        raise HTTPException(404, "Conversation introuvable dans ce contexte")
    values = {key: value for key, value in {"title": body.title, "messages": body.messages}.items() if value is not None}
    changed = db.execute(update(AssistantThread).where(AssistantThread.id == thread_id,
                        AssistantThread.revision == body.expected_revision)
                         .values(**values, revision=body.expected_revision + 1,
                                 updated_at=datetime.now(timezone.utc)))
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "La conversation a changé ; relire la version enregistrée avant de sauvegarder")
    db.commit()
    db.refresh(row)
    return _describe_thread(row)
