"""Reviewed Notes -> ERP report + Brain truth; recoverable across both stores."""
from datetime import datetime, timezone
import hashlib
import json
from uuid import NAMESPACE_URL, uuid5

from fastapi import HTTPException
from sqlalchemy import select

from app.meeting_session_models import MeetingSessionCommand
from app.models import AuditLog, KnowledgeItem, ProvenanceLink, Source, SourceArtifact
from backend.app.project_note_schemas import NoteContent, content_text
from backend.app.services.project_operator import current_operator
from . import meeting_sessions as sessions
from .meeting_audio import summary_markdown
from .projections import enqueue


def _id(sid, suffix):
    return str(uuid5(NAMESPACE_URL, 'agent:notes-publication:' + sid + ':' + suffix))


def _snapshot(row, payload):
    from backend.app.db import SessionLocal as ERP
    from backend.app.project_note_models import NoteVersion
    from backend.app.services import project_notes as notes
    with ERP() as erp:
        notes._lock(erp)
        note = notes.read_note(erp, row.project_id, row.note_id)
        if (note['revision'], note['version_id']) != (payload['expected_note_revision'], payload['expected_note_version_id']):
            raise HTTPException(409, 'La note a changé ; relire sa version avant publication.')
        version = erp.get(NoteVersion, note['version_id'])
        value = notes._value(version)
        blocks = NoteContent.model_validate(value['content']).blocks
        for kind in ('decisions', 'actions', 'open_points'):
            for item in payload['summary'][kind]:
                index = item['block_index']
                if index >= len(blocks) or item['quote'] not in content_text(NoteContent(blocks=[blocks[index]])):
                    raise HTTPException(422, 'Chaque élément doit citer exactement un bloc présent dans la note.')
        if not payload['summary']['overview'].strip() and not any(payload['summary'][k] for k in ('decisions', 'actions', 'open_points')):
            raise HTTPException(422, 'Compte rendu vide ; compléter la synthèse avant publication.')
        return {'note_id': row.note_id, 'note_version_id': version.id, 'note_revision': version.revision,
            'note_sha256': version.sha256, 'note': value, 'summary': payload['summary'],
            'title': row.title, 'date': row.date, 'project_id': row.project_id, 'brain_project_id': row.brain_project_id,
            'operator_id': current_operator().id}


def _erp_report(sid, frozen):
    from backend.app.db import SessionLocal as ERP
    from backend.app.models import Meeting, MeetingAction, Project
    report_id = _id(sid, 'report')
    action_ids = [_id(sid, f'action:{i}') for i in range(len(frozen['summary']['actions']))]
    markdown = summary_markdown(frozen['summary'])
    markdown += f"\n\nSource : note {frozen['note_id']}, version {frozen['note_version_id']}, révision {frozen['note_revision']}."
    with ERP() as erp:
        if erp.get(Project, frozen['project_id']) is None:
            raise HTTPException(409, 'Projet ERP introuvable ; publication conservée pour reprise.')
        report = erp.get(Meeting, report_id)
        if report:
            if (report.project_id, report.title, report.date, report.decisions) != (
                    frozen['project_id'], frozen['title'], frozen['date'], markdown):
                raise HTTPException(409, 'Compte rendu existant différent ; aucune modification écrasée.')
            for action_id in action_ids:
                action = erp.get(MeetingAction, action_id)
                if action is None or action.meeting_id != report_id or action.project_id != frozen['project_id']:
                    raise HTTPException(409, 'Action de publication manquante ; reprise manuelle requise.')
        else:
            erp.add(Meeting(id=report_id, project_id=frozen['project_id'], title=frozen['title'], date=frozen['date'],
                participants='', decisions=markdown))
            erp.flush()
            for i, item in enumerate(frozen['summary']['actions']):
                erp.add(MeetingAction(id=action_ids[i], meeting_id=report_id, project_id=frozen['project_id'],
                    title=item['text'], owner=item['owner'], due_date=item['due_date']))
            erp.commit()
    return report_id, action_ids


