"""Trusted server operator context, independent from a person's business role.

This module is a foundation, not an HTTP authentication layer. Runtime middleware
and internal dispatch must enforce the same context before activating a reader.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import json
import os

from fastapi import HTTPException


@dataclass(frozen=True)
class Operator:
    id: str
    role: str
    project_ids: frozenset[str] | None = None
    person_id: str | None = None

    def __post_init__(self):
        if not self.id or self.role not in {"owner", "editor", "reader"}:
            raise ValueError("Contexte d'opérateur invalide")
        if self.project_ids is not None and not isinstance(self.project_ids, frozenset):
            raise ValueError("La portée d'opérateur doit être immuable")
        if self.person_id is not None and (not isinstance(self.person_id, str) or not 1 <= len(self.person_id) <= 36):
            raise ValueError("Personne de l'opérateur invalide")


_operator: ContextVar[Operator | None] = ContextVar("project_operator", default=None)


def configured_operator() -> Operator:
    """Never read operator identity/privileges from a caller's JSON or headers."""
    role = os.environ.get("AGENT_OPERATOR_ROLE", "owner")
    actor_id = os.environ.get("AGENT_OPERATOR_ID", "local")
    raw_scope = os.environ.get("AGENT_OPERATOR_PROJECT_IDS")
    scope = None
    if raw_scope is not None:
        try:
            values = json.loads(raw_scope)
        except (TypeError, ValueError) as exc:
            raise ValueError("AGENT_OPERATOR_PROJECT_IDS doit être une liste JSON") from exc
        if not isinstance(values, list) or any(not isinstance(x, str) or not x for x in values):
            raise ValueError("AGENT_OPERATOR_PROJECT_IDS doit être une liste d'identifiants")
        scope = frozenset(values)
    return Operator(actor_id, role, scope, os.environ.get("AGENT_OPERATOR_PERSON_ID") or None)


def current_operator() -> Operator:
    return _operator.get() or configured_operator()


@contextmanager
def operator_context(operator: Operator):
    """For trusted server code only; lexical reset prevents cross-request leaks."""
    token = _operator.set(operator)
    try:
        yield
    finally:
        _operator.reset(token)


def require_project_access(project_id: str, *, write=False) -> Operator:
    operator = current_operator()
    if operator.project_ids is not None and project_id not in operator.project_ids:
        raise HTTPException(404, "Projet introuvable")
    if write and operator.role == "reader":
        raise HTTPException(403, "Opérateur en lecture seule")
    return operator


def require_reference_write() -> Operator:
    operator = current_operator()
    if operator.role != "owner" or operator.project_ids is not None:
        raise HTTPException(403, "Administration des référentiels réservée à l'opérateur propriétaire")
    return operator
