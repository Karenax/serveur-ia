"""Read-only evidence-based project dashboard analyses."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Project
from ..services.project_operator import require_project_access
from ..services.project_knowledge_analysis import describe

router = APIRouter(prefix="/api/v1/projects", tags=["project-knowledge"])


@router.get("/{project_id}/knowledge-analysis")
def analysis(project_id: str, offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=50), db: Session = Depends(get_db)):
    require_project_access(project_id)
    if not db.get(Project, project_id):
        raise HTTPException(404, "Projet introuvable")
    return describe(db, project_id, offset, limit)
