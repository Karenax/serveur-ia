"""Transactional L4 review commands. Readers never create drafts or publish audio.

The caller owns commit/rollback. One ERP planning lock serializes review commands
with task/milestone/deliverable commands; the review revision catches stale forms.
"""
import base64
from copy import deepcopy
import hashlib

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func

from app.db_support import utc_iso
from ..models import BrainLink, Milestone, Project
from ..project_identity_models import ProjectMember, uid, now
from ..project_review_models import ProjectReview, ReviewEvent, ReviewPublication
from ..project_review_schemas import ReviewContent
from .planning_revision import begin_change, revision
from .project_deliverable_rules import frozen_json
from .project_deliverables import read_deliverable
from .project_identity import _person, _project

SECTIONS = (
    {'code': 'vigilance_points', 'label': 'Points de vigilance', 'required': True},
    {'code': 'expected_functions', 'label': 'Fonctions attendues', 'required': True},
    {'code': 'initial_constraints', 'label': 'Contraintes initiales', 'required': True},
    {'code': 'decisions', 'label': 'Décisions', 'required': False},
    {'code': 'actions', 'label': 'Actions', 'required': False},
)


def catalogue():
    # Only operational types are actionable. The catalogue can grow when the
    # six other XPilot trames have actually been defined and qualified.
    return [{'code': 'rlp', 'label': 'Revue de lancement de projet', 'sections': deepcopy(list(SECTIONS))}]


def _review(db, project_id, review_id):
    _project(db, project_id)
    row = db.query(ProjectReview).filter_by(id=review_id, project_id=project_id).first()
    if not row:
        raise HTTPException(404, 'Revue introuvable dans ce projet')
    return row


def _latest(db, project_id):
    return db.query(ProjectReview).filter_by(project_id=project_id, type_code='rlp').order_by(ProjectReview.number.desc()).first()


def _value(row):
    return {'id': row.id, 'number': row.number, 'type_code': row.type_code, 'status': row.status,
            'review_revision': row.revision, 'previous_review_id': row.previous_review_id,
            'content': deepcopy(row.content), 'provenance': deepcopy(row.provenance)}


def read_review(db, project_id, review_id):
    row = _review(db, project_id, review_id)
    publication = db.query(ReviewPublication).filter_by(review_id=row.id, project_id=project_id).first()
    return {**_value(row), 'project_id': project_id, 'revision': revision(db, project_id),
            'can_edit': _project(db, project_id).role != 'reader' and row.status == 'draft',
            'can_create_revision': (_project(db, project_id).role != 'reader'
                                    and row.status == 'published' and _latest(db, project_id).id == row.id),
            'created_at': utc_iso(row.created_at), 'updated_at': utc_iso(row.updated_at),
            'publication': {'id': publication.id, 'sha256': publication.sha256,
                            'pdf_sha256': publication.pdf_sha256, 'created_at': utc_iso(publication.created_at)}
            if publication else None, 'publication_blockers': publication_blockers(db, project_id, row)}


def list_reviews(db, project_id, *, offset=0, limit=50):
    actor = _project(db, project_id)
    if not 0 <= offset <= 1000000 or not 1 <= limit <= 200:
        raise HTTPException(422, 'Pagination de revues invalide')
    query = db.query(ProjectReview).filter_by(project_id=project_id).order_by(ProjectReview.number.desc())
    return {'items': [{'id': row.id, 'number': row.number, 'status': row.status,
                       'review_revision': row.revision, 'meeting_date': row.content['meeting_date'],
                       'participants': len(row.content['participants']), 'updated_at': utc_iso(row.updated_at)}
                      for row in query.offset(offset).limit(limit)],
            'total': query.count(), 'offset': offset, 'limit': limit, 'revision': revision(db, project_id),
            'can_edit': actor.role != 'reader'}


def _validate_content(db, project_id, content, provenance):
    values = content.model_dump()
    for participant in values['participants']:
        person = _person(db, participant['person_id'])
        if person:
            # Names displayed at publication are snapshots of trusted identity.
            participant['name'] = f'{person.first_name} {person.last_name}'.strip()
            participant['function'] = person.function
    if content.milestone_id:
        milestone = db.query(Milestone).filter_by(id=content.milestone_id, project_id=project_id).first()
        if not milestone:
            raise HTTPException(422, 'Jalon de revue étranger au projet')
    for identity in content.deliverable_ids:
        if not read_deliverable(db, project_id, identity)['active']:
            raise HTTPException(409, 'Un livrable de la revue est archivé')
    for item in content.items:
        if any(key not in provenance for key in item.evidence_ids):
            raise HTTPException(422, 'Preuve de revue inconnue : importer sa réunion avant de la citer')
    return values


