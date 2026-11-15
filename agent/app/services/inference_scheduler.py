"""Bounded, cooperative reservations for each inference server in Agent.

Running requests are never preempted. Priorities only order waiting requests;
capture and speech use separate resources. External applications are not seen.
"""
from __future__ import annotations
from app.operational_limits import INFERENCE_MAX_WAITERS, INFERENCE_WAIT_SECONDS

from contextlib import contextmanager, asynccontextmanager
import asyncio
from contextvars import ContextVar
from dataclasses import dataclass, field
import itertools
import threading
import time
from urllib.parse import urlsplit


PRIORITIES = {"question": 0, "manual": 10, "synthesis": 20,
              "proactive": 30, "enhancement": 40, "background": 50}
_kind = ContextVar("agent_inference_kind", default="manual")
_wait_timeout = ContextVar('agent_inference_wait_timeout', default=None)
_wait_cancel = ContextVar('agent_inference_wait_cancel', default=None)
_condition = threading.Condition(threading.RLock())
_sequence = itertools.count()
_engines: dict[str, "EngineState"] = {}

MAX_WAITERS = INFERENCE_MAX_WAITERS
DEFAULT_WAIT_SECONDS = INFERENCE_WAIT_SECONDS


class InferenceBusy(RuntimeError):
    """A bounded queue, cancellation or reservation deadline prevented work."""


@dataclass
class Ticket:
    priority: int
    order: int
    owner: object


@dataclass
class EngineState:
    owner: object | None = None
    depth: int = 0
    waiting: list[Ticket] = field(default_factory=list)


def engine_key(url: str, *, category: str = 'generation') -> str:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Adresse du moteur IA invalide")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    host = parsed.hostname.lower()
    if host in {'localhost', '127.0.0.1', '::1'}:
        host = '127.0.0.1'
    return f"{category}:{parsed.scheme}://{host}:{port}"


def current_priority() -> int:
    # Idle callers retain their existing foreground/idle contract.
    from . import llm_activity
    if _kind.get() == "manual" and llm_activity._background == threading.get_ident():
        return PRIORITIES["background"]
    return PRIORITIES[_kind.get()]


@contextmanager
def priority_scope(kind: str):
    if kind not in PRIORITIES:
        raise ValueError("Priorité IA inconnue")
    token = _kind.set(kind)
    try:
        yield
    finally:
        _kind.reset(token)


@contextmanager
def wait_policy(*, timeout: float, cancel: threading.Event | None = None):
    """A caller can bound/cancel waiting without preempting a running engine."""
    if timeout < 0:
        raise ValueError('Délai de réservation IA invalide')
    delay_token = _wait_timeout.set(timeout)
    cancel_token = _wait_cancel.set(cancel)
    try:
        yield
    finally:
        _wait_cancel.reset(cancel_token)
        _wait_timeout.reset(delay_token)


def waiting_policy():
    return _wait_timeout.get(), _wait_cancel.get()


@contextmanager
def lease(engine: str, *, priority: int | None = None,
          timeout: float = DEFAULT_WAIT_SECONDS, cancel: threading.Event | None = None):
    if not engine or timeout < 0:
        raise ValueError("Réservation IA invalide")
    policy_timeout = _wait_timeout.get()
    if policy_timeout is not None:
        timeout = min(timeout, policy_timeout)
    if cancel is None:
        cancel = _wait_cancel.get()
    owner = threading.get_ident()
    deadline = time.monotonic() + timeout
    ticket = None
    with _condition:
        state = _engines.setdefault(engine, EngineState())
        if state.owner == owner:
            state.depth += 1
        else:
            if len(state.waiting) >= MAX_WAITERS:
                raise InferenceBusy("File IA pleine ; réessayer après les demandes en cours")
            ticket = Ticket(current_priority() if priority is None else priority,
                            next(_sequence), owner)
            state.waiting.append(ticket)
            try:
                while True:
                    if cancel is not None and cancel.is_set():
                        raise InferenceBusy("Demande IA annulée avant son démarrage")
                    first = min(state.waiting, key=lambda item: (item.priority, item.order))
                    if state.owner is None and first is ticket:
                        state.waiting.remove(ticket)
                        state.owner, state.depth = owner, 1
                        break
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise InferenceBusy("Moteur IA occupé ; délai d'attente dépassé")
                    _condition.wait(min(remaining, 0.1))
            except BaseException:
                if ticket in state.waiting:
                    state.waiting.remove(ticket)
                if state.owner is None and not state.waiting:
                    _engines.pop(engine, None)
                _condition.notify_all()
                raise
    try:
        yield
    finally:
        with _condition:
            state.depth -= 1
            if state.depth == 0:
                state.owner = None
                if not state.waiting:
                    _engines.pop(engine, None)
            _condition.notify_all()


@asynccontextmanager
async def async_lease(engine: str, *, timeout: float = DEFAULT_WAIT_SECONDS):
    """Share the thread queue without blocking the event loop or reentering by thread ID."""
    if not engine or timeout < 0:
        raise ValueError('Réservation IA invalide')
    policy, cancel = waiting_policy()
    deadline = time.monotonic() + (min(timeout, policy) if policy is not None else timeout)
    owner = object()
    ticket = Ticket(current_priority(), next(_sequence), owner)
    with _condition:
        state = _engines.setdefault(engine, EngineState())
        if len(state.waiting) >= MAX_WAITERS:
            raise InferenceBusy('File IA pleine ; réessayer après les demandes en cours')
        state.waiting.append(ticket)
    acquired = False
    try:
        while True:
            with _condition:
                if cancel is not None and cancel.is_set():
                    raise InferenceBusy('Demande IA annulée avant son démarrage')
                first = min(state.waiting, key=lambda item: (item.priority, item.order))
                if state.owner is None and first is ticket:
                    state.waiting.remove(ticket)
                    state.owner, state.depth = owner, 1
                    acquired = True
                    break
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise InferenceBusy("Moteur IA occupé ; délai d'attente dépassé")
            await asyncio.sleep(min(remaining, 0.05))
        yield
    finally:
        with _condition:
            if acquired:
                state.owner, state.depth = None, 0
            elif ticket in state.waiting:
                state.waiting.remove(ticket)
            if state.owner is None and not state.waiting:
                _engines.pop(engine, None)
            _condition.notify_all()


def status() -> dict:
    with _condition:
        return {"active": sum(state.owner is not None for state in _engines.values()),
                "waiting": sum(len(state.waiting) for state in _engines.values()),
                "max_waiters_per_engine": MAX_WAITERS,
                "scope": "Agent process; external applications are not observed",
                "preemption": False}