def _brain_report(db, row, frozen, meeting_id):
    source_id = _id(row.id, 'source')
    source = db.get(Source, source_id)
    metadata = {'origin_kind': 'published_erp_note', 'session_id': row.id, 'meeting_id': meeting_id,
        **{key: frozen[key] for key in ('note_id', 'note_version_id', 'note_revision', 'note_sha256')},
        'erp_project_id': frozen['project_id'], 'subject': frozen['title'], 'reviewed_by': frozen['operator_id']}
    if source is None:
        capsule = json.dumps({'session_id': row.id, 'note_version_id': frozen['note_version_id'],
            'note_sha256': frozen['note_sha256']}, sort_keys=True, separators=(',', ':'))
        source = Source(id=source_id, project_id=frozen['brain_project_id'], source_type='document', status='resolved',
            author=frozen['operator_id'], original_uri=f'agent-note-publication://{row.id}',
            sha256=hashlib.sha256(capsule.encode()).hexdigest(), mime_type='application/vnd.agent.note+json', source_metadata=metadata)
        db.add(source)
        db.flush()
        db.add(SourceArtifact(id=_id(row.id, 'artifact'), source_id=source_id, kind='published_note_text',
            content_text=frozen['note']['title'] + '\n' + frozen['note']['plain_text'],
            content_json={**metadata, 'content': frozen['note']['content']}))
    collections = [('meeting_summary', [{'text': summary_markdown(frozen['summary']), 'quote': frozen['note']['plain_text'], 'block_index': None}]),
        ('decision', frozen['summary']['decisions']), ('action', frozen['summary']['actions']), ('open_point', frozen['summary']['open_points'])]
    for kind, items in collections:
        for index, item in enumerate(items):
            kid = _id(row.id, f'{kind}:{index}')
            if db.get(KnowledgeItem, kid):
                continue
            value = item['text']
            if kind == 'action':
                value += f" — Responsable : {item.get('owner') or 'à définir'} ; échéance : {item.get('due_date') or 'à définir'}"
            db.add(KnowledgeItem(id=kid, project_id=frozen['brain_project_id'], kind=kind,
                subject=frozen['title'] if kind == 'meeting_summary' else item['text'][:512], value=value,
                created_by='meeting-notes', validated_by=frozen['operator_id'], validated_at=datetime.now(timezone.utc)))
            db.flush()
            db.add(ProvenanceLink(knowledge_item_id=kid, source_id=source_id,
                locator={**metadata, 'block_index': item['block_index'], 'quote': item['quote']},
                excerpt_hash=hashlib.sha256(item['quote'].encode()).hexdigest()))
            enqueue(db, frozen['brain_project_id'], 'truth', knowledge_id=kid)


def publish_notes(db, sid, body, *, after_erp_commit=None):
    row = sessions.get_session(db, sid, write=True)
    payload = body.model_dump(mode='json')
    with sessions._lock:
        previous = db.get(MeetingSessionCommand, payload['command_id'])
        if not previous:
            if not row.note_id or not row.project_id or not row.brain_project_id:
                raise HTTPException(409, 'Sauvegarder la note dans un projet avant publication.')
            other = db.scalar(select(MeetingSessionCommand).where(MeetingSessionCommand.session_id == sid,
                MeetingSessionCommand.kind == 'publish-notes', MeetingSessionCommand.status != 'rejected'))
            if other:
                raise HTTPException(409, 'Cette séance possède déjà une publication ; reprendre sa commande conservée.')
            frozen = _snapshot(row, payload)
        command = sessions._begin(db, row, 'publish-notes', payload, server_data={'_snapshot': frozen} if not previous else None)
        if command.status == 'completed':
            return {**command.result, 'replayed': True}
        frozen = command.body['_snapshot']
        try:
            meeting_id, action_ids = _erp_report(sid, frozen)
            if after_erp_commit:
                after_erp_commit()
            _brain_report(db, row, frozen, meeting_id)
            row.revision += 1
            row.updated_at = sessions.now()
            row.pending_command_id = None
            command.status, command.error = 'completed', None
            command.result = {'meeting_id': meeting_id, 'published_note_version_id': frozen['note_version_id']}
            sessions.append_event(db, row, 'notes.published', {'meeting_id': meeting_id, 'note_version_id': frozen['note_version_id']})
            db.add(AuditLog(event_type='meeting.notes.published.v1', project_id=frozen['brain_project_id'],
                actor=frozen['operator_id'], payload={'session_id': sid, 'meeting_id': meeting_id, 'note_version_id': frozen['note_version_id']}))
            result = {'session': sessions.serialize_session(db, row), 'meeting_id': meeting_id, 'action_ids': action_ids,
                'published_note_version_id': frozen['note_version_id'], 'replayed': False}
            command.result = result
            db.commit()
            return result
        except Exception as exc:
            db.rollback()
            command = db.get(MeetingSessionCommand, payload['command_id'])
            command.error = str(exc.detail)[:500] if isinstance(exc, HTTPException) else 'Publication interrompue ; reprendre la commande conservée.'
            db.commit()
            raise
