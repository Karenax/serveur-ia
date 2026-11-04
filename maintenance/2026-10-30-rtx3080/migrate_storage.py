"""Verify SSD model samples, copy/verify PLE, and update active storage paths."""
import hashlib
import json
from pathlib import Path
import shutil
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / 'stockage-F'
OLD_MODEL = 'D:/Serveur IA/strata-data/model-q4/Qwen3.8-Flash-Next-Uncensored-IQ4_XS-00001-of-00003.gguf'
NEW_MODEL = 'F:/Qwen3.8-Flash-Next-Uncensored-IQ4_XS-00001-of-00003.gguf'
OLD_PLE = 'C:/Temp/Strata-ngram-recherche/iq4-xs-ple-iq4_nl.gguf'
NEW_PLE = 'F:/iq4-xs-ple-iq4_nl.gguf'


def write(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    OUT.mkdir(exist_ok=False)
    samples = []
    for index in range(1, 4):
        old = Path(OLD_MODEL.replace('00001-of-', f'{index:05d}-of-'))
        new = Path(NEW_MODEL.replace('00001-of-', f'{index:05d}-of-'))
        size = old.stat().st_size
        assert new.stat().st_size == size, new
        hashes = []
        with old.open('rb') as source, new.open('rb') as target:
            for offset in sorted({0, size - 2**20, *[int((size - 2**20) * n / 15) for n in range(1, 15)]}):
                source.seek(offset)
                target.seek(offset)
                a, b = source.read(2**20), target.read(2**20)
                assert a == b, (new, offset)
                hashes.append({'offset': offset, 'bytes': len(a), 'sha256': hashlib.sha256(a).hexdigest()})
        samples.append({'source': str(old.resolve()), 'target': str(new.resolve()), 'size': size,
                        'sample_blocks': hashes, 'full_file_hash_verified': False})
        print('Model size and 16 distributed sample blocks match: ' + new.name, flush=True)
    write('model-sample-validation.json', samples)
    source, target = Path(OLD_PLE), Path(NEW_PLE)
    temporary = target.with_suffix(target.suffix + '.copying-20261030')
    assert not target.exists() and not temporary.exists()
    h = hashlib.sha256()
    started = time.monotonic()
    copied = 0
    next_print = 0
    with source.open('rb') as src, temporary.open('xb') as dst:
        while data := src.read(16 * 2**20):
            h.update(data)
            dst.write(data)
            copied += len(data)
            if time.monotonic() - started > next_print:
                print(json.dumps({'ple_copied_gib': round(copied / 2**30, 2), 'seconds': round(time.monotonic() - started)}), flush=True)
                next_print += 30
    with temporary.open('rb') as stream:
        target_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
    assert copied == source.stat().st_size and target_hash == h.hexdigest()
    temporary.rename(target)
    write('ple-copy-validation.json', {'source': str(source), 'target': str(target), 'bytes': copied,
                                     'source_sha256': h.hexdigest(), 'target_sha256': target_hash,
                                     'full_hash_verified': True, 'source_retained_until_load_validation': True})
    print('PLE full SHA-256 verified: ' + target_hash, flush=True)
    names = ['lanceur/base-strata.json', 'strata-iq4-p100-hybride.json', 'lanceur/reglages.json',
             'lanceur/reglages-par-defaut.json', 'lanceur/derniers-reglages-valides.json']
    changes = []

    def replace(value):
        if isinstance(value, dict):
            return {k: replace(v) for k, v in value.items()}
        if isinstance(value, list):
            return [replace(v) for v in value]
        if isinstance(value, str):
            norm = value.replace('\\', '/')
            if norm == OLD_MODEL:
                return NEW_MODEL
            if norm == OLD_PLE:
                return NEW_PLE
        return value

    for name in names:
        path = ROOT / name
        backup = OUT / 'avant' / name
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup)
        before = json.loads(path.read_text(encoding='utf-8-sig'))
        after = replace(before)
        if before != after:
            path.write_text(json.dumps(after, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        changes.append({'path': name, 'changed': before != after, 'before_sha256': hashlib.sha256(backup.read_bytes()).hexdigest(),
                        'after_sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    write('configuration-changes.json', changes)
    print('Active storage profiles updated; source PLE retained until real load succeeds.', flush=True)


if __name__ == '__main__':
    main()
