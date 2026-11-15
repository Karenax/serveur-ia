"""Pure immutable document SQL protections, used also by offline backup."""
import re
import json
from pathlib import Path


def _sql(value):
    # Preserve quoted literals: uppercasing a document ID or trigger condition
    # changes its meaning even when SQL keywords themselves ignore case.
    parts = re.split(r"('(?:''|[^'])*'|\"(?:\"\"|[^\"])*\")", str(value).strip().rstrip(';'))
    return ''.join(part if index % 2 else re.sub(r'\s+', ' ', part).casefold()
                   for index, part in enumerate(parts)).strip()


def immutable_triggers():
    result = {}
    for table in ('project_document_search_versions', 'project_document_draft_versions'):
        for operation in ('UPDATE', 'DELETE'):
            name = f'trg_{table}_{operation.lower()}_immutable'
            result[name] = (f'CREATE TRIGGER {name} BEFORE {operation} ON {table} '
                            "BEGIN SELECT RAISE(ABORT, 'Saved document versions are immutable'); END")
    for table in ('project_document_search_states', 'project_document_drafts'):
        name = f'trg_{table}_delete_retained'
        result[name] = (f'CREATE TRIGGER {name} BEFORE DELETE ON {table} '
                        "BEGIN SELECT RAISE(ABORT, 'Document history must be retained'); END")
        name = f'trg_{table}_revision_cas'
        identity = 'NEW.id != OLD.id'
        if table == 'project_document_drafts':
            identity += ' OR NEW.project_id != OLD.project_id OR NEW.document_id != OLD.document_id'
        result[name] = (f'CREATE TRIGGER {name} BEFORE UPDATE ON {table} '
                        f'WHEN NEW.revision != OLD.revision + 1 OR {identity} '
                        "BEGIN SELECT RAISE(ABORT, 'Document revision must advance once'); END")
    return result


def schema_specification():
    value = json.loads((Path(__file__).resolve().parents[1] / 'data/document_forms_schema.json').read_text(encoding='utf-8'))
    if (value.get('format') != 'agent-document-sqlite-schema' or type(value.get('version')) is not int
            or value['version'] != 1 or set(value) != {'format', 'version', 'tables'}):
        raise ValueError('Contrat SQLite documentaire incompatible')
    return value['tables']


def _checks(statement):
    """Read CHECK expressions with nested parentheses and SQL quoted literals."""
    result = []
    for match in re.finditer(r'\bCHECK\s*\(', statement, re.IGNORECASE):
        index, start, depth, quote = match.end(), match.end(), 1, None
        while index < len(statement) and depth:
            char = statement[index]
            if quote:
                if char == quote:
                    if index+1 < len(statement) and statement[index+1] == quote:
                        index += 1
                    else:
                        quote = None
            elif char in "'\"":
                quote = char
            elif char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
            index += 1
        if depth:
            raise ValueError('Contrainte documentaire illisible')
        result.append(_sql(statement[start:index-1]))
    return sorted(result)


def validate_sqlite_schema(db, *, specification=None, triggers=None):
    """Same protected signature as the model preflight, without runtime imports."""
    spec = schema_specification() if specification is None else specification
    existing = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    present = existing & set(spec)
    if not present:
        return False
    for name in present:
        table = spec[name]
        columns = list(db.execute(f'PRAGMA table_info({name})'))
        actual = {row[1]: {'type': row[2], 'nullable': not bool(row[3]), 'default': _sql(row[4] or '')} for row in columns}
        primary = [row[1] for row in sorted(columns, key=lambda row: row[5]) if row[5]]
        indexes = {}
        unique = []
        for row in db.execute(f'PRAGMA index_list({name})'):
            quoted_index = row[1].replace('"', '""')
            parts = [column[2] for column in db.execute(f'PRAGMA index_info("{quoted_index}")')]
            if row[3] == 'u':
                unique.append(parts)
            elif row[3] != 'pk':
                indexes[row[1]] = {'columns': parts, 'unique': bool(row[2])}
        foreign = {}
        for row in db.execute(f'PRAGMA foreign_key_list({name})'):
            value = foreign.setdefault(row[0], {'columns': [], 'table': row[2], 'targets': [],
                                                'on_update': row[5], 'on_delete': row[6]})
            value['columns'].append((row[1], row[3]))
            value['targets'].append((row[1], row[4]))
        for value in foreign.values():
            for key in ('columns', 'targets'):
                value[key] = [item[1] for item in sorted(value[key])]
        foreign_values = sorted(foreign.values(), key=lambda item: json.dumps(item, sort_keys=True))
        sql = db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()[0]
        if (actual != table['columns'] or primary != table['primary_key'] or sorted(unique) != table['unique']
                or _checks(sql) != table['checks'] or foreign_values != table['foreign_keys']
                or any(indexes.get(key) != expected for key, expected in table['indexes'].items())):
            raise ValueError('Schéma documentaire incompatible : ' + name)
    installed = {row[0]: row[1] for row in db.execute("SELECT name, sql FROM sqlite_master WHERE type='trigger'")}
    triggers = immutable_triggers() if triggers is None else triggers
    if any(name in installed and _sql(installed[name]) != _sql(expected) for name, expected in triggers.items()):
        raise ValueError('Protection documentaire incompatible')
    complete = present == set(spec) and set(triggers).issubset(installed)
    populated = any(db.execute(f'SELECT 1 FROM {name} LIMIT 1').fetchone() for name in present)
    if populated and (not complete or not {'projects', 'network_links'}.issubset(existing)):
        raise ValueError('Protection documentaire incomplète avec données')
    return complete


