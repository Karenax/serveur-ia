"""Closed publication journal contract. Pure validation; never filesystem IO.

Captures remain verbatim across imports. The latest import event carries current
artifact/link bindings separately, so historical destinations never authorize IO.
"""
import json
import re
from pathlib import PurePosixPath, PureWindowsPath

from app.services.deliverable_manifest import freeze
from ..project_document_publication_schemas import DocumentPublicationCommand, DocumentPublicationAbandon
from .document_paths import _relative
from .project_document_archive import identity

KINDS = {'publication_requested', 'publication_prepared', 'publication_succeeded',
         'publication_backup_requested', 'publication_backup_saved','publication_abandoned'}
CAPTURE_KEYS = {'format', 'version', 'project_id', 'job_id', 'job_revision', 'artifact_id',
                'document_id', 'artifact_sha256', 'size_bytes', 'link_id', 'link_sha256',
                'relative_directory', 'directory', 'directory_identity', 'filename', 'occupied',
                'write_policy_sha256'}
V2_CAPTURE_KEYS = CAPTURE_KEYS | {'replace_existing', 'existing_receipt'}


def capture_keys(version):
    return V2_CAPTURE_KEYS if version == 2 else CAPTURE_KEYS


def command_body(command, version):
    body = command.model_dump()
    if version == 1 and command.link_to_project:
        raise ValueError('Rattachement absent de ce format de publication')
    if version == 1 and body.get('replace_existing') is False:
        body.pop('replace_existing')
    return body


