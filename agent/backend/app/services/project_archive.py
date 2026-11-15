"""Versioned project archive preserving rows, relationships and CDC files."""
import base64
import hashlib
import uuid
from contextlib import ExitStack, nullcontext
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import DateTime, inspect, select, text, update

from ..db import Base
from ..models import BrainLink, Project
from .client_directory import client_directory
from . import project_identity_archive as identity_archive
from . import project_planning_archive as planning_archive
from . import project_deliverable_archive as deliverable_archive
from . import project_deliverable_archive_store as deliverable_store
from . import project_archive_v5 as v5
from . import project_archive_brain as brain_archive
from . import project_review_archive as review_archive
from . import project_review_archive_store as review_store
from . import project_document_archive as document_archive
from . import project_document_archive_store as document_store
from . import project_document_job_archive as job_archive
from . import project_note_archive as note_archive
from . import project_note_archive_store as note_store

MAX_ARCHIVE_BYTES = 150 * 1024**2


def _validate_tables(metadata, tables, *, parents=None, detached_sources=False):
    children = {"cdc_source_pages", "cdc_evidence_anchors", "source_artifacts",
                "provenance_links", "validation_decisions"}
    allowed = {t.name for t in metadata.tables.values()
               if (t.name == "projects" or "project_id" in t.c or t.name in children)
               and not t.name.startswith('project_document_')
               and not t.name.startswith('project_note')
               and not t.name.startswith('foresight_')
               and t.name != 'project_knowledge_analyses'}
    if not isinstance(tables, dict) or set(tables) - allowed:
        raise HTTPException(400, "Table inconnue ou globale interdite dans l’archive projet")
    projects = tables.get("projects", [])
    if (not isinstance(projects, list) or len(projects) != 1 or not isinstance(projects[0], dict)
            or not isinstance(projects[0].get("id"), str) or not projects[0]["id"]):
        raise HTTPException(400, "Un seul projet identifié est requis")
    pid = projects[0]["id"]
    lookup = {**tables, **(parents or {})}
    identities = set()
    for name, rows in tables.items():
        if not isinstance(rows, list) or len(rows) > 100000 or any(not isinstance(row, dict) for row in rows):
            raise HTTPException(400, f"Liste de lignes invalide : {name}")
    for name, rows in tables.items():
        table = metadata.tables[name]
        if not isinstance(rows, list) or len(rows) > 100000:
            raise HTTPException(400, "Liste de lignes invalide")
        primary_keys = set()
        for row in rows:
            if not isinstance(row, dict) or set(row) - set(table.c.keys()):
                raise HTTPException(400, f"Colonnes invalides : {name}")
            key = tuple(row.get(column.name) for column in table.primary_key)
            if not key or any(not isinstance(value, (str, int)) or isinstance(value, bool) or value == "" for value in key):
                raise HTTPException(400, "Clé primaire absente ou invalide dans l'archive")
            if key in primary_keys:
                raise HTTPException(400, "Ligne dupliquée dans l'archive")
            primary_keys.add(key)
            if "id" in row:
                if row["id"] in identities:
                    raise HTTPException(400, "Identifiant ambigu entre tables d'archive")
                identities.add(row["id"])
            if "project_id" in row and row["project_id"] != pid and not (detached_sources and name == 'sources' and row['project_id'] is None):
                raise HTTPException(400, "Ligne appartenant à un autre projet")
            for column in table.c:
                if isinstance(column.type, DateTime) and row.get(column.name):
                    try:
                        datetime.fromisoformat(row[column.name])
                    except (ValueError, TypeError) as exc:
                        raise HTTPException(400, "Date d’archive invalide") from exc
                for foreign in column.foreign_keys:
                    value = row.get(column.name)
                    if value is not None and not any(
                        parent.get(foreign.column.name) == value
                        for parent in lookup.get(foreign.column.table.name, [])
                    ):
                        raise HTTPException(400, "Relation sortant du projet ou parent absent")


