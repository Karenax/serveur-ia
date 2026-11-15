"""Scoped grounded answers, additive Notes retries and bounded proactive work."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import re
from threading import Barrier, Event
from uuid import NAMESPACE_URL, uuid4, uuid5

from fastapi import HTTPException
import pytest
from sqlalchemy import func, select

from app.meeting_session_models import LiveTranscriptSegment, MeetingSession, MeetingSessionCommand, MeetingSessionEvent
from app.meeting_session_schemas import SessionNoteSave
from app.models import KnowledgeItem, MemoryProjection, Project as BrainProject, Source, SourceArtifact
from app.services import scoped_assistant as assistant, session_enhancements as enhancements
from app.services import meeting_sessions as sessions
from app.services.settings_service import save_section
from backend.app.models import Project
from backend.app.project_note_models import NoteVersion
from backend.app.services.project_operator import Operator, operator_context
from tests.test_meeting_sessions import stores as stores_fixture, create, command, content, key

stores = stores_fixture


def enable(db):
    save_section(db, 'ai', {'enabled': True})
    save_section(db, 'foresight', {'enabled': True, 'mode': 'local'})


def source(db, bid, text='Le devis contient une réserve de 50 euros.'):
    row = Source(project_id=bid, source_type='document', status='resolved', original_uri='fictif://test',
        sha256=hashlib.sha256(uuid4().bytes).hexdigest(), source_metadata={'subject': 'Devis fictif'})
    db.add(row)
    db.flush()
    db.add(SourceArtifact(source_id=row.id, kind='body_text', content_text=text))
    db.commit()
    return row


def note_session(db, pid=None):
    row = create(db, project_id=pid, kind='note')
    saved = command(db, row['id'], 'notes', 1, title='Note humaine', content=content('Réserve humaine de 50 euros.'))
    return sessions.get_session(db, row['id']), saved


def model(monkeypatch, value):
    monkeypatch.setattr('app.services.ai_client.chat_text', value if callable(value) else lambda *args, **kwargs: value)


ENHANCEMENT_EVIDENCE = 'Le contrôle fictif du banc est prévu mardi.'


def enhancement_session(db, pid=None):
    """Keep the human note and provide a separate, real working transcript."""
    row, saved = note_session(db, pid)
    db.add(LiveTranscriptSegment(id=key(), session_id=row.id, track='mic', start_ms=0, end_ms=1000,
                                speaker='MIC', text=ENHANCEMENT_EVIDENCE))
    db.commit()
    return row, saved


def enhancement_reference(messages, quote=ENHANCEMENT_EVIDENCE):
    """Use the reference actually assigned to the quoted fixture passage."""
    context = messages[-1]['content']
    headers = list(re.finditer(r'(?m)^\[(C\d+)\] \([^\n]+\) [^\n]+\n', context))
    references = [header.group(1) for index, header in enumerate(headers)
                  if quote in context[header.end():headers[index + 1].start() if index + 1 < len(headers) else len(context)]]
    assert len(references) == 1, 'The mocked reply must quote one actual prepared passage'
    return references[0]


def enhancement_reply(messages, text='Le contrôle du banc doit être préparé pour mardi.', *,
                      evidence=ENHANCEMENT_EVIDENCE, quote=None, reference=None):
    return json.dumps({'additions': [{'text': text,
        'reference': reference if reference is not None else enhancement_reference(messages, evidence),
        'quote': evidence if quote is None else quote}]})


def enhancement_model(monkeypatch, text='Le contrôle du banc doit être préparé pour mardi.'):
    model(monkeypatch, lambda cfg, messages, **kwargs: enhancement_reply(messages, text))


def test_local_source_scope_never_uses_remote_embeddings(stores, monkeypatch):
    brain, _, pid, bid = stores
    monkeypatch.setattr('app.services.unified_search.search', lambda *args, **kwargs: pytest.fail('remote recall in local mode'))
    calls = []
    def generate(cfg, messages, **kwargs):
        calls.append(cfg)
        assert '50 euros' in messages[-1]['content']
        return 'La réserve est de 50 euros [C1].'
    model(monkeypatch, generate)
    with brain() as db:
        enable(db)
        src = source(db, bid)
        row = sessions.get_session(db, create(db, project_id=pid)['id'])
        answer = asyncio.run(assistant.answer(db, row, query='devis réserve', scope='sources', source_ids=[src.id]))
        assert answer['status'] == 'answered' and answer['citations'][0]['source_id'] == src.id
        assert not calls[0]['fallback_enabled'] and calls[0]['base_url'].startswith('http://127.0.0.1')
        assert asyncio.run(assistant.answer(db, row, query='devis réserve', scope='sources', source_ids=[src.id]))['id'] == answer['id']
        assert len(calls) == 1


def test_source_scope_rejects_other_project_and_superseded_before_generation(stores, monkeypatch):
    brain, erp, pid, _ = stores
    model(monkeypatch, lambda *args, **kwargs: pytest.fail('unauthorized generation'))
    with brain() as db:
        enable(db)
        other = BrainProject(code='SECRET', name='Secret')
        db.add(other)
        db.commit()
        src = source(db, other.id)
        row = sessions.get_session(db, create(db, project_id=pid)['id'])
        with operator_context(Operator('local', 'editor', frozenset([pid]))):
            with pytest.raises(HTTPException) as caught:
                asyncio.run(assistant.prepare(db, row, query='devis', scope='sources', source_ids=[src.id]))
            assert caught.value.status_code == 404
        src.source_metadata = {**src.source_metadata, 'superseded': True}
        db.commit()
        with pytest.raises(HTTPException) as caught:
            asyncio.run(assistant.prepare(db, row, query='devis', scope='sources', source_ids=[src.id]))
        assert caught.value.status_code == 404
    with erp() as db:
        assert db.get(Project, pid)


def test_source_changed_during_generation_marks_obsolete(stores, monkeypatch):
    brain, _, pid, bid = stores
    with brain() as db:
        enable(db)
        src = source(db, bid)
        row = sessions.get_session(db, create(db, project_id=pid)['id'])
        def generate(*args, **kwargs):
            with brain() as other:
                changed = other.get(Source, src.id)
                changed.source_metadata = {**changed.source_metadata, 'superseded': True}
                other.commit()
            return 'Une réserve est présente [C1].'
        model(monkeypatch, generate)
        answer = asyncio.run(assistant.answer(db, row, query='réserve devis', scope='sources', source_ids=[src.id]))
        assert answer['stale'] and answer['status'] == 'obsolete'


def test_fabricated_answer_reference_is_rejected(stores, monkeypatch):
    brain, _, _, _ = stores
    model(monkeypatch, 'Une fausse référence [C999] prouve tout.')
    with brain() as db:
        enable(db)
        row, _ = note_session(db)
        with pytest.raises(HTTPException) as caught:
            asyncio.run(assistant.answer(db, row, query='réserve'))
        assert caught.value.status_code == 502
        assert db.scalar(select(func.count()).select_from(MeetingSessionEvent).where(MeetingSessionEvent.kind == 'assistant.answer')) == 0


def test_enhancement_accept_preserves_human_blocks_and_replay_once(stores, monkeypatch):
    brain, erp, pid, _ = stores
    enhancement_model(monkeypatch)
    with brain() as db:
        enable(db)
        row, saved = enhancement_session(db, pid)
        proposal = asyncio.run(enhancements.propose(db, row))
        reference = proposal['citations'][0]['reference']
        assert proposal['citations'][0]['quote'] == ENHANCEMENT_EVIDENCE
        accepted = enhancements.decide(db, row, proposal['id'], 'accept', saved['revision'])
        blocks = accepted['note']['content']['blocks']
        assert blocks[0] == content('Réserve humaine de 50 euros.').model_dump()['blocks'][0]
        assert len(blocks) == 2 and blocks[1]['runs'][0]['text'].endswith(f'[{reference}]')
        assert enhancements.decide(db, row, proposal['id'], 'accept', 2)['note_revision'] == 2
        assert db.scalar(select(func.count()).select_from(KnowledgeItem)) == 0
    with erp() as db:
        assert db.scalar(select(func.count()).select_from(NoteVersion)) == 2


def test_enhancement_recovery_after_erp_note_commit_without_brain_receipt(stores, monkeypatch):
    brain, erp, pid, _ = stores
    enhancement_model(monkeypatch, 'Ajout relu.')
    with brain() as db:
        enable(db)
        row, saved = enhancement_session(db, pid)
        proposal = asyncio.run(enhancements.propose(db, row))
        original = sessions._finish
        monkeypatch.setattr(sessions, '_finish', lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError('lost response')))
        with pytest.raises(RuntimeError):
            enhancements.decide(db, row, proposal['id'], 'accept', saved['revision'])
        db.rollback()
        monkeypatch.setattr(sessions, '_finish', original)
        recovered = enhancements.decide(db, row, proposal['id'], 'accept', saved['revision'])
        assert recovered['note_revision'] == 2 and len(recovered['note']['content']['blocks']) == 2
    with erp() as db:
        assert db.scalar(select(func.count()).select_from(NoteVersion)) == 2


@pytest.mark.parametrize('addition', [
    {'text': 'Ajout', 'reference': 'C999', 'quote': ENHANCEMENT_EVIDENCE},
    {'text': 'Ajout', 'reference': None, 'quote': 'citation absente'},
])
def test_invalid_enhancement_citations_are_rejected(stores, monkeypatch, addition):
    brain, _, _, _ = stores
    model(monkeypatch, lambda cfg, messages, **kwargs: enhancement_reply(messages, **addition))
    with brain() as db:
        enable(db)
        row, _ = enhancement_session(db)
        with pytest.raises(HTTPException) as caught:
            asyncio.run(enhancements.propose(db, row))
        assert caught.value.status_code == 502


def test_readers_cannot_accept_enhancement(stores, monkeypatch):
    brain, _, pid, _ = stores
    enhancement_model(monkeypatch, 'Ajout')
    with brain() as db:
        enable(db)
        row, saved = enhancement_session(db, pid)
        proposal = asyncio.run(enhancements.propose(db, row))
        with operator_context(Operator('local', 'reader', frozenset([pid]))):
            with pytest.raises(HTTPException) as caught:
                enhancements.decide(db, row, proposal['id'], 'accept', saved['revision'])
            assert caught.value.status_code == 403


def test_note_only_enhancement_is_empty_without_generation_or_note_save(stores, monkeypatch):
    brain, erp, pid, _ = stores
    model(monkeypatch, lambda *args, **kwargs: pytest.fail('The current note is not evidence for new additions'))
    with brain() as db:
        enable(db)
        row, saved = note_session(db, pid)
        original_note = sessions.session_note(db, row)
        proposal = asyncio.run(enhancements.propose(db, row))
        assert proposal['text'] == '' and proposal['content']['blocks'] == [] and proposal['citations'] == []
        assert proposal['status'] == 'pending'
        assert sessions.session_note(db, row) == original_note and row.revision == saved['revision']
        assert asyncio.run(enhancements.propose(db, row))['id'] == proposal['id']
        assert db.scalar(select(func.count()).select_from(MeetingSessionEvent).where(
            MeetingSessionEvent.session_id == row.id, MeetingSessionEvent.kind == 'enhancement.proposed')) == 1
    with erp() as db:
        assert db.scalar(select(func.count()).select_from(NoteVersion)) == 1


def test_accepting_new_empty_enhancement_does_not_create_note_version(stores, monkeypatch):
    brain, erp, pid, _ = stores
    model(monkeypatch, lambda *args, **kwargs: pytest.fail('No separate evidence: no generation'))
    with brain() as db:
        enable(db)
        row, saved = note_session(db, pid)
        original_note = sessions.session_note(db, row)
        proposal = asyncio.run(enhancements.propose(db, row))
        with pytest.raises(HTTPException, match='Aucun ajout utile') as caught:
            enhancements.decide(db, row, proposal['id'], 'accept', saved['revision'])
        assert caught.value.status_code == 409
        assert sessions.session_note(db, row) == original_note and row.revision == saved['revision']
        command_id = str(uuid5(NAMESPACE_URL, f'enhancement-accept:{row.id}:{proposal["id"]}'))
        assert db.get(MeetingSessionCommand, command_id) is None
        assert db.scalar(select(func.count()).select_from(MeetingSessionEvent).where(
            MeetingSessionEvent.session_id == row.id, MeetingSessionEvent.kind == 'enhancement.decision')) == 0
    with erp() as db:
        assert db.scalar(select(func.count()).select_from(NoteVersion)) == 1


@pytest.mark.parametrize('receipt_phase', ['prepared', 'completed'])
def test_legacy_empty_enhancement_acceptance_recovers_durable_note_saga(stores, monkeypatch, receipt_phase):
    brain, erp, pid, _ = stores
    model(monkeypatch, lambda *args, **kwargs: pytest.fail('Historical recovery must not generate'))
    with brain() as db:
        enable(db)
        row, saved = note_session(db, pid)
        proposal = asyncio.run(enhancements.propose(db, row))
        original_note = sessions.session_note(db, row)
        command_id = str(uuid5(NAMESPACE_URL, f'enhancement-accept:{row.id}:{proposal["id"]}'))
        body = SessionNoteSave(command_id=command_id, expected_revision=saved['revision'],
            title=original_note['title'], content=original_note['content'],
            expected_note_revision=original_note['revision'], expected_note_version_id=original_note['version_id'])
        # Reproduce the old empty acceptance through the real Notes command,
        # whose ERP commit can precede its Brain receipt and enhancement decision.
        original_finish = sessions._finish
        if receipt_phase == 'prepared':
            monkeypatch.setattr(sessions, '_finish', lambda *args, **kwargs:
                                (_ for _ in ()).throw(RuntimeError('lost historical Brain receipt')))
            with pytest.raises(RuntimeError, match='lost historical Brain receipt'):
                sessions.execute_command(db, row.id, 'notes', body)
            db.rollback()
            monkeypatch.setattr(sessions, '_finish', original_finish)
        else:
            sessions.execute_command(db, row.id, 'notes', body)
        assert db.get(MeetingSessionCommand, command_id).status == receipt_phase
        with erp() as other:
            assert other.scalar(select(func.count()).select_from(NoteVersion)) == 2
        recovered = enhancements.decide(db, row, proposal['id'], 'accept', saved['revision'])
        assert recovered['note_revision'] == 2
        assert recovered['note']['content'] == original_note['content']
        assert db.get(MeetingSessionCommand, command_id).status == 'completed'
        assert enhancements.decide(db, row, proposal['id'], 'accept', saved['revision'])['note_revision'] == 2
        assert db.scalar(select(func.count()).select_from(MeetingSessionEvent).where(
            MeetingSessionEvent.session_id == row.id, MeetingSessionEvent.kind == 'enhancement.decision')) == 1
    with erp() as db:
        assert db.scalar(select(func.count()).select_from(NoteVersion)) == 2


def test_proactive_tick_is_bounded_deduped_and_failure_reserved(stores, monkeypatch):
    from app.services import session_proactive
    # Earlier lifespan shutdown tests deliberately stop the production worker.
    monkeypatch.setattr(session_proactive, '_stop', Event())
    brain, _, _, _ = stores
    calls = []
    async def answer(db, row, **kwargs):
        calls.append(row.id)
        raise RuntimeError('test generation failed')
    monkeypatch.setattr(assistant, 'answer', answer)
    with brain() as db:
        enable(db)
        save_section(db, 'foresight', {'proactive_enabled': True})
        # Seed persisted legacy records for scheduling, without starting captures.
        # Exclusive capture admission is exercised by the capture tests.
        for _ in range(2):
            state = create(db)
            db.get(MeetingSession, state['id']).state = 'recording'
            db.add(LiveTranscriptSegment(id=key(), session_id=state['id'], track='mic', start_ms=0, end_ms=1000,
                text='Qui vérifie le devis ?', speaker='mic'))
        db.commit()
    session_proactive.tick()
    assert len(calls) == 1
    session_proactive.tick()
    assert len(calls) == 2 and calls[0] != calls[1]
    session_proactive.tick()
    assert len(calls) == 2


def test_calendar_context_uid_timezone_idempotence_and_no_erp_meeting(stores):
    from app.services.session_calendar import attach_context
    from app.services.source_connectors import calendar_preview
    from backend.app.models import Meeting
    brain, erp, _, _ = stores
    raw = b'BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nUID:fictif\r\nSUMMARY:Revue\r\nDTSTART;TZID=Europe/Paris:20261011T140000\r\nDTEND;TZID=Europe/Paris:20261011T150000\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n'
    preview = calendar_preview(raw)
    assert preview['events'][0]['dtstart_parameters'] == ['TZID=Europe/Paris']
    with brain() as db:
        row = create(db)
        cid = key()
        attached = attach_context(db, row['id'], raw, 'fictif', cid, 1)
        assert attach_context(db, row['id'], raw, 'fictif', cid, 1) == attached
        events = list(db.scalars(select(MeetingSessionEvent).where(MeetingSessionEvent.kind == 'calendar.context')))
        assert len(events) == 1 and events[0].data['dtstart'] == '20261011T140000'
        assert events[0].data['context_only']
        with pytest.raises(HTTPException) as caught:
            attach_context(db, row['id'], raw, 'absent', key(), 2)
        assert caught.value.status_code == 422
        with pytest.raises(HTTPException) as caught:
            attach_context(db, row['id'], raw, 'fictif', 'not-uuid', 2)
        assert caught.value.status_code == 422
    with erp() as db:
        assert db.scalar(select(func.count()).select_from(Meeting)) == 0


def test_scoped_graph_uses_persisted_links_and_stats_projection_purpose(stores, monkeypatch):
    from app.services import fusion_insights
    brain, _, pid, bid = stores
    with brain() as db:
        enable(db)
        src = source(db, bid)
        db.add(MemoryProjection(project_id=bid, purpose='evidence', source_id=src.id, status='indexed', content_hash='x'))
        db.commit()
        with operator_context(Operator('local', 'editor', frozenset([pid]))):
            graph = fusion_insights.graph(db)
            assert all(not edge['inferred'] for edge in graph['edges'])
            assert any(node.get('source_id') == src.id for node in graph['nodes'])
            result = fusion_insights.stats(db)
            assert result['sources']['indexed'] == 0
            assert result['sources']['projection_receipts_indexed'] == 1


def test_local_truth_is_fresh_and_dedup_id_changes_with_knowledge_version(stores, monkeypatch):
    brain, _, pid, bid = stores
    calls = []
    def generate(*args, **kwargs):
        calls.append(True)
        return 'Budget confirmé [C1].'
    model(monkeypatch, generate)
    with brain() as db:
        enable(db)
        knowledge = KnowledgeItem(project_id=bid, kind='fact', subject='Budget', value='Budget 50 euros', status='validated')
        db.add(knowledge)
        db.commit()
        row = sessions.get_session(db, create(db, project_id=pid)['id'])
        first = asyncio.run(assistant.answer(db, row, query='budget', scope='project'))
        knowledge.value, knowledge.version = 'Budget 60 euros', 2
        db.commit()
        second = asyncio.run(assistant.answer(db, row, query='budget', scope='project'))
        assert first['id'] != second['id'] and len(calls) == 2
        stored = assistant.stored_answers(db, row, 'assistant.answer')['items']
        assert any(a['id'] == first['id'] and a['stale'] for a in stored)


def test_local_truth_from_superseded_source_is_excluded(stores, monkeypatch):
    from app.models import ProvenanceLink
    brain, _, pid, bid = stores
    model(monkeypatch, lambda *args, **kwargs: pytest.fail('stale knowledge used'))
    with brain() as db:
        enable(db)
        src = source(db, bid)
        src.source_metadata = {**src.source_metadata, 'superseded': True}
        knowledge = KnowledgeItem(project_id=bid, kind='fact', subject='Devis', value='Devis 50 euros', status='validated')
        db.add(knowledge)
        db.flush()
        db.add(ProvenanceLink(knowledge_item_id=knowledge.id, source_id=src.id, locator={}))
        db.commit()
        row = sessions.get_session(db, create(db, project_id=pid)['id'])
        answer = asyncio.run(assistant.answer(db, row, query='devis', scope='project'))
        assert answer['citations'] == [] and 'ne permet pas' in answer['answer']


def test_calendar_context_is_working_citation_and_not_a_validated_date(stores, monkeypatch):
    from app.services.session_calendar import attach_context
    brain, _, _, _ = stores
    model(monkeypatch, 'Le calendrier importé contient une revue [C1].')
    with brain() as db:
        enable(db)
        state = create(db)
        raw = b'BEGIN:VCALENDAR\nBEGIN:VEVENT\nUID:test\nSUMMARY:Revue\nDTSTART;TZID=Europe/Paris:20261011T140000\nEND:VEVENT\nEND:VCALENDAR'
        state = attach_context(db, state['id'], raw, 'test', key(), 1)
        assert state['calendar_context']['uid'] == 'test'
        answer = asyncio.run(assistant.answer(db, sessions.get_session(db, state['id']), query='revue'))
        assert answer['citations'][0]['level'] == 'working'
        assert 'TZID=Europe/Paris' in answer['citations'][0]['excerpt']
        assert db.scalar(select(func.count()).select_from(KnowledgeItem)) == 0


def test_simultaneous_same_question_has_one_durable_answer_event(stores, monkeypatch):
    brain, _, _, _ = stores
    barrier = Barrier(2)
    def generate(*args, **kwargs):
        barrier.wait(5)
        return 'La réserve est indiquée [C1].'
    model(monkeypatch, generate)
    with brain() as db:
        enable(db)
        row, _ = note_session(db)
        sid = row.id
    def ask():
        with brain() as db:
            return asyncio.run(assistant.answer(db, sessions.get_session(db, sid), query='réserve'))
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: ask(), range(2)))
    assert results[0]['id'] == results[1]['id']
    with brain() as db:
        assert db.scalar(select(func.count()).select_from(MeetingSessionEvent).where(MeetingSessionEvent.kind == 'assistant.answer')) == 1


def test_configured_project_scope_preserves_historical_note_version_provenance(stores, monkeypatch):
    brain, _, pid, bid = stores
    with brain() as db:
        enable(db)
        save_section(db, 'foresight', {'enabled': True, 'mode': 'configured'})
        src = source(db, bid)
        row = sessions.get_session(db, create(db, project_id=pid)['id'])
        url = f'/api/v1/projects/{pid}/notes/historical-note/versions/historical-version'
        async def prepared(*args, **kwargs):
            return {'enabled': True}, [], {'citations': [{'source_id': src.id, 'source_url': url,
                'locator': {'note_version_id': 'historical-version'}, 'reference': 'V1', 'excerpt': 'Réserve historique'}], 'warnings': []}
        monkeypatch.setattr('app.routers.core.prepare_chat', prepared)
        _, _, metadata = asyncio.run(assistant.prepare(db, row, query='réserve', scope='project'))
        assert metadata['citations'][0]['source_url'] == url
        assert metadata['citations'][0]['locator']['note_version_id'] == 'historical-version'
