"""Versioned, idempotent schema upgrades. Historical readers remain explicit."""
VERSION = 2
INDEX_SCHEMA = '''
CREATE INDEX IF NOT EXISTS document_owner_project_updated ON documents(owner,project,updated DESC);
CREATE INDEX IF NOT EXISTS memory_owner_project_updated ON memories(owner,project,updated DESC);
CREATE INDEX IF NOT EXISTS conversation_owner_project_updated ON conversations(owner,project,updated DESC);
CREATE INDEX IF NOT EXISTS project_owner_updated ON projects(owner,updated DESC);
CREATE INDEX IF NOT EXISTS job_owner_created ON jobs(owner,created DESC);
CREATE INDEX IF NOT EXISTS command_owner_created ON assistant_commands(owner,created);
'''


def ensure_supported(db, *, archive=False):
    version = db.execute('PRAGMA user_version').fetchone()[0]
    if version not in ((1, VERSION) if archive else (0, 1, VERSION)):
        raise ValueError('Version des espaces incompatible. Conservez cette base et utilisez un serveur compatible.')
    return version


def upgrade(db):
    ensure_supported(db)
    # Execute each DDL inside the caller's transaction; executescript commits.
    for statement in INDEX_SCHEMA.split(';'):
        if statement.strip():
            db.execute(statement)
    db.execute("INSERT OR IGNORE INTO settings VALUES('migration:2','preserve-history-and-indexes')")
    db.execute(f'PRAGMA user_version={VERSION}')
