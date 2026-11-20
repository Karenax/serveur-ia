"""Explicit, synchronous publication with durable intent and file identity receipts.

Owns commits: intent precedes exclusive candidate IO, prepared receipt precedes
promotion, success follows final verification. Unknown candidates are retained.
No startup recovery, regeneration, implicit replacement or directory creation.
"""
import json
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, select

from ..models import NetworkLink, REQUIRED_NETWORK_LINKS
from ..project_document_job_models import DocumentJobArtifact, DocumentJobItem, DocumentJobEvent
from . import document_jobs as jobs, document_publications as destinations
from . import document_publication_history as history
from .document_publication_io import AnchoredDirectory
from .document_template_catalogue import document_spec
from .document_worker_lease import WorkerLease
from .project_documents import _link_sha256
from .project_identity import _project
from .project_operator import current_operator


def _rows(db, model, job):
    rows = list(db.scalars(select(model).where(model.job_id == job.id, model.project_id == job.project_id)
                          .limit(100001).execution_options(populate_existing=True)))
    if len(rows) > 100000:
        raise HTTPException(409, 'Historique de publication trop volumineux')
    return [{column.name:getattr(row, column.name) for column in model.__table__.columns} for row in rows]


def _records(db, job):
    events = _rows(db, DocumentJobEvent, job)
    imports = [row for row in events if row['kind'] == 'archive_imported']
    try:
        imported = json.loads(max(imports, key=lambda row:row['revision'])['detail']) if imports else None
        return history.validate(events, job={'id':job.id, 'project_id':job.project_id, 'execution_blocked':job.execution_blocked},
            artifacts={row['id']:row for row in _rows(db, DocumentJobArtifact, job)},
            items={row['id']:row for row in _rows(db, DocumentJobItem, job)}, imported=imported)
    except (ValueError, KeyError, TypeError, HTTPException) as exc:
        raise HTTPException(409, 'Journal de publication incohérent') from exc


def _writable(job):
    if job.execution_blocked:
        raise HTTPException(409, 'Historique importé ou restauré : publication et reprise désactivées')
    if job.status in {'queued', 'running'}:
        raise HTTPException(409, 'Terminer ou interrompre le lot avant sa publication')


def _result(job, record):
    return {'project_id':job.project_id, 'job_id':job.id, 'job_revision':job.revision,
            'command_id':record['command']['command_id'], 'artifact_id':record['binding']['artifact_id'],
            'command':dict(record['command']), 'reviewed_preview':dict(record['preview']),
            'state':record['state'], 'network_published':record['state'] == 'succeeded',
            'needs_inspection':record['state'] == 'requested',
            'can_abandon':not job.execution_blocked and current_operator().role!='reader'
                          and job.status not in {'queued','running'} and record['state']=='requested',
            'execution_blocked':job.execution_blocked,
            'can_resume':not job.execution_blocked and current_operator().role != 'reader'
                         and job.status not in {'queued', 'running'} and record['state'] in {'prepared','backup_requested','backup_saved','succeeded'},
            'destination':record['preview']['directory'] + '/' + record['preview']['filename'],
            'candidate':record['candidate'], 'receipt':record['receipt'],
            'backup':record.get('backup'), 'backup_receipt':record['backup_receipt'],
            'requested_revision':record['requested_revision'], 'updated_revision':record['updated_revision']}


def list_publications(db, project_id, job_id, *, offset=0, limit=30, artifact_id=None):
    job = jobs._job(db, project_id, job_id)
    if type(offset) is not int or type(limit) is not int or not 0 <= offset <= 1000000 or not 1 <= limit <= 200:
        raise HTTPException(422, 'Pagination de publication invalide')
    records = sorted(_records(db, job).values(), key=lambda row:row['requested_revision'], reverse=True)
    if artifact_id is not None:
        if db.scalar(select(DocumentJobArtifact.id).where(DocumentJobArtifact.id==artifact_id,
                DocumentJobArtifact.project_id==project_id,DocumentJobArtifact.job_id==job_id)) is None:
            raise HTTPException(404,'Copie documentaire introuvable dans ce lot')
        records=[row for row in records if row['binding']['artifact_id']==artifact_id]
    return {'project_id':project_id, 'job_id':job_id, 'job_revision':job.revision,
            'execution_blocked':job.execution_blocked, 'total':len(records), 'offset':offset, 'limit':limit,
            'items':[_result(job, row) for row in records[offset:offset + limit]]}


