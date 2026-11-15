"""Explicit, bounded identity commands; no monetary or authorization fields."""
from typing import Literal

from pydantic import Field, model_validator

from .schemas import DomainInput, IsoDate

ReferenceKind = Literal["client", "agency", "business_unit", "family", "typology"]
MemberRole = Literal[
    "responsable_projet", "pilote_etude", "be_3d", "be_2d", "verificateur_be", "qualite",
    "calcul", "charge_fabrication", "collaborateur_projet", "lecteur_projet"]


class RevisionCommand(DomainInput):
    expected_revision: int = Field(ge=0)


class ReferenceCreate(DomainInput):
    kind: ReferenceKind
    code: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=255)


class ReferencePatch(RevisionCommand):
    label: str | None = Field(default=None, min_length=1, max_length=255)
    active: bool | None = None

    @model_validator(mode="after")
    def no_explicit_null(self):
        for name in self.model_fields_set - {"expected_revision"}:
            if getattr(self, name) is None:
                raise ValueError(f"{name} ne peut être nul")
        return self


class PersonCreate(DomainInput):
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    email: str = Field(default="", max_length=255)
    trigram: str = Field(default="", max_length=12)
    function: str = Field(default="", max_length=120)
    service: str = Field(default="", max_length=120)
    phone: str = Field(default="", max_length=40)
    agency_id: str | None = Field(default=None, min_length=1, max_length=36)


class PersonPatch(RevisionCommand):
    first_name: str | None = Field(default=None, min_length=1, max_length=120)
    last_name: str | None = Field(default=None, min_length=1, max_length=120)
    email: str | None = Field(default=None, max_length=255)
    trigram: str | None = Field(default=None, max_length=12)
    function: str | None = Field(default=None, max_length=120)
    service: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    agency_id: str | None = Field(default=None, min_length=1, max_length=36)
    active: bool | None = None

    @model_validator(mode="after")
    def no_explicit_null(self):
        for name in self.model_fields_set - {"expected_revision", "agency_id"}:
            if getattr(self, name) is None:
                raise ValueError(f"{name} ne peut être nul")
        return self


class IdentityPatch(RevisionCommand):
    client_id: str | None = Field(default=None, min_length=1, max_length=36)
    agency_id: str | None = Field(default=None, min_length=1, max_length=36)
    business_unit_id: str | None = Field(default=None, min_length=1, max_length=36)
    family_id: str | None = Field(default=None, min_length=1, max_length=36)
    typology_id: str | None = Field(default=None, min_length=1, max_length=36)
    responsible_id: str | None = Field(default=None, min_length=1, max_length=36)
    description: str | None = Field(default=None, max_length=20000)
    client_reference: str | None = Field(default=None, max_length=120)
    client_site: str | None = Field(default=None, max_length=255)
    client_contact: str | None = Field(default=None, max_length=255)
    equipment_number: str | None = Field(default=None, max_length=120)
    quantity: int | None = Field(default=None, ge=1, le=1000000)
    start_date: IsoDate | None = None
    planned_end_date: IsoDate | None = None
    standby: bool | None = None

    @model_validator(mode="after")
    def no_null_text(self):
        nullable = {"quantity", "responsible_id", "client_id", "agency_id", "business_unit_id", "family_id", "typology_id"}
        for name in self.model_fields_set - nullable - {"expected_revision"}:
            if getattr(self, name) is None:
                raise ValueError(f"{name} ne peut être nul ; utiliser une valeur vide")
        return self


class MemberCreate(RevisionCommand):
    person_id: str = Field(min_length=1, max_length=36)
    role: MemberRole
    start_date: IsoDate = ""
    end_date: IsoDate = ""


class MemberPatch(RevisionCommand):
    role: MemberRole | None = None
    start_date: IsoDate | None = None
    end_date: IsoDate | None = None

    @model_validator(mode="after")
    def no_explicit_null(self):
        for name in self.model_fields_set - {"expected_revision"}:
            if getattr(self, name) is None:
                raise ValueError(f"{name} ne peut être nul")
        return self
