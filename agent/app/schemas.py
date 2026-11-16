"""Pydantic schemas."""
from pydantic import BaseModel as PydanticBaseModel, ConfigDict, Field, field_validator
from typing import Literal


class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid", allow_inf_nan=False)


class ProjectCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=256)
    status: Literal["active", "paused", "done", "archived", "cancelled"] = "active"
    customer_id: str | None = None
    aliases: list[str] = []


class ProjectOut(BaseModel):
    id: str
    code: str
    name: str
    status: str
    customer_id: str | None = None
    aliases: list = []

    model_config = ConfigDict(from_attributes=True)


class ResolutionConfirm(BaseModel):
    project_id: str
    defer_enrichment: bool = False
    pending_only: bool = False


class ProposalDecision(BaseModel):
    supersedes_id: str | None = None
    actor: str = Field(default="validator", min_length=1, max_length=128)
    comment: str | None = None
    subject: str | None = None
    value: str | None = None


class RecallQuery(BaseModel):
    query: str
    scopes: list[str] = ["truth", "evidence"]


class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=12000)


class ChatQuery(BaseModel):
    query: str = Field(min_length=2, max_length=2000)
    project_id: str | None = None
    include_evidence: bool = True
    history: list[ChatHistoryMessage] = Field(default_factory=list, max_length=12)

    @field_validator("history")
    @classmethod
    def bounded_history(cls, history):
        if sum(len(message.content) for message in history) > 12000:
            raise ValueError("Historique limité à 12000 caractères au total")
        return history
