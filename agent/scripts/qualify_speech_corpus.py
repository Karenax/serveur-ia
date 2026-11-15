"""Measured French industrial STT and real durable worker, isolated fixtures.

SAPI is a fictitious single speaker. These checks do not qualify meeting noise,
real voices, speaker identity, desktop Teams, or browser end-to-end latency.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import unicodedata
import uuid
import wave

ROOT = Path(__file__).resolve().parents[1]
INDUSTRIAL = [
    ("Le projet Alpha vingt-quatre utilise un câble de deux virgule cinq millimètres carrés.",
     {"project_code": r"alpha[- ]?(?:vingt[- ]quatre|24)", "section_mm2": r"(?:deux virgule cinq|2[.,]5) (?:millimetres carres|mm2)"}),
    ("L'alimentation est de deux cent trente volts et le courant maximal de seize ampères.",
     {"voltage": r"(?:deux cent trente|230) ?(?:volts|v)\b", "current": r"(?:seize|16) ?(?:amperes|a)\b"}),
    ("La puissance est de mille deux cent cinquante watts pour un éclairement de trois cent cinquante lux.",
     {"power": r"(?:mille deux cent cinquante|1250|1 ?250) ?(?:watts|w)\b", "illumination": r"(?:trois cent cinquante|350) ?lux(?:e)?\b"}),
    ("Ne démarrez pas la machine avant la validation de la consignation.",
     {"negation": r"demarre(?:z|r) pas", "reservation": r"avant la validation de la consignation"}),
    ("Le client n'accepte pas l'option automatique et demande de conserver la commande manuelle.",
     {"negation": r"accepte pas", "manual_option": r"commande manuelle"}),
    ("La livraison fictive est prévue le quinze octobre deux mille vingt-six à quatorze heures trente.",
     {"date": r"(?:quinze|15) octobre (?:deux mille vingt[- ]six|2026)", "time": r"(?:quatorze heures trente|14(?: h|h|:| heures )30)"}),
    ("La prochaine réunion fictive aura lieu lundi dix-neuf octobre à neuf heures.",
     {"date": r"lundi (?:dix[- ]neuf|19) octobre", "time": r"(?:neuf heures|9 ?(?:heures|h))"}),
    ("Marie Dupont prépare un devis de deux mille quatre cents euros hors taxes.",
     {"person": r"marie du ?pont", "amount": r"(?:deux mille quatre cents?|2400|2 ?400) ?(?:euros|€)", "tax_basis": r"hors taxes?\b"}),
    ("La tolérance est de plus ou moins zéro virgule deux millimètres pour une longueur de un virgule cinq mètres.",
     {"tolerance": r"plus ou moins (?:zero virgule deux|0[.,]2) (?:millimetres|mm)", "length": r"(?:un virgule cinq|1[.,]5) (?:metres|m)\b"}),
    ("La vitesse maximale est de cent vingt tours par minute et la température limite de quatre-vingts degrés Celsius.",
     {"speed": r"(?:cent vingt|120) tours par minute", "temperature": r"(?:quatre[- ]vingts?|80) ?(?:degres celsius|° ?c|celsius)"}),
    ("Aucun montage ne sera lancé sans l'accord du bureau études et du responsable qualité.",
     {"negation": r"aucun montage", "reservation": r"sans l accord du bureau (?:d )?etudes"}),
    ("La révision B du document ne remplace pas la révision A avant la validation de l'essai.",
     {"revision_b": r"revision b\b", "revision_a": r"revision a\b", "negation": r"remplace pas", "reservation": r"avant la validation de l essai"}),
]


def fold(text):
    value = ''.join(char for char in unicodedata.normalize('NFKD', text.lower()) if not unicodedata.combining(char))
    return re.sub(r'\s+', ' ', value.replace("'", ' ').replace('’', ' ').replace('-', ' ')).strip()


NUMBER_WORDS = {"2026": "deux mille vingt six", "1250": "mille deux cent cinquante",
                "2250": "deux mille deux cent cinquante",
                "2400": "deux mille quatre cents", "230": "deux cent trente", "350": "trois cent cinquante",
                "120": "cent vingt", "80": "quatre vingts", "24": "vingt quatre", "16": "seize",
                "15": "quinze", "19": "dix neuf", "14": "quatorze", "30": "trente", "9": "neuf"}


def words(text):
    value = fold(text)
    value = re.sub(r'(?<=\d)\s+(?=\d{3}(?:\D|$))', '', value)
    value = re.sub(r'(\d)\s*€', r'\1 euros', value)
    value = re.sub(r'(\d)\s*°\s*c\b', r'\1 degres celsius', value)
    for unit, spelling in ((r'a\b', 'amperes'), (r'w\b', 'watts'), (r'v\b', 'volts'), (r'mm2\b', 'millimetres carres')):
        value = re.sub(r'(\d)\s*' + unit, r'\1 ' + spelling, value)
    for numeric, spelling in ((r'2[,.]5', 'deux virgule cinq'), (r'0[,.]2', 'zero virgule deux'),
                              (r'1[,.]5', 'un virgule cinq'), (r'14\s*(?:h|:)\s*30', 'quatorze heures trente')):
        value = re.sub(r'\b' + numeric + r'\b', spelling, value)
    value = re.sub(r'(\d)\s*h\b', r'\1 heures', value)
    value = re.sub(r'(\d)\s*mm\b', r'\1 millimetres', value)
    value = re.sub(r'(\d)\s*m\b', r'\1 metres', value)
    for numeric, spelling in NUMBER_WORDS.items():
        value = re.sub(r'\b' + numeric + r'\b', spelling, value)
    return re.findall(r'[a-z0-9]+', value)


def wer(reference, hypothesis):
    expected, actual = words(reference), words(hypothesis)
    row = list(range(len(actual) + 1))
    for i, token in enumerate(expected, 1):
        following = [i]
        for j, observed in enumerate(actual, 1):
            following.append(min(following[-1] + 1, row[j] + 1, row[j - 1] + (token != observed)))
        row = following
    return {'errors': row[-1], 'reference_words': len(expected), 'wer': row[-1] / max(1, len(expected))}


def synthesize(directory):
    manifest = directory / 'industrial-phrases.json'
    items = [{'text': text, 'critical': critical, 'rate': (i % 5) - 2,
              'file': str(directory / f'industrial-{i+1:02d}.wav')} for i, (text, critical) in enumerate(INDUSTRIAL)]
    manifest.write_text(json.dumps(items, ensure_ascii=False), encoding='utf-8')
    script = directory / 'synthesize.ps1'
    script.write_text("""param([string]$Manifest)
