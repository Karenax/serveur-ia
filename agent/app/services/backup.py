"""Offline, hash-checked backup and restore into a new directory only."""
import hashlib
import json
import shutil
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath

from ..db_support import backup_sqlite
from . import client_directory_backup


def _obsolete_storage_path(path):
    return tuple(part.casefold() for part in path.parts[:2]) == ('storage', 'multimodal')


def file_digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block := stream.read(1024**2):
            value.update(block)
    return value.hexdigest()


def restored_eg2_index(value, storage):
    """Resolve a historical managed index against the restored storage root."""
    if not isinstance(value, str) or not value:
        return None
    parts = PureWindowsPath(value).parts
    positions = [i for i, part in enumerate(parts[:-2])
                 if part.casefold() == 'storage' and parts[i + 1].casefold() == 'eg2']
    if len(positions) != 1:
        return None
    relative = parts[positions[0] + 1:]
    if any(part == '..' or ':' in part for part in relative) or not relative[-1].lower().endswith('.db'):
        return None
    candidate = storage.joinpath(*relative).resolve()
    return candidate if candidate.is_relative_to(storage.resolve()) and candidate.is_file() else None


def verify_backup(source):
    """Verify bytes and both databases without restoring or changing a backup."""
    source = Path(source).resolve()
    manifest = json.loads((source / 'backup.json').read_text(encoding='utf-8'))
    if (not isinstance(manifest, dict) or manifest.get('format') != 'agent-offline-backup' or manifest.get('version') != 1
            or not isinstance(manifest.get('files'), dict)
            or not {'brain/project_brain.db', 'erp/minipilot.db'}.issubset(manifest['files'])):
        raise ValueError('Manifeste de sauvegarde incomplet')
    for name, expected in manifest['files'].items():
        if not isinstance(name, str) or not isinstance(expected, str):
            raise ValueError('Chemin ou empreinte invalide')
        relative = PurePosixPath(name)
        if (relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name
                or not relative.parts or relative.as_posix() != name):
            raise ValueError('Chemin de sauvegarde interdit')
        original = source / name
        path = original.resolve()
        if original.is_symlink() or not path.is_relative_to(source) or not path.is_file() or file_digest(path) != expected:
            raise ValueError('Pièce absente, redirigée ou empreinte incorrecte')
    for name in ('brain/project_brain.db', 'erp/minipilot.db'):
        with closing(sqlite3.connect((source / name).as_uri() + '?mode=ro', uri=True)) as db:
            if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or db.execute('PRAGMA foreign_key_check').fetchone():
                raise ValueError('Base sauvegardée invalide')
    client_directory_backup.validate(manifest, source / 'erp/minipilot.db')
    return {'status': 'verified', 'files': len(manifest['files']),
            'verified_at': datetime.now(timezone.utc).isoformat()}


