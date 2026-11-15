"""SQLite connection policy and additive, recorded schema migrations."""
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import event, text


def utc_iso(value):
    """SQLite loses timezone metadata; stored UTC timestamps must retain their offset."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def configure_sqlite(engine):
    if engine.dialect.name != "sqlite":
        return

    @event.listens_for(engine, "connect")
    def pragmas(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=10000")
        import unicodedata
        def fold(value):
            text = unicodedata.normalize("NFKD", str(value or "").casefold())
            return "".join(c for c in text if not unicodedata.combining(c))
        connection.create_function("agent_fold", 1, fold, deterministic=True)


def backup_sqlite(path: Path, destination: Path):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(destination)
    # SQLite connection context managers commit/rollback but do not close.
    # A portable snapshot must not depend on transient WAL/SHM files or GC.
    with closing(sqlite3.connect(str(path))) as source, closing(sqlite3.connect(str(destination))) as target:
        source.backup(target)
        if target.execute("PRAGMA journal_mode=DELETE").fetchone()[0] != "delete":
            raise RuntimeError("Sauvegarde SQLite non autonome")
        if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("Sauvegarde SQLite invalide")


def record_schema(engine, domain, version):
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS schema_migrations "
                          "(domain TEXT NOT NULL, version INTEGER NOT NULL, applied_at TEXT NOT NULL, "
                          "PRIMARY KEY (domain, version))"))
        conn.execute(text("INSERT OR IGNORE INTO schema_migrations VALUES (:domain, :version, :now)"),
                     {"domain": domain, "version": version, "now": datetime.now(timezone.utc).isoformat()})