def _rows(db, metadata, project_id, *, include_documents=False, include_jobs=False, include_notes=False):
    available = set(inspect(db.get_bind()).get_table_names())
    note_rows = False
    for name in note_archive.PROJECT_TABLES & available:
        if 'project_id' not in {column['name'] for column in inspect(db.get_bind()).get_columns(name)}:
            raise HTTPException(409, 'Schéma de notes incomplet ; export refusé')
        if db.execute(text(f'SELECT 1 FROM {name} WHERE project_id=:pid LIMIT 1'), {'pid': project_id}).first():
            if not include_notes:
                raise HTTPException(409, 'Notes riches : archive typée version 9 requise ; export ancien refusé')
            note_store.require_schema(db)
            note_rows = True
    job_rows = False
    for name in job_archive.PROJECT_TABLES & available:
        if 'project_id' not in {column['name'] for column in inspect(db.get_bind()).get_columns(name)}:
            raise HTTPException(409, 'Schéma de file documentaire incomplet ; export refusé')
        if db.execute(text(f'SELECT 1 FROM {name} WHERE project_id=:pid LIMIT 1'), {'pid': project_id}).first():
            if not include_jobs:
                raise HTTPException(409, 'Lots documentaires : archive projet typée version 8 requise')
            job_archive.require_schema(db)
            from .. import project_document_job_models  # noqa: F401
            job_rows = True
    document_rows = False
    for name in ('project_document_drafts', 'project_document_draft_versions'):
        if name in available:
            columns = {column['name'] for column in inspect(db.get_bind()).get_columns(name)}
            if 'project_id' not in columns:
                raise HTTPException(409, 'Schéma documentaire incomplet ; export refusé')
            if db.execute(
                    text(f'SELECT 1 FROM {name} WHERE project_id=:pid LIMIT 1'),
                    {'pid': project_id}).first():
                if not include_documents:
                    raise HTTPException(409, 'Historique documentaire : archive typée L5 requise')
                document_store.require_schema(db)
                document_rows = True
    if identity_archive.PROJECT_TABLES & available:
        # Support a fresh process where the additive model has not been imported.
        from .. import project_identity_models  # noqa: F401
        required = identity_archive.PROJECT_TABLES | identity_archive.REFERENCE_TABLES | {"project_reference_changes"}
        if not required.issubset(available):
            raise HTTPException(409, "Migration d'identité incomplète : export refusé")
    result = {}
    review_rows = False
    if review_archive.PROJECT_TABLES & available:
        from .. import project_review_models  # noqa: F401
        for name in review_archive.PROJECT_TABLES & available:
            if 'project_id' not in {column['name'] for column in inspect(db.get_bind()).get_columns(name)}:
                raise HTTPException(409, 'Schéma de revues incomplet ; export refusé')
            table = metadata.tables.get(name)
            if table is not None and db.execute(select(table.c.project_id).where(table.c.project_id==project_id).limit(1)).first():
                review_store.require_schema(db)
                review_rows = True
                break
    for table in metadata.sorted_tables:
        if table.name not in available:
            continue  # Optional schemas may be registered while still dormant.
        if table.name.startswith('foresight_'):
            continue  # Catalogue identities/versions require the coordinated global backup.
        if table.name in {'meeting_sessions', 'meeting_session_chunks', 'meeting_live_segments',
                'meeting_session_events', 'meeting_session_commands', 'meeting_staged_note_versions',
                'note_evidence_bindings', 'note_evidence_receipts', 'note_evidence_outbox'}:
            continue  # Studio snapshots/commands use their separate typed export.
        if table.name == 'project_knowledge_analyses':
            continue  # Derived cache refers to original Brain IDs; recompute after project import.
        if table.name.startswith('project_note'):
            if not note_rows or table.name not in note_archive.PROJECT_TABLES:
                continue
        if table.name.startswith('project_document_'):
            if table.name in job_archive.PROJECT_TABLES:
                if not job_rows:
                    continue
            elif not document_rows or table.name not in document_archive.PROJECT_TABLES:
                continue
        # No review placeholders in legacy v2-v5; populated reviews require the
        # complete protected schema and are exported only by the typed v6 path.
        if table.name in review_archive.PROJECT_TABLES and not review_rows:
            continue
        # L3 models can be loaded by isolated qualification before runtime
        # activation. Never query an absent table or export incomplete L3 data.
        if table.name.startswith("project_deliverable_") and table.name not in available:
            continue
        if table.name in identity_archive.PROJECT_TABLES and table.name not in available:
            continue
        if table.name in planning_archive.PROJECT_TABLES and table.name not in available:
            continue
        if table.name in {'assistant_threads', 'mail_enrichment_jobs'} and table.name not in available:
            continue
        if table.name == "projects":
            rows = db.execute(select(table).where(table.c.id == project_id)).mappings().all()
        elif "project_id" in table.c:
            rows = db.execute(select(table).where(table.c.project_id == project_id)).mappings().all()
        elif table.name == "cdc_source_pages":
            ids = [r["id"] for r in result.get("cdc_sources", [])]
            rows = db.execute(select(table).where(table.c.source_id.in_(ids))).mappings().all()
        elif table.name == "cdc_evidence_anchors":
            ids = [r["id"] for r in result.get("cdc_items", [])]
            rows = db.execute(select(table).where(table.c.item_id.in_(ids))).mappings().all()
        elif table.name == "source_artifacts":
            ids = [r["id"] for r in result.get("sources", [])]
            rows = db.execute(select(table).where(table.c.source_id.in_(ids))).mappings().all()
        elif table.name in ("provenance_links", "validation_decisions"):
            parent, column = (("knowledge_items", "knowledge_item_id") if table.name == "provenance_links"
                              else ("proposals", "proposal_id"))
            ids = [r["id"] for r in result.get(parent, [])]
            rows = db.execute(select(table).where(table.c[column].in_(ids))).mappings().all()
        else:
            continue
        result[table.name] = [{k: v.isoformat() if isinstance(v, datetime) else v
                               for k, v in row.items()} for row in rows]
    return result


