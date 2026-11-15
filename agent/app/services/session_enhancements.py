"""Additions only: cited suggestions never replace existing human note blocks."""
import json
import re
import unicodedata
import urllib.error
from uuid import NAMESPACE_URL, uuid5

from fastapi import HTTPException
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool
from contextlib import nullcontext

from ..meeting_session_models import MeetingSessionEvent
from ..meeting_session_schemas import SessionNoteSave
from . import meeting_sessions as sessions, scoped_assistant as assistant


def _events(db, row, kind):
    return list(db.scalars(select(MeetingSessionEvent).where(MeetingSessionEvent.session_id == row.id,
                MeetingSessionEvent.kind == kind).order_by(MeetingSessionEvent.id.desc()).limit(1000)))


def _find(db, row, kind, identity):
    return db.scalar(select(MeetingSessionEvent).where(MeetingSessionEvent.session_id == row.id,
        MeetingSessionEvent.kind == kind, MeetingSessionEvent.data['id'].as_string() == identity)
        .order_by(MeetingSessionEvent.id.desc()).limit(1))


def list_proposals(db, row):
    db.refresh(row)
    sessions.get_session(db, row.id)
    decisions = {event.data['id']: event.data['decision'] for event in reversed(_events(db, row, 'enhancement.decision'))}
    items = []
    for event in _events(db, row, 'enhancement.proposed')[:100]:
        value = dict(event.data)
        if not assistant.answer_visible(db, value):
            continue
        value['status'] = decisions.get(value['id'], value['status'])
        if value['status'] == 'pending' and not assistant.context_current(db, row, value):
            value['status'] = 'obsolete'
        items.append(value)
    from .session_proactive import automatic_status
    result = {'items': items, 'automatic': automatic_status(db, row)}
    # Snapshot/freshness checks refresh ORM rows. Revalidate the scope after
    # them so a concurrent project move cannot reveal old excerpts on replay.
    db.refresh(row)
    sessions.get_session(db, row.id)
    result['items'] = [item for item in result['items'] if assistant.answer_visible(db, item)]
    return result


def _addition_evidence(citations, sid):
    def current_note(citation):
        locator = citation.get('locator') or {}
        return (locator.get('session_id') == sid and locator.get('note_version_id')
                and 'block' in locator)
    notes = [citation for citation in citations if current_note(citation)]
    return ([citation for citation in citations if not current_note(citation)],
            '\n'.join(citation['excerpt'] for citation in notes))


def _addition_response_format(citations):
    references = sorted({citation['reference'] for citation in citations})
    if not references:
        raise ValueError('Aucune preuve distincte de la note')
    item = {'type': 'object', 'additionalProperties': False,
            'required': ['text', 'reference', 'quote'],
            'properties': {'text': {'type': 'string', 'minLength': 1, 'maxLength': 4500},
                           'reference': {'type': 'string', 'enum': references},
                           'quote': {'type': 'string', 'minLength': 3, 'maxLength': 3000}}}
    schema = {'type': 'object', 'additionalProperties': False, 'required': ['additions'],
              'properties': {'additions': {'type': 'array', 'maxItems': 12, 'items': item}}}
    return {'type': 'json_schema', 'json_schema': {
        'name': 'meeting_note_additions', 'strict': True, 'schema': schema}}


def _already_noted(text, note):
    def normalized(value):
        return re.sub(r'[^\w]+', ' ', unicodedata.normalize('NFKC', value).casefold()).strip()
    addition, existing = normalized(text), normalized(note)
    return bool(addition and f' {addition} ' in f' {existing} ')


