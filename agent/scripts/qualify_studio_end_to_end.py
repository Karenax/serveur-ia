"""Isolated FastAPI qualification with real local generation and fictitious speech."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
import unicodedata
from urllib.parse import urlsplit
import urllib.request
from uuid import uuid4
import wave

ROOT = Path(__file__).resolve().parents[1]


def folded(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', value.casefold()) if not unicodedata.combining(c))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--audio', type=Path, default=ROOT / 'logs/foresight-runtime/qualification/reunion-fictive.wav')
    parser.add_argument('--report', type=Path, default=ROOT / 'logs/foresight-runtime/studio-end-to-end.json')
    parser.add_argument('--endpoint', default='http://127.0.0.1:1234')
    parser.add_argument('--model', default='google/gemma-4-e4b')
    args = parser.parse_args()
    endpoint = urlsplit(args.endpoint)
    if endpoint.scheme != 'http' or endpoint.hostname not in {'127.0.0.1', 'localhost', '::1'} or endpoint.username or endpoint.password:
        parser.error('Le moteur de qualification doit être sur la machine locale')
    instant = datetime.now(timezone.utc)
    directory = args.report.parent / ('http-' + instant.strftime('%Y%m%d-%H%M%S-%f'))
    directory.mkdir(parents=True, exist_ok=False)
    os.environ.update(MINIPILOT_HOME=str(directory / 'erp'), PB_DATABASE_URL='sqlite:///' + (directory / 'brain.db').as_posix(),
        PB_STORAGE_DIR=str(directory / 'storage'), PB_MEMORY_ENGINE='fake', AGENT_TESTING='1',
        AGENT_MEETING_SESSIONS_ENABLED='1', AGENT_OPERATOR_ROLE='owner', AGENT_OPERATOR_ID='qualification')
    os.environ.pop('AGENT_OPERATOR_PROJECT_IDS', None)
    sys.path.insert(0, str(ROOT))
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from sqlalchemy import func, select
    from app.db import init_db, SessionLocal as Brain
    from backend.app.db import init_db as init_erp, SessionLocal as ERP
    from app.models import Project as BrainProject, Source, SourceArtifact, KnowledgeItem, ProvenanceLink
    from backend.app.models import BrainLink, Project, Meeting, MeetingAction, Task
    from backend.app.project_note_models import NoteVersion
    from backend.app.project_note_schemas import NoteContent, content_text
    from app.meeting_session_models import MeetingAudioChunk
    from app.routers import meeting_sessions, session_assistant, meeting_notes_publication
    from app.services import live_speech
    from app.services.settings_service import save_section
    init_db()
    init_erp()
    report = {'created_at': instant.isoformat(), 'isolated_directory': str(directory), 'passed': False,
        'hardware_capture_tested': False, 'real_local_generation': True, 'real_speech_runtime': True,
        'endpoint': args.endpoint, 'model': args.model, 'http_calls': [], 'network_hosts': [], 'checks': {}, 'errors': []}
    original_open = urllib.request.urlopen
    def local_open(request, *values, **options):
        url = request.full_url if hasattr(request, 'full_url') else str(request)
        host = urlsplit(url).hostname
        report['network_hosts'].append(host)
        if host not in {'127.0.0.1', 'localhost', '::1'}:
            raise RuntimeError('Appel réseau externe interdit dans cette qualification')
        return original_open(request, *values, **options)
    urllib.request.urlopen = local_open
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(args.endpoint.rstrip('/') + '/api/v1/models', timeout=10) as response:
            inventory = json.load(response)
        loaded = [item for item in inventory.get('models', []) if item.get('loaded_instances') and
                  args.model in {item.get('key'), item.get('id'), item.get('model_key')}]
        assert loaded, 'Modèle local téléchargé mais pas confirmé chargé'
        report['checks']['local_model_loaded'] = True
        with Brain() as db:
            project = BrainProject(code='HTTP-FICTIF', name='Qualification Studio fictive')
            db.add(project)
            db.commit()
            bid = project.id
            save_section(db, 'ai', {'enabled': True, 'provider': 'openai_compatible', 'base_url': args.endpoint,
                'model': args.model, 'fallback_enabled': False, 'fallback_autostart': False})
            save_section(db, 'foresight', {'enabled': True, 'mode': 'local',
                'local_generation_endpoint': args.endpoint, 'local_generation_model': args.model})
            source = Source(project_id=bid, source_type='document', status='resolved', original_uri='fictif://qualification',
                sha256=hashlib.sha256(b'industrial-fixture').hexdigest(), source_metadata={'subject': 'Exigence fictive de puissance'})
            db.add(source)
            db.flush()
            db.add(SourceArtifact(source_id=source.id, kind='body_text', content_text=
                'La puissance maximale est de 250 W. La commande du matériel n’est pas autorisée avant validation du devis.'))
            db.commit()
            source_id = source.id
        with ERP() as db:
            project = Project(code='HTTP-FICTIF', title='Qualification Studio fictive')
            db.add(project)
            db.flush()
            db.add(BrainLink(project_id=project.id, brain_project_id=bid))
            db.commit()
            pid = project.id
        app = FastAPI()
        for router in [meeting_sessions.router, session_assistant.router, meeting_notes_publication.router]:
            app.include_router(router)
        http = TestClient(app)
        def call(method, url, **options):
            request_started = time.perf_counter()
            response = http.request(method, url, **options)
            report['http_calls'].append({'method': method, 'url': url, 'status': response.status_code,
                'elapsed_seconds': round(time.perf_counter() - request_started, 3)})
            if response.status_code >= 400:
                raise AssertionError(f'{method} {url}: {response.status_code} {response.text[:1200]}')
            print(json.dumps({'stage': url.rsplit('/', 1)[-1], 'status': response.status_code}), flush=True)
            return response
        state = call('POST', '/api/v1/meeting-sessions', json={'command_id': str(uuid4()),
            'title': 'Réunion fictive de qualification', 'project_id': pid}).json()
        prefix = '/api/v1/meeting-sessions/' + state['id']
        state = call('POST', prefix + '/resume', json={'command_id': str(uuid4()), 'expected_revision': state['revision']}).json()
        raw = args.audio.read_bytes()
        with wave.open(str(args.audio), 'rb') as reader:
            duration_ms = round(reader.getnframes() * 1000 / reader.getframerate())
        checksum = hashlib.sha256(raw).hexdigest()
        upload = {'command_id': str(uuid4()), 'sha256': checksum, 'start_ms': '0', 'duration_ms': str(duration_ms)}
        ack = call('PUT', prefix + '/chunks/mic/0', data=upload,
            files={'file': (args.audio.name, raw, 'audio/wav')}).json()
        replay_ack = call('PUT', prefix + '/chunks/mic/0', data=upload,
            files={'file': (args.audio.name, raw, 'audio/wav')}).json()
        assert ack == replay_ack, 'Le reçu de la même commande doit être identique'
        sequence_replay = call('PUT', prefix + '/chunks/mic/0', data={**upload, 'command_id': str(uuid4())},
            files={'file': (args.audio.name, raw, 'audio/wav')}).json()
        assert sequence_replay['replayed'] and sequence_replay['accepted_chunk'] == ack['accepted_chunk']
        assert hashlib.sha256(call('GET', prefix + '/audio').content).hexdigest() == checksum
        report['checks']['audio_sha256_and_ack_replay'] = True
        with Brain() as db:
            chunk_id = db.scalar(select(MeetingAudioChunk.id).where(MeetingAudioChunk.session_id == state['id']))
        live_speech.process_chunk(chunk_id)
        transcript = call('GET', prefix + '/segments').json()
        assert transcript, 'Le véritable moteur STT n’a produit aucun segment'
        processing = call('GET', prefix).json()
        assert processing['transcript_processing_complete'] and processing['transcript_provisional']
        report['transcript'] = ' '.join(item['text'] for item in transcript)
        report['checks']['real_stt_segment_persisted'] = True
        human = {'type': 'paragraph', 'runs': [{'text': 'Le devis n’est pas validé. Réserve humaine : ne pas commander le matériel.'}]}
        note = {'blocks': [human]}
        state = call('PUT', prefix + '/notes', json={'command_id': str(uuid4()), 'expected_revision': state['revision'],
            'title': 'Notes humaines de qualification', 'content': note}).json()
        canonical_human = state['note']['content']['blocks'][0]
        answer = call('POST', prefix + '/ask', json={'query': 'Le devis est-il validé ? Réponds clairement à partir de la note.',
            'scope': 'session', 'expected_revision': state['revision']}).json()
        text = folded(answer['answer'])
        assert answer['status'] == 'answered' and answer['citations']
        assert re.search(r"(?:n['’]est\s+pas|pas\s+(?:encore\s+)?valide|non\s+valide)", text), 'Négation humaine non conservée dans la réponse'
        report['session_answer'] = answer
        report['checks']['real_answer_keeps_human_negation'] = True
        source_answer = call('POST', prefix + '/ask', json={'query':
            'Quelle limite de puissance et quelle autorisation de commande sont indiquées ?', 'scope': 'sources', 'source_ids': [source_id]}).json()
        assert source_answer['status'] == 'answered' and '250' in source_answer['answer']
        assert any(item.get('source_id') == source_id for item in source_answer['citations'])
        report['source_answer'] = source_answer
        report['checks']['real_source_answer_cites_selected_source_and_number'] = True
        proposal = call('POST', prefix + '/enhancements', json={'expected_revision': state['revision']}).json()
        assert proposal['status'] == 'pending' and proposal['content']['blocks'], 'Le moteur n’a proposé aucun ajout exploitable'
        assert any(item['locator'].get('segment_id') for item in proposal['citations']), 'La proposition reformule seulement une note déjà présente'
        for citation in proposal['citations']:
            assert citation['quote'] in citation['excerpt']
        state = call('POST', prefix + '/enhancements/' + proposal['id'] + '/decision',
            json={'decision': 'accept', 'expected_revision': state['revision']}).json()
        accepted = state['note']['content']['blocks']
        assert accepted[0] == canonical_human and len(accepted) > 1, 'La note humaine a été modifiée au lieu d’ajouter un bloc'
        accepted_state = call('POST', prefix + '/enhancements/' + proposal['id'] + '/decision',
            json={'decision': 'accept', 'expected_revision': state['revision']}).json()
        assert accepted_state['note_version_id'] == state['note_version_id']
        report['proposal'] = proposal
        report['checks']['reviewed_addition_preserves_human_blocks_and_replay'] = True
        chosen_index = next((i for i, block in enumerate(accepted) if i > 0 and 'devis' in folded(content_text(NoteContent.model_validate({'blocks': [block]})))) , 1)
        action = content_text(NoteContent.model_validate({'blocks': [accepted[chosen_index]]}))
        publication = {'command_id': str(uuid4()), 'expected_revision': state['revision'],
            'expected_note_revision': state['note_revision'], 'expected_note_version_id': state['note_version_id'],
            'summary': {'overview': 'Compte rendu fictif relu pour qualification.', 'decisions': [],
                'actions': [{'text': action[:255], 'block_index': chosen_index, 'quote': action[:200], 'owner': 'BE', 'due_date': ''}],
                'open_points': [{'text': 'Le devis n’est pas validé.', 'block_index': 0, 'quote': 'Le devis n’est pas validé.'}]}}
        published = call('POST', prefix + '/publish-notes', json=publication).json()
        assert call('POST', prefix + '/publish-notes', json=publication).json()['meeting_id'] == published['meeting_id']
        with ERP() as db:
            assert db.scalar(select(func.count()).select_from(Meeting)) == 1
            assert db.scalar(select(func.count()).select_from(MeetingAction)) == 1
            assert db.scalar(select(func.count()).select_from(Task)) == 0
            assert db.scalar(select(func.count()).select_from(NoteVersion)) == 2
        with Brain() as db:
            assert db.scalar(select(func.count()).select_from(KnowledgeItem)) == 3
            provenance = list(db.scalars(select(ProvenanceLink)))
            assert len(provenance) == 3 and all(item.locator['note_version_id'] == state['note_version_id'] for item in provenance)
        report['publication'] = published
        report['checks']['publication_replay_exact_version_no_automatic_task'] = True
        state = call('POST', prefix + '/finalize', json={'command_id': str(uuid4()),
            'expected_revision': published['session']['revision']}).json()
        assert state['state'] == 'completed' and state['recording_id']
        report['checks']['real_audio_finalized_with_existing_recording_pipeline'] = True
        report['passed'] = all(report['checks'].values())
    except Exception as exc:
        report['errors'].append(type(exc).__name__ + ': ' + str(exc))
    finally:
        urllib.request.urlopen = original_open
        if live_speech._resident is not None:
            live_speech._resident.close()
            live_speech._resident = None
        report['elapsed_seconds'] = round(time.perf_counter() - started, 3)
        report['network_hosts'] = sorted(set(report['network_hosts']))
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'passed': report['passed'], 'report': str(args.report), 'checks': report['checks'], 'errors': report['errors']}, ensure_ascii=False))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
