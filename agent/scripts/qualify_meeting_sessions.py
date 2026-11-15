"""Offline synthetic corpus and long-file capture qualification, isolated SQLite.

This never starts Agent, uses hardware capture, or opens canonical user stores.
SAPI fixtures are distinct French phrases spoken by one installed synthetic voice.
Long PCM files qualify persistence/mix/quotas, never speech accuracy or live latency.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4
import wave

ROOT = Path(__file__).resolve().parents[1]
PHRASES = [
    'Réunion fictive. Le bureau études vérifiera le devis demain matin.',
    'Le client fictif confirme une livraison de la maquette mardi prochain.',
    'Le technicien contrôlera le câblage de la machine avant son démarrage.',
    'La revue de projet valide le plan mécanique après correction de la cote.',
    'Une pause est décidée pendant le contrôle de la fiche de sécurité.',
    'Le service achats consultera deux fournisseurs pour le capteur industriel.',
    'Le chef de projet confirme que le budget de démonstration reste inchangé.',
    'La responsable qualité demande une mesure supplémentaire sur le prototype.',
    'La réunion de démonstration traite la préparation du dossier technique.',
    'Le compte rendu importé précise la date de la prochaine visite atelier.',
    'Le partenaire fictif présentera une solution alternative pendant la revue.',
    'Après interruption la capture reprend et conserve la décision déjà notée.',
]


def key():
    return str(uuid4())


def wave_bytes(frames, rate, channels=1):
    output = io.BytesIO()
    with wave.open(output, 'wb') as stream:
        stream.setnchannels(channels)
        stream.setsampwidth(2)
        stream.setframerate(rate)
        stream.writeframes(frames)
    return output.getvalue()


def synthesize(directory):
    manifest = directory / 'phrases.json'
    manifest.write_text(json.dumps([{'text': text, 'file': str(directory / f'phrase-{i+1:02d}.wav'), 'rate': (i % 5) - 2}
        for i, text in enumerate(PHRASES)], ensure_ascii=False), encoding='utf-8')
    script = directory / 'synthesize.ps1'
    script.write_text("""param([string]$Manifest)
