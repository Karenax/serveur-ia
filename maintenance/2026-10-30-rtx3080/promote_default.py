"""Promote a completed production smoke test without overwriting unrelated settings."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'lanceur'))
from core import build_config, defaults_from_config, read_json, write_json, validate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('validated_run', type=Path)
    parser.add_argument('--backup-dir', type=Path, default=HERE / 'default-architecture/avant')
    parser.add_argument('--status-dir', type=Path, default=HERE / 'default-architecture')
    options = parser.parse_args()
    run = options.validated_run.resolve()
    final = read_json(run / 'final.json')
    assert final and final['error'] is None and final['fingerprints_identical'], final
    results = read_json(run / 'results.json')
    assert results and all(row['quality_pass'] for row in results), results
    image = next(row for row in results if row['label'] == 'vision')['content'].lower()
    assert '47' in image and ('cercle' in image or 'rond' in image) and ('carré' in image or 'carre' in image), image
    cfg = read_json(run / 'config.json')
    settings = defaults_from_config(cfg)
    assert settings['context'] == 262144, settings['context']
    assert settings['gpus'].split(',') == [
        'GPU-c7ec5bca-5502-9e99-2ede-30270b7bde2f',
        'GPU-a39f1b57-5a26-b53d-e943-44ef8042a438',
        'GPU-486d5352-582e-2880-78bf-3dec4688e142',
    ]
    assert cfg['vision']['cuda_device'] == 'GPU-97ca6406-8625-b829-b053-191c238ff046'
    assert Path(cfg['exe']).resolve() == Path('F:/Kiara/moteurs/strata-0.1.54-cuda12/strata.exe').resolve()
    assert hashlib.sha256(Path(cfg['exe']).read_bytes()).hexdigest() == '53b22657c08456b8101eac987fae2c8232d737758c687586ca5e571b78afe6e2'
    folder = options.status_dir
    backup = options.backup_dir
    names = ['lanceur/base-strata.json', 'strata-iq4-p100-hybride.json',
             'lanceur/reglages.json', 'lanceur/reglages-par-defaut.json']
    for name in names:
        assert read_json(ROOT / name) == read_json(backup / name), f'Profile changed externally: {name}'
    settings.update(host=read_json(backup / 'lanceur/reglages.json')['host'], port=8080)
    cfg['env'].pop('STRATA_P100_DIAGNOSTIC_SYNC_FILE', None)
    cfg = build_config(cfg, settings, ROOT / 'strata-engine-iq4-rtx3080.log')
    validate(settings, check_paths=True)
    assert build_config(cfg, defaults_from_config(cfg))['args'] == cfg['args']
    for name in names[:2]:
        write_json(ROOT / name, cfg)
    for name in names[2:]:
        write_json(ROOT / name, settings)
    write_json(folder / 'status.json', {
        'phase': 'defaults_saved_pending_managed_start', 'validated_run': str(run),
        'context': settings['context'], 'gpus': settings['gpus'], 'mtp': settings['mtp_enabled'],
        'kv_resident': cfg['args'][cfg['args'].index('--kv-resident') + 1] if '--kv-resident' in cfg['args'] else 0,
        'sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in names},
    })
    print('Defaults saved; managed restart and final verification remain.')


if __name__ == '__main__':
    main()
