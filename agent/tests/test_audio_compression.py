"""Real codec, journal recovery and speech-decoder round trip, no devices/model."""
import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from app.services.live_speech import runtime_paths
from scripts.audio_codec import opus_duration_ms
from scripts.native_chunk_journal import reconcile, inventory, Limits
from tests.test_meeting_sessions import stores, create, key

__all__ = ['stores']

SID = 'a2c258bb-74b8-4403-8f01-866d81fc5294'


@pytest.fixture
def encoded(tmp_path):
    python = runtime_paths()[0]
    if not python.is_file():
        pytest.skip('Optional speech runtime absent')
    code = '''
import json,sys
from pathlib import Path
import numpy as np
from scripts.audio_codec import encode_opus
from scripts.native_chunk_journal import commit_chunk
from faster_whisper.audio import decode_audio
p=Path(sys.argv[1])
x=(np.sin(np.arange(80000)*2*np.pi*440/16000)*12000).astype('<i2').tobytes()
assert encode_opus(x)==encode_opus(x), 'Codec retry changed bytes'
a=commit_chunk(p,sys.argv[2],'mic',0,x,10800000,codec='opus')
assert commit_chunk(p,sys.argv[2],'mic',0,x,10800000,codec='opus')==a
b=commit_chunk(p,sys.argv[2],'mic',1,x[:3840],10805000,codec='opus')
x=decode_audio(a['path'],sampling_rate=16000)
assert len(x)==80000
assert int(np.argmax(abs(np.fft.rfft(x))))==2200
print(json.dumps([a,b]))
'''
    result = subprocess.run([str(python), '-X', 'utf8', '-c', code, str(tmp_path), SID],
                            cwd=Path(__file__).resolve().parents[1], capture_output=True,
                            text=True, timeout=40, check=True)
    return tmp_path, json.loads(result.stdout)


def test_compressed_journal_exact_retry_tail_and_recovery_without_codec_runtime(encoded):
    folder, packets = encoded
    for packet in packets:
        payload = Path(packet['path']).read_bytes()
        assert packet['sha256'] == hashlib.sha256(payload).hexdigest()
        assert opus_duration_ms(payload) == packet['duration_ms']
    assert packets[0]['size_bytes'] < 24000  # 160044-byte legacy WAV -> ~21 KB
    assert packets[1]['duration_ms'] == 120
    Path(packets[1]['path']).with_suffix('.json').unlink()  # fictitious crash
    assert reconcile(folder, SID, authorize=lambda: None) == packets
    assert inventory(folder, Limits())['audio_bytes'] == sum(p['size_bytes'] for p in packets)


def test_compressed_intent_rejects_corrupt_audio_without_overwriting(encoded):
    folder, packets = encoded
    path = Path(packets[0]['path'])
    before = path.read_bytes()
    data = bytearray(before)
    data[-10] ^= 1
    with pytest.raises(ValueError, match='checksum'):
        opus_duration_ms(data)
    path.write_bytes(data)
    with pytest.raises(ValueError, match='differs'):
        reconcile(folder, SID, authorize=lambda: None)
    assert path.read_bytes() == data


def test_compressed_fragment_has_durable_receipt_and_verified_direct_admission(encoded, stores, monkeypatch):
    from app.services import meeting_sessions, live_speech, native_audio
    from app.services.settings_service import save_section
    monkeypatch.setattr(live_speech, 'wake_worker', lambda: None)
    monkeypatch.setattr(native_audio, 'status', lambda sid=None: {'session': None})
    folder, packets = encoded
    payload = Path(packets[0]['path']).read_bytes()
    with stores[0]() as db:
        save_section(db, 'foresight', {'enabled': True, 'live_transcription_enabled': True})
        sid = create(db, kind='meeting')['id']
        arguments = dict(raw=payload, filename='capture.ogg', mime_type='audio/ogg',
            command_id=key(), sha256=hashlib.sha256(payload).hexdigest(), start_ms=0, duration_ms=5000)
        first = meeting_sessions.store_chunk(db, sid, 'mic', 0, **arguments)
        assert first['acknowledged'] and first['speech_admission']['status'] == 'pending'
        assert meeting_sessions.store_chunk(db, sid, 'mic', 0, **arguments) == first
        arguments.update(command_id=key(), start_ms=5000, duration_ms=1000)
        second = meeting_sessions.store_chunk(db, sid, 'mic', 1, **arguments)
        assert second['acknowledged'] and second['speech_admission']['status'] == 'retained'


