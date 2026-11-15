"""Read-only checks for additive migrations; no runtime imports or database writes."""
import hashlib
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path


def _quote(name):
    return '"' + name.replace('"', '""') + '"'


@contextmanager
def readonly_database(path):
    path = Path(path).resolve(strict=True)
    if not path.is_file():
        raise ValueError("Une base SQLite existante est requise")
    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    try:
        connection.execute("PRAGMA query_only=ON")
        connection.execute("BEGIN")
        yield connection
    finally:
        connection.close()


def _digest(value):
    if isinstance(value, bytes):
        payload = b"blob:" + value
    else:
        payload = (type(value).__name__ + ":" + json.dumps(value, ensure_ascii=False)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def capture_baseline(path):
    """Hash every existing cell, keyed by primary key (or rowid); permit additions."""
    tables = {}
    with readonly_database(path) as db:
        integrity = [row[0] for row in db.execute("PRAGMA integrity_check")]
        if integrity != ["ok"]:
            raise ValueError("L'intégrité SQLite doit être vérifiée avant la migration")
        names = [row[0] for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        for name in names:
            info = db.execute(f"PRAGMA table_info({_quote(name)})").fetchall()
            columns = [row[1] for row in info]
            keys = [row[1] for row in sorted(info, key=lambda row: row[5]) if row[5]]
            key_expressions = [_quote(key) for key in keys]
            if not keys:
                # Pick the unshadowed SQLite rowid alias, not a user's column.
                lowered_columns = {column.casefold() for column in columns}
                alias = next((value for value in ("rowid", "_rowid_", "oid") if value not in lowered_columns), None)
                if alias is None:
                    raise ValueError(f"Identité de ligne non déterminable : {name}")
                keys = [alias]
                key_expressions = [alias]
            selected = key_expressions + [_quote(column) for column in columns]
            rows = {}
            for row in db.execute(f"SELECT {', '.join(selected)} FROM {_quote(name)}"):
                key = json.dumps([_digest(value) for value in row[:len(keys)]])
                if key in rows:
                    raise ValueError(f"Identité de ligne ambiguë : {name}")
                rows[key] = {column: _digest(value) for column, value in zip(columns, row[len(keys):])}
            tables[name] = {"columns": columns, "key_columns": keys, "rows": rows}
    return {"format": "agent-additive-migration-baseline", "version": 1, "tables": tables}


def compare_baseline(before, after):
    """A migration may add data but must preserve all prior tables, keys and values."""
    for baseline in (before, after):
        if baseline.get("format") != "agent-additive-migration-baseline" or baseline.get("version") != 1:
            raise ValueError("Référentiel de conservation non reconnu")
    issues = []
    checked_rows = 0
    checked_cells = 0
    for name, previous in before["tables"].items():
        current = after["tables"].get(name)
        if current is None:
            issues.append({"table": name, "kind": "missing_table"})
            continue
        if previous["key_columns"] != current["key_columns"]:
            issues.append({"table": name, "kind": "changed_identity"})
            continue
        for column in previous["columns"]:
            if column not in current["columns"]:
                issues.append({"table": name, "column": column, "kind": "missing_column"})
        for key, old_values in previous["rows"].items():
            checked_rows += 1
            new_values = current["rows"].get(key)
            if new_values is None:
                issues.append({"table": name, "row_key_hashes": key, "kind": "missing_row"})
                continue
            for column, digest in old_values.items():
                checked_cells += 1
                if column in new_values and new_values[column] != digest:
                    issues.append({"table": name, "column": column, "row_key_hashes": key,
                                   "kind": "changed_value"})
    return {"preserved": not issues, "checked_rows": checked_rows, "checked_cells": checked_cells,
            "issues": issues}


def project_preflight(erp_path, brain_path):
    """Diagnose identities without merging, relinking or migrating anything."""
    def projects(db):
        names = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "projects" not in names:
            raise ValueError("Table projects absente")
        return {row[0]: (row[1] or "").strip().casefold()
                for row in db.execute("SELECT id, code FROM projects")}

    def duplicate_groups(values):
        grouped = {}
        for identity, code in values.items():
            if code:
                grouped.setdefault(code, []).append(identity)
        return [ids for ids in grouped.values() if len(ids) > 1]

    with readonly_database(erp_path) as erp, readonly_database(brain_path) as brain:
        erp_projects, brain_projects = projects(erp), projects(brain)
        erp_tables = {row[0] for row in erp.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        links = erp.execute("SELECT project_id, brain_project_id FROM brain_links").fetchall() if "brain_links" in erp_tables else []
        broken, mismatches = [], []
        for pid, bid in links:
            if pid not in erp_projects or bid not in brain_projects:
                broken.append({"erp_project_id": pid, "brain_project_id": bid})
            elif erp_projects[pid] != brain_projects[bid]:
                mismatches.append({"erp_project_id": pid, "brain_project_id": bid})
        return {"read_only": True, "erp_projects": len(erp_projects), "brain_projects": len(brain_projects),
                "linked_erp_projects": len(links), "unlinked_erp_projects": len(set(erp_projects) - {p for p, _ in links}),
                "duplicate_erp_codes": duplicate_groups(erp_projects), "duplicate_brain_codes": duplicate_groups(brain_projects),
                "blank_erp_codes": [pid for pid, code in erp_projects.items() if not code],
                "blank_brain_codes": [pid for pid, code in brain_projects.items() if not code],
                "broken_links": broken, "different_linked_codes": mismatches,
                "foreign_key_violations": {"erp": len(erp.execute("PRAGMA foreign_key_check").fetchall()),
                                           "brain": len(brain.execute("PRAGMA foreign_key_check").fetchall())}}
