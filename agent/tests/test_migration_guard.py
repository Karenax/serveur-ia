"""Conservation checks use isolated SQLite files; never alter application databases."""
import sqlite3

import pytest

from backend.app.services.migration_guard import capture_baseline, compare_baseline, project_preflight


def create_database(path):
    with sqlite3.connect(path) as db:
        db.executescript("""
            CREATE TABLE projects (id TEXT PRIMARY KEY, code TEXT, hourly_rate REAL, details BLOB);
            INSERT INTO projects VALUES ('p1', 'AIRB26LTH0205-A', 85, X'0001');
            CREATE TABLE history (id INTEGER PRIMARY KEY, project_id TEXT, value TEXT);
            INSERT INTO history VALUES (1, 'p1', '2026-10-05');
            CREATE TABLE legacy (message TEXT);
            INSERT INTO legacy VALUES ('donnée héritée');
        """)


def test_additive_migration_and_old_financial_values_are_preserved(tmp_path):
    source = tmp_path / "erp.db"
    create_database(source)
    before = capture_baseline(source)
    with sqlite3.connect(source) as db:
        db.execute("ALTER TABLE projects ADD COLUMN agency_id TEXT")
        db.execute("CREATE TABLE agencies (id TEXT PRIMARY KEY, name TEXT)")
        db.execute("INSERT INTO projects (id, code) VALUES ('p2','NEW-0002')")
    report = compare_baseline(before, capture_baseline(source))
    assert report["preserved"] and report["checked_rows"] == 3
    assert report["checked_cells"] == 8
    assert before["tables"]["projects"]["columns"] == ["id", "code", "hourly_rate", "details"]


@pytest.mark.parametrize(("sql", "kind"), [
    ("DELETE FROM projects WHERE id='p1'", "missing_row"),
    ("UPDATE projects SET hourly_rate=0", "changed_value"),
    ("UPDATE projects SET details=X'0100'", "changed_value"),
    ("DROP TABLE history", "missing_table"),
    ("ALTER TABLE projects DROP COLUMN hourly_rate", "missing_column"),
])
def test_destructive_or_silent_changes_are_reported(tmp_path, sql, kind):
    source = tmp_path / "erp.db"
    create_database(source)
    before = capture_baseline(source)
    with sqlite3.connect(source) as db:
        db.execute(sql)
    report = compare_baseline(before, capture_baseline(source))
    assert not report["preserved"]
    assert any(issue["kind"] == kind for issue in report["issues"])


def test_composite_identity_and_null_or_empty_values_are_distinct(tmp_path):
    source = tmp_path / "data.db"
    with sqlite3.connect(source) as db:
        db.executescript("CREATE TABLE x (a TEXT,b TEXT,v TEXT,PRIMARY KEY(a,b)) WITHOUT ROWID;"
                         "INSERT INTO x VALUES ('a','1',NULL),('a','2','');")
    before = capture_baseline(source)
    with sqlite3.connect(source) as db:
        db.execute("UPDATE x SET v='' WHERE b='1'")
    report = compare_baseline(before, capture_baseline(source))
    assert len(report["issues"]) == 1 and report["issues"][0]["kind"] == "changed_value"


def test_read_only_capture_never_creates_missing_database_or_changes_source(tmp_path):
    source = tmp_path / "erp.db"
    with pytest.raises(FileNotFoundError):
        capture_baseline(source)
    assert not source.exists()
    create_database(source)
    original = source.read_bytes()
    assert capture_baseline(source) == capture_baseline(source)
    assert source.read_bytes() == original


def test_rowid_shadowing_is_case_insensitive(tmp_path):
    source = tmp_path / "legacy.db"
    with sqlite3.connect(source) as db:
        db.executescript("CREATE TABLE notes (ROWID TEXT,message TEXT);"
                         "INSERT INTO notes VALUES ('duplicate','one'),('duplicate','two');")
    before = capture_baseline(source)
    assert before["tables"]["notes"]["key_columns"] == ["_rowid_"]
    with sqlite3.connect(source) as db:
        db.execute("DELETE FROM notes WHERE message='one'")
    report = compare_baseline(before, capture_baseline(source))
    assert len(report["issues"]) == 1 and report["issues"][0]["kind"] == "missing_row"


def test_preflight_exposes_ambiguity_without_relinking(tmp_path):
    erp, brain = tmp_path / "erp.db", tmp_path / "brain.db"
    for path in (erp, brain):
        with sqlite3.connect(path) as db:
            db.execute("CREATE TABLE projects (id TEXT PRIMARY KEY, code TEXT)")
    with sqlite3.connect(erp) as db:
        db.executescript("INSERT INTO projects VALUES ('e1',' DUP '),('e2','dup'),('e3',''),('e4','OTHER');"
                         "CREATE TABLE brain_links (project_id TEXT PRIMARY KEY,brain_project_id TEXT);"
                         "INSERT INTO brain_links VALUES ('e1','b1'),('e4','b-missing');")
    with sqlite3.connect(brain) as db:
        db.execute("INSERT INTO projects VALUES ('b1','DIFFERENT')")
    before = [path.read_bytes() for path in (erp, brain)]
    report = project_preflight(erp, brain)
    assert report["duplicate_erp_codes"] == [["e1", "e2"]]
    assert report["blank_erp_codes"] == ["e3"]
    assert report["broken_links"] == [{"erp_project_id": "e4", "brain_project_id": "b-missing"}]
    assert report["different_linked_codes"] == [{"erp_project_id": "e1", "brain_project_id": "b1"}]
    assert report["unlinked_erp_projects"] == 2
    assert [path.read_bytes() for path in (erp, brain)] == before