def _attachment_link(db, project_id, capture):
    if len(str(Path(capture['directory']) / capture['filename'])) > 1024:
        raise HTTPException(422, 'Chemin trop long pour rattacher le fichier au projet')
    spec = document_spec(capture['document_id'])
    code, aliases = spec['link_code'], spec['link_aliases']
    links = list(db.scalars(select(NetworkLink).where(
        NetworkLink.project_id == project_id, func.lower(NetworkLink.code).in_([code, *aliases]))
        .order_by(NetworkLink.ordre, NetworkLink.id)))
    link = next((row for row in links if row.code.casefold() == code), links[0] if links else None)
    if link is not None and link.id == capture['link_id']:
        raise HTTPException(409, 'Choisissez un autre lien de dossier pour rattacher le fichier au projet')
    return link


def _attach_file(db, project_id, capture):
    spec = document_spec(capture['document_id'])
    code = spec['link_code']
    link = _attachment_link(db, project_id, capture)
    if link is None:
        labels = dict(REQUIRED_NETWORK_LINKS)
        link = NetworkLink(project_id=project_id, code=code, libelle=labels.get(code, spec['label']),
                           ordre=spec['link_order'])
        db.add(link)
    else:
        link.code = code
    link.chemin = str(Path(capture['directory']) / capture['filename'])


def _append(db, project_id, job_id, kind, detail, *, expected_revision=None, attach=None):
    job = jobs._job(db, project_id, job_id, write=True)
    _writable(job)
    jobs._change(db, job, job.revision if expected_revision is None else expected_revision)
    jobs._event(db, job, kind, detail)
    db.flush()
    # Validate the entire publication chain before making this receipt durable.
    _records(db, job)
    if attach is not None:
        _attach_file(db, project_id, attach)
    db.commit()
    return jobs._job(db, project_id, job_id, write=True)


def _lease(db):
    url = db.get_bind().url
    if url.get_backend_name() != 'sqlite' or not url.database or url.database == ':memory:':
        raise HTTPException(409, 'Base SQLite persistante requise pour la publication')
    try:
        lease = WorkerLease(url.database, namespace='publication')
        if not lease.acquire():
            raise HTTPException(409, 'Une publication documentaire est déjà en cours ; conserver la même commande')
        return lease
    except (OSError, ValueError) as exc:
        raise HTTPException(409, 'Verrou de publication documentaire indisponible') from exc


def publish(db, project_id, artifact_id, command, *, storage_root, policy=None):
    """Same exact command reconciles prepared/final identity; never writes twice."""
    with db.no_autoflush:
        _project(db, project_id, write=True)  # BEFORE lock metadata or filesystem IO.
    if db.new or db.dirty or db.deleted:
        raise HTTPException(409, 'Session dédiée requise pour la publication documentaire')
    jobs._ready(db, write=True)
    artifact = db.scalar(select(DocumentJobArtifact).where(DocumentJobArtifact.id == artifact_id,
                                                          DocumentJobArtifact.project_id == project_id))
    if artifact is None:
        raise HTTPException(404, 'Copie documentaire introuvable')
    job_id = artifact.job_id
    _writable(jobs._job(db, project_id, job_id, write=True))
    # End the preliminary read transaction. A held OS lease serializes all
    # publication commands across processes, independently of the worker lease.
    db.rollback()
    lease = _lease(db)
    try:
        return _publish_locked(db, project_id, artifact_id, job_id, command, storage_root=storage_root, policy=policy)
    except Exception:
        db.rollback()
        raise
    finally:
        lease.close()