def _prepare_addition_request(messages, metadata, sid, *, note_text=None):
    evidence, selected_note_text = _addition_evidence(metadata['citations'], sid)
    if note_text is None:  # Isolated short-fixture callers; production supplies the full snapshot.
        note_text = selected_note_text
    metadata = {**metadata, 'citations': evidence}
    messages = [dict(message) for message in messages]
    excerpts = '\n\n'.join(f"[{c['reference']}] ({c['level']}) {c['title']}\n{c['excerpt']}" for c in evidence)
    messages[-1]['content'] = ('Question : Décisions, actions, réserves et points ouverts à ajouter à la note'
        + '\n\nNote existante à conserver (comparaison uniquement, aucune référence citable) :\n'
        + selected_note_text + '\n\nExtraits :\n' + excerpts)
    instructions = (
        ' Propose uniquement des ajouts utiles absents de la note, jamais une réécriture. '
        'Retourne seulement JSON {"additions":[{"text":"...","reference":"C1","quote":"citation verbatim"}]}. '
        'Maximum 12 ajouts. Chaque quote doit être une sous-chaîne exacte de son extrait. '
        'Conserve chiffres, unités, négations, réserves et incertitudes ; ne transforme pas une proposition en décision.'
        ' Compare chaque ajout à tous les blocs de la note existante ; écarte toute reformulation d’une information déjà notée. '
        'Quand une transcription existe, privilégie ses tâches, responsables et dates absents de la note. '
        'N’ajoute pas une réserve déjà présente. Si aucun ajout nouveau n’est utile, retourne {"additions":[]}.')
    if not messages[0]['content'].endswith(instructions):
        messages[0]['content'] += instructions
    return messages, metadata, note_text, _addition_response_format(evidence) if evidence else None


def _validate_addition_reply(raw, metadata, note_text):
    value = json.loads(raw.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip())
    if not isinstance(value, dict) or set(value) != {'additions'}:
        raise ValueError('Objet additions invalide')
    additions = value['additions']
    if not isinstance(additions, list) or len(additions) > 12:
        raise ValueError('Maximum 12 ajouts ; réponse refusée sans suppression arbitraire')
    citations = {c['reference']: c for c in metadata['citations']}
    blocks = []
    used = []
    for item in additions:
        if set(item) != {'text', 'reference', 'quote'} or not all(isinstance(v, str) for v in item.values()):
            raise ValueError('Format d’ajout invalide')
        citation = citations.get(item['reference'])
        if not citation or len(item['quote'].strip()) < 3 or item['quote'] not in citation['excerpt']:
            raise ValueError('Citation non vérifiable')
        if not item['text'].strip() or len(item['text']) > 4500:
            raise ValueError('Texte d’ajout invalide')
        if any(_already_noted(item['text'], previous['text'])
               and _already_noted(previous['text'], item['text']) for previous in additions[:len(blocks)]):
            raise ValueError('Ajouts identiques dans une même réponse')
        if _already_noted(item['text'], note_text):
            raise ValueError('Ajout déjà présent dans la note')
        blocks.append({'type': 'paragraph', 'runs': [{'text': item['text'] + f" [{item['reference']}]"}]})
        used.append({**citation, 'quote': item['quote']})
    return additions, blocks, used


