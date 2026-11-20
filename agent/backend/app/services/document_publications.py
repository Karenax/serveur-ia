"""Read-only destination review for an explicit publication of a validated copy.

Write roots are separate from read roots. No directory or file is created by
preview. Durable intent/receipt commands are integrated separately.
"""
import json
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select

from ..models import NetworkLink
from ..project_document_job_models import DocumentJobArtifact, DocumentJobItem
from . import document_jobs as jobs
from .document_file_access import FilePolicy, _mapped, configured_policy
from .document_paths import _relative
from .document_publication_io import AnchoredDirectory, _name
from .project_documents import _link_sha256
from .project_identity import _project
from .project_operator import current_operator


def configured_write_policy(project_id=None):
    return configured_policy(project_id, write=True)


def _destination(db, project_id, choice, policy):
    link = db.scalar(select(NetworkLink).where(NetworkLink.id == choice.link_id, NetworkLink.project_id == project_id))
    if link is None:
        raise HTTPException(404, 'Lien de destination introuvable dans ce projet')
    relative = _relative(choice.relative_directory)
    if not isinstance(policy, FilePolicy) or not policy.roots:
        raise HTTPException(409, 'Renseigner les racines d’écriture documentaire autorisées sur le serveur')
    configured = _mapped(link.chemin, policy)
    eligible = [Path(root) for root in policy.roots if configured == Path(root) or configured.is_relative_to(Path(root))]
    if not eligible:
        raise HTTPException(403, 'Lien de destination hors des racines d’écriture autorisées')
    root = max(eligible, key=lambda path:len(path.parts))
    directory = configured / relative
    if len(directory.parts) > 64:
        raise HTTPException(422, 'Destination documentaire trop profonde')
    return root, directory, relative


def preview(db, project_id, artifact_id, choice, *, storage_root, policy=None):
    _project(db, project_id)  # BEFORE configuration, metadata or filesystem IO.
    jobs._ready(db, write=True)
    artifact = db.scalar(select(DocumentJobArtifact).where(DocumentJobArtifact.project_id == project_id,
                                                          DocumentJobArtifact.id == artifact_id))
    if artifact is None:
        raise HTTPException(404, 'Copie documentaire introuvable')
    job = jobs._job(db, project_id, artifact.job_id)
    item = db.scalar(select(DocumentJobItem).where(DocumentJobItem.id == artifact.item_id,
                                                   DocumentJobItem.job_id == job.id, DocumentJobItem.project_id == project_id))
    if item is None:
        raise HTTPException(409, 'Copie sans fichier de lot valide')
    jobs.artifact_content(db, project_id, artifact_id, storage_root=storage_root)
    filename = _name(artifact.filename)  # Always server-derived from the frozen copy.
    policy = configured_write_policy(project_id) if policy is None else policy
    root, directory, relative = _destination(db, project_id, choice, policy)
    source_destination = jobs.source_destination(item)
    updating_source = (source_destination is not None and source_destination['replace_existing']
                       and source_destination['link_id'] == choice.link_id
                       and source_destination['relative_directory'] == relative)
    expected_source = json.loads(item.snapshot)['preview']['source_sha256'] if updating_source else None
    with AnchoredDirectory(root, directory) as opened:
        occupied = opened.exists(filename)
        existing = opened.describe(filename) if choice.replace_existing and occupied else None
        replacement_supported = opened.native is not None
        capture = {'format':'agent-document-publication-preview','version':2,
            'project_id':project_id,'job_id':job.id,'job_revision':job.revision,'artifact_id':artifact.id,
            'document_id':item.document_id,'artifact_sha256':artifact.sha256,'size_bytes':artifact.size_bytes,
            'link_id':choice.link_id,'link_sha256':_link_sha256(db, project_id, choice.link_id),
            'relative_directory':relative,'directory':str(directory),'directory_identity':opened.identity,
            'filename':filename,'occupied':occupied,
            'replace_existing':choice.replace_existing,'existing_receipt':existing,
            'write_policy_sha256':jobs.frozen({'roots':policy.roots,'drive_mappings':policy.drive_mappings})[1]}
    blockers = []
    if current_operator().role == 'reader':
        blockers.append('read_only')
    if job.execution_blocked:
        blockers.append('execution_blocked')
    if job.status in {'queued','running'}:
        blockers.append('job_active')
    if occupied and not choice.replace_existing:
        blockers.append('destination_occupied')
    if choice.replace_existing and not occupied:
        blockers.append('replacement_target_missing')
    if choice.replace_existing and not replacement_supported:
        blockers.append('replacement_not_supported')
    if updating_source and (not occupied or (existing is not None and existing['sha256'] != expected_source)):
        blockers.append('source_changed')
    return {**capture,'preview_sha256':jobs.frozen(capture)[1],'destination':str(directory / filename),
            'can_publish':not blockers,'blockers':blockers,'read_only':True,'network_published':False}