def export_archive(db, project_id):
    from .project_operator import require_project_access
    require_project_access(project_id)
    from app.db import Base as BrainBase, SessionLocal
    from app import models, workspace_models  # noqa: F401
    from app.config import RAW_DIR, STORAGE_DIR
    from ..routers.cdc import cdc_storage_root
    tables = _rows(db, Base.metadata, project_id, include_documents=True, include_jobs=True, include_notes=True)
    if not tables.get("projects"):
        raise HTTPException(404, "Projet introuvable")
    has_reviews = any(tables.get(name) for name in review_archive.PROJECT_TABLES)
    has_documents = any(tables.get(name) for name in document_archive.PROJECT_TABLES)
    has_jobs = any(tables.get(name) for name in job_archive.PROJECT_TABLES)
    has_notes = any(tables.get(name) for name in note_archive.PROJECT_TABLES)
    note_references = note_store.section_for(tables) if has_notes else None
    without_notes = note_archive.native_view(tables)
    job_references = job_archive.section_for(without_notes) if has_jobs else None
    without_jobs = job_archive.native_view(without_notes)
    document_references = document_archive.section_for(without_jobs) if has_documents else None
    native_tables = document_archive.native_view(without_jobs)
    deliverable_references = deliverable_store.export_references(db, Base.metadata, native_tables) if has_notes or has_jobs or has_documents or has_reviews or v5.needs_deliverables(db, Base.metadata, native_tables) else None
    planning_tables = v5.planning_view(native_tables) if deliverable_references is not None else native_tables
    planning_references = planning_archive.export_templates(db, Base.metadata, planning_tables) if has_notes or has_jobs or has_documents or planning_archive.has_planning(planning_tables) else None
    references = None
    if deliverable_references is not None or planning_references is not None or any(tables.get(name) for name in identity_archive.PROJECT_TABLES):
        identity_archive.validate_identity(tables)
        extra = v5.merge_identity_dependencies(
            planning_archive.identity_dependencies(planning_tables, planning_references) if planning_references is not None else None,
            deliverable_archive.identity_dependencies(tables, deliverable_references) if deliverable_references is not None else None,
            review_archive.identity_dependencies(tables) if has_reviews else None)
        references = identity_archive.export_references(db, Base.metadata, tables, extra=extra)
        if planning_references is not None and planning_archive.has_planning(planning_tables):
            planning_archive.validate_planning(Base.metadata, planning_tables, planning_references, references)
        if deliverable_references is not None:
            deliverable_archive.validate(Base.metadata, native_tables, deliverable_references, references, planning_references=planning_references)
    else:
        # Old projects keep their v2 format without empty L1 placeholders.
        tables = {name: rows for name, rows in tables.items() if name not in identity_archive.PROJECT_TABLES}
    if planning_references is None:
        tables = {name: rows for name, rows in tables.items() if name not in planning_archive.PROJECT_TABLES}
    files = []
    total = ((review_archive.embedded_bytes(tables) if has_reviews else 0)
             + (document_archive.embedded_bytes(tables) if has_documents else 0)
             + (job_archive.embedded_bytes(tables) if has_jobs else 0)
             + (sum(len(row['snapshot'].encode('utf-8')) for name in ('project_note_versions', 'project_note_imports')
                    for row in tables.get(name, [])) if has_notes else 0))
    if total > MAX_ARCHIVE_BYTES:
        raise HTTPException(413, 'Archive trop volumineuse : utiliser la sauvegarde globale')

    def add_file(path, owner, area, allowed, expected=None):
        nonlocal total
        path = Path(path).resolve()
        roots = allowed if isinstance(allowed, tuple) else (allowed,)
        if not any(path.is_relative_to(root.resolve()) for root in roots) or not path.is_file():
            raise HTTPException(409, "Pièce source absente ou hors stockage : sauvegarde impossible")
        total += path.stat().st_size
        if total > MAX_ARCHIVE_BYTES:
            raise HTTPException(413, "Archive trop volumineuse : utiliser la sauvegarde globale")
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if expected and (digest != expected['sha256'] or len(data) != expected['size_bytes']):
            raise HTTPException(409, 'Fichier de livrable modifié depuis sa publication')
        files.append({"owner": owner, "area": area, "name": path.name,
                      "sha256": digest,
                      "data": base64.b64encode(data).decode("ascii")})

    for row in tables.get("cdc_sources", []):
        if row.get("storage_path"):
            add_file(row["storage_path"], row["id"], "cdc", cdc_storage_root())
    from ..db import APP_DIR
    if has_jobs:
        from types import SimpleNamespace
        from .document_job_artifacts import read_artifact
        for row in tables['project_document_job_artifacts']:
            content = read_artifact(APP_DIR / 'document-artifacts', SimpleNamespace(**row))
            total += len(content)
            if total > MAX_ARCHIVE_BYTES:
                raise HTTPException(413, 'Archive trop volumineuse : utiliser la sauvegarde globale')
            files.append({'owner': row['id'], 'area': 'document-job', 'name': row['storage_key'],
                          'sha256': row['sha256'], 'data': base64.b64encode(content).decode('ascii')})
    if has_notes:
        note_files = note_store.export_files(db, project_id, tables)
        total += sum(row['size_bytes'] for name in ('project_note_attachments', 'project_note_imports') for row in tables[name])
        if total > MAX_ARCHIVE_BYTES:
            raise HTTPException(413, 'Archive trop volumineuse : utiliser la sauvegarde globale')
        files.extend(note_files)
    for row in tables.get("delivery_versions", []):
        add_file(row["path"], row["id"], "delivery", APP_DIR / "exports")
    if deliverable_references is not None:
        metadata = {row['version_id']: row for row in tables.get('project_deliverable_version_metadata', [])}
        for row in tables.get('project_deliverable_file_versions', []):
            path = Path(metadata[row['id']]['storage_path'] or row['path']).resolve()
            # Linked CDC versions use their original delivery transport piece.
            if row['source_delivery_id']:
                delivery = next(item for item in tables['delivery_versions'] if item['id'] == row['source_delivery_id'])
                if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256'] or path.stat().st_size != row['size_bytes']:
                    raise HTTPException(409, 'Fichier CDC lié différent de sa publication')
                if Path(delivery['path']).resolve() != path:
                    raise HTTPException(409, 'Emplacement CDC lié différent de sa livraison')
            else:
                add_file(path, row['id'], 'deliverable', (APP_DIR, STORAGE_DIR), expected=row)
    link = db.get(BrainLink, project_id)
    brain = None
    if link:
        with SessionLocal() as session:
            brain = _rows(session, BrainBase.metadata, link.brain_project_id)
            if not brain.get("projects"):
                raise HTTPException(409, "Liaison Brain invalide")
            brain["meeting_recordings"] = [r for r in brain.get("meeting_recordings", []) if r["erp_project_id"] == project_id]
            brain_archive.include_source_parents(session, BrainBase.metadata, brain)
            _validate_tables(BrainBase.metadata, brain, detached_sources=True)
            for row in brain.get("sources", []):
                content_hash = brain_archive.library_content_hash(row)
                if content_hash:
                    original = Path(row['original_uri'] or '')
                    declared = original if original.is_relative_to(RAW_DIR) and original.is_file() else None
                else:
                    declared = review_store.raw_path(row, brain) if has_reviews else None
                raw = [Path(declared)] if declared else list(RAW_DIR.glob(f"{row['sha256']}*"))
                if raw:
                    add_file(raw[0], row["id"], "raw", RAW_DIR)
                    if (content_hash or has_reviews) and files[-1]['sha256'] != (content_hash or row['sha256']):
                        raise HTTPException(409, 'Pièce source différente de son empreinte Brain')
    if planning_references is not None:
        planning_archive.validate_evidence(planning_tables, planning_references, brain)
    if deliverable_references is not None:
        v5.validate_file_bindings(tables, [(entry, base64.b64decode(entry['data']), entry['sha256']) for entry in files])
    if has_reviews:
        review_archive.validate(Base.metadata, native_tables, references, deliverable_references, brain)
    result = {"format": "agent-project-archive", "version": 9 if has_notes else 8 if has_jobs else 7 if has_documents else 6 if has_reviews else 5 if deliverable_references is not None else 4 if planning_references is not None else 3 if references is not None else 2,
              "project": tables["projects"][0], "tables": tables, "brain": brain, "files": files}
    if references is not None:
        result["references"] = references
    if planning_references is not None:
        result["planning_references"] = planning_references
    if deliverable_references is not None:
        result['deliverable_references'] = deliverable_references
        result.setdefault('planning_references', {name: [] for name in planning_archive.REFERENCE_TABLES})
    if document_references is not None:
        result['document_references'] = document_references
    if job_references is not None:
        result['document_job_references'] = job_references
    if note_references is not None:
        result['note_references'] = note_references
    warnings = []
    with SessionLocal() as session:
        available = set(inspect(session.get_bind()).get_table_names())
        if 'meeting_sessions' in available and session.execute(text(
                'SELECT 1 FROM meeting_sessions WHERE project_id=:pid LIMIT 1'), {'pid': project_id}).first():
            warnings.append('Les captures Studio sont à exporter séparément ou par la sauvegarde globale ; '
                'les fragments audio et commandes Studio ne sont pas inclus dans cette archive projet.')
        projects = (result.get('brain') or {}).get('projects') or []
        if projects and 'foresight_library_items' in available and session.execute(text(
                'SELECT 1 FROM foresight_library_items WHERE project_id=:pid LIMIT 1'),
                {'pid': projects[0]['id']}).first():
            warnings.append('Le catalogue, ses versions et ses liaisons fournisseur ne sont pas inclus dans '
                'cette archive projet ; les sources canoniques et leurs médias exportables sont conservés. '
                'Utiliser la sauvegarde globale coordonnée pour conserver le catalogue complet.')
    if warnings:
        result['warnings'] = warnings
    return result


