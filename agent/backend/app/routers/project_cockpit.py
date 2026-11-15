"""Independent cockpit reads; existing scoped L2/L3 command routes are reused."""
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..services import project_cockpit as service

router = APIRouter(prefix='/api/v1/projects/{project_id}/cockpit', tags=['project-cockpit'])


@router.get('')
def structure(project_id: str, search: str = Query('', max_length=200), show_past: bool = False,
              offset: int = Query(0, ge=0, le=1000000), limit: int = Query(50, ge=1, le=100),
              db: Session = Depends(get_db)):
    return service.structure(db, project_id, search=search, show_past=show_past, offset=offset, limit=limit)


@router.get('/items/{kind}')
def items(project_id: str, kind: Literal['tasks', 'deliverables'], milestone_id: str | None = None,
          unassigned: bool = False, search: str = Query('', max_length=200),
          offset: int = Query(0, ge=0, le=1000000), limit: int = Query(25, ge=1, le=100),
          db: Session = Depends(get_db)):
    action = service.task_page if kind == 'tasks' else service.document_page
    return action(db, project_id, milestone_id=milestone_id, unassigned=unassigned,
                  search=search, offset=offset, limit=limit)


@router.get('/alerts')
def alerts(project_id: str, offset: int = Query(0, ge=0, le=1000000), limit: int = Query(25, ge=1, le=100),
           db: Session = Depends(get_db)):
    return service.alerts(db, project_id, offset=offset, limit=limit)