async def propose(db, row, *, automatic=False, expected_stamp=None):
    sessions.require_enabled(db)
    db.refresh(row)
    row = sessions.get_session(db, row.id, write=True)
    from .ai_client import chat_text
    from .inference_scheduler import InferenceBusy, priority_scope, wait_policy
    from .llm_activity import Deferred
    cfg, messages, metadata = await assistant.prepare(db, row, query='Décisions, actions, réserves et points ouverts à ajouter à la note', scope='session')
    db.refresh(row)
    sessions.get_session(db, row.id, write=True)
    if expected_stamp is not None and metadata['session_stamp'] != expected_stamp:
        raise HTTPException(409, 'Le contexte enregistré a changé avant l’enrichissement ; attendre sa nouvelle stabilisation')
    identity = str(uuid5(NAMESPACE_URL, f'enhancement:{row.id}:{metadata["session_stamp"]}'))
    previous = _find(db, row, 'enhancement.proposed', identity)
    if previous:
        cached = next((item for item in list_proposals(db, row)['items'] if item['id'] == identity), None)
        if cached is None:
            raise HTTPException(404, 'Suggestion indisponible dans votre périmètre')
        return cached
    if not metadata['citations']:
        raise HTTPException(409, 'Aucun passage disponible pour une amélioration sourcée')
    from backend.app.project_note_schemas import NoteContent, content_text
    note_stamp, note_snapshot, _ = assistant.session_snapshot(db, row)
    if note_stamp != metadata['session_stamp']:
        raise HTTPException(409, 'La note ou la transcription a changé ; relancer depuis la version enregistrée')
    full_note_text = content_text(NoteContent.model_validate(note_snapshot['content'])) if note_snapshot else ''
    messages, metadata, note_text, response_format = _prepare_addition_request(
        messages, metadata, row.id, note_text=full_note_text)
    evidence = metadata['citations']
    structured = (cfg.get('provider') or '').lower() == 'openai_compatible' and bool(evidence)
    def generate():
        with priority_scope('enhancement' if automatic else 'manual'), (
                nullcontext() if automatic else wait_policy(timeout=900)):
            # Structured suggestions use one transport and never repeat a reply.
            active_cfg = {**cfg, 'fallback_enabled': False, 'fallback_autostart': False} if automatic else cfg
            options = {'raise_errors': True}
            if automatic:
                options.update(timeout=600, retry_empty=False)
            if structured:
                options.update(retry_empty=False, response_format=response_format)
            return chat_text(active_cfg, messages, max_tokens=1800, **options)
    try:
        raw = await run_in_threadpool(generate) if evidence else '{"additions":[]}'
    except (InferenceBusy, Deferred) as exc:
        if automatic:
            raise
        raise HTTPException(503, 'Le moteur IA traite une autre demande. Vos notes sont conservées ; réessayez dans quelques instants.') from exc
    except urllib.error.HTTPError as exc:
        if structured and exc.code in {400, 404, 422}:
            raise HTTPException(502, 'Le serveur IA a refusé le format demandé. Aucun ajout n’a été appliqué ; vos notes sont conservées.') from exc
        raise
    if not raw:
        raise HTTPException(502, 'Le moteur IA n’a renvoyé aucune proposition. Vos notes sont conservées ; réessayez.')
    try:
        additions, blocks, used = _validate_addition_reply(raw, metadata, note_text)
        from backend.app.project_note_schemas import NoteContent
        content = NoteContent.model_validate({'blocks': blocks}).model_dump(mode='json')
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        detail = ('La suggestion reprend un ajout déjà présent dans votre note. Aucun ajout n’a été appliqué.'
                  if str(exc) == 'Ajout déjà présent dans la note'
                  else 'La suggestion IA contient un format ou une citation invalide')
        raise HTTPException(502, detail) from exc
    db.expire_all()
    db.refresh(row)
    sessions.get_session(db, row.id, write=True)
    _, note, _ = assistant.session_snapshot(db, row)
    result = {'id': identity, **metadata, 'citations': used, 'content': content,
              'text': '\n'.join(item['text'] for item in additions),
              'note_revision': note.get('revision') if note else None,
              'note_version_id': note.get('version_id') if note else None,
              'created_at': sessions.now().isoformat(),
              'status': 'pending' if assistant.context_current(db, row, metadata) else 'obsolete'}
    with sessions._lock:
        from sqlalchemy import text
        db.execute(text('UPDATE meeting_sessions SET revision=revision WHERE 0'))
        db.refresh(row)
        sessions.get_session(db, row.id, write=True)
        if not assistant.answer_visible(db, result):
            raise HTTPException(404, 'Suggestion indisponible dans votre périmètre')
        existing = _find(db, row, 'enhancement.proposed', identity)
        if existing:
            cached = dict(existing.data)
            if not assistant.answer_visible(db, cached):
                raise HTTPException(404, 'Suggestion indisponible dans votre périmètre')
            if cached['status'] == 'pending' and not assistant.context_current(db, row, cached):
                cached['status'] = 'obsolete'
            return cached
        if not assistant.context_current(db, row, metadata):
            result['status'] = 'obsolete'
        sessions.append_event(db, row, 'enhancement.proposed', result)
        db.commit()
        return result