def _event(db, actor, state, row, action, previous):
    db.flush()
    db.add(ReviewEvent(project_id=row.project_id, review_id=row.id, planning_revision=state.revision,
                       actor_id=actor.id, action=action, previous=previous, value=_value(row)))


def create_review(db, project_id, payload):
    actor, state = begin_change(db, project_id, payload.expected_revision)
    latest = _latest(db, project_id)
    if latest:
        raise HTTPException(409, 'Une RLP existe déjà : ouvrir son brouillon ou créer une nouvelle révision')
    row = ProjectReview(project_id=project_id, type_code=payload.type_code, number=1, actor_id=actor.id,
                        content=_validate_content(db, project_id, payload.content, {}), provenance={})
    db.add(row)
    _event(db, actor, state, row, 'review_created', {})
    return read_review(db, project_id, row.id)


def _lock(db, project_id, review_id, payload, *, published=False):
    actor, state = begin_change(db, project_id, payload.expected_revision)
    row = _review(db, project_id, review_id)
    if row.revision != payload.expected_review_revision:
        raise HTTPException(409, 'La revue a changé : recharger avant de modifier')
    if row.status != ('published' if published else 'draft'):
        raise HTTPException(409, 'Révision figée : créer une nouvelle révision' if not published else 'Publier avant de créer une révision')
    return actor, state, row


def save_review(db, project_id, review_id, payload):
    actor, state, row = _lock(db, project_id, review_id, payload)
    previous = _value(row)
    row.content = _validate_content(db, project_id, payload.content, row.provenance)
    row.revision += 1
    row.updated_at = now()
    _event(db, actor, state, row, 'review_saved', previous)
    return read_review(db, project_id, row.id)


def create_revision(db, project_id, review_id, payload):
    actor, state, previous = _lock(db, project_id, review_id, payload, published=True)
    latest = _latest(db, project_id)
    if latest.id != previous.id:
        raise HTTPException(409, 'Une révision plus récente existe déjà')
    row = ProjectReview(project_id=project_id, type_code='rlp', number=previous.number + 1,
                        content=deepcopy(previous.content), provenance=deepcopy(previous.provenance),
                        previous_review_id=previous.id, actor_id=actor.id)
    db.add(row)
    _event(db, actor, state, row, 'review_revision_created', {'previous_review_id': previous.id})
    return read_review(db, project_id, row.id)


def publication_blockers(db, project_id, row):
    if row.status == 'published':
        return []
    content = ReviewContent.model_validate(row.content)
    blockers = []
    if not content.meeting_date:
        blockers.append('Date de réunion requise')
    if not content.participants:
        blockers.append('Au moins un participant requis')
    if not db.query(ProjectMember.id).filter_by(project_id=project_id, active=True).first():
        blockers.append('Équipe projet à compléter')
    if not content.deliverable_ids:
        blockers.append('Au moins un livrable actif à sélectionner')
    for identity in content.deliverable_ids:
        if not read_deliverable(db, project_id, identity)['active']:
            blockers.append('Un livrable sélectionné est archivé')
    sections = {item.section_code for item in content.items}
    blockers.extend(f"Section à compléter : {section['label']}" for section in SECTIONS
                    if section['required'] and section['code'] not in sections)
    if any(not item.reviewed for item in content.items):
        blockers.append('Vérifier chaque point avant publication')
    return blockers