Add-Type -AssemblyName System.Speech
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
$voice = $speaker.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -eq 'fr-FR' } | Select-Object -First 1
if (-not $voice) { throw 'Voix francaise SAPI indisponible' }
$speaker.SelectVoice($voice.VoiceInfo.Name)
$items = Get-Content -LiteralPath $Manifest -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($item in $items) {
    $speaker.Rate = [int]$item.rate
    $speaker.SetOutputToWaveFile([string]$item.file)
    $speaker.Speak([string]$item.text)
    $speaker.SetOutputToNull()
}
$speaker.Dispose()
$voice.VoiceInfo.Name
""", encoding='utf-8-sig')
    result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(script),
        '-Manifest', str(manifest)], capture_output=True, text=True, timeout=180)
    if result.returncode:
        raise RuntimeError('Synthèse vocale SAPI du corpus impossible')
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--long', action='store_true', help='Add 60/120 minute two-track PCM persistence/mix tests')
    parser.add_argument('--report', type=Path, default=ROOT / 'logs' / 'foresight-runtime' / 'session-qualification.json')
    args = parser.parse_args()
    instant = datetime.now(timezone.utc)
    directory = args.report.parent / ('sessions-' + instant.strftime('%Y%m%d-%H%M%S-%f'))
    directory.mkdir(parents=True, exist_ok=False)
    os.environ.update(MINIPILOT_HOME=str(directory / 'erp'), PB_DATABASE_URL='sqlite:///' + (directory / 'brain.db').as_posix(),
        PB_STORAGE_DIR=str(directory / 'storage'), PB_MEMORY_ENGINE='fake', AGENT_TESTING='1', AGENT_MEETING_SESSIONS_ENABLED='1',
        AGENT_OPERATOR_ROLE='owner', AGENT_OPERATOR_ID='qualification', AGENT_OPERATOR_PROJECT_IDS='')
    os.environ.pop('AGENT_OPERATOR_PROJECT_IDS', None)
    sys.path.insert(0, str(ROOT))
    from app.db import init_db, SessionLocal as Brain
    from backend.app.db import init_db as init_erp, SessionLocal as ERP
    from app.models import Project as BrainProject, Source, MeetingRecording
    from backend.app.models import BrainLink, Project
    from app.meeting_session_schemas import SessionCreate, Command, SessionNoteSave
    from app.meeting_notes_publication_schemas import PublishNotes
    from app.meeting_session_models import MeetingAudioChunk
    from app.services import meeting_sessions as sessions
    from app.services.meeting_notes_publication import publish_notes
    from app.routers.meeting_sessions import audio
    from backend.app.project_note_schemas import NoteContent
    from sqlalchemy import select
    init_db()
    init_erp()
    with Brain() as db:
        bp = BrainProject(code='SYNTHETIC-QUALIFICATION', name='Qualification fictive')
        db.add(bp)
        db.commit()
        bid = bp.id
    with ERP() as db:
        project = Project(code='SYNTHETIC-QUALIFICATION', title='Qualification fictive')
        db.add(project)
        db.flush()
        db.add(BrainLink(project_id=project.id, brain_project_id=bid))
        db.commit()
        pid = project.id
    report = {'created_at': instant.isoformat(), 'isolated_directory': str(directory), 'passed': False,
        'hardware_capture_tested': False, 'speech_accuracy_tested': False, 'live_latency_tested': False,
        'synthetic_speakers': 1, 'cases': [], 'long_files': [], 'errors': []}
    voice = synthesize(directory)
    report['synthetic_voice'] = voice

    def command(db, state, kind):
        return sessions.execute_command(db, state['id'], kind, Command(command_id=key(), expected_revision=state['revision']))

    def upload(db, state, raw, track, sequence, start_ms, duration_ms, *, cid=None):
        return sessions.store_chunk(db, state['id'], track, sequence, raw=raw, filename='fictif.wav', mime_type='audio/wav',
            command_id=cid or key(), sha256=hashlib.sha256(raw).hexdigest(), start_ms=start_ms, duration_ms=duration_ms)

    for index, phrase in enumerate(PHRASES, 1):
        started = time.monotonic()
        try:
            path = directory / f'phrase-{index:02d}.wav'
            with wave.open(str(path), 'rb') as reader:
                rate, frames = reader.getframerate(), reader.readframes(reader.getnframes())
            frame_count = len(frames) // 2
            duration = round(frame_count * 1000 / rate)
            first_frames = frame_count // 2
            split_ms = round(first_frames * 1000 / rate)
            first = wave_bytes(frames[:first_frames * 2], rate)
            second = wave_bytes(frames[first_frames * 2:], rate)
            names = ['mic', 'system', 'dual-sync', 'split', 'pause-gap', 'out-of-order', 'ack-replay',
                'slow-voice', 'stereo', 'import', 'dual-offset', 'restart']
            with Brain() as db:
                state = sessions.create_session(db, SessionCreate(command_id=key(), title=f'Corpus {index:02d} {names[index-1]}',
                    kind='import' if index == 10 else 'meeting', project_id=pid))
                state = command(db, state, 'resume')
                if index in {4, 5, 6}:
                    if index == 6:
                        upload(db, state, second, 'mic', 1, split_ms, duration - split_ms)
                    upload(db, state, first, 'mic', 0, 0, split_ms)
                    if index == 5:
                        state = command(db, state, 'pause')
                        state = command(db, state, 'resume')
                    if index != 6:
                        upload(db, state, second, 'mic', 1, split_ms + (250 if index == 5 else 0), duration - split_ms)
                else:
                    raw = path.read_bytes()
                    if index == 9:
                        stereo = bytearray()
                        for offset in range(0, len(frames), 2):
                            stereo.extend(frames[offset:offset+2] * 2)
                        raw = wave_bytes(stereo, rate, 2)
                    cid = key()
                    ack = upload(db, state, raw, 'system' if index == 2 else 'mic', 0, 0, duration, cid=cid)
                    if index == 7:
                        assert upload(db, state, raw, 'mic', 0, 0, duration, cid=cid) == ack
                    if index in {3, 11}:
                        upload(db, state, path.read_bytes(), 'system', 0, 1000 if index == 11 else 0, duration)
                    if index == 12:
                        sessions.recover_interrupted(db)
                        state = sessions.serialize_session(db, sessions.get_session(db, state['id']))
                        assert state['state'] == 'interrupted'
                        state = command(db, state, 'resume')
                state = command(db, state, 'finalize')
                assert state['state'] == 'completed' and state['recording_id']
                playback = audio(state['id'], 'system' if index == 2 else 'mic', db)
                assert playback.body and playback.media_type == 'audio/wav'
                chunks = list(db.scalars(select(MeetingAudioChunk).where(MeetingAudioChunk.session_id == state['id'])))
                assert all(hashlib.sha256(sessions.chunk_path(c).read_bytes()).hexdigest() == c.sha256 for c in chunks)
                note = NoteContent.model_validate({'blocks': [{'type': 'paragraph', 'runs': [{'text': phrase}]}]})
                state = sessions.execute_command(db, state['id'], 'notes', SessionNoteSave(command_id=key(),
                    expected_revision=state['revision'], title=state['title'], content=note))
                publish = PublishNotes(command_id=key(), expected_revision=state['revision'], expected_note_revision=state['note_revision'],
                    expected_note_version_id=state['note_version_id'], summary={'overview': phrase,
                    'actions': [{'text': phrase[:255], 'block_index': 0, 'quote': phrase, 'owner': 'Qualification', 'due_date': ''}]})
                result = publish_notes(db, state['id'], publish)
                assert publish_notes(db, state['id'], publish)['meeting_id'] == result['meeting_id']
                source = db.get(Source, db.get(MeetingRecording, state['recording_id']).source_id)
                with wave.open(source.original_uri, 'rb') as reader:
                    output_ms = round(reader.getnframes() * 1000 / reader.getframerate())
                report['cases'].append({'case': index, 'mode': names[index-1], 'passed': True, 'duration_ms': duration,
                    'output_duration_ms': output_ms, 'chunks': len(chunks), 'raw_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                    'recording_id': state['recording_id'], 'meeting_id': result['meeting_id'], 'elapsed_seconds': round(time.monotonic()-started, 3)})
        except Exception as exc:
            report['cases'].append({'case': index, 'passed': False, 'error': type(exc).__name__ + ': ' + str(exc)[:500]})
            report['errors'].append(f'corpus:{index}')

    if args.long:
        minute = wave_bytes(b'\0\0' * (16000 * 60), 16000)
        for minutes in [60, 120]:
            started = time.monotonic()
            try:
                with Brain() as db:
                    state = sessions.create_session(db, SessionCreate(command_id=key(), title=f'PCM synthétique {minutes} minutes', project_id=pid))
                    state = command(db, state, 'resume')
                    for sequence in range(minutes):
                        for track in ['mic', 'system']:
                            upload(db, state, minute, track, sequence, sequence * 60000, 60000)
                    before = sessions.serialize_session(db, sessions.get_session(db, state['id']))
                    assert before['total_bytes'] < sessions.MAX_CAPTURE_BYTES
                    state = command(db, state, 'finalize')
                    source = db.get(Source, db.get(MeetingRecording, state['recording_id']).source_id)
                    with wave.open(source.original_uri, 'rb') as reader:
                        actual_ms = round(reader.getnframes() * 1000 / reader.getframerate())
                    assert actual_ms == minutes * 60000
                    chunks = list(db.scalars(select(MeetingAudioChunk).where(MeetingAudioChunk.session_id == state['id'])))
                    assert all(hashlib.sha256(sessions.chunk_path(c).read_bytes()).hexdigest() == c.sha256 for c in chunks)
                    report['long_files'].append({'minutes': minutes, 'passed': True, 'tracks': 2, 'sample_rate': 16000,
                        'bits_per_sample': 16, 'total_input_bytes': before['total_bytes'], 'output_bytes': Path(source.original_uri).stat().st_size,
                        'duration_ms': actual_ms, 'chunks': len(chunks), 'elapsed_seconds': round(time.monotonic()-started, 3),
                        'speech_accuracy_tested': False})
            except Exception as exc:
                report['long_files'].append({'minutes': minutes, 'passed': False, 'error': type(exc).__name__ + ': ' + str(exc)[:500]})
                report['errors'].append(f'long:{minutes}')
    report['passed'] = len(report['cases']) == 12 and not report['errors']
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'passed': report['passed'], 'cases': len(report['cases']), 'long_files': len(report['long_files']), 'report': str(args.report)}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