def decide(db, row, proposal_id, decision, expected_revision):
    # The one-process API serializes the entire decision, including its ERP
    # Notes saga, under the shared reentrant lock. All callers use this entry
    # point. Independent API processes would need a durable decision claim.
    with sessions._lock:
        return _decide(db, row, proposal_id, decision, expected_revision)


def _decide(db, row, proposal_id, decision, expected_revision):
    sessions.require_enabled(db)
    db.refresh(row)
    row = sessions.get_session(db, row.id, write=True)
    if decision not in {'accept', 'reject'}:
        raise HTTPException(422, 'Décision de suggestion invalide')
    previous_event = _find(db, row, 'enhancement.decision', proposal_id)
    previous = previous_event.data if previous_event else None
    if previous:
        if previous['decision'] != ('accepted' if decision == 'accept' else 'rejected'):
            raise HTTPException(409, 'Cette suggestion a déjà reçu une autre décision')
        db.refresh(row)
        sessions.get_session(db, row.id, write=True)
        return sessions.serialize_session(db, row)
    proposal = _find(db, row, 'enhancement.proposed', proposal_id)
    value = proposal.data if proposal else None
    if value is None:
        raise HTTPException(404, 'Suggestion introuvable')
    if not assistant.answer_visible(db, value):
        raise HTTPException(404, 'Suggestion indisponible dans votre périmètre')
    # Resolve a crash after note commit by checking its durable command before
    # freshness (the successful save necessarily changed the old base).
    command_id = str(uuid5(NAMESPACE_URL, f'enhancement-accept:{row.id}:{proposal_id}'))
    from ..meeting_session_models import MeetingSessionCommand
    receipt = db.get(MeetingSessionCommand, command_id)
    if receipt and receipt.status == 'prepared':
        if decision != 'accept':
            raise HTTPException(409, 'Un ajout conservé doit être repris avant de le refuser')
        sessions.execute_command(db, row.id, 'notes', SessionNoteSave.model_validate(receipt.body))
        db.refresh(row)
        db.refresh(receipt)
    replayed = bool(receipt and receipt.status == 'completed')
    if not replayed and row.revision != expected_revision:
        raise HTTPException(409, 'La séance a évolué ; le brouillon est conservé')
    if decision == 'accept' and not replayed:
        if not (value.get('content') or {}).get('blocks'):
            raise HTTPException(409, 'Aucun ajout utile à appliquer ; la note est conservée')
        if value['status'] != 'pending' or not assistant.context_current(db, row, value):
            raise HTTPException(409, 'Suggestion périmée ; régénérer depuis la note actuelle')
        _, note, _ = assistant.session_snapshot(db, row)
        current = note['content'] if note else {'version': 1, 'blocks': []}
        from backend.app.project_note_schemas import NoteContent
        content = NoteContent.model_validate({**current, 'blocks': [*current['blocks'], *value['content']['blocks']]})
        sessions.execute_command(db, row.id, 'notes', SessionNoteSave(command_id=command_id,
            expected_revision=expected_revision, title=note['title'] if note else row.title, content=content,
            expected_note_revision=note.get('revision') if note else None,
            expected_note_version_id=note.get('version_id') if note else None))
        db.refresh(row)
    with sessions._lock:
        from sqlalchemy import text
        db.execute(text('UPDATE meeting_sessions SET revision=revision WHERE 0'))
        db.refresh(row)
        sessions.get_session(db, row.id, write=True)
        existing = _find(db, row, 'enhancement.decision', proposal_id)
        if decision == 'reject' and not existing and row.revision != expected_revision:
            raise HTTPException(409, 'La séance a évolué ; relire la suggestion avant de décider')
        if not assistant.answer_visible(db, value):
            raise HTTPException(404, 'Suggestion indisponible dans votre périmètre')
        resolved = 'accepted' if decision == 'accept' else 'rejected'
        if existing and existing.data['decision'] != resolved:
            raise HTTPException(409, 'Cette suggestion a déjà reçu une autre décision')
        if not existing:
            sessions.append_event(db, row, 'enhancement.decision', {'id': proposal_id,
                'decision': resolved, 'command_id': command_id if decision == 'accept' else None})
            db.commit()
        return sessions.serialize_session(db, row)