def publish_review(db, project_id, review_id, payload, *, pdf_builder=None):
    actor, state, row = _lock(db, project_id, review_id, payload)
    previous = _value(row)
    _validate_content(db, project_id, ReviewContent.model_validate(row.content), row.provenance)
    blockers = publication_blockers(db, project_id, row)
    if blockers:
        raise HTTPException(409, detail={'message': 'Revue incomplète', 'blockers': blockers})
    project = db.get(Project, project_id)
    publication_id = uid()
    stamp = now()
    snapshot = {'format': 'agent-project-review', 'version': 1, 'publication_id': publication_id,
                'project': {'id': project.id, 'code': project.code, 'title': project.title},
                'review': _value(row), 'published_by': actor.id, 'published_at': utc_iso(stamp),
                'deliverables': [read_deliverable(db, project_id, key) for key in row.content['deliverable_ids']],
                'team': [{'person_id': member.person_id, 'role': member.role,
                          'name': f'{_person(db, member.person_id).first_name} {_person(db, member.person_id).last_name}'.strip()}
                         for member in db.query(ProjectMember).filter_by(project_id=project_id, active=True).order_by(ProjectMember.id)]}
    snapshot['review']['status'] = 'published'
    snapshot['review']['review_revision'] = row.revision + 1
    encoded, digest = frozen_json(snapshot)
    if pdf_builder is None:
        from .project_review_pdf import build_pdf
        pdf_builder = build_pdf
    document = pdf_builder(snapshot)
    if not isinstance(document, bytes) or not document.startswith(b'%PDF-') or len(document) > 10 * 1024 * 1024:
        raise HTTPException(503, 'Document PDF invalide ou trop volumineux ; brouillon conservé')
    publication = ReviewPublication(id=publication_id, project_id=project_id, review_id=row.id,
                                    snapshot=encoded, sha256=digest, pdf_base64=base64.b64encode(document).decode('ascii'),
                                    pdf_sha256=hashlib.sha256(document).hexdigest(), actor_id=actor.id, created_at=stamp)
    db.add(publication)
    row.status = 'published'
    row.revision += 1
    row.updated_at = stamp
    _event(db, actor, state, row, 'review_published', previous)
    return read_review(db, project_id, row.id)


def publication(db, project_id, review_id):
    _review(db, project_id, review_id)
    row = db.query(ReviewPublication).filter_by(project_id=project_id, review_id=review_id).first()
    if not row:
        raise HTTPException(404, 'Révision non publiée')
    try:
        pdf = base64.b64decode(row.pdf_base64, validate=True)
        if (hashlib.sha256(pdf).hexdigest() != row.pdf_sha256
                or hashlib.sha256(row.snapshot.encode('utf-8')).hexdigest() != row.sha256):
            raise ValueError('hash')
    except ValueError as exc:
        raise HTTPException(409, 'Publication altérée : vérifier la sauvegarde') from exc
    return row, pdf


def import_recording(db, brain, project_id, review_id, payload):
    """Read Brain only; copy verified evidence into an editable ERP draft.

    Importing never edits the recording, creates a meeting/task or publishes a
    report. The captured revisions make later source changes visible, and the
    copied speaker excerpt remains available independently of those changes.
    """
    from app.models import MeetingRecording
    from app.services.meeting_audio import BUSY, _normal
    actor, state, row = _lock(db, project_id, review_id, payload)
    link = db.get(BrainLink, project_id)
    recording = brain.get(MeetingRecording, payload.recording_id)
    if (not link or not recording or recording.erp_project_id != project_id
            or recording.project_id != link.brain_project_id):
        raise HTTPException(404, 'Réunion introuvable dans ce projet')
    if (recording.job_status in BUSY or recording.stage == 'publishing'
            or recording.revision != payload.expected_recording_revision
            or recording.reviewed_revision != recording.revision or recording.summary_revision != recording.revision
            or not recording.summary):
        raise HTTPException(409, 'La synthèse doit correspondre à la transcription validée actuelle')
    original = _value(row)
    content, evidence = deepcopy(row.content), deepcopy(row.provenance)
    source = {'recording_id': recording.id, 'brain_project_id': recording.project_id,
              'erp_project_id': project_id, 'source_id': recording.source_id,
              'revision': recording.revision, 'summary_model': recording.summary_model,
              'summary_sha256': frozen_json(recording.summary)[1]}
    # A repeated request with a fresh ERP revision remains idempotent. Later
    # re-analysis/revision is a distinct import and retains the older evidence.
    if any(all(value.get(key) == item for key, item in source.items()) for value in evidence.values()):
        raise HTTPException(409, 'Cette synthèse a déjà été importée ; ses preuves sont conservées')
    segments = {segment['id']: segment for segment in recording.segments}
    for kind, section in (('decisions', 'decisions'), ('actions', 'actions'), ('open_points', 'vigilance_points')):
        for proposed in recording.summary.get(kind, []):
            segment = segments.get(proposed.get('segment_id'))
            quote = proposed.get('quote', '')
            if not segment or not quote.strip() or _normal(quote) not in _normal(segment['text']):
                raise HTTPException(409, 'Citation de synthèse absente de la transcription')
            key = uid()
            evidence[key] = {**source, 'segment_id': segment['id'], 'quote': quote,
                             'text': segment['text'], 'speaker': recording.speaker_names.get(segment['speaker'], segment['speaker']),
                             'start': segment['start'], 'end': segment['end']}
            content['items'].append({'id': uid(), 'section_code': section, 'text': proposed['text'],
                                     'reviewed': False, 'evidence_ids': [key],
                                     'owner': proposed.get('owner', ''), 'due_date': proposed.get('due_date', '')})
    if not evidence or evidence == row.provenance:
        raise HTTPException(409, 'La synthèse ne contient aucun point sourcé à importer')
    # The overview is also labelled as a source proposal, never a silent
    # replacement of the user's notes. Each evidence retains its model/hash.
    if recording.summary.get('overview'):
        content['notes'] = '\n\n'.join(value for value in (content['notes'],
            f"Proposition issue de la réunion {recording.title} (à vérifier) :\n{recording.summary['overview']}") if value)
    content['meeting_date'] = content['meeting_date'] or recording.date
    try:
        normalized = ReviewContent.model_validate(content)
    except ValidationError as exc:
        raise HTTPException(422, 'Import trop volumineux ou synthèse invalide ; brouillon conservé') from exc
    row.content = _validate_content(db, project_id, normalized, evidence)
    row.provenance = evidence
    row.revision += 1
    row.updated_at = now()
    _event(db, actor, state, row, 'review_recording_imported', original)
    return read_review(db, project_id, row.id)


