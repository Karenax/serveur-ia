"""Isolation des tests : base SQLite temporaire, JAMAIS la vraie base utilisateur."""
import os
import tempfile
import pytest

_tmp = tempfile.mkdtemp(prefix="minipilot-test-")
os.environ["MINIPILOT_HOME"] = _tmp
os.environ["PB_DATABASE_URL"] = "sqlite:///" + _tmp.replace("\\", "/") + "/brain.db"
os.environ["PB_STORAGE_DIR"] = _tmp + "/storage"
os.environ["PB_INFOMANIAK_DIR"] = ""
os.environ["PB_MEMORY_ENGINE"] = "fake"

os.environ["AGENT_TESTING"] = "1"


@pytest.fixture(scope="session", autouse=True)
def initialize_test_databases():
    from app.db import init_db
    from backend.app.db import init_db as init_erp
    init_db()
    init_erp()


@pytest.fixture(autouse=True)
def isolated_settings(initialize_test_databases):
    from app.db import SessionLocal
    from app.services.settings_service import DEFAULTS, save_section
    with SessionLocal() as db:
        for key, value in DEFAULTS.items():
            save_section(db, key, {**value, **({"clear_api_key": True} if key == "ai" else {})})
    yield
