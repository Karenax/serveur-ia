"""Server-side operator policy shared by HTTP, internal dispatch and queries.

The local operator is configured on the server; business membership and client
headers never grant privileges. Scoped unknown endpoints fail closed.
"""
import re

from fastapi import HTTPException
from sqlalchemy import or_, select

from backend.app.services.project_operator import current_operator

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
PUBLIC_PATHS = frozenset({"/", "/app", "/health", "/api/v1/session", "/docs", "/redoc", "/openapi.json"})
SCOPED_LISTS = frozenset({
    "/api/v1/portfolio", "/api/v1/project-catalogue", "/api/v1/actions", "/api/v1/search",
    "/api/v1/project-references", "/api/v1/project-people",
    "/v1/projects", "/v1/stats", "/v1/proposals", "/v1/resolution/pending", "/v1/sources", "/v1/search",
    "/v1/mail/page", "/v1/mail/project-usage",
    "/api/v1/workspace/knowledge", "/api/v1/workspace/proposals", "/api/v1/workspace/meetings", "/api/v1/workspace/jobs",
    "/api/v1/workspace/assistant-threads", "/api/v1/brain/projects", "/api/v1/brain/proposals", "/api/v1/brain/sources",
    "/api/v1/meeting-sessions", "/api/v1/meeting-sessions/capabilities",
    "/api/v1/workspace/sources", "/api/v1/workspace/fusion-stats", "/api/v1/workspace/source-graph",
    "/api/v1/workspace/sources/search", "/api/v1/workspace/indexing",
    "/api/v1/workspace/native-capture",
    "/api/v1/brain/status", "/api/v1/ai/status", "/api/v1/meeting-audio/status",
    "/api/v1/connections/status",
    "/api/v1/planning-templates",
    "/api/v1/deliverable-types",
    "/api/v1/review-types",
})
ADMIN_PREFIXES = (
    "/v1/settings", "/v1/thunderbird", "/api/v1/operations", "/api/v1/sage", "/ui/settings",
    "/api/v1/brain/ai-settings", "/api/v1/brain/mail-settings", "/api/v1/brain/memory-settings",
    "/api/v1/brain/overview", "/api/v1/brain/ingest", "/api/v1/brain/ai-test", "/api/v1/brain/memory-test",
    "/api/v1/projects/import-json",
    "/api/v1/document-settings",
    "/api/v1/workspace/sources/connectors",
    "/api/v1/workspace/fusion-settings",
)


def erp_ids():
    return current_operator().project_ids


def brain_ids():
    scope = erp_ids()
    if scope is None:
        return None
    from backend.app.db import SessionLocal
    from backend.app.models import BrainLink, Project
    with SessionLocal() as db:
        return frozenset(row[0] for row in db.query(BrainLink.brain_project_id).join(
            Project, Project.id == BrainLink.project_id).filter(Project.id.in_(scope)).all())


def filter_erp(query, column):
    scope = erp_ids()
    return query if scope is None else query.filter(column.in_(scope))


def filter_brain(query, column):
    scope = brain_ids()
    return query if scope is None else query.filter(column.in_(scope))


def filter_proposals(query):
    scope = brain_ids()
    if scope is None:
        return query
    from app.models import Proposal, Source
    return query.filter(Proposal.project_id.in_(scope), or_(
        Proposal.source_id.is_(None), Proposal.source_id.in_(select(Source.id).where(Source.project_id.in_(scope)))))


def require_erp(project_id):
    if not isinstance(project_id, str) or not project_id:
        raise HTTPException(422, "Identifiant de projet invalide")
    scope = erp_ids()
    if scope is not None and project_id not in scope:
        raise HTTPException(404, "Projet introuvable")


def require_brain(project_id):
    if not isinstance(project_id, str) or not project_id:
        raise HTTPException(422, "Identifiant de connaissance invalide")
    scope = brain_ids()
    if scope is not None and project_id not in scope:
        raise HTTPException(404, "Projet de connaissance introuvable")