def _remap(value, mapping):
    if isinstance(value, dict):
        return {mapping.get(k, k): _remap(v, mapping) for k, v in value.items()}
    if isinstance(value, list):
        return [_remap(v, mapping) for v in value]
    return mapping.get(value, value) if isinstance(value, str) else value


def _insert(db, metadata, tables, mapping, overrides=None, *, planning_context=None, typed_brain=False, deliverable_hashes=None, typed_reviews=False, typed_documents=False, typed_jobs=False):
    for table in metadata.sorted_tables:
        pending = list(tables.get(table.name, []))
        ordered = []
        # Knowledge versions have a self-reference: restore parents first even
        # when an archive editor has reordered the exported array.
        while pending:
            ids = {row["id"] for row in pending if row.get("id")}
            ready = [row for row in pending if row.get("supersedes_id") not in ids
                     and (table.name!='project_reviews' or row.get('previous_review_id') not in ids)]
            if not ready:
                raise HTTPException(400, "Cycle dans les versions de connaissance")
            ordered.extend(ready)
            pending = [row for row in pending if row not in ready]
        for raw in ordered:
            if set(raw) - set(table.c.keys()):
                raise HTTPException(400, f"Colonnes inconnues : {table.name}")
            if typed_jobs and table.name in job_archive.PROJECT_TABLES:
                row = deepcopy(raw)  # Prepared flat IDs; journal text must not be remapped.
            elif typed_brain:
                row = deepcopy(raw)
                for column in table.c:
                    if column.primary_key or column.foreign_keys or column.name == 'project_id' or (table.name == 'memory_projections'
                            and column.name in {'source_id', 'knowledge_item_id', 'dataset_mapping_id'}) or (
                            table.name == 'validation_decisions' and column.name == 'resulting_knowledge_id'):
                        value = row.get(column.name)
                        if isinstance(value, str):
                            row[column.name] = mapping.get(value, value)
                if typed_reviews and table.name=='source_artifacts' and isinstance(raw.get('content_json'), dict):
                    if raw['content_json'].get('recording_id') in mapping:
                        row['content_json'] = review_archive.remap_audio_artifact(raw, mapping)['content_json']
            elif typed_documents and table.name in document_archive.PROJECT_TABLES:
                row = document_archive.remap_row(raw, table.name, mapping)
            elif typed_reviews and table.name in review_archive.PROJECT_TABLES:
                row = review_archive.remap_row(raw, table.name, mapping, planning_context)
            elif deliverable_hashes is not None and (table.name in deliverable_archive.PROJECT_TABLES | deliverable_archive.REFERENCE_TABLES or (
                    table.name == 'project_planning_changes' and raw.get('action') in deliverable_archive.ACTIONS)):
                row = deliverable_archive.remap_row(raw, table, mapping, manifest_hashes=deliverable_hashes)
            elif planning_context is not None and table.name not in identity_archive.PROJECT_TABLES | identity_archive.REFERENCE_TABLES:
                row = planning_archive.remap_row(raw, table, mapping, planning_context, _remap)
            elif table.name in identity_archive.PROJECT_TABLES | identity_archive.REFERENCE_TABLES:
                row = identity_archive.remap_identity_row(raw, table, mapping)
            else:
                row = _remap(raw, mapping)
            if table.name == "milestones" and "forecast_date" not in row:
                row["forecast_date"] = row.get("due_date") or ""
            if table.name == "projects" and overrides:
                row.update(overrides)
            for col in table.c:
                if isinstance(col.type, DateTime) and row.get(col.name):
                    row[col.name] = datetime.fromisoformat(row[col.name])
            db.execute(table.insert().values(**row))


def import_archive(db, data, code=None):
    if isinstance(data, dict) and data.get('version') in {8,9}:
        from .project_operator import require_reference_write
        require_reference_write()
    if (isinstance(data, dict) and data.get('format')=='agent-project-archive'
            and type(data.get('version')) is int and data['version'] in {6,7,8,9}):
        from app.db import SessionLocal
        from .project_archive_transaction import coordinated
        with SessionLocal() as owner:
            brain_engine = owner.get_bind()
        preparations = []
        try:
            with ExitStack() as directories, coordinated(db, brain_engine) as (erp, brain):
                result = _import_archive(erp, data, code, directories=directories,
                                         coordinated_brain=brain, preparations=preparations)
        except Exception as exc:
            for preparation in preparations:
                preparation.outcome('import_failed')
            if isinstance(exc, HTTPException):
                raise
            raise HTTPException(409, 'Échec de restauration ; données existantes conservées. Vérifier le journal de préparation avant de relancer') from exc
        for preparation in preparations:
            preparation.outcome('sql_committed')
        return result
    with ExitStack() as directories:
        return _import_archive(db, data, code, directories=directories)