def create_backup(output: Path, brain_db: Path, erp_home: Path, storage: Path, *, client_root: Path | None = None):
    output = output.resolve()
    sources = [brain_db.resolve(), erp_home.resolve(), storage.resolve()]
    if client_root is not None:
        sources.append(client_root.resolve())
    if any(output == p or output.is_relative_to(p) for p in sources):
        raise ValueError("La sauvegarde doit être extérieure aux données")
    if output.exists():
        raise FileExistsError("Le dossier de sauvegarde doit être nouveau")
    if not brain_db.is_file() or not (erp_home / "minipilot.db").is_file():
        raise FileNotFoundError("Les deux bases doivent exister")
    from .note_backup import collect_files as collect_note_files, validate_files as validate_note_files
    # Qualify committed note history and all managed originals before output.
    # The SQLite snapshot below is qualified again to detect intervening edits.
    collect_note_files(erp_home / 'minipilot.db', erp_home)
    from .storage_capacity import require_capacity
    estimate = brain_db.stat().st_size
    for directory in (erp_home, storage):
        estimate += sum(path.stat().st_size for path in directory.rglob('*') if path.is_file()
                        and not path.is_symlink() and 'backups' not in path.relative_to(directory).parts
                        and (directory != storage or not _obsolete_storage_path(Path('storage') / path.relative_to(directory))))
    if client_root is not None:
        folders = client_directory_backup.client_directories(client_root, erp_home / 'minipilot.db')
        estimate += sum(metadata.st_size for _, metadata in client_directory_backup.client_files(folders))
    require_capacity(output.parent, estimate)
    output.mkdir(parents=True)
    backup_sqlite(brain_db, output / "brain" / "project_brain.db")
    backup_sqlite(erp_home / "minipilot.db", output / "erp" / "minipilot.db")
    from .meeting_session_backup import collect as collect_sessions, validate as validate_sessions
    session_files = collect_sessions(output / 'brain/project_brain.db', storage)
    from .document_backup import validate_document_history
    validate_document_history(output / 'erp/minipilot.db')
    from .document_jobs_backup import collect_files as collect_job_files, validate_files as validate_job_files
    document_job_files = collect_job_files(output / 'erp/minipilot.db', erp_home)
    note_files = collect_note_files(output / 'erp/minipilot.db', erp_home)
    from .deliverable_backup import collect_bindings, validate_bindings
    deliverable_files = collect_bindings(output / 'erp/minipilot.db', erp_home, storage)
    for source, destination in [(storage, output / "storage"), (erp_home, output / "erp")]:
        for path in source.rglob("*"):
            relative = path.relative_to(source)
            if (not path.is_file() or path.is_symlink() or "backups" in relative.parts
                    or relative.as_posix() == "backup-status.json"
                    or not path.resolve().is_relative_to(source.resolve())):
                continue
            if source == erp_home and (relative.as_posix().startswith("minipilot.db") or relative.name.endswith(("-wal", "-shm"))):
                continue
            if source == storage and (_obsolete_storage_path(Path('storage') / relative)
                                      or (relative.parts[0] == 'eg2' and relative.name.endswith(('-wal', '-shm')))):
                continue
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if source == storage and relative.parts[0] == 'eg2' and path.suffix == '.db':
                backup_sqlite(path, target)
            else:
                shutil.copy2(path, target)
    client_directories = (client_directory_backup.capture(client_root, output, output / 'erp/minipilot.db')
                          if client_root is not None else None)
    files = {p.relative_to(output).as_posix(): file_digest(p)
             for p in output.rglob("*") if p.is_file()}
    manifest = {"format": "agent-offline-backup", "version": 1,
                "created_at": datetime.now(timezone.utc).isoformat(), "files": files}
    if client_directories is not None:
        manifest['client_directories'] = client_directories
    if deliverable_files:
        manifest['deliverable_files'] = deliverable_files
        validate_bindings(output / 'erp/minipilot.db', output, manifest)
    if document_job_files:
        manifest['document_job_files'] = document_job_files
    validate_job_files(output / 'erp/minipilot.db', output, manifest)
    if note_files:
        manifest['note_files'] = note_files
    if session_files:
        manifest['meeting_session_files'] = session_files
    validate_sessions(output / 'brain/project_brain.db', output, manifest)
    validate_note_files(output / 'erp/minipilot.db', output, manifest)
    (output / "backup.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    verification = verify_backup(output)
    storage.mkdir(parents=True, exist_ok=True)
    (storage / "backup-status.json").write_text(json.dumps({"directory": str(output),
        "created_at": manifest["created_at"], **verification}), encoding="utf-8")
    return manifest


def restore_backup(source: Path, output: Path):
    source, output = source.resolve(), output.resolve()
    if output.exists():
        raise FileExistsError("La restauration exige un dossier neuf")
    manifest = json.loads((source / "backup.json").read_text(encoding="utf-8"))
    if (not isinstance(manifest, dict) or manifest.get("format") != "agent-offline-backup"
            or manifest.get("version") != 1):
        raise ValueError("Format de sauvegarde non reconnu")
    if not isinstance(manifest.get('files'), dict):
        raise ValueError('Liste de pièces de sauvegarde invalide')
    if not {"brain/project_brain.db", "erp/minipilot.db"}.issubset(manifest['files']):
        raise ValueError("Les deux bases sont requises dans le manifeste")
    for name, digest in manifest["files"].items():
        if not isinstance(name, str) or not isinstance(digest, str):
            raise ValueError('Chemin ou empreinte de sauvegarde invalide')
        relative = PurePosixPath(name)
        if (relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name
                or not relative.parts or relative.as_posix() != name):
            raise ValueError('Chemin relatif de sauvegarde interdit')
        original = source / name
        file = original.resolve()
        if not file.is_relative_to(source) or original.is_symlink() or not file.is_file():
            raise ValueError("Pièce absente ou chemin interdit")
        try:
            actual = file_digest(file)
        except OSError as exc:
            raise ValueError('Pièce de sauvegarde inaccessible') from exc
        if actual != digest:
            raise ValueError("Pièce absente, chemin interdit ou empreinte incorrecte")
    for name in ["brain/project_brain.db", "erp/minipilot.db"]:
        with sqlite3.connect(f"file:{(source / name).as_posix()}?mode=ro", uri=True) as db:
            if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Base de sauvegarde invalide")
    client_directory_backup.validate(manifest, source / 'erp/minipilot.db')
    from .note_backup import validate_files as validate_note_files, freeze_restored_commands
    validate_note_files(source / 'erp/minipilot.db', source, manifest)
    from .meeting_session_backup import validate as validate_sessions, relocate as relocate_sessions
    session_files = validate_sessions(source / 'brain/project_brain.db', source, manifest)
    from .deliverable_backup import validate_bindings, relocate_bindings
    from .document_backup import validate_document_history
    validate_document_history(source / 'erp/minipilot.db')
    from .document_jobs_backup import validate_files as validate_job_files, suspend_restored_jobs
    validate_job_files(source / 'erp/minipilot.db', source, manifest)
    deliverable_files = validate_bindings(source / 'erp/minipilot.db', source, manifest)
    output.mkdir(parents=True)
    restored_files = [name for name in manifest["files"] if not _obsolete_storage_path(PurePosixPath(name))]
    for name in restored_files:
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / name, target)
    # Portable managed paths are remapped in the restored databases. Originals
    # and their hash-checked archive remain untouched.
    with sqlite3.connect(output / "erp/minipilot.db") as db:
        client_directory_backup.relocate(output, db, manifest.get('client_directories'))
        rows = db.execute("SELECT id, storage_path FROM cdc_sources WHERE storage_path IS NOT NULL").fetchall()
        for row_id, path in rows:
            parts = Path(path).parts
            if "cdc" in parts:
                new_path = output / "erp" / Path(*parts[parts.index("cdc"):])
                db.execute("UPDATE cdc_sources SET storage_path=? WHERE id=?", (str(new_path), row_id))
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "cdc_analysis_jobs" in tables:
            db.execute("UPDATE cdc_analysis_jobs SET status='interrupted' WHERE status IN ('queued', 'running')")
        if "delivery_versions" in tables:
            for row_id, path in db.execute("SELECT id, path FROM delivery_versions").fetchall():
                parts = Path(path).parts
                if "exports" in parts:
                    new_path = output / "erp" / Path(*parts[parts.index("exports"):])
                    db.execute("UPDATE delivery_versions SET path=? WHERE id=?", (str(new_path), row_id))
    with sqlite3.connect(output / "brain/project_brain.db") as db:
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "app_settings" in tables:
            row = db.execute("SELECT value FROM app_settings WHERE key='memory'").fetchone()
            memory = json.loads(row[0] or '{}') if row else {}
            if isinstance(memory, dict) and memory.get('index_path'):
                index = restored_eg2_index(memory['index_path'], output / 'storage')
                memory['index_path'] = str(index) if index else ''
                db.execute("UPDATE app_settings SET value=? WHERE key='memory'", (json.dumps(memory),))
        if "meeting_recordings" in tables:
            db.execute("UPDATE meeting_recordings SET job_status='interrupted', "
                       "error='Sauvegarde restaurée : relancer le traitement explicitement' "
                       "WHERE job_status IN ('queued', 'running')")
        if "mail_triage_jobs" in tables:
            db.execute("UPDATE mail_triage_jobs SET status='interrupted', "
                       "error='Sauvegarde restaurée : relancer le traitement explicitement' "
                       "WHERE status IN ('queued', 'running')")
        if "mail_enrichment_jobs" in tables:
            db.execute("UPDATE mail_enrichment_jobs SET status='failed', "
                       "error='Sauvegarde restaurée : reprendre l’enrichissement explicitement' "
                       "WHERE status IN ('queued', 'running')")
        raw = output / 'storage' / 'raw'
        for row_id, digest, uri, metadata in db.execute("SELECT id, sha256, original_uri, source_metadata FROM sources").fetchall():
            value = json.loads(metadata or '{}')
            if value.get('library_item_id') and value.get('content_sha256'):
                # An OCR interpretation has its own source digest but shares the retained PDF.
                filename = PureWindowsPath(uri or '').name
                stored = (PurePosixPath('storage', 'raw') / filename).as_posix()
                path = raw / filename if manifest['files'].get(stored) == value['content_sha256'] else None
            else:
                path = next(raw.glob(f'{digest}*'), None)
            if path is not None:
                value['raw_path'] = str(path)
                db.execute("UPDATE sources SET original_uri=?, source_metadata=? WHERE id=?",
                           (str(path), json.dumps(value, ensure_ascii=False), row_id))
    relocate_bindings(output / 'erp/minipilot.db', output, deliverable_files)
    relocate_sessions(output / 'brain/project_brain.db', output, session_files)
    from .meeting_session_backup import relocate_derived_storage
    relocate_derived_storage(output)
    suspend_restored_jobs(output / 'erp/minipilot.db')
    freeze_restored_commands(output / 'erp/minipilot.db')
    return {"directory": str(output), "files": len(restored_files)}
