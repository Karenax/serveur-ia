"""Direct GPU selection, isolated SQL/files; never load a native library/model."""
import hashlib
import json
import os

import pytest
from fastapi import HTTPException

from app.db import SessionLocal
from app.models import AppSetting
from app.routers import fusion_insights as route
from app.services import live_speech, speech_acceleration as acceleration
from app.services.settings_service import get_section, save_section
from scripts import speech_runtime


@pytest.fixture
def installed(tmp_path, monkeypatch):
    monkeypatch.delenv('PB_SPEECH_DEVICE', raising=False)
    monkeypatch.delenv('PB_SPEECH_MODELS_DIR', raising=False)
    monkeypatch.delenv('PB_SPEECH_THREADS', raising=False)
    monkeypatch.setattr(acceleration, 'ROOT', tmp_path)
    monkeypatch.setattr(acceleration, 'BUNDLE', tmp_path / '.runtime/speech-cuda')
    monkeypatch.setattr(live_speech, 'ROOT', tmp_path)
    files = []
    for relative in ['cublas/bin/cublas64_12.dll', 'cublas/bin/cublasLt64_12.dll', 'cudnn/bin/cudnn64_9.dll']:
        path = acceleration.BUNDLE / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = b'FICTITIOUS DLL, NEVER LOAD'
        path.write_bytes(raw)
        files.append({'relative_path': relative, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
    bundled = tmp_path / '.venv-speech/Lib/site-packages/ctranslate2'
    bundled.mkdir(parents=True)
    (bundled / 'cudnn64_9.dll').write_bytes(b'FICTITIOUS, NEVER LOAD')
    (acceleration.BUNDLE / 'manifest.json').write_text(json.dumps({'schema': acceleration.SCHEMA, 'files': files}))
    models = tmp_path / '.models/audio-medium'
    models.mkdir(parents=True)
    whisper = models / 'whisper-medium'
    whisper.mkdir()
    (whisper / 'model.bin').write_bytes(b'FICTITIOUS, NOT WEIGHTS')
    config = {'model': 'medium', 'whisper': str(whisper), 'cpu_threads': 4}
    for name in ['segmentation', 'embedding']:
        path = models / (name + '.onnx')
        path.write_bytes(b'FICTITIOUS')
        config[name] = str(path)
    (models / 'models.json').write_text(json.dumps(config))
    with SessionLocal() as db:
        before = db.get(AppSetting, 'foresight')
        original = None if before is None else dict(before.value)
        save_section(db, 'foresight', {'enabled': True, 'live_transcription_enabled': False, 'live_speech_device': 'cpu'})
        try:
            yield db, models
        finally:
            db.rollback()
            row = db.get(AppSetting, 'foresight')
            if original is None:
                db.delete(row)  # Only this fixture-created setting in the temporary test DB.
                db.commit()
            else:
                row.value = original
                db.commit()


def test_default_CPU_and_GPU_choice_open_no_native_runtime(installed):
    db, models = installed
    assert acceleration.configured_device(db) == 'cpu'
    assert acceleration.describe(db)['cuda_available'] is True
    save_section(db, 'foresight', {'live_speech_device': 'cuda'})
    assert live_speech.runtime_paths()[1] == models
    profile = live_speech.speech_profile(models)
    assert profile['device'] == 'cuda' and profile['model'] == 'medium'
    assert acceleration.describe(db)['selection_starts_model'] is False


def test_null_optional_choice_defaults_to_CPU_without_loading_or_rewriting(installed, monkeypatch):
    db, _ = installed
    save_section(db, 'foresight', {'live_speech_device': None})
    monkeypatch.setattr(acceleration, 'cuda_profile', lambda *args: pytest.fail('No GPU profile for an unset choice'))
    monkeypatch.setattr(live_speech, 'ResidentWhisper', lambda *args, **kwargs: pytest.fail('No model while reading settings'))
    assert acceleration.configured_device(db) == 'cpu'
    assert get_section(db, 'foresight')['live_speech_device'] is None


@pytest.mark.parametrize('value', ['', 'invalid', True, False, 0, 1, [], {}])
def test_explicit_invalid_saved_choice_remains_refused(installed, value):
    db, _ = installed
    save_section(db, 'foresight', {'live_speech_device': value})
    with pytest.raises(ValueError, match='CPU ou GPU'):
        acceleration.configured_device(db)


def test_settings_GPU_and_child_environment_have_identical_profile_without_global_mutation(installed, monkeypatch):
    db, models = installed
    save_section(db, 'foresight', {'live_speech_device': 'cuda'})
    parent = live_speech.speech_profile(models)
    before = dict(os.environ)
    child = speech_runtime.child_environment(parent)
    assert dict(os.environ) == before and child['PB_SPEECH_DEVICE'] == 'cuda'
    with monkeypatch.context() as scope:
        for key in ['PB_SPEECH_DEVICE', 'PB_SPEECH_CUDA_DLL_DIRS', 'PB_SPEECH_THREADS']:
            scope.setenv(key, child[key])
        observed = speech_runtime.configured_cuda_profile(models)
    assert observed == parent
    assert speech_runtime.profile_key(observed) == speech_runtime.profile_key(parent)


def test_changed_DLL_is_rejected_instead_of_loading_or_falling_back(installed):
    db, models = installed
    save_section(db, 'foresight', {'live_speech_device': 'cuda'})
    assert live_speech.speech_profile(models)['device'] == 'cuda'
    path = acceleration.BUNDLE / 'cublas/bin/cublas64_12.dll'
    path.write_bytes(b'TAMPERED, NEVER LOAD')
    with pytest.raises(ValueError):
        live_speech.speech_profile(models)
    assert acceleration.configured_device(db) == 'cuda'
    assert not acceleration.describe(db)['cuda_available']


def test_direct_GPU_choice_keeps_complete_and_grouped_profiles_on_CPU(installed, tmp_path):
    db, models = installed
    save_section(db, 'foresight', {'live_speech_device': 'cuda'})
    from app.services import session_batch_transcription, grouped_batch
    resident = session_batch_transcription._new_resident(tmp_path)
    assert resident.process is None and resident.device_override == 'cpu'
    assert live_speech.speech_profile(models)['device'] == 'cuda'
    assert live_speech.speech_profile(models, device_override=resident.device_override)['device'] == 'cpu'
    assert grouped_batch._profile_snapshot()['profile']['device'] == 'cpu'


def test_complete_runtime_availability_does_not_depend_on_direct_GPU_readiness(installed, monkeypatch):
    db, _ = installed
    save_section(db, 'foresight', {'live_speech_device': 'cuda'})
    from app.services import session_batch_transcription, meeting_audio
    monkeypatch.setattr(live_speech, 'runtime_status', lambda: pytest.fail('Do not use direct qualification for full audio'))
    monkeypatch.setattr(meeting_audio, 'runtime_status', lambda **kwargs: {'ready': True})
    assert session_batch_transcription.available() is True


def test_complete_capability_remains_available_if_saved_direct_GPU_is_unavailable(installed, monkeypatch):
    db, _ = installed
    save_section(db, 'foresight', {'live_speech_device': 'cuda'})
    from app.services import meeting_sessions, session_batch_transcription, meeting_audio, native_audio
    monkeypatch.setattr(live_speech, 'runtime_status', lambda: {'ready': False, 'installed': False, 'device': 'cuda'})
    monkeypatch.setattr(meeting_audio, 'runtime_status', lambda **kwargs: {'ready': True, 'detail': 'CPU batch'})
    monkeypatch.setattr(session_batch_transcription, 'available', lambda: True)
    monkeypatch.setattr(native_audio, 'status', lambda *args: {})
    assert meeting_sessions.capabilities(db)['transcription']['session_batch_ready'] is True


def test_environment_selection_remains_explicit_and_does_not_use_bundle(installed, monkeypatch):
    db, _ = installed
    monkeypatch.setenv('PB_SPEECH_DEVICE', 'cpu')
    save_section(db, 'foresight', {'live_speech_device': 'cuda'})
    assert acceleration.configured_device(db) == 'cpu'
    assert acceleration.describe(db)['environment_override']


def test_invalid_environment_is_reported_without_hiding_the_settings_page(installed, monkeypatch):
    db, _ = installed
    monkeypatch.setenv('PB_SPEECH_DEVICE', 'invalid')
    result = acceleration.describe(db)
    assert result['selected'] is None and result['environment_override']
    assert 'PB_SPEECH_DEVICE' in result['detail']


@pytest.fixture
def control_calls(installed, monkeypatch):
    events = []
    monkeypatch.setattr(route.sessions, 'capabilities', lambda db: {})
    monkeypatch.setattr(live_speech, 'stop_worker', lambda **kwargs: events.append('stop-direct'))
    from app.services import audio_cpu_coordinator
    monkeypatch.setattr(audio_cpu_coordinator, '_running_batch', lambda db: False)
    return installed[0], events


def test_invalid_GPU_installation_preserves_setting_and_running_worker(control_calls, monkeypatch):
    db, events = control_calls
    def unavailable(*args):
        raise ValueError('Fictitious unavailable dependency')
    monkeypatch.setattr(acceleration, 'cuda_profile', unavailable)
    with pytest.raises(HTTPException) as failure:
        route._configure(route.Controls(enabled=True, live_speech_device='cuda'), db)
    assert failure.value.status_code == 422 and events == []
    assert get_section(db, 'foresight')['live_speech_device'] == 'cpu'


def test_GPU_choice_is_persisted_and_older_clients_cannot_reset_it(control_calls):
    db, events = control_calls
    result = route._configure(route.Controls(enabled=True, live_speech_device='cuda'), db)
    assert result['live_speech_device'] == 'cuda' and events[0] == 'stop-direct'
    result = route._configure(route.Controls(enabled=True), db)
    assert result['live_speech_device'] == 'cuda'
    assert get_section(db, 'foresight')['live_speech_device'] == 'cuda'
    result = route._configure(route.Controls(enabled=True, live_speech_device='cpu'), db)
    assert result['live_speech_device'] == 'cpu'


def test_full_transcription_blocks_device_change_without_cancelling_it(control_calls, monkeypatch):
    db, events = control_calls
    from app.services import audio_cpu_coordinator
    monkeypatch.setattr(audio_cpu_coordinator, '_running_batch', lambda db: True)
    with pytest.raises(HTTPException) as failure:
        route._configure(route.Controls(enabled=True, live_speech_device='cuda'), db)
    assert failure.value.status_code == 409 and events == []
    assert get_section(db, 'foresight')['live_speech_device'] == 'cpu'


def test_operator_configuration_override_cannot_be_silently_ignored(control_calls, monkeypatch):
    db, events = control_calls
    monkeypatch.setenv('PB_SPEECH_DEVICE', 'cpu')
    with pytest.raises(HTTPException) as failure:
        route._configure(route.Controls(enabled=True, live_speech_device='cuda'), db)
    assert failure.value.status_code == 409 and events == []