def _publish_locked(db, project_id, artifact_id, job_id, command, *, storage_root, policy):
    job = jobs._job(db, project_id, job_id, write=True)
    _writable(job)
    records = _records(db, job)
    record = records.get(command.command_id)
    if record is not None and record['preview']['version'] == 1 and command.link_to_project:
        raise HTTPException(409, 'Ce reçu ne contient pas de rattachement ; conservez la commande d’origine')
    body = history.command_body(command,record['preview']['version']) if record else command.model_dump()
    if record is not None and (record['command'] != body or record['binding']['artifact_id'] != artifact_id):
        raise HTTPException(409, 'Cette commande de publication désigne une autre copie ou destination')
    if record is not None and record['state']=='abandoned':
        raise HTTPException(409,'Commande clôturée : préparer et relire une nouvelle publication')
    # Managed bytes must still agree with their immutable generation receipt.
    content, filename = jobs.artifact_content(db, project_id, artifact_id, storage_root=storage_root)
    policy = destinations.configured_write_policy(project_id) if policy is None else policy
    root, directory, relative = destinations._destination(db, project_id, command, policy)
    if record is None:
        reviewed = destinations.preview(db, project_id, artifact_id, command, storage_root=storage_root, policy=policy)
        if (not reviewed['can_publish'] or reviewed['job_revision'] != command.expected_revision
                or reviewed['preview_sha256'] != command.expected_preview_sha256):
            raise HTTPException(409, 'Destination ou lot modifié : relire l’aperçu avant de publier')
        capture = {key:reviewed[key] for key in history.capture_keys(reviewed['version'])}
        if any(row['state'] not in {'succeeded','abandoned'} and row['binding']['artifact_id'] == artifact_id
               and row['preview']['directory'] == str(directory) and row['preview']['filename'] == filename
               for row in records.values()):
            raise HTTPException(409, 'Publication antérieure incertaine : consulter son reçu et conserver sa commande')
    else:
        capture = record['preview']
    if (capture['link_sha256'] != _link_sha256(db, project_id, command.link_id)
            or capture['write_policy_sha256'] != jobs.frozen({'roots':policy.roots, 'drive_mappings':policy.drive_mappings})[1]
            or capture['directory'] != str(directory) or capture['relative_directory'] != relative
            or capture['filename'] != filename):
        raise HTTPException(409, 'Configuration ou lien de publication modifié : reprise refusée')
    if command.link_to_project and (record is None or record['state'] != 'succeeded'):
        _attachment_link(db, project_id, capture)
    with AnchoredDirectory(root, directory) as opened:
        if opened.identity != capture['directory_identity']:
            raise HTTPException(409, 'Identité du dossier de destination différente de la relecture')
        if record is None:
            replacement = capture.get('replace_existing',False)
            if replacement:
                if opened.native is None:
                    raise HTTPException(409,'Remplacement ancré disponible sur Windows uniquement')
                opened.verify(filename,capture['existing_receipt'])
            elif opened.exists(filename):
                raise HTTPException(409, 'Destination occupée : aucun fichier remplacé')
            candidate = '.agent-publish-' + uuid4().hex + '.pending'
            intention = {'command':body, 'command_sha256':jobs.frozen(body)[1], 'preview':capture, 'candidate':candidate}
            if capture['version']==2:
                intention['backup'] = '.agent-backup-'+uuid4().hex+'.bak' if replacement else None
            job = _append(db, project_id, job_id, 'publication_requested',
                          intention,
                          expected_revision=command.expected_revision)
            receipt = opened.create_candidate(candidate, content)
            job = _append(db, project_id, job_id, 'publication_prepared',
                          {'command_id':command.command_id, 'receipt':receipt})
            record = _records(db, job)[command.command_id]
        elif record['state'] == 'requested':
            # A crash before receipt commit cannot prove candidate ownership,
            # even when its bytes match. Retain it and require inspection.
            raise HTTPException(409, {'code':'publication_uncertain', 'command_id':command.command_id,
                                     'state':'requested', 'message':'Candidat sans reçu durable : inspection requise, aucune réécriture automatique'})
        receipt = record['receipt']
        if capture.get('replace_existing'):
            job, record = _replace(db,project_id,job_id,job,record,opened,filename)
        elif opened.exists(filename):
            opened.verify(filename, receipt)
        elif record['state'] == 'succeeded':
            raise HTTPException(409, 'Fichier publié absent : le reçu historique ne permet pas de le recréer')
        else:
            _writable(jobs._job(db, project_id, job_id, write=True))
            opened.promote(record['candidate'], filename, receipt)
        if record['state'] != 'succeeded':
            job = _append(db, project_id, job_id, 'publication_succeeded',
                          {'command_id':command.command_id, 'receipt':receipt},
                          attach=capture if command.link_to_project else None)
            record = _records(db, job)[command.command_id]
        return _result(job, record)