def history(db, project_id, review_id, *, offset=0, limit=50):
    _review(db, project_id, review_id)
    if not 0 <= offset <= 1000000 or not 1 <= limit <= 200:
        raise HTTPException(422, 'Pagination invalide')
    query = db.query(ReviewEvent).filter_by(project_id=project_id, review_id=review_id).order_by(ReviewEvent.planning_revision.desc())
    return {'items': [{'id': row.id, 'action': row.action, 'actor_id': row.actor_id,
                       'planning_revision': row.planning_revision, 'created_at': utc_iso(row.created_at)}
                      for row in query.offset(offset).limit(limit)], 'total': query.count(),
            'offset': offset, 'limit': limit, 'revision': revision(db, project_id)}


def history_detail(db, project_id, review_id, event_id):
    _review(db, project_id, review_id)
    event = db.query(ReviewEvent).filter_by(project_id=project_id, review_id=review_id, id=event_id).first()
    if not event:
        raise HTTPException(404, 'Événement introuvable dans cette revue')
    return {'id': event.id, 'action': event.action, 'actor_id': event.actor_id,
            'planning_revision': event.planning_revision, 'created_at': utc_iso(event.created_at),
            'previous': deepcopy(event.previous), 'value': deepcopy(event.value), 'bindings': deepcopy(event.bindings)}


def recording_choices(db, brain, project_id, *, offset=0, limit=25):
    """Bounded scalar read, with the same ownership/revision gate as import.

    Transcripts and summaries are fetched only when an operator opens a source.
    The import command rechecks eligibility; listing never locks or mutates Brain.
    """
    from app.models import MeetingRecording
    from app.services.meeting_audio import BUSY
    _project(db, project_id)
    if not 0 <= offset <= 1000000 or not 1 <= limit <= 100:
        raise HTTPException(422, 'Pagination de réunions invalide')
    link = db.get(BrainLink, project_id)
    if not link:
        return {'items': [], 'total': 0, 'offset': offset, 'limit': limit}
    query = brain.query(MeetingRecording).filter(
        MeetingRecording.erp_project_id == project_id,
        MeetingRecording.project_id == link.brain_project_id,
        MeetingRecording.reviewed_revision == MeetingRecording.revision,
        MeetingRecording.summary_revision == MeetingRecording.revision,
        func.json_type(MeetingRecording.summary) == 'object', MeetingRecording.summary != {},
        MeetingRecording.job_status.notin_(BUSY), MeetingRecording.stage != 'publishing')
    columns = (MeetingRecording.id, MeetingRecording.title, MeetingRecording.date,
               MeetingRecording.revision, MeetingRecording.summary_model)
    rows = query.with_entities(*columns).order_by(MeetingRecording.created_at.desc(), MeetingRecording.id).offset(offset).limit(limit)
    return {'items': [{'id': row.id, 'title': row.title, 'date': row.date, 'revision': row.revision,
                       'summary_model': row.summary_model} for row in rows],
            'total': query.count(), 'offset': offset, 'limit': limit}
