"""Bounded L2 commands; privileges and monetary fields are never caller inputs."""
from typing import Literal

from pydantic import Field, FiniteFloat, model_validator

from .project_identity_schemas import RevisionCommand
from .schemas import DomainInput, IsoDate
from .services.project_planning_rules import TemplateDefinition

PlanningTaskStatus = Literal["todo", "assigned", "in_progress", "blocked", "done", "cancelled"]


class PlanningTemplateCreate(DomainInput):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    typology_id: str | None = Field(default=None, min_length=1, max_length=36)
    definition: TemplateDefinition


class PlanningTemplatePatch(RevisionCommand):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    typology_id: str | None = Field(default=None, min_length=1, max_length=36)
    active: bool | None = None

    @model_validator(mode="after")
    def no_null(self):
        if any(getattr(self, key) is None for key in self.model_fields_set - {"typology_id"}):
            raise ValueError("Le nom et l'état ne peuvent être nuls")
        return self


class PlanningTemplatePublish(RevisionCommand):
    definition: TemplateDefinition


class PlanningTemplatePreview(RevisionCommand):
    start_date: IsoDate = ""
    excluded_dates: list[IsoDate] = Field(default_factory=list, max_length=3660)
    milestone_mapping: dict[str, str] = Field(default_factory=dict, max_length=100)
    forecast_policy: Literal["preserve", "fill_empty", "replace"] = "fill_empty"
    update_tasks: bool = False

    @model_validator(mode="after")
    def valid_mappings(self):
        if any(not value or len(value) > 36 for value in self.milestone_mapping.values()):
            raise ValueError("Identifiant de jalon invalide")
        if any(not value for value in self.excluded_dates) or len(set(self.excluded_dates)) != len(self.excluded_dates):
            raise ValueError("Exclusions de calendrier vides ou dupliquées")
        return self


class PlanningTemplateApply(PlanningTemplatePreview):
    expected_preview_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class MilestonePlanningPatch(RevisionCommand):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    code: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    position: int | None = Field(default=None, ge=0, le=100000)
    workflow_status: Literal["pending", "open", "validated", "blocked", "skipped"] | None = None
    comment: str | None = Field(default=None, max_length=20000)
    active: bool | None = None
    contractual_date: IsoDate | None = None
    forecast_date: IsoDate | None = None
    actual_date: IsoDate | None = None

    @model_validator(mode="after")
    def no_null(self):
        for key in self.model_fields_set - {"code", "position", "expected_revision"}:
            if getattr(self, key) is None:
                raise ValueError(f"{key} ne peut être nul")
        return self


class TaskPlanningPatch(RevisionCommand):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    status: PlanningTaskStatus | None = None
    parent_task_id: str | None = Field(default=None, min_length=1, max_length=36)
    milestone_id: str | None = Field(default=None, min_length=1, max_length=36)
    responsible_id: str | None = Field(default=None, min_length=1, max_length=36)
    priority: Literal["low", "normal", "high", "urgent"] | None = None
    start_date: IsoDate | None = None
    end_date: IsoDate | None = None
    planned_hours: FiniteFloat | None = Field(default=None, ge=0, le=1000000)
    design: bool | None = None
    manufacturing: bool | None = None
    comment: str | None = Field(default=None, max_length=20000)
    active: bool | None = None

    @model_validator(mode="after")
    def no_null(self):
        for key in self.model_fields_set - {"parent_task_id", "milestone_id", "responsible_id", "expected_revision"}:
            if getattr(self, key) is None:
                raise ValueError(f"{key} ne peut être nul")
        return self


class TaskPlanningCreate(TaskPlanningPatch):
    title: str = Field(min_length=1, max_length=255)


class BaselineMetadataPatch(RevisionCommand):
    label: str | None = Field(default=None, min_length=1, max_length=255)
    comment: str | None = Field(default=None, max_length=20000)
    active: bool | None = None

    @model_validator(mode="after")
    def no_null(self):
        if any(getattr(self, key) is None for key in self.model_fields_set - {"expected_revision"}):
            raise ValueError("Les métadonnées de référence ne peuvent être nulles")
        if self.label is not None and not self.label.strip():
            raise ValueError("Le nom de référence est requis")
        return self