def _digest(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError('Empreinte de publication invalide')


def _file_identity(value):
    if not isinstance(value, str) or len(value) > 100 or not re.fullmatch(r'(?:nt:[0-9]+:[0-9a-f]{32}|posix:[0-9]+:[0-9]+)', value):
        raise ValueError('Identité de publication invalide')
    if value.startswith('nt:') and value.endswith(':' + '0' * 32):
        raise ValueError('Identité de publication nulle')


def _receipt(value, capture):
    if not isinstance(value, dict) or set(value) != {'identity', 'sha256', 'size_bytes'}:
        raise ValueError('Reçu de publication fermé requis')
    _file_identity(value['identity'])
    if (type(value['size_bytes']) is not int or value['size_bytes'] != capture['size_bytes']
            or value['sha256'] != capture['artifact_sha256']):
        raise ValueError('Reçu différent de la copie documentaire')


def validate(events, *, job, artifacts, items, imported=None):
    """Return command states with current bindings; reject impossible chains."""
    records = {}
    candidates = set()
    backups = set()
    suspension = min((row['revision'] for row in events if row['kind'] in {'archive_imported', 'store_restored'}), default=None)
    if suspension is not None and any(row['kind'] in KINDS for row in events) and not job.get('execution_blocked'):
        raise ValueError('Publication historique sans suspension d’exécution')
    bindings = None if imported is None else imported.get('publication_bindings', {})
    if bindings is not None and not isinstance(bindings, dict):
        raise ValueError('Liaisons de publication invalides')
    for event in sorted(events, key=lambda row: row['revision']):
        kind = event['kind']
        if kind not in KINDS:
            continue
        if suspension is not None and event['revision'] > suspension:
            raise ValueError('Publication postérieure à l’import ou à la restauration')
        raw = event['detail']
        if not isinstance(raw, str) or len(raw.encode()) > 4 * 1024 * 1024:
            raise ValueError('Événement de publication non borné')
        detail = json.loads(raw)
        if not isinstance(detail, dict) or freeze(detail)[0] != raw:
            raise ValueError('Événement de publication non canonique')
        if kind == 'publication_requested':
            capture = detail.get('preview')
            if not isinstance(capture, dict) or type(capture.get('version')) is not int or capture['version'] not in {1,2}:
                raise ValueError('Version de publication invalide')
            expected_keys = {'command', 'command_sha256', 'preview', 'candidate'} | ({'backup'} if capture['version']==2 else set())
            if set(detail) != expected_keys:
                raise ValueError('Intention de publication fermée requise')
            command = command_body(DocumentPublicationCommand.model_validate(detail['command']), capture['version'])
            if command != detail['command'] or freeze(command)[1] != detail['command_sha256']:
                raise ValueError('Intention différente de son empreinte')
            cid = command['command_id']
            if cid in records:
                raise ValueError('Commande de publication dupliquée')
            if set(capture) != capture_keys(capture['version']):
                raise ValueError('Capture de publication fermée requise')
            replacement = capture.get('replace_existing',False)
            if type(replacement) is not bool or command.get('replace_existing',False) != replacement:
                raise ValueError('Choix de remplacement incohérent')
            if capture['version']==2:
                if replacement:
                    existing = capture['existing_receipt']
                    if not isinstance(existing, dict) or type(existing.get('size_bytes')) is not int or not 1<=existing['size_bytes']<=50*1024*1024:
                        raise ValueError('Reçu de l’original invalide')
                    _digest(existing.get('sha256'))
                    _receipt(existing, {'size_bytes':existing['size_bytes'],'artifact_sha256':existing['sha256']})
                    if not isinstance(detail['backup'],str) or not re.fullmatch(r'\.agent-backup-[0-9a-f]{32}\.bak',detail['backup']):
                        raise ValueError('Nom de sauvegarde invalide')
                    if detail['backup'] in backups:
                        raise ValueError('Nom de sauvegarde dupliqué')
                    backups.add(detail['backup'])
                elif capture['existing_receipt'] is not None or detail['backup'] is not None:
                    raise ValueError('Sauvegarde sans choix de remplacement')
            if (capture['format'] != 'agent-document-publication-preview' or type(capture['version']) is not int
                    or capture['occupied'] is not replacement
                    or type(capture['job_revision']) is not int or capture['job_revision'] < 1
                    or capture['job_revision'] != command['expected_revision']
                    or freeze(capture)[1] != command['expected_preview_sha256']
                    or capture['link_id'] != command['link_id']
                    or capture['relative_directory'] != command['relative_directory']
                    or _relative(capture['relative_directory']) != capture['relative_directory']):
                raise ValueError('Capture différente de la destination relue')
            for key in ('project_id', 'job_id', 'artifact_id', 'link_id'):
                identity(capture[key])
            for key in ('artifact_sha256', 'link_sha256', 'write_policy_sha256'):
                _digest(capture[key])
            _file_identity(capture['directory_identity'])
            directory = capture['directory']
            if (not isinstance(directory, str) or not 1 <= len(directory) <= 4096
                    or any(ord(char) < 32 for char in directory)
                    or not (PureWindowsPath(directory).is_absolute() or PurePosixPath(directory).is_absolute())):
                raise ValueError('Dossier de publication historique invalide')
            name = capture['filename']
            if not isinstance(name, str) or not 1 <= len(name) <= 255 or _relative(name) != name or '/' in name:
                raise ValueError('Nom de publication historique invalide')
            if not isinstance(detail['candidate'], str) or not re.fullmatch(r'\.agent-publish-[0-9a-f]{32}\.pending', detail['candidate']):
                raise ValueError('Candidat de publication invalide')
            if detail['candidate'] in candidates:
                raise ValueError('Candidat de publication dupliqué')
            candidates.add(detail['candidate'])
            binding = {'artifact_id':capture['artifact_id'], 'link_id':capture['link_id']} if bindings is None else bindings.get(cid)
            if not isinstance(binding, dict) or set(binding) != {'artifact_id', 'link_id'}:
                raise ValueError('Liaison de publication absente')
            identity(binding['link_id'])
            artifact = artifacts.get(binding['artifact_id'])
            item = None if artifact is None else items.get(artifact['item_id'])
            if (not artifact or artifact['job_id'] != job['id'] or not item
                    or capture['document_id'] != item['document_id']
                    or capture['filename'] != artifact['filename']
                    or capture['artifact_sha256'] != artifact['sha256']
                    or type(capture['size_bytes']) is not int or capture['size_bytes'] != artifact['size_bytes']):
                raise ValueError('Publication sans copie documentaire correspondante')
            if bindings is None:
                if (capture['project_id'] != job['project_id'] or capture['job_id'] != job['id']
                        or capture['job_revision'] != event['revision'] - 1):
                    raise ValueError('Publication étrangère au lot ou à sa révision')
            elif capture['project_id'] != json.loads(item['snapshot'])['preview']['source']['project_id']:
                raise ValueError('Publication étrangère au projet historique')
            records[cid] = {**detail, 'binding':binding, 'state':'requested', 'receipt':None, 'backup_receipt':None,
                            'requested_revision':event['revision'], 'updated_revision':event['revision']}
        else:
            if kind=='publication_abandoned':
                if set(detail)!={'command_id','expected_revision','retain_files','reviewed'} or detail['command_id'] not in records:
                    raise ValueError('Clôture de publication sans intention')
                ack = {key:value for key,value in detail.items() if key!='command_id'}
                if DocumentPublicationAbandon.model_validate(ack).model_dump()!=ack or ack['expected_revision']!=event['revision']-1:
                    raise ValueError('Clôture différente de sa confirmation ou révision')
                record=records[detail['command_id']]
                if record['state']!='requested':
                    raise ValueError('Clôture interdite après un reçu préparé')
                record.update(state='abandoned',abandon_command=ack,updated_revision=event['revision'])
                continue
            if set(detail) != {'command_id', 'receipt'} or detail['command_id'] not in records:
                raise ValueError('Reçu de publication sans intention')
            record = records[detail['command_id']]
            if kind in {'publication_backup_requested','publication_backup_saved'}:
                if not record['preview'].get('replace_existing') or detail['receipt'] != record['preview']['existing_receipt']:
                    raise ValueError('Sauvegarde différente de l’original relu')
                expected_state = 'prepared' if kind=='publication_backup_requested' else 'backup_requested'
                if record['state'] != expected_state:
                    raise ValueError('Séquence de sauvegarde incohérente')
                record['state'] = 'backup_requested' if kind=='publication_backup_requested' else 'backup_saved'
                record['backup_receipt'] = detail['receipt']
                record['updated_revision'] = event['revision']
                continue
            _receipt(detail['receipt'], record['preview'])
            if kind == 'publication_prepared':
                if record['preview'].get('replace_existing') and detail['receipt']['identity']==record['preview']['existing_receipt']['identity']:
                    raise ValueError('Candidat et original doivent être distincts')
                if record['state'] != 'requested':
                    raise ValueError('Préparation de publication dupliquée ou tardive')
                record.update(state='prepared', receipt=detail['receipt'])
            else:
                expected_state = 'backup_saved' if record['preview'].get('replace_existing') else 'prepared'
                if record['state'] != expected_state or detail['receipt'] != record['receipt']:
                    raise ValueError('Publication sans reçu préparé correspondant')
                record['state'] = 'succeeded'
            record['updated_revision'] = event['revision']
    if bindings is not None and set(bindings) != set(records):
        raise ValueError('Inventaire des liaisons de publication différent du journal')
    return records


def current_links(events, *, job, artifacts, items, imported=None):
    return {row['binding']['link_id'] for row in validate(events, job=job, artifacts=artifacts,
                                                       items=items, imported=imported).values()}


def for_job(ledger, job):
    events = [row for row in ledger['job_events'].values() if row['job_id'] == job['id']]
    imports = [row for row in events if row['kind'] == 'archive_imported']
    imported = json.loads(max(imports, key=lambda row:row['revision'])['detail']) if imports else None
    return validate(events, job=job, artifacts=ledger['job_artifacts'], items=ledger['job_items'], imported=imported)