def pending_mail_scope(query, scope):
    """A pending mail is visible only through a project within the operator's scope."""
    from app.models import Proposal, Source
    if scope is None:
        return query
    outside = select(Proposal.source_id).where(
        Proposal.kind == "project_attach", Proposal.status == "pending",
        Proposal.source_id.is_not(None),
        or_(Proposal.project_id.is_(None), ~Proposal.project_id.in_(scope)))
    return query.filter(
        Proposal.project_id.in_(scope),
        or_(Source.project_id.in_(scope),
            Source.project_id.is_(None) & ~Source.id.in_(outside)))


def rejected_mail_scope(query, scope):
    """Unrestricted owners see the archive; scoped editors see their own in-scope decisions."""
    from app.models import Proposal, Source, ValidationDecision

    query = query.filter(Source.source_type == "email", Source.status == "rejected")
    operator = current_operator()
    if operator.role == "reader":
        return query.filter(False)
    if scope is None:
        return query
    rejected = select(Proposal.source_id).where(
        Proposal.kind == "project_attach", Proposal.status == "rejected", Proposal.source_id.is_not(None))
    own = rejected.join(ValidationDecision, ValidationDecision.proposal_id == Proposal.id).where(
        Proposal.project_id.in_(scope),
        ValidationDecision.decision == "reject", ValidationDecision.actor == operator.id)
    outside = rejected.where(or_(Proposal.project_id.is_(None), ~Proposal.project_id.in_(scope)))
    return query.filter(Source.id.in_(own), ~Source.id.in_(outside),
                        or_(Source.project_id.is_(None), Source.project_id.in_(scope)))


def require_mail_proposal(db, proposal_id, scope):
    from app.models import Proposal, Source
    query = db.query(Proposal).join(Source, Source.id == Proposal.source_id).filter(
        Proposal.id == proposal_id, Proposal.kind == "project_attach", Proposal.status == "pending",
        Source.source_type == "email", Source.status == "resolution_pending")
    if not pending_mail_scope(query, scope).first():
        raise HTTPException(404, "Proposition de classement introuvable ou déjà traitée")


def _record(kind, identifier):
    if not isinstance(identifier, str) or not 1 <= len(identifier) <= 36:
        raise HTTPException(422, "Identifiant d'objet invalide")
    from app.db import SessionLocal
    from app.models import Proposal, Source
    from app.workspace_models import AssistantThread, MailEnrichmentJob
    model = {"sources": Source, "proposals": Proposal, "resolution": Source,
             "assistant-threads": AssistantThread, "mail-enrichments": MailEnrichmentJob}[kind]
    with SessionLocal() as db:
        row = db.get(model, identifier)
        if row is None or not row.project_id:
            raise HTTPException(404, "Objet introuvable dans les projets autorisés")
        require_brain(row.project_id)
        if kind in {"proposals", "mail-enrichments"} and row.source_id:
            source = db.get(Source, row.source_id)
            if not source or not source.project_id:
                raise HTTPException(404, "Source de proposition hors périmètre")
            require_brain(source.project_id)


def _project_body(path, body):
    if not isinstance(body, dict):
        return
    if body.get("project_id"):
        require_brain(body["project_id"])
    if body.get("brain_project_id"):
        require_brain(body["brain_project_id"])
    if body.get("thread_id"):
        _record("assistant-threads", body["thread_id"])
    if path.startswith("/v1/") and body.get("source_id"):
        _record("sources", body["source_id"])


