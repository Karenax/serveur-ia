"""Scoped, paged planning commands, alongside the legacy échéancier endpoint."""
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..project_identity_schemas import RevisionCommand
from ..project_planning_schemas import (
    BaselineMetadataPatch, MilestonePlanningPatch, PlanningTemplateApply, PlanningTemplateCreate, PlanningTemplatePatch,
    PlanningTemplatePreview, PlanningTemplatePublish, TaskPlanningCreate, TaskPlanningPatch,
)
from ..services import project_planning as planning
from ..services import planning_templates as templates

router = APIRouter(prefix="/api/v1/projects/{project_id}/planning", tags=["project-planning"])
catalog_router = APIRouter(prefix="/api/v1/planning-templates", tags=["planning-templates"])


def _command(db, action, *args, **kwargs):
    try:
        result = action(db, *args, **kwargs)
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise


@router.get("/state")
def state(project_id: str, db: Session = Depends(get_db)):
    return planning.planning_info(db, project_id)


@router.get("/items/{kind}")
def items(project_id: str, kind: Literal["tasks", "milestones"], search: str = Query("", max_length=200),
          include_inactive: bool = False, offset: int = Query(0, ge=0, le=1000000),
          limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    return planning.planning_items(db, project_id, kind, search=search, include_inactive=include_inactive,
                                   offset=offset, limit=limit)


@router.patch("/tasks/{task_id}")
def patch_task(project_id: str, task_id: str, payload: TaskPlanningPatch, db: Session = Depends(get_db)):
    return _command(db, planning.patch_task, project_id, task_id, payload)


@router.get("/items/{kind}/{item_id}")
def item(project_id: str, kind: Literal['tasks', 'milestones'], item_id: str, db: Session = Depends(get_db)):
    return planning.planning_item(db, project_id, kind, item_id)


@router.post("/tasks", status_code=201)
def create_task(project_id: str, payload: TaskPlanningCreate, db: Session = Depends(get_db)):
    return _command(db, planning.create_task, project_id, payload)


@router.patch("/milestones/{milestone_id}")
def patch_milestone(project_id: str, milestone_id: str, payload: MilestonePlanningPatch, db: Session = Depends(get_db)):
    return _command(db, planning.patch_milestone, project_id, milestone_id, payload)


@router.get("/history")
def history(project_id: str, offset: int = Query(0, ge=0, le=1000000), limit: int = Query(50, ge=1, le=200),
            db: Session = Depends(get_db)):
    return planning.planning_history(db, project_id, offset=offset, limit=limit)


@router.get("/history/{change_id}")
def history_detail(project_id: str, change_id: str, db: Session = Depends(get_db)):
    return planning.planning_history_detail(db, project_id, change_id)


class BaselineCreate(RevisionCommand):
    kind: Literal["initial", "contractual", "review", "amendment"]
    label: str = Field(min_length=1, max_length=255)


@router.post("/baselines", status_code=201)
def create_baseline(project_id: str, payload: BaselineCreate, db: Session = Depends(get_db)):
    return _command(db, planning.create_baseline, project_id, **payload.model_dump())


@router.get("/baselines")
def baselines(project_id: str, include_inactive: bool = False, offset: int = Query(0, ge=0, le=1000000), limit: int = Query(50, ge=1, le=200),
              db: Session = Depends(get_db)):
    return planning.list_baselines(db, project_id, offset=offset, limit=limit, include_inactive=include_inactive)


@router.get('/baselines/{baseline_id}')
def baseline_detail(project_id: str, baseline_id: str, db: Session = Depends(get_db)):
    return planning.baseline_detail(db, project_id, baseline_id)


@router.patch('/baselines/{baseline_id}')
def patch_baseline_metadata(project_id: str, baseline_id: str, payload: BaselineMetadataPatch, db: Session = Depends(get_db)):
    return _command(db, planning.patch_baseline_metadata, project_id, baseline_id, payload)


@router.get("/baselines/{baseline_id}/compare")
def compare_baseline(project_id: str, baseline_id: str, db: Session = Depends(get_db)):
    return planning.compare_baseline(db, project_id, baseline_id)


@catalog_router.get("")
def list_templates(search: str = Query("", max_length=200), include_inactive: bool = False,
                   typology_id: str | None = None, offset: int = Query(0, ge=0, le=1000000),
                   limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    return templates.list_templates(db, search=search, include_inactive=include_inactive,
                                    typology_id=typology_id, offset=offset, limit=limit)


@catalog_router.get("/standard-definition")
def standard_definition():
    from ..services.project_planning_rules import default_template
    return default_template().model_dump()


@catalog_router.post("", status_code=201)
def create_template(payload: PlanningTemplateCreate, db: Session = Depends(get_db)):
    return _command(db, templates.create_template, payload)


@catalog_router.patch("/{template_id}")
def patch_template(template_id: str, payload: PlanningTemplatePatch, db: Session = Depends(get_db)):
    return _command(db, templates.patch_template, template_id, payload)


@catalog_router.get('/{template_id}')
def template_detail(template_id: str, db: Session = Depends(get_db)):
    return templates.template_detail(db, template_id)


@catalog_router.get("/{template_id}/versions")
def versions(template_id: str, offset: int = Query(0, ge=0, le=1000000), limit: int = Query(50, ge=1, le=200),
             db: Session = Depends(get_db)):
    return templates.versions(db, template_id, offset=offset, limit=limit)


@catalog_router.get("/{template_id}/versions/{version_id}")
def read_version(template_id: str, version_id: str, db: Session = Depends(get_db)):
    return templates.read_version(db, template_id, version_id)


@catalog_router.post("/{template_id}/versions", status_code=201)
def publish_version(template_id: str, payload: PlanningTemplatePublish, db: Session = Depends(get_db)):
    return _command(db, templates.publish_version, template_id, payload)


@router.get("/mapping-proposals")
def mapping_proposals(project_id: str, db: Session = Depends(get_db)):
    return templates.mapping_proposals(db, project_id)


@router.post("/templates/{version_id}/preview")
def preview_template(project_id: str, version_id: str, payload: PlanningTemplatePreview, db: Session = Depends(get_db)):
    return templates.preview_application(db, project_id, version_id, payload)


@router.post("/templates/{version_id}/apply")
def apply_template(project_id: str, version_id: str, payload: PlanningTemplateApply, db: Session = Depends(get_db)):
    return _command(db, templates.apply_template, project_id, version_id, payload)
