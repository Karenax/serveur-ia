"""Explicit additive installation on an existing ERP; no implicit live execution."""
from sqlalchemy import UniqueConstraint, inspect

from ..project_identity_models import IDENTITY_TABLES


def install_identity_schema(engine, *, backup):
    """Caller supplies a coherent backup callback; it must succeed before DDL.

    Only creates the six new tables. Historical project rows, financial cells and
    Brain links are deliberately untouched. Re-running is idempotent.
    """
    # Register the existing parent tables even when called in a fresh process.
    from .. import models  # noqa: F401

    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    if "projects" not in existing:
        raise ValueError("Une base ERP existante est requise")
    for table in IDENTITY_TABLES:
        if table.name in existing:
            columns = {column["name"] for column in inspector.get_columns(table.name)}
            if not set(table.columns.keys()).issubset(columns):
                raise ValueError(f"Schéma d'identité incomplet : {table.name}")
            primary = set(inspector.get_pk_constraint(table.name)["constrained_columns"])
            if primary != {column.name for column in table.primary_key}:
                raise ValueError(f"Identité de table incompatible : {table.name}")
            expected_foreign = {(tuple(foreign.column_keys), foreign.referred_table.name,
                                 tuple(element.column.name for element in foreign.elements))
                                for foreign in table.foreign_key_constraints}
            actual_foreign = {(tuple(foreign["constrained_columns"]), foreign["referred_table"],
                               tuple(foreign["referred_columns"])) for foreign in inspector.get_foreign_keys(table.name)}
            unique = {tuple(constraint.columns.keys()) for constraint in table.constraints
                      if isinstance(constraint, UniqueConstraint)}
            actual_unique = {tuple(item["column_names"]) for item in inspector.get_unique_constraints(table.name)}
            indexes = {item["name"]: item for item in inspector.get_indexes(table.name)}
            indexes_valid = True
            for index in table.indexes:
                actual = indexes.get(index.name)
                expected_where = index.dialect_options["sqlite"].get("where")
                actual_where = (actual or {}).get("dialect_options", {}).get("sqlite_where")
                expected_sql = "" if expected_where is None else str(expected_where).strip()
                actual_sql = "" if actual_where is None else str(actual_where).strip()
                if (not actual or bool(actual["unique"]) != bool(index.unique)
                        or actual["column_names"] != [column.name for column in index.columns]
                        or actual_sql != expected_sql):
                    indexes_valid = False
                    break
            if (not expected_foreign.issubset(actual_foreign) or not unique.issubset(actual_unique)
                    or not indexes_valid):
                raise ValueError(f"Contraintes d'identité incomplètes : {table.name}")
    missing = [table.name for table in IDENTITY_TABLES if table.name not in existing]
    if not missing:
        return {"created_tables": []}
    backup()
    IDENTITY_TABLES[0].metadata.create_all(engine, tables=list(IDENTITY_TABLES))
    return {"created_tables": missing}