def _import_archive(db, data, code=None, *, coordinated_brain=None, preparations=None, directories=None):
    from app.db import Base as BrainBase, SessionLocal
    from app import models, workspace_models  # noqa: F401
    from app.config import RAW_DIR
    from ..routers.cdc import cdc_storage_root
    if (not isinstance(data, dict) or data.get("format") != "agent-project-archive"
            or type(data.get("version")) is not int or data.get("version") not in {2, 3, 4, 5, 6, 7,8,9}):
        raise HTTPException(400, "Version d’archive non supportée")
    data = deepcopy(data)
    version = data["version"]
    if version in {6,7,8,9} and (coordinated_brain is None or preparations is None):
        raise HTTPException(409, 'Les revues exigent la transaction ERP/Brain coordonnée')
    incoming_tables = data.get('tables')
    if version not in {6,7,8,9} and isinstance(incoming_tables, dict) and any(incoming_tables.get(name) for name in (
            'project_reviews', 'project_review_publications', 'project_review_events')):
        raise HTTPException(400, 'Une archive typée RLP est requise ; import générique refusé')
    tables = data.get("tables") or {}
    if not isinstance(tables, dict):
        raise HTTPException(400, "Tables d'archive invalides")
    has_reviews = any(tables.get(name) for name in review_archive.PROJECT_TABLES)
    document_context = None
    has_documents = bool(document_archive.PROJECT_TABLES & set(tables))
    note_context = None
    if version == 9:
        note_context = note_store.validate(tables, data.get('note_references'))
        note_store.require_schema(db)
    elif 'note_references' in data or note_archive.PROJECT_TABLES & set(tables):
        raise HTTPException(400, 'Les notes exigent une archive typée version 9')
    without_notes = note_archive.native_view(tables)
    has_jobs = bool(job_archive.PROJECT_TABLES & set(tables))
    job_context = None
    if version == 8 or version == 9 and has_jobs:
        job_context = job_archive.validate(without_notes, data.get('document_job_references'))
        job_archive.require_schema(db)
    elif 'document_job_references' in data or job_archive.PROJECT_TABLES & set(tables):
        raise HTTPException(400, 'Les lots documentaires exigent une archive typée version 8')
    without_jobs = job_archive.native_view(without_notes)
    if version == 7 or version in {8,9} and has_documents:
        document_context = document_archive.validate(without_jobs, data.get('document_references'))
        document_store.require_schema(db)
    elif 'document_references' in data or document_archive.PROJECT_TABLES & set(tables):
        raise HTTPException(400, 'Les formulaires documentaires exigent une archive typée version 7')
    native_tables = document_archive.native_view(without_jobs)
    if version in {6,7,8,9}:
        expected_keys = {'format','version','project','tables','brain','files','references','planning_references','deliverable_references'}
        if version == 7 or version in {8,9} and has_documents:
            expected_keys.add('document_references')
        if version == 8 or version == 9 and has_jobs:
            expected_keys.add('document_job_references')
        if version == 9:
            expected_keys.add('note_references')
        warnings = data.get('warnings', [])
        if (set(data) - {'warnings'} != expected_keys
                or not isinstance(warnings, list) or any(not isinstance(message, str) for message in warnings)
                or (version == 6 or has_reviews) and (not review_archive.PROJECT_TABLES.issubset(tables) or not tables.get('project_reviews'))
                or data['project']!=next(iter(tables.get('projects', [])), None)):
            raise HTTPException(400, 'Enveloppe d’archive typée absente ou incohérente')
        review_store.require_schema(db)
    references = {}
    planning_references = {}
    deliverable_references = {}
    events = tables.get('project_planning_changes', [])
    if version not in {5,6,7,8,9} and (data.get('deliverable_references') or any(tables.get(name) for name in deliverable_archive.PROJECT_TABLES)
                         or any(row.get('action') in deliverable_archive.ACTIONS for row in (events if isinstance(events, list) else []) if isinstance(row, dict))):
        raise HTTPException(400, 'Les données de livrables exigent une archive version 5')
    planning_tables = v5.planning_view(native_tables) if version in {5,6,7,8,9} else native_tables
    if version in {5,6,7,8,9}:
        deliverable_references = data.get('deliverable_references')
        deliverable_archive.validate_section(Base.metadata, deliverable_references)
        deliverable_store.require_schema(db)
    if version in {3, 4, 5, 6, 7,8,9}:
        from .. import project_identity_models  # noqa: F401
        # Envelope/keys first; domain rules then operate on bounded row dictionaries.
        references = data.get("references")
        identity_archive._rows(Base.metadata, references)
        if version in {4, 5, 6, 7,8,9}:
            planning_references = data.get("planning_references")
            planning_archive.validate_section(Base.metadata, planning_references)
            planning_archive.require_schema(db)
        elif data.get('planning_references') or any(tables.get(name) for name in planning_archive.PROJECT_TABLES):
            raise HTTPException(400, "Les données de planning exigent une archive version 4")
        _validate_tables(Base.metadata, native_tables, parents={**references, **planning_references, **deliverable_references})
        identity_archive.validate_identity(tables)
        extra = v5.merge_identity_dependencies(
            planning_archive.identity_dependencies(planning_tables, planning_references) if version in {4, 5, 6, 7,8,9} else None,
            deliverable_archive.identity_dependencies(tables, deliverable_references) if version in {5,6,7,8,9} else None,
            review_archive.identity_dependencies(tables) if version in {6,7,8,9} else None)
        identity_archive.validate_references(Base.metadata, tables, references, extra=extra)
        if version == 4 or version in {5,6,7,8,9} and planning_archive.has_planning(planning_tables):
            planning_archive.validate_planning(Base.metadata, planning_tables, planning_references, references)
        elif version in {5,6,7,8,9} and any(planning_references.values()):
            raise HTTPException(400, 'Modèles de planning étrangers à ce projet')
        if version in {5,6,7,8,9}:
            deliverable_archive.validate(Base.metadata, native_tables, deliverable_references, references, planning_references=planning_references)
    else:
        if data.get("references") or any(tables.get(name) for name in identity_archive.PROJECT_TABLES):
            raise HTTPException(400, "Les données d'identité exigent une archive version 3")
        if data.get('planning_references') or any(tables.get(name) for name in planning_archive.PROJECT_TABLES):
            raise HTTPException(400, "Les données de planning exigent une archive version 4")
        _validate_tables(Base.metadata, tables)
    projects = tables.get("projects", [])
    if len(projects) != 1:
        raise HTTPException(400, "L’archive doit contenir un seul projet")
    raw_code = code or projects[0].get("code") or ""
    if not isinstance(raw_code, str) or len(raw_code.strip()) > 64:
        raise HTTPException(400, "Code de projet d'archive invalide")
    target_code = raw_code.strip()
    # Serialize code checking and reference reconciliation with concurrent edits.
    # Acquires SQLite's write lock without modifying an existing project cell.
    db.execute(update(Project).where(Project.id.is_(None)).values(title=Project.title))
    if not target_code or any((row.code or "").strip().casefold() == target_code.casefold() for row in db.query(Project)):
        raise HTTPException(409, "Code de projet absent ou déjà utilisé")
    brain = data.get("brain")
    if brain:
        _validate_tables(BrainBase.metadata, brain, detached_sources=True)
        brain_archive.validate_detached_sources(brain)
        meeting_ids = {m["id"] for m in tables.get("meetings", [])}
        if any(r.get("erp_project_id") != projects[0]["id"] or
               (r.get("published_meeting_id") and r["published_meeting_id"] not in meeting_ids)
               for r in brain.get("meeting_recordings", [])):
            raise HTTPException(400, "Enregistrement audio rattaché à un compte rendu ou projet hors archive")
        if any(link.get("brain_project_id") != brain["projects"][0]["id"]
               for link in tables.get("brain_links", [])):
            raise HTTPException(400, "Liaison Brain hors archive")
    elif tables.get("brain_links"):
        raise HTTPException(400, "Liaison Brain sans données Brain")
    if version in {4, 5, 6, 7,8,9}:
        planning_archive.validate_evidence(planning_tables, planning_references, brain)
    if has_reviews:
        review_archive.validate(Base.metadata, native_tables, references, deliverable_references, brain)
    combined = [tables, references, planning_references, deliverable_references] + ([brain] if brain and version not in {4, 5, 6, 7,8,9} else [])
    project_row_ids = {r["id"] for group in [tables] + ([brain] if brain and version not in {4, 5, 6, 7,8,9} else [])
                       for rows in group.values() for r in rows if isinstance(r.get("id"), str)}
    if any(row["id"] in project_row_ids for rows in references.values() for row in rows):
        raise HTTPException(400, "Identifiant de référentiel ambigu avec un objet projet")
    mapping = {r["id"]: str(uuid.uuid4()) for group in combined
               for rows in group.values() for r in rows if isinstance(r.get("id"), str)}
    if document_context is not None:
        if document_context['unresolved_link_ids'] & set(mapping):
            raise HTTPException(400, 'Lien documentaire manquant confondu avec un autre objet')
        mapping.update({key: str(uuid.uuid4()) for key in document_context['unresolved_link_ids']})
    if job_context is not None:
        absent = job_context['unresolved_link_ids'] - (document_context['unresolved_link_ids'] if document_context else set())
        if absent & set(mapping):
            raise HTTPException(400, 'Lien de lot manquant confondu avec un autre objet')
        mapping.update({key: str(uuid.uuid4()) for key in absent})
    if version in {4, 5, 6, 7,8,9}:
        erp_ids = [r['id'] for group in combined for rows in group.values() for r in rows if isinstance(r.get('id'), str)]
        if len(set(erp_ids)) != len(erp_ids):
            raise HTTPException(400, "Identifiant ambigu entre projet, personnes et modèles")
    brain_mapping = {row['id']: str(uuid.uuid4()) for rows in (brain or {}).values() for row in rows if isinstance(row.get('id'), str)} if version in {4, 5, 6, 7,8,9} else mapping
    new_id = mapping[projects[0]["id"]]
    pending_references = identity_archive.reconcile_references(db, Base.metadata, references, mapping) if references else {}
    pending_templates = planning_archive.reconcile_templates(db, Base.metadata, planning_references, mapping) if version in {4, 5, 6, 7,8,9} else {}
    pending_deliverables = deliverable_store.reconcile_references(db, Base.metadata, deliverable_references, mapping,
        typology_ids=deliverable_archive.dependencies(tables, deliverable_references)['typologies']) if version in {5,6,7,8,9} else {}
    deliverable_hashes = v5.manifest_hashes(tables, mapping) if version in {5,6,7,8,9} else None
    note_rows = note_archive.remap_rows(tables, mapping) if note_context is not None else None
    if note_rows is not None:
        note_store.section_for({'projects': [{'id': new_id}], **note_rows})
    job_rows = None
    if version == 8 or version == 9 and has_jobs:
        from .document_forms import _actor
        from .project_operator import current_operator
        job_rows = job_archive.import_rows(tables, mapping, actor=_actor(current_operator()))
    # Validate every file before any database write. Files are addressed by hash,
    # never by the untrusted filename supplied in the archive.
    decoded = []
    total = ((review_archive.embedded_bytes(tables) if has_reviews else 0)
             + (document_archive.embedded_bytes(tables) if has_documents else 0)
             + (job_archive.embedded_bytes(tables) if version in {8,9} and has_jobs else 0)
             + (sum(len(row['snapshot'].encode('utf-8')) for name in ('project_note_versions', 'project_note_imports')
                    for row in tables.get(name, [])) if note_context is not None else 0))
    if total > MAX_ARCHIVE_BYTES:
        raise HTTPException(413, 'Archive trop volumineuse')
    files = data.get("files", [])
    if not isinstance(files, list) or len(files) > 100000:
        raise HTTPException(400, "Liste de pièces d'archive invalide")
    brain_sources = {row['id']: row for row in (brain or {}).get('sources', [])}
    owners_by_area = {"cdc": {row["id"] for row in tables.get("cdc_sources", [])},
                      "delivery": {row["id"] for row in tables.get("delivery_versions", [])},
                      "raw": set(brain_sources)}
    if version in {5,6,7,8,9}:
        owners_by_area['deliverable'] = {row['id'] for row in tables.get('project_deliverable_file_versions', []) if row['source_delivery_id'] is None}
    if version in {8,9} and has_jobs:
        job_artifacts = {row['id']: row for row in tables['project_document_job_artifacts']}
        owners_by_area['document-job'] = set(job_artifacts)
    if note_context is not None:
        for area, table in note_archive.AREAS.items():
            owners_by_area[area] = {row['id'] for row in tables[table]}
    received = set()
    for entry in files:
        if not isinstance(entry, dict) or not isinstance(entry.get("owner"), str) or not isinstance(entry.get("area"), str):
            raise HTTPException(400, "Propriétaire de pièce d'archive invalide")
        owner = (entry["area"], entry["owner"])
        if entry["owner"] not in owners_by_area.get(entry["area"], set()) or owner in received:
            raise HTTPException(400, "Zone/propriétaire inconnu ou pièce d'archive dupliquée")
        received.add(owner)
        if version in {8,9} and has_jobs and entry['area'] == 'document-job':
            artifact = job_artifacts[entry['owner']]
            if not isinstance(entry.get('data'), str) or len(entry['data']) > 4 * ((artifact['size_bytes'] + 2) // 3):
                raise HTTPException(400, 'Copie documentaire encodée au-delà de la taille déclarée')
        if note_context is not None and entry['area'] in note_archive.AREAS:
            row = note_context['assets' if entry['area'] == 'note-file' else 'imports'][entry['owner']]
            if not isinstance(entry.get('data'), str) or len(entry['data']) > 4 * ((row['size_bytes'] + 2) // 3):
                raise HTTPException(400, 'Fichier de note encodé au-delà de sa taille déclarée')
        try:
            content = base64.b64decode(entry["data"], validate=True)
        except (ValueError, TypeError, KeyError) as exc:
            raise HTTPException(400, "Pièce encodée invalide") from exc
        total += len(content)
        if total > MAX_ARCHIVE_BYTES:
            raise HTTPException(413, "Archive trop volumineuse")
        digest = hashlib.sha256(content).hexdigest()
        owner_mapping = brain_mapping if entry['area'] == 'raw' else mapping
        if digest != entry.get("sha256") or entry.get("owner") not in owner_mapping:
            raise HTTPException(400, "Empreinte ou propriétaire de pièce invalide")
        if entry['area'] == 'raw':
            source = brain_sources[entry['owner']]
            content_hash = brain_archive.library_content_hash(source)
            if (content_hash or version in {6,7,8,9}) and digest != (content_hash or source['sha256']):
                raise HTTPException(400, 'Pièce source différente de son empreinte Brain')
        decoded.append((entry, content, digest))
    required_files = {("cdc", row["id"]) for row in tables.get("cdc_sources", []) if row.get("storage_path")}
    required_files.update(("delivery", row["id"]) for row in tables.get("delivery_versions", []))
    if version in {5,6,7,8,9}:
        required_files.update(v5.required_files(tables))
    if version in {6,7,8,9}:
        required_files.update(('raw', row['id']) for row in (brain or {}).get('sources', []) if review_store.raw_path(row, brain))
    if not required_files.issubset(received):
        raise HTTPException(400, "Pièce CDC ou version de livrable absente de l'archive")
    if version in {5,6,7,8,9}:
        v5.validate_file_bindings(tables, decoded)
    if version in {8,9} and has_jobs:
        job_archive.validate_files(tables, decoded)
    if note_context is not None:
        note_store.validate_files(tables, data['note_references'], decoded)
    with (nullcontext(coordinated_brain) if coordinated_brain is not None else SessionLocal()) as session:
        reuse = None
        if brain:
            if len(brain.get("projects", [])) != 1:
                raise HTTPException(400, "Projet Brain invalide")
            original = brain["projects"][0]
            from app.models import Project as BrainProject
            reuse = session.get(BrainProject, original["id"])
            if reuse:
                if version in {4, 5, 6, 7,8,9}:
                    planning_archive.validate_reused_brain(session, BrainBase.metadata, tables, brain)
                if version in {6,7,8,9}:
                    review_store.validate_reused_transcriptions(session, BrainBase.metadata, brain)
                brain_mapping[original["id"]] = reuse.id
            elif session.query(BrainProject).filter_by(code=target_code).first():
                raise HTTPException(409, "Code Brain déjà utilisé")
            if not reuse:
                source_table = BrainBase.metadata.tables['sources']
                incoming_hashes = {row['sha256'] for row in brain.get('sources', [])}
                if session.execute(select(source_table.c.id).where(source_table.c.sha256.in_(incoming_hashes)).limit(1)).first():
                    raise HTTPException(409, 'Sources déjà présentes dans un autre cœur canonique : restaurer dans un dossier neuf ou réutiliser le projet Brain d’origine')
        destinations = []
        exclusive_note_paths = []
        for entry, content, digest in decoded:
            area = entry.get("area")
            if area == "cdc":
                target = cdc_storage_root() / new_id / f"{digest}.bin"
                source = next((r for r in tables.get("cdc_sources", []) if r["id"] == entry["owner"]), None)
                if source is None:
                    raise HTTPException(400, "Source CDC absente")
                source["storage_path"] = str(target)
            elif area == "raw" and brain:
                target = RAW_DIR / f"{digest}.bin"
                source = brain_sources[entry['owner']]
                source["original_uri"] = str(target)
                source["source_metadata"] = {**source.get("source_metadata", {}), "raw_path": str(target)}
            elif area == "delivery":
                from ..db import APP_DIR
                target = APP_DIR / "exports" / new_id / f"{mapping[entry['owner']]}.md"
                delivery_version = next((r for r in tables.get("delivery_versions", []) if r["id"] == entry["owner"]), None)
                if delivery_version is None:
                    raise HTTPException(400, "Version de livrable absente")
                delivery_version["path"] = str(target)
                if version in {5,6,7,8,9}:
                    linked = {row['id'] for row in tables.get('project_deliverable_file_versions', []) if row['source_delivery_id'] == entry['owner']}
                    for metadata in tables.get('project_deliverable_version_metadata', []):
                        if metadata['version_id'] in linked:
                            metadata['storage_path'] = str(target)
            elif area == 'deliverable' and version in {5,6,7,8,9}:
                from ..db import APP_DIR
                target = APP_DIR / 'deliverables' / new_id / (mapping[entry['owner']] + '.bin')
                metadata = next(row for row in tables['project_deliverable_version_metadata'] if row['version_id'] == entry['owner'])
                metadata['storage_path'] = str(target)
            elif area == 'document-job' and version in {8,9}:
                from ..db import APP_DIR
                target = APP_DIR / 'document-artifacts' / mapping[entry['owner']]
                if target.exists() or target.is_symlink() or any(part.is_symlink() or part.is_junction() for part in target.parents):
                    raise HTTPException(409, 'Destination de copie documentaire déjà occupée ou liée')
            elif note_rows is not None and area in note_archive.AREAS:
                from ..db import APP_DIR
                row = next(row for row in note_rows[note_archive.AREAS[area]] if row['id'] == mapping[entry['owner']])
                target = note_store.destination(APP_DIR, area, row)
                exclusive_note_paths.append(target)
            else:
                raise HTTPException(400, "Zone de stockage inconnue")
            if version in {5,6,7,8,9}:
                allowed = cdc_storage_root() if area == 'cdc' else RAW_DIR if area == 'raw' else APP_DIR
                if not target.resolve().is_relative_to(allowed.resolve()) or target.is_symlink():
                    raise HTTPException(409, 'Destination de pièce hors stockage géré')
                if target.exists() and (not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != digest):
                    raise HTTPException(409, 'Pièce déjà présente avec un contenu différent')
            destinations.append((target, content))
        if version in {6,7,8,9}:
            from ..db import APP_DIR
            from .project_archive_files import PreparedFiles
            preparation = PreparedFiles(APP_DIR, new_id, brain_mapping[brain['projects'][0]['id']] if brain else None, destinations, brain_reused=bool(reuse), exclusive_paths=exclusive_note_paths)
            preparations.append(preparation)
            preparation.prepare()
        else:
            for target, content in destinations:
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    target.write_bytes(content)
        try:
            if brain:
                for recording in brain.get("meeting_recordings", []):
                    if recording.get("job_status") in {"queued", "running"}:
                        recording["job_status"] = "interrupted"
                        recording["error"] = "Archive importée : relancer le traitement explicitement"
            for job in tables.get("cdc_analysis_jobs", []):
                if job.get("status") in {"queued", "running"}:
                    job["status"] = "interrupted"
                    job["error"] = "Archive importée : reprise à demander explicitement"
            for job in tables.get("milestone_scan_jobs", []):
                if job.get("status") in {"queued", "running"}:
                    job["status"] = "interrupted"
                    job["error"] = "Archive importée : recherche à reprendre"
            for ledger in tables.get("milestone_inputs", []):
                ledger["status"] = "failed"
                ledger["error"] = "Archive importée : preuves à relire"
            if brain:
                for row in brain.get("memory_dataset_mappings", []):
                    row["engine"], row["engine_version"] = "eg2", "eg2-v1"
            if brain and not reuse:
                for row in brain.get("memory_projections", []):
                    row["status"] = "pending"
                    row["external_ref"] = None
                audio_mapping = brain_mapping if version in {4, 5, 6, 7,8,9} else mapping
                if version in {4, 5, 6, 7,8,9}:
                    # Cross-store fields use ERP IDs even when UUID namespaces overlap.
                    for recording in brain.get('meeting_recordings', []):
                        recording['erp_project_id'] = new_id
                        if recording.get('published_meeting_id'):
                            recording['published_meeting_id'] = mapping[recording['published_meeting_id']]
                _insert(session, BrainBase.metadata, brain, audio_mapping, {"code": target_code}, typed_brain=version in {4, 5, 6, 7,8,9}, typed_reviews=version in {6,7,8,9})
            elif brain and reuse:
                # Reuse canonical sources/knowledge already present, while
                # preserving the imported ERP project's own audio workflow.
                cloned_artifacts = review_store.cloned_transcriptions(brain) if version in {6,7,8,9} else []
                cloned_ids = {row['id'] for row in cloned_artifacts}
                reused = {r["id"]: r["id"] for name, rows in brain.items() if name != "meeting_recordings"
                          for r in rows if isinstance(r.get("id"), str) and r['id'] not in cloned_ids}
                if version in {4, 5, 6, 7,8,9}:
                    brain_mapping.update(reused)
                    for recording in brain.get('meeting_recordings', []):
                        recording['erp_project_id'] = new_id
                        if recording.get('published_meeting_id'):
                            recording['published_meeting_id'] = mapping[recording['published_meeting_id']]
                    audio_mapping = brain_mapping
                else:
                    audio_mapping = {**mapping, **reused}
                _insert(session, BrainBase.metadata, {"meeting_recordings": brain.get("meeting_recordings", []),
                        'source_artifacts':cloned_artifacts}, audio_mapping, typed_brain=version in {4, 5, 6, 7,8,9}, typed_reviews=version in {6,7,8,9})
            if version in {4, 5, 6, 7,8,9}:
                for baseline in tables.get('project_planning_baselines', []):
                    moved = planning_archive.remap_row(baseline, Base.metadata.tables['project_planning_baselines'], mapping, brain_mapping, _remap)
                    mapping['baseline-hash:' + baseline['id']] = moved['sha256']
            _insert(db, Base.metadata, {**pending_references, **pending_templates, **pending_deliverables}, mapping,
                    planning_context=brain_mapping if version in {4, 5, 6, 7,8,9} else None, deliverable_hashes=deliverable_hashes, typed_reviews=version in {6,7,8,9})
            _insert(db, Base.metadata, without_jobs, mapping, {"code": target_code},
                    planning_context=brain_mapping if version in {4, 5, 6, 7,8,9} else None, deliverable_hashes=deliverable_hashes, typed_reviews=version in {6,7,8,9}, typed_documents=version in {7,8,9})
            if job_rows is not None:
                _insert(db, Base.metadata, job_rows, {}, typed_jobs=True)
            if note_rows is not None:
                note_store.insert_rows(db, note_rows)
            if directories is not None:
                directories.enter_context(client_directory(db, new_id))
            # Legacy v2-v5 retain their dual commit/global backup behavior.
            # v6 is committed once by the outer coordinated transaction.
            if coordinated_brain is None:
                session.commit()
                db.commit()
        except HTTPException:
            if coordinated_brain is None:
                session.rollback()
                db.rollback()
            raise
        except Exception as exc:
            if coordinated_brain is None:
                session.rollback()
                db.rollback()
            raise HTTPException(409, "Archive incompatible avec les données existantes ; consulter les journaux avant de relancer") from exc
    return {"id": new_id, "code": target_code, "title": projects[0]["title"], "version": version}
