"""Explicit direct-ASR choice. Import never opens a device or model."""
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import re

from scripts import speech_runtime

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / '.runtime' / 'speech-cuda'
SCHEMA = 'agent-speech-cuda-runtime-v1'


def configured_device(db=None):
    if 'PB_SPEECH_DEVICE' in os.environ:
        return speech_runtime.device()
    from .settings_service import get_section
    if db is None:
        from app.db import SessionLocal
        with SessionLocal() as connection:
            return configured_device(connection)
    value = get_section(db, 'foresight').get('live_speech_device', 'cpu')
    # Optional settings serialized by legacy clients may contain JSON null.
    # An unset choice uses CPU; explicit invalid choices remain errors.
    if value is None:
        return 'cpu'
    if value not in ('cpu', 'cuda'):
        raise ValueError('Le calcul de la transcription directe doit être CPU ou GPU')
    return value


@lru_cache(maxsize=4)
def _verify(identity):
    for path, digest, _, _ in identity:
        actual = hashlib.sha256()
        with Path(path).open('rb') as source:
            while block := source.read(2 * 1024 * 1024):
                actual.update(block)
        if actual.hexdigest() != digest:
            raise ValueError('Une bibliothèque de transcription GPU a changé ; réinstaller le runtime')


def bundle_directories():
    base = BUNDLE.resolve(strict=True)
    manifest = json.loads((base / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('schema') != SCHEMA or not isinstance(manifest.get('files'), list) or not manifest['files']:
        raise ValueError('Installation GPU de transcription incomplète')
    identities = []
    for entry in manifest['files']:
        relative = Path(entry['relative_path'])
        path = (base / relative).resolve(strict=True)
        if relative.is_absolute() or not path.is_relative_to(base) or path.suffix.lower() != '.dll':
            raise ValueError('Bibliothèque GPU hors installation autorisée')
        stat = path.stat()
        if stat.st_size != entry['bytes']:
            raise ValueError('Bibliothèque GPU de taille différente ; réinstaller le runtime')
        identities.append((str(path), entry['sha256'], stat.st_size, stat.st_mtime_ns))
    actual = {str(path.resolve(strict=True)) for name in ('cublas', 'cudnn')
        for path in (base / name / 'bin').glob('*.dll')}
    if actual != {identity[0] for identity in identities}:
        raise ValueError('Le contenu du runtime GPU ne correspond plus au manifeste')
    _verify(tuple(identities))
    # CTranslate2 explicitly loads its bundled cuDNN. Preserve that actual
    # loader path; NVIDIA's separate directory supplies the other components.
    bundled = ROOT / '.venv-speech' / 'Lib' / 'site-packages' / 'ctranslate2'
    return speech_runtime.cuda_directories([str(base / 'cublas' / 'bin'),
        str(base / 'cudnn' / 'bin'), str(bundled)])


def cuda_profile(models):
    directories = None if 'PB_SPEECH_DEVICE' in os.environ else bundle_directories()
    return speech_runtime.configured_cuda_profile(models, directories=directories)


def describe(db):
    available, detail = False, 'Installer les bibliothèques locales pour proposer le GPU.'
    try:
        bundle_directories()
        available, detail = True, 'Bibliothèques GPU installées pour le direct en essai ; le texte reste à relire.'
    except (OSError, ValueError, KeyError, TypeError):
        pass
    try:
        selected = configured_device(db)
    except ValueError as exc:
        selected, detail = None, str(exc)
    return {'selected': selected, 'cuda_available': available,
        'environment_override': 'PB_SPEECH_DEVICE' in os.environ, 'detail': detail,
        'selection_starts_model': False}


def validate_operational_evidence(evidence, *, model_identity, runtime_profile):
    """A real fictitious pipeline sample qualifies operation, never physical audio."""
    if not isinstance(evidence, dict) or evidence.get('schema') != 'agent-speech-operational-evidence-v1':
        return None
    try:
        if evidence.get('operational_pipeline_passed') is not True:
            return None
        if any(evidence.get(key) is not False for key in ['industrial_quality_qualified',
                'physical_microphone_test', 'physical_capture_qualified', 'qualified_live_latency']):
            return None
        if evidence.get('resident_and_owned_Job_closed') is not True:
            return None
        identity = evidence.get('model_identity')
        if (not isinstance(identity, dict) or identity != model_identity
                or type(identity.get('size')) is not int or type(identity.get('mtime_ns')) is not int
                or not isinstance(evidence.get('model_sha256'), str)
                or not re.fullmatch('[0-9a-f]{64}', evidence['model_sha256'])):
            return None
        if runtime_profile.get('device') != 'cuda' or evidence.get('runtime_profile') != runtime_profile:
            return None
        if not isinstance(evidence.get('model'), str) or not evidence['model'] or evidence['model'] != runtime_profile.get('model'):
            return None
        key = speech_runtime.profile_key(runtime_profile)
        if evidence.get('runtime_profile_key') != key or speech_runtime.profile_key(evidence['runtime_profile']) != key:
            return None
        speech_runtime.validate_observation(evidence.get('actual_native_constructor'), runtime_profile)
        population = evidence['population']
        utterances, visible, packets = (population[name] for name in [
            'fictitious_utterances', 'actual_visible_text_receipts', 'stored_and_processed_packets'])
        if any(type(value) is not int or value <= 0 for value in [utterances, visible, packets]):
            return None
        if visible != utterances:
            return None
    except (AttributeError, KeyError, TypeError, ValueError):
        return None
    return {'operational_pipeline_test_passed': True, 'validation_scope': 'fictitious_integrated_pipeline',
        'runtime_profile_key': key, 'physical_capture_qualified': False,
        'industrial_quality_qualified': False, 'qualified_live_latency': False}


def operational_readiness(status, model_identity):
    if (status.get('ready') is True or status.get('installed') is not True
            or 'PB_SPEECH_QUALIFICATION_REPORT' in os.environ):
        return status
    try:
        evidence = json.loads((BUNDLE / 'operational-evidence-active.json').read_text(encoding='utf-8'))
        validation = validate_operational_evidence(evidence, model_identity=model_identity,
            runtime_profile=status.get('runtime_profile'))
    except (OSError, ValueError, TypeError):
        return status
    if validation is None:
        return status
    return {**status, **validation, 'ready': True, 'real_test_passed': True,
        'real_test_model': evidence['model'], 'physical_microphone_test_passed': False}
