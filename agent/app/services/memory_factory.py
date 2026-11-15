"""EG2 production memory; SQL fixture adapter only for isolated tests."""
import os


def resolve_engine(db_factory=None):
    if os.environ.get("AGENT_TESTING") == "1":
        from ..config import settings
        if settings.memory_engine == "fake":
            return "fake"
    return "eg2"


def get_memory_adapter(db_factory=None):
    if resolve_engine(db_factory) == "fake":
        from .memory_port import FakeMemoryAdapter
        return FakeMemoryAdapter(db_factory)
    from .eg2_memory import EG2MemoryAdapter
    return EG2MemoryAdapter(db_factory)
