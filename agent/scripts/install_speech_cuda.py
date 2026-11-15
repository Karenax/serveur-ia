"""Copy already installed NVIDIA packages into Agent's durable speech runtime.

No downloads, imports of NVIDIA code, model loading, microphone or driver changes.
Existing installations are never replaced. Keep package licenses and RECORD proofs.
"""
import argparse
import base64
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = {'cublas': 'nvidia_cublas_cu12-12.9.2.10.dist-info',
            'cudnn': 'nvidia_cudnn_cu12-9.5.1.17.dist-info'}


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as source:
        while block := source.read(2 * 1024 * 1024):
            value.update(block)
    return value.hexdigest()


def _publish(stage, target):
    """Publish without replacement; retain preparation after persistent refusal."""
    deadline = time.monotonic() + 2.0
    while True:
        if os.path.lexists(target):
            raise FileExistsError('Installation existante conservée ; aucune bibliothèque remplacée')
        try:
            os.rename(stage, target)
            return
        except OSError as exc:
            # Windows may briefly deny rename while a freshly written file is
            # open. Do not alter permissions or retry other I/O failures.
            if getattr(exc, 'winerror', None) not in {5, 32, 33} or time.monotonic() >= deadline:
                raise
            time.sleep(0.05)


def install(source, target=None):
    source = Path(source).resolve(strict=True)
    target = Path(target) if target is not None else ROOT / '.runtime/speech-cuda'
    if target.exists():
        raise FileExistsError('Installation existante conservée ; aucune bibliothèque remplacée')
    target.parent.mkdir(parents=True, exist_ok=True)
    candidates, licenses = [], []
    records = []
    for package, metadata in PACKAGES.items():
        record = source / metadata / 'RECORD'
        records.append({'path': str(record), 'sha256': digest(record)})
        with record.open(encoding='utf-8', newline='') as stream:
            entries = {row[0]: row[1:] for row in csv.reader(stream)}
        binaries = sorted((source / 'nvidia' / package / 'bin').glob('*.dll'))
        if not binaries:
            raise ValueError('Paquet NVIDIA incomplet : ' + package)
        license_paths = [p for p in (source / metadata).rglob('*')
            if p.is_file() and p.name.lower().startswith('license')]
        selected = binaries + license_paths
        if not license_paths:
            raise ValueError('Licence NVIDIA absente : ' + package)
        for original in selected:
            original = original.resolve(strict=True)
            if not original.is_relative_to(source):
                raise ValueError('Fichier hors des paquets fournis')
            relative = original.relative_to(source).as_posix()
            recorded_hash, recorded_size = entries[relative]
            if not recorded_hash.startswith('sha256='):
                raise ValueError('Empreinte SHA256 du paquet manquante')
            expected = base64.urlsafe_b64decode(recorded_hash[7:] + '===').hex()
            if original.stat().st_size != int(recorded_size) or digest(original) != expected:
                raise ValueError('Le paquet NVIDIA ne correspond plus à son RECORD')
            destination = (Path(package) / 'bin' / original.name if original.suffix.lower() == '.dll'
                else Path('licenses') / metadata / original.relative_to(source / metadata))
            row = {'relative_path': destination.as_posix(), 'sha256': expected, 'bytes': original.stat().st_size}
            (candidates if original.suffix.lower() == '.dll' else licenses).append((original, row))
    required = {'cublas64_12.dll', 'cublasLt64_12.dll', 'cudnn64_9.dll'}
    if not required.issubset({Path(row['relative_path']).name for _, row in candidates}):
        raise ValueError('Bibliothèques NVIDIA requises absentes')
    total = sum(row['bytes'] for _, row in candidates + licenses)
    if shutil.disk_usage(target.parent).free < total:
        raise OSError('Espace insuffisant pour la copie exacte du runtime')
    stage = target.parent / ('speech-cuda-install-' + uuid4().hex)
    stage.mkdir(exist_ok=False)
    for original, row in candidates + licenses:
        destination = stage / row['relative_path']
        destination.parent.mkdir(parents=True, exist_ok=True)
        with original.open('rb') as src, destination.open('xb') as dst:
            shutil.copyfileobj(src, dst, length=2 * 1024 * 1024)
            dst.flush()
            os.fsync(dst.fileno())
        if digest(destination) != row['sha256']:
            raise ValueError('Échec de relecture de la copie ; préparation conservée')
    manifest = {'schema': 'agent-speech-cuda-runtime-v1', 'at_utc': datetime.now(timezone.utc).isoformat(),
        'files': [row for _, row in candidates], 'licenses': [row for _, row in licenses],
        'packages': PACKAGES, 'source_records': records,
        'provenance': 'Retained installed NVIDIA packages, verified against their RECORD; no wheel reacquisition',
        'download': False, 'source_modified': False, 'model_or_device_opened': False,
        'total_bytes': total}
    with (stage / 'manifest.json').open('x', encoding='utf-8') as stream:
        json.dump(manifest, stream, indent=2, ensure_ascii=False)
        stream.flush()
        os.fsync(stream.fileno())
    _publish(stage, target)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='Dossier local contenant nvidia/ et les dist-info')
    args = parser.parse_args()
    result = install(args.source)
    print(json.dumps({'installed': str(ROOT / '.runtime/speech-cuda'), 'bytes': result['total_bytes'],
        'DLLs': len(result['files']), 'licenses': len(result['licenses']), 'download': False}))