def _replace(db, project_id, job_id, job, record, opened, filename):
    """Journal every boundary; anchored no-replace moves keep original intact."""
    if opened.native is None:
        raise HTTPException(409,'Remplacement ancré disponible sur Windows uniquement')
    receipt, original = record['receipt'], record['preview']['existing_receipt']
    backup, cid = record['backup'], record['command']['command_id']
    if record['state']=='succeeded':
        opened.verify(backup,original)
        opened.verify(filename,receipt)
        return job,record
    final_is_new = False
    if opened.exists(filename):
        actual = opened.describe(filename)
        if actual==receipt:
            final_is_new = True
        elif actual != original:
            raise HTTPException(409,'Destination remplacée par un tiers : sauvegarde et candidat conservés')
    if not final_is_new:
        opened.verify(record['candidate'],receipt)  # BEFORE moving any original.
    if record['state']=='prepared':
        # First pass must still see exactly the reviewed original.
        opened.verify(filename,original)
        if opened.exists(backup):
            raise HTTPException(409,'Nom de sauvegarde occupé : aucun original déplacé')
        job = _append(db,project_id,job_id,'publication_backup_requested',{'command_id':cid,'receipt':original})
        record = _records(db,job)[cid]
    if record['state']=='backup_requested':
        if opened.exists(backup):
            opened.verify(backup,original)
        else:
            if final_is_new:
                raise HTTPException(409,'Original sauvegardé absent : reprise refusée')
            _writable(jobs._job(db,project_id,job_id,write=True))
            opened.promote(filename,backup,original)  # Native rename from held file, never replace.
        job = _append(db,project_id,job_id,'publication_backup_saved',{'command_id':cid,'receipt':original})
        record = _records(db,job)[cid]
    opened.verify(backup,original)
    if not final_is_new:
        _writable(jobs._job(db,project_id,job_id,write=True))
        opened.promote(record['candidate'],filename,receipt)
    else:
        opened.verify(filename,receipt)
    return job,record


def abandon(db,project_id,job_id,command_id,payload):
    """Explicitly close uncertain intent, preserving every file without any probe."""
    with db.no_autoflush:
        job=jobs._job(db,project_id,job_id,write=True)
    if db.new or db.dirty or db.deleted:
        raise HTTPException(409,'Session dédiée requise pour clôturer la publication')
    _writable(job)
    db.rollback()
    lease=_lease(db)  # Cannot close an intent while another process still writes.
    try:
        job=jobs._job(db,project_id,job_id,write=True)
        _writable(job)
        record=_records(db,job).get(command_id)
        if record is None:
            raise HTTPException(404,'Intention de publication introuvable')
        body=payload.model_dump()
        if record['state']=='abandoned':
            if record['abandon_command']!=body:
                raise HTTPException(409,'Cette clôture désigne une autre confirmation')
            return _result(job,record)
        if record['state']!='requested':
            raise HTTPException(409,'Un reçu préparé existe : reprendre cette publication et conserver ses preuves')
        job=_append(db,project_id,job_id,'publication_abandoned',{'command_id':command_id,**body},
                    expected_revision=payload.expected_revision)
        return _result(job,_records(db,job)[command_id])
    except Exception:
        db.rollback()
        raise
    finally:
        lease.close()