def test_download_of_two_compressed_fragments_is_one_complete_stream(encoded, stores, monkeypatch):
    from app.services import meeting_sessions, live_speech, native_audio
    monkeypatch.setattr(live_speech, 'wake_worker', lambda: None)
    monkeypatch.setattr(native_audio, 'status', lambda sid=None: {'session': None})
    folder, packets = encoded
    with stores[0]() as db:
        sid = create(db, kind='meeting')['id']
        for index, packet in enumerate(packets):
            payload = Path(packet['path']).read_bytes()
            meeting_sessions.store_chunk(db, sid, 'mic', index, raw=payload,
                filename='capture.ogg', mime_type='audio/ogg', command_id=key(),
                sha256=hashlib.sha256(payload).hexdigest(), start_ms=index*5000,
                duration_ms=packet['duration_ms'])
        audio, mime, filename = meeting_sessions.consolidated_audio(db, meeting_sessions.get_session(db, sid))
        assert mime == 'audio/ogg' and filename.endswith('.ogg')
        assert opus_duration_ms(audio) == 5120


@pytest.mark.parametrize('previous_status,context', [
    ('pending', True), ('running', True), ('completed', True),
    ('retained', False), ('failed', False), ('batch_pending', False), ('batch_running', False),
])
def test_compressed_context_uses_only_contiguous_admitted_audio(encoded, previous_status, context):
    from app.services.live_speech import prepare_direct_chunk
    folder, packets = encoded
    rows = [{'id': str(i), 'session_id': SID, 'track': 'mic', 'sequence': i,
        'storage_path': p['path'], 'size_bytes': p['size_bytes'], 'sha256': p['sha256'],
        'start_ms': i*5000, 'duration_ms': p['duration_ms'], 'mime_type': 'audio/ogg',
        'speech_status': previous_status if i == 0 else 'running'} for i, p in enumerate(packets)]
    before = {path.name for path in folder.iterdir()}
    prepared = prepare_direct_chunk(rows[1], rows, storage_root=folder, derived_root=folder/'derived')
    assert prepared.assembled is context
    assert prepared.context_path == (Path(packets[0]['path']) if context else None)
    assert prepared.offset_ms == (0 if context else 5000)
    assert prepared.context_ms == (5000 if context else 0)
    assert prepared.clip_end_ms == (5120 if context else 120)
    assert {path.name for path in folder.iterdir()} == before  # no persisted PCM
    if context:
        code = (
            'import json,sys; from pathlib import Path; '
            'from scripts.transcribe_live import decode_request; '
            'from faster_whisper.audio import decode_audio; '
            'r={"path":sys.argv[1],"context":{"path":sys.argv[2],"duration_ms":5000}}; '
            'x=decode_request(r,Path(sys.argv[3]),decode_audio); print(json.dumps({"frames":len(x)}))')
        result = subprocess.run([str(runtime_paths()[0]), '-c', code, str(prepared.path),
            str(prepared.context_path), str(folder)], cwd=Path(__file__).resolve().parents[1],
            capture_output=True, text=True, check=True, timeout=30)
        assert json.loads(result.stdout)['frames'] == 81920  # Previous 5 s + 120 ms, decoded only in memory
    rows[0]['start_ms'] -= 1000
    no_gap_bridge = prepare_direct_chunk(rows[1], rows, storage_root=folder, derived_root=folder/'derived')
    assert no_gap_bridge.context_path is None and no_gap_bridge.offset_ms == 5000


def test_context_outside_storage_is_rejected_before_decoding(tmp_path):
    from scripts.transcribe_live import decode_request
    current = tmp_path/'current.ogg'
    current.write_bytes(b'not decoded')
    decoded = []
    def forbidden(*args, **kwargs):
        decoded.append(args)
        raise AssertionError('Decoder must not run')
    with pytest.raises(ValueError, match='hors limites'):
        decode_request({'path': str(current), 'context': {'path': str(tmp_path.parent/'outside.ogg'),
            'duration_ms':500}}, tmp_path, forbidden)
    assert not decoded