Add-Type -AssemblyName System.Speech
$voice = New-Object System.Speech.Synthesis.SpeechSynthesizer
$french = $voice.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -eq 'fr-FR' } | Select-Object -First 1
if (-not $french) { throw 'Voix francaise fictive indisponible' }
$voice.SelectVoice($french.VoiceInfo.Name)
foreach ($item in (Get-Content -LiteralPath $Manifest -Raw -Encoding UTF8 | ConvertFrom-Json)) {
 $voice.Rate = [int]$item.rate
 $voice.SetOutputToWaveFile([string]$item.file)
 $voice.Speak([string]$item.text)
 $voice.SetOutputToNull()
}
$voice.Dispose()
$french.VoiceInfo.Name
""", encoding='utf-8-sig')
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
        '-File', str(script), '-Manifest', str(manifest)], capture_output=True, text=True,
        timeout=180, creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise ValueError('Génération du corpus SAPI fictif impossible')
    return items, result.stdout.strip()


def pcm(data, rate=16000):
    output = io.BytesIO()
    with wave.open(output, 'wb') as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(rate)
        target.writeframes(data)
    return output.getvalue()


def normalize(source, destination):
    result = subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(source),
        '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', str(destination)], capture_output=True, timeout=30,
        creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise ValueError('Normalisation de la fixture PCM impossible')


def percentile(values, fraction):
    values = sorted(values)
    return values[min(len(values) - 1, round((len(values) - 1) * fraction))] if values else None


def score_report(report):
    industrial = [case for case in report['cases'] if case['condition'] == 'clean_sapi_industrial']
    for case in report['cases']:
        case.update(wer(case['reference'], case['transcript']))
    for case, (_, critical) in zip(industrial, INDUSTRIAL, strict=True):
        case['critical_fields'] = {key: {'passed': bool(re.search(pattern, fold(case['transcript']))),
                                         'expected_pattern': pattern} for key, pattern in critical.items()}
    errors, count = sum(case['errors'] for case in industrial), sum(case['reference_words'] for case in industrial)
    checks = [check for case in industrial for check in case['critical_fields'].values()]
    report.update(clean_industrial_weighted_wer=errors / max(1, count), critical_correct=sum(check['passed'] for check in checks),
                  critical_total=len(checks), industrial_quality_gate_passed=errors / max(1, count) <= .10 and all(check['passed'] for check in checks),
                  critical_failures=[{'case': i + 1, 'field': key, 'transcript': case['transcript']}
                      for i, case in enumerate(industrial) for key, value in case['critical_fields'].items() if not value['passed']],
                  wer_normalization='French accents/punctuation, declared numeric spelling and unit symbol equivalents')
    report['quality_thresholds_provisional'] = {'weighted_wer_max': .10,
                                               'critical_fields_expected': 'all exact values checked by declared patterns'}
    if report.get('resources') and not report['resources'].get('scope'):
        report['resources']['measured'] = False
        report['resources']['invalid_for_runtime_tree'] = True
        report['resources']['reason'] = 'Initial observer measured Windows venv launcher only; use speech-resource-qualification.json'
    return report


def qualify_worker(directory, wave_path):
    # Environment is set before first canonical config/DB import in this script.
    from app.db import init_db, SessionLocal
    from backend.app.db import init_db as init_erp
    from app.meeting_session_models import MeetingAudioChunk, MeetingSessionEvent, LiveTranscriptSegment
    from app.meeting_session_schemas import SessionCreate, Command, SessionSegmentEdit
    from app.services import live_speech, meeting_sessions as service
    init_db()
    init_erp()
    with wave.open(str(wave_path), 'rb') as source:
        raw = source.readframes(source.getnframes())
    with SessionLocal() as db:
        session = service.create_session(db, SessionCreate(command_id=str(uuid.uuid4()), title='Worker STT fictif'))
        session = service.execute_command(db, session['id'], 'resume', Command(command_id=str(uuid.uuid4()), expected_revision=1))
    live_speech.start_worker()
    timings, chunks = [], []
    try:
        for ordinal, start in enumerate(range(0, len(raw), 160000)):
            data = pcm(raw[start:start + 160000])
            submitted = time.perf_counter()
            with SessionLocal() as db:
                receipt = service.store_chunk(db, session['id'], 'system', ordinal, raw=data,
                    filename=f'fictif-{ordinal}.wav', mime_type='audio/wav', command_id=str(uuid.uuid4()),
                    sha256=hashlib.sha256(data).hexdigest(), start_ms=start // 32, duration_ms=(len(data) - 44) // 32)
                cid = receipt['id'] if 'id' in receipt else db.query(MeetingAudioChunk).filter_by(session_id=session['id'], sequence=ordinal).one().id
            # Real background pending/running/completed worker, no direct process_chunk call.
            deadline = time.monotonic() + 40
            while time.monotonic() < deadline:
                with SessionLocal() as db:
                    row = db.get(MeetingAudioChunk, cid)
                    state, error = row.speech_status, row.speech_error
                if state in {'completed', 'failed'}:
                    break
                time.sleep(.025)
            if state != 'completed':
                raise ValueError('Worker STT en échec : ' + str(error or state))
            timings.append(time.perf_counter() - submitted)
            chunks.append(cid)
        with SessionLocal() as db:
            segments = db.query(LiveTranscriptSegment).filter_by(session_id=session['id']).order_by(LiveTranscriptSegment.start_ms).all()
            if not segments:
                raise ValueError('Aucun segment durable produit par le worker')
            original = segments[0]
            fixed = original.text + ' [correction humaine fictive]'
            current = service.get_session(db, session['id'])
            service.edit_segment(db, session['id'], original.id, SessionSegmentEdit(command_id=str(uuid.uuid4()),
                expected_session_revision=current.revision, expected_segment_revision=original.revision,
                text=fixed, speaker='Marie fictive'))
            original = db.get(LiveTranscriptSegment, original.id)
            original.finalized = True  # Controlled fixture flag; no claim of production human validation.
            db.get(MeetingAudioChunk, original.chunk_id).speech_status = 'pending'
            db.commit()
            corrected_id, expected_revision = original.id, original.revision
        live_speech.wake_worker()
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            with SessionLocal() as db:
                row = db.get(LiveTranscriptSegment, corrected_id)
                state = db.get(MeetingAudioChunk, row.chunk_id).speech_status
            if state in {'completed', 'failed'}:
                break
            time.sleep(.025)
        with SessionLocal() as db:
            corrected = db.get(LiveTranscriptSegment, corrected_id)
            retained = corrected.text == fixed and corrected.speaker == 'Marie fictive' and corrected.finalized and corrected.revision == expected_revision
            segments = db.query(LiveTranscriptSegment).filter_by(session_id=session['id']).order_by(LiveTranscriptSegment.start_ms).all()
            events = db.query(MeetingSessionEvent).filter_by(session_id=session['id'], kind='transcript.updated').count()
            limits = all(0 <= item.start_ms <= item.end_ms <= len(raw) // 32 for item in segments)
            return {'passed': retained and limits and state == 'completed', 'chunks': len(chunks),
                    'segment_count': len(segments), 'durable_transcript_events': events,
                    'timecodes_within_original': limits, 'human_correction_retained_on_real_retry': retained,
                    'fixture_finalized_flag_retained': corrected.finalized,
                    'pending_to_durable_s': timings, 'p50_s': percentile(timings, .5), 'p95_s': percentile(timings, .95),
                    'segment_text': [item.text for item in segments], 'browser_sse_visibility_measured': False}
    finally:
        live_speech.stop_worker()


def main():
    import numpy as np
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline-manifest', type=Path)
    parser.add_argument('--industrial-manifest', type=Path, help='Reuse exact already generated fixtures')
    parser.add_argument('--models', type=Path, help='Separate model directory; never changes installed small config')
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--skip-worker', action='store_true')
    parser.add_argument('--rescore', type=Path, help='Rescore existing unchanged transcripts; preserve raw report')
    parser.add_argument('--report', type=Path, default=ROOT / 'logs' / 'foresight-runtime' / 'speech-corpus-qualification.json')
    args = parser.parse_args()
    if args.rescore:
        original = args.rescore.read_bytes()
        preserved = args.rescore.with_name(args.rescore.stem + '-raw-' + uuid.uuid4().hex[:8] + '.json')
        preserved.write_bytes(original)
        report = score_report(json.loads(original))
        report['rescored_from_existing_transcripts_at'] = datetime.now(timezone.utc).isoformat()
        report['preserved_raw_report'] = str(preserved.resolve())
        args.rescore.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({key: report[key] for key in ('clean_industrial_weighted_wer', 'critical_correct',
            'critical_total', 'critical_failures', 'industrial_quality_gate_passed', 'preserved_raw_report')}, ensure_ascii=False))
        return 0
    directory = args.report.parent / ('speech-corpus-' + uuid.uuid4().hex)
    directory.mkdir(parents=True)
    os.environ.update(MINIPILOT_HOME=str(directory / 'erp'), PB_DATABASE_URL='sqlite:///' + (directory / 'brain.db').as_posix(),
        PB_STORAGE_DIR=str(directory / 'storage'), PB_MEMORY_ENGINE='fake', AGENT_TESTING='1', AGENT_MEETING_SESSIONS_ENABLED='1',
        AGENT_OPERATOR_ROLE='owner', AGENT_OPERATOR_ID='qualification')
    os.environ.pop('AGENT_OPERATOR_PROJECT_IDS', None)
    if args.models:
        os.environ['PB_SPEECH_MODELS_DIR'] = str(args.models.resolve())
    os.environ['PB_SPEECH_THREADS'] = str(args.threads)
    sys.path.insert(0, str(ROOT))
    from app.services.live_speech import ResidentWhisper, model_fingerprint, speech_profile, speech_profile_key
    from app.services.audio_capture import PreparedAudio
    if args.industrial_manifest:
        items = json.loads(args.industrial_manifest.read_text(encoding='utf-8'))
        for item, (_, critical) in zip(items, INDUSTRIAL, strict=True):
            item['critical'] = critical
        voice = 'Hortense (exact pre-existing SAPI fixtures)'
    else:
        items, voice = synthesize(directory)
    if args.baseline_manifest:
        items.extend({**item, 'critical': {}, 'baseline': True} for item in json.loads(args.baseline_manifest.read_text(encoding='utf-8')))
    runtime = ResidentWhisper(directory)
    cases = []
    from scripts.qualify_speech_resources import ProcessTreeMeter
    runtime.start()
    if args.models and runtime.models.resolve() != args.models.resolve():
        raise ValueError('Le modèle effectivement chargé diffère du modèle demandé')
    config = json.loads((runtime.models / 'models.json').read_text(encoding='utf-8'))
    if runtime.ready_details.get('model') != config.get('model'):
        raise ValueError('Le worker ne confirme pas le modèle attendu')
    meter = ProcessTreeMeter(runtime.process.pid)

    def qualify(item, path, mode):
        observed = runtime.transcribe(PreparedAudio(path, 0, 0, None, False), track='system')
        text = ' '.join(row['text'] for row in observed['segments'])
        checks = {key: {'passed': bool(re.search(pattern, fold(text))), 'expected_pattern': pattern}
                  for key, pattern in item.get('critical', {}).items()}
        case = {'reference': item['text'], 'transcript': text, 'condition': mode, 'audio': str(path),
                'audio_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), **wer(item['text'], text),
                'critical_fields': checks, 'duration_ms': observed['duration_ms'], 'compute_s': observed['compute_s'],
                'real_time_factor': observed['compute_s'] / (observed['duration_ms'] / 1000),
                'timecodes': observed['segments']}
        cases.append(case)
        print(json.dumps({'progress': len(cases), 'condition': mode, 'wer': case['wer'],
                          'compute_s': case['compute_s']}, ensure_ascii=False), flush=True)
        return case

    try:
        for i, item in enumerate(items):
            path = directory / f'normalized-{i+1:02d}.wav'
            normalize(item['file'], path)
            qualify(item, path, 'clean_sapi_baseline' if item.get('baseline') else 'clean_sapi_industrial')
        chosen = directory / 'normalized-04.wav'
        with wave.open(str(chosen), 'rb') as source:
            samples = np.frombuffer(source.readframes(source.getnframes()), dtype='<i2').astype(np.float32)
        random = np.random.default_rng(1729)
        noise = random.normal(0, np.sqrt(np.mean(samples**2)) / 10**(12/20), len(samples))
        noisy = directory / 'noise-snr12db.wav'
        noisy.write_bytes(pcm(np.clip(samples + noise, -32768, 32767).astype('<i2').tobytes()))
        qualify(items[3], noisy, 'synthetic_white_noise_snr12db')
        phone = directory / 'telephone8k.wav'
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(chosen),
            '-af', 'lowpass=f=3400,highpass=f=300', '-ar', '8000', str(phone)], check=True,
            capture_output=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
        qualify(items[3], phone, 'synthetic_telephone_band_8k')
        with wave.open(str(directory / 'normalized-05.wav'), 'rb') as source:
            other = np.frombuffer(source.readframes(source.getnframes()), dtype='<i2').astype(np.float32)
        overlap = np.zeros(max(len(samples), len(other) + 3200), np.float32)
        overlap[:len(samples)] += samples / 2
        overlap[3200:3200 + len(other)] += other / 2
        overlapping = directory / 'same-voice-overlap.wav'
        overlapping.write_bytes(pcm(np.clip(overlap, -32768, 32767).astype('<i2').tobytes()))
        qualify({'text': items[3]['text'] + ' ' + items[4]['text'], 'critical': {**items[3]['critical'], **items[4]['critical']}},
                overlapping, 'synthetic_same_voice_overlap_200ms')
    finally:
        resources = meter.finish()
        resources['model_load_s'] = runtime.ready_details['load_s']
        runtime.close()
    worker = {'passed': True, 'not_run': True} if args.skip_worker else qualify_worker(directory, directory / 'normalized-01.wav')
    industrial = [case for case in cases if case['condition'] == 'clean_sapi_industrial']
    errors, count = sum(case['errors'] for case in industrial), sum(case['reference_words'] for case in industrial)
    checks = [check for case in industrial for check in case['critical_fields'].values()]
    failed_fields = [{'case': i + 1, 'field': key, 'transcript': case['transcript']} for i, case in enumerate(industrial)
                     for key, value in case['critical_fields'].items() if not value['passed']]
    report = {'created_at': datetime.now(timezone.utc).isoformat(), 'directory': str(directory),
              'model_sha256': model_fingerprint(), 'models': str(runtime.models.resolve()), 'actual_model': runtime.ready_details['model'],
              'runtime_profile': speech_profile(runtime.models), 'runtime_profile_key': speech_profile_key(runtime.models),
              'synthetic_voice': voice, 'synthetic_speaker_count': 1,
              'operational_passed': bool(cases and worker['passed']),
              'industrial_quality_gate_passed': errors / max(1, count) <= .10 and all(check['passed'] for check in checks),
              'quality_thresholds_provisional': {'weighted_wer_max': .10, 'critical_fields_expected': 'all exact values checked by declared patterns'},
              'clean_industrial_weighted_wer': errors / max(1, count), 'critical_correct': sum(check['passed'] for check in checks),
              'critical_total': len(checks), 'critical_failures': failed_fields,
              'compute_p50_s': percentile([case['compute_s'] for case in cases], .5),
              'compute_p95_s': percentile([case['compute_s'] for case in cases], .95), 'worker': worker, 'cases': cases,
              'resources': resources, 'wer_normalization': 'French accents/punctuation, declared numeric spelling and unit symbol equivalents',
              'real_meeting_accuracy_qualified': False, 'real_multi_speaker_quality_qualified': False,
              'physical_hardware_or_teams_tested': False, 'production_data_modified': False}
    score_report(report)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({key: report[key] for key in ('directory', 'operational_passed', 'industrial_quality_gate_passed',
        'clean_industrial_weighted_wer', 'critical_correct', 'critical_total', 'critical_failures', 'compute_p50_s', 'compute_p95_s', 'worker')}, ensure_ascii=False))
    return 0 if report['operational_passed'] else 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