def authorize(method, path, *, query=None, body=None):
    """HTTP/dispatch guard. It does not replace parent checks inside domain services."""
    operator = current_operator()
    query = query or {}
    method = method.upper()
    path = path.rstrip("/") or "/"
    if operator.id == 'kiara-thunderbird':
        from kiara_shared.thunderbird import bridge_route
        if method == 'POST' and not query and bridge_route(path):
            return
        raise HTTPException(403, 'Commande indisponible pour la liaison Thunderbird')
    if operator.id == 'kiara-thunderbird-reply':
        if not query and (method, path) in {('GET', '/v1/thunderbird/status'), ('POST', '/v1/thunderbird/drafts')}:
            return
        raise HTTPException(403, 'Seules les réponses Thunderbird sont accessibles sur ce poste')
    if operator.role == "owner" and operator.project_ids is None:
        return
    if (method, path) == ('POST', '/api/v1/session'):
        return  # Only the standalone handler can exchange its configured credential.
    if (method, path) in {
        ("GET", "/api/v1/workspace/fusion-settings/personal"),
        ("PUT", "/api/v1/workspace/fusion-settings/personal"),
        ("GET", "/api/v1/document-settings/personal"),
        ("PUT", "/api/v1/document-settings/personal"),
        ("GET", "/api/v1/document-settings/personal/history"),
        ("POST", "/api/v1/document-settings/personal/restore"),
    }:
        return  # These handlers always use the authenticated operator's own key.
    read_query = method == "POST" and (bool(re.fullmatch(r"/v1/projects/[^/]+/memory/recall", path))
                                      or bool(re.fullmatch(r"/api/v1/projects/[^/]+/planning/templates/[^/]+/preview", path))
                                      or bool(re.fullmatch(r"/api/v1/projects/[^/]+/deliverable-plan/selection/preview", path))
                                      or bool(re.fullmatch(r"/api/v1/projects/[^/]+/documents/preview", path))
                                      or bool(re.fullmatch(r"/api/v1/projects/[^/]+/documents/discover(?:-folder)?", path))
                                      or bool(re.fullmatch(r"/api/v1/projects/[^/]+/documents/artifacts/[^/]+/publication-preview", path))
                                      or path in {"/v1/projects/chat", "/v1/projects/chat/stream", "/api/v1/brain/chat"})
    read_query = read_query or method == "POST" and bool(re.fullmatch(r"/api/v1/meeting-sessions/[^/]+/(?:ask|live-answers)", path))
    if method not in SAFE_METHODS and not read_query and operator.role == "reader":
        raise HTTPException(403, "Opérateur en lecture seule : modification interdite")
    public = path in PUBLIC_PATHS or path.startswith(("/assets/", "/static/", "/app/"))
    if public and method in SAFE_METHODS:
        return
    match = re.fullmatch(r"/internal/kiara/projects/([^/]+)/(context|conversations|memories)", path)
    if match and (method == "GET" or match[2] in {"conversations", "memories"} and method == "POST"):
        require_erp(match[1])
        return
    if path in {'/internal/kiara/conversations', '/internal/kiara/memories', '/internal/kiara/transcriptions'} and method == 'GET':
        return
    if method in SAFE_METHODS and path in {"/api/v1/document-settings", "/api/v1/workspace/fusion-settings"}:
        return
    admin = any(path == prefix or path.startswith(prefix + "/") for prefix in ADMIN_PREFIXES)
    if admin:
        raise HTTPException(403, "Administration réservée à l'opérateur propriétaire sans restriction de projets")
    if method not in SAFE_METHODS and re.fullmatch(r"/api/v1/projects/[^/]+/brain(?:/ensure)?", path):
        raise HTTPException(403, "Modification des liaisons Brain réservée à l'opérateur propriétaire")
    if operator.project_ids is None:
        return
    if path in {'/api/v1/notes/projects', '/api/v1/notes/all'} and method in SAFE_METHODS:
        return  # Both queries apply the operator's project scope.
    if path == '/api/v1/notes/personal' or path.startswith('/api/v1/notes/personal/'):
        return  # The private notebook checks ownership on every note and image.
    if path == "/api/v1/meeting-sessions" and method == "POST":
        if not isinstance(body, dict) or not body.get("project_id"):
            raise HTTPException(403, "Choisir un projet autorisé pour la séance")
        require_erp(body["project_id"])
        return
    match = re.fullmatch(r"/api/v1/meeting-sessions/([^/]+)(?:/.*)?", path)
    if match and match[1] != "capabilities":
        from app.db import SessionLocal
        from .meeting_sessions import get_session
        with SessionLocal() as db:
            get_session(db, match[1], write=method not in SAFE_METHODS and not read_query)
        if isinstance(body, dict) and body.get("project_id"):
            require_erp(body["project_id"])
        return
    if path.startswith("/api/v1/workspace/sources/"):
        _project_body(path, body)
        return  # The handler checks the exact source/project before reading bytes.
    if method in SAFE_METHODS and re.fullmatch(
            r"/api/v1/(?:planning-templates|deliverable-types)/[^/]+(?:/versions(?:/[^/]+)?)?", path):
        # Templates are limited by visible project usages; common deliverable
        # definitions are readable but never administrable from a scoped actor.
        return
    if method in SAFE_METHODS and re.fullmatch(r"/api/v1/project-references/[^/]+/deliverable-types", path):
        # The domain reference lookup enforces visible project typologies.
        return
    match = re.match(r"/api/v1/projects/([^/]+)(?:/|$)", path)
    if match and match[1] not in {"import", "import-json"}:
        require_erp(match[1])
        _project_body(path, body)
        return
    match = re.match(r"/(?:v1|ui)/projects/([^/]+)(?:/|$)", path)
    if match and match[1] not in {"chat"}:
        require_brain(match[1])
        _project_body(path, body)
        return
    match = re.match(r"/v1/(sources|proposals|resolution)/([^/]+)(?:/|$)", path)
    if match and path != "/v1/resolution/pending":
        try:
            _record(match[1], match[2])
        except HTTPException as denied:
            if (denied.status_code != 404 or operator.role == "reader" or method not in SAFE_METHODS
                    or not re.fullmatch(r"/v1/sources/[^/]+(?:/raw|/attachments/\d+)?", path)):
                raise
            from app.db import SessionLocal
            from app.models import Proposal, Source
            scope = brain_ids()
            with SessionLocal() as db:
                source = db.query(Source.id).filter(Source.id == match[2])
                if rejected_mail_scope(source, scope).first():
                    return
                if not path.endswith("/raw"):
                    pending = db.query(Proposal.id).join(Source, Source.id == Proposal.source_id).filter(
                        Source.id == match[2], Source.project_id.is_(None), Source.source_type == "email",
                        Source.status == "resolution_pending", Proposal.kind == "project_attach", Proposal.status == "pending")
                    if pending_mail_scope(pending, scope).first():
                        return
            raise
        _project_body(path, body)
        return
    match = re.fullmatch(r"/(?:v1|api/v1/brain)/triage/([^/]+)/(accept|assign|reject)", path)
    if match and method == "POST":
        from app.db import SessionLocal
        with SessionLocal() as db:
            require_mail_proposal(db, match[1], brain_ids())
        _project_body(path, body)
        return
    match = re.match(r"/api/v1/brain/(sources|triage)/([^/]+)(?:/|$)", path)
    if match:
        _record("sources" if match[1] == "sources" else "proposals", match[2])
        _project_body(path, body)
        return
    match = re.match(r"/api/v1/workspace/(assistant-threads|mail-enrichments)/([^/]+)(?:/|$)", path)
    if match:
        _record(match[1], match[2])
        return
    if path in SCOPED_LISTS and method in SAFE_METHODS:
        project_id = query.get("project_id")
        if project_id:
            brain_query = path in {"/v1/sources", "/v1/search", "/v1/mail/page", "/api/v1/workspace/knowledge", "/api/v1/workspace/proposals",
                                   "/api/v1/workspace/assistant-threads", "/api/v1/brain/sources", "/api/v1/workspace/sources",
                                   "/api/v1/workspace/source-graph", "/api/v1/workspace/fusion-stats"}
            (require_brain if brain_query else require_erp)(project_id)
        return
    if path == "/api/v1/workspace/assistant-threads" and method == "POST":
        if not isinstance(body, dict) or not body.get("project_id"):
            raise HTTPException(403, "Choisir un projet autorisé pour la conversation")
        _project_body(path, body)
        return
    if path in {"/v1/projects/chat", "/v1/projects/chat/stream", "/api/v1/brain/chat"}:
        _project_body(path, body)
        return
    raise HTTPException(403, "Fonction globale indisponible dans cette portée de projets")
