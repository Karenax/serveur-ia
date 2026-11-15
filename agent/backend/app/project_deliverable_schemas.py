"""Bounded L3 commands. Generation, checklist completion and visa are distinct."""
from typing import Literal

from pydantic import Field, model_validator

from .project_identity_schemas import RevisionCommand
from .schemas import DomainInput

DocumentStatus = Literal['draft', 'to_verify', 'validated', 'to_revise', 'archived']
Category = Literal['studies', 'fabrication', 'project_end']


class CheckDefinition(DomainInput):
    code: str = Field(pattern=r'^[a-z][a-z0-9_-]{0,63}$')
    label: str = Field(min_length=1, max_length=500)
    milestone_code: str = Field(default='', max_length=64)
    is_gate: bool = False
    transverse: bool = False
    contributes: bool = True
    active: bool = True
    typology_codes: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode='after')
    def applicability(self):
        if len(set(self.typology_codes)) != len(self.typology_codes) or any(
                not code or len(code) > 64 for code in self.typology_codes):
            raise ValueError('Typologies conditionnelles invalides')
        return self


class TypeDefinition(DomainInput):
    category: Category = 'studies'
    design: bool = True
    position: int = Field(default=0, ge=0, le=100000)
    checklist: list[CheckDefinition] = Field(default_factory=list, max_length=250)

    @model_validator(mode='after')
    def unique_codes(self):
        if len({item.code for item in self.checklist}) != len(self.checklist):
            raise ValueError('Codes de checklist dupliqués')
        return self


class TypeCreate(DomainInput):
    code: str = Field(pattern=r'^[a-z][a-z0-9_-]{0,63}$')
    label: str = Field(min_length=1, max_length=255)
    definition: TypeDefinition


class TypePublish(RevisionCommand):
    definition: TypeDefinition


class TypePatch(RevisionCommand):
    label: str | None = Field(default=None, min_length=1, max_length=255)
    active: bool | None = None

    @model_validator(mode='after')
    def no_null(self):
        if any(getattr(self, key) is None for key in self.model_fields_set):
            raise ValueError('Valeur nulle interdite')
        return self


class TypologyTypesPatch(RevisionCommand):
    type_ids: list[str] = Field(max_length=100)

    @model_validator(mode='after')
    def unique_ids(self):
        if len(set(self.type_ids)) != len(self.type_ids) or any(not item or len(item) > 36 for item in self.type_ids):
            raise ValueError('Identifiants de types invalides ou dupliqués')
        return self


class SelectionPreview(RevisionCommand):
    type_version_ids: list[str] = Field(max_length=100)
    typology_id: str | None = Field(default=None, min_length=1, max_length=36)
    milestone_mapping: dict[str, str] = Field(default_factory=dict, max_length=100)
    excluded_milestone_codes: list[str] = Field(default_factory=list, max_length=100)
    existing_mapping: dict[str, str] = Field(default_factory=dict, max_length=100)
    deactivate_missing: bool = False
    responsible_id: str | None = Field(default=None, min_length=1, max_length=36)
    verifier_id: str | None = Field(default=None, min_length=1, max_length=36)

    @model_validator(mode='after')
    def bounded_mappings(self):
        for values in (self.type_version_ids, self.excluded_milestone_codes):
            if len(set(values)) != len(values) or any(not item or len(item) > 64 for item in values):
                raise ValueError('Sélection dupliquée ou invalide')
        for mapping in (self.milestone_mapping, self.existing_mapping):
            if any(not key or len(key) > 64 or not value or len(value) > 36 for key, value in mapping.items()):
                raise ValueError('Correspondance invalide')
        if set(self.excluded_milestone_codes).intersection(self.milestone_mapping):
            raise ValueError('Un jalon ne peut être à la fois inclus et exclu')
        if len(set(self.existing_mapping.values())) != len(self.existing_mapping):
            raise ValueError('Un livrable ne peut représenter plusieurs types')
        return self


class SelectionApply(SelectionPreview):
    expected_preview_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')


class DeliverableCreate(RevisionCommand):
    title: str = Field(min_length=1, max_length=255)
    type_version_id: str | None = Field(default=None, min_length=1, max_length=36)
    milestone_ids: list[str] = Field(default_factory=list, max_length=100)
    # Explicit mapping avoids treating legacy 'Revue de conception' as PDR/CDR.
    milestone_mapping: dict[str, str] = Field(default_factory=dict, max_length=100)
    responsible_id: str | None = Field(default=None, min_length=1, max_length=36)
    verifier_id: str | None = Field(default=None, min_length=1, max_length=36)

    @model_validator(mode='after')
    def unique_milestones(self):
        if len(set(self.milestone_ids)) != len(self.milestone_ids):
            raise ValueError('Jalons dupliqués')
        if any(not key or len(key) > 64 or not value or len(value) > 36
               for key, value in self.milestone_mapping.items()):
            raise ValueError('Correspondance de jalon invalide')
        return self


class DeliverablePatch(RevisionCommand):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    responsible_id: str | None = Field(default=None, min_length=1, max_length=36)
    verifier_id: str | None = Field(default=None, min_length=1, max_length=36)
    active: bool | None = None
    comment: str | None = Field(default=None, max_length=20000)

    @model_validator(mode='after')
    def no_null(self):
        for key in self.model_fields_set - {'responsible_id', 'verifier_id'}:
            if getattr(self, key) is None:
                raise ValueError(f'{key} ne peut être nul')
        return self


class ChecklistCreate(RevisionCommand):
    code: str = Field(pattern=r'^[a-z][a-z0-9_-]{0,63}$')
    label: str = Field(min_length=1, max_length=500)
    milestone_id: str | None = Field(default=None, min_length=1, max_length=36)
    is_gate: bool = False
    transverse: bool = False
    contributes: bool = True


class ChecklistPatch(RevisionCommand):
    label: str | None = Field(default=None, min_length=1, max_length=500)
    completed: bool | None = None
    active: bool | None = None
    comment: str | None = Field(default=None, max_length=20000)
    proof: str | None = Field(default=None, max_length=20000)

    @model_validator(mode='after')
    def no_null(self):
        if any(getattr(self, key) is None for key in self.model_fields_set):
            raise ValueError('Valeur nulle interdite')
        return self


class FilePublication(RevisionCommand):
    reference: str = Field(min_length=1, max_length=120)
    comment: str = Field(default='', max_length=20000)
    generated: bool = False
    source_delivery_id: str | None = Field(default=None, min_length=1, max_length=36)


class VersionMetadataPatch(RevisionCommand):
    reference: str | None = Field(default=None, min_length=1, max_length=120)
    comment: str | None = Field(default=None, max_length=20000)

    @model_validator(mode='after')
    def no_null(self):
        if any(getattr(self, key) is None for key in self.model_fields_set):
            raise ValueError('Valeur nulle interdite')
        return self


class DocumentTransition(RevisionCommand):
    status: DocumentStatus
    version_id: str = Field(min_length=1, max_length=36)
    comment: str = Field(default='', max_length=20000)
