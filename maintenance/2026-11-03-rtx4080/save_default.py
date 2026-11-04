"""Save the authorized, previously measured RTX 4080/DFlash2 default profile."""
import copy
import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = HERE / 'default-mode'
sys.path.insert(0, str(ROOT / 'lanceur'))
from core import arg, build_config, defaults_from_config, read_json, validate, write_json


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verified_copy(source, destination, expected):
    if digest(source) != expected:
        raise ValueError(f'Source checksum differs: {source}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if digest(destination) != expected:
            raise FileExistsError(destination)
    else:
        shutil.copy2(source, destination)
    if digest(destination) != expected:
        raise ValueError(f'Copied checksum differs: {destination}')


def main():
    OUT.mkdir(exist_ok=False)
    names = ['lanceur/base-strata.json', 'strata-iq4-p100-hybride.json',
             'lanceur/reglages.json', 'lanceur/reglages-par-defaut.json',
             'lanceur/derniers-reglages-valides.json', 'lanceur/exploitation.json']
    before = {name: digest(ROOT / name) for name in names}
    for name in names:
        destination = OUT / 'before' / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    measured = read_json(HERE / 'v0156-dflash2-auto-c08-repeat/config.json')
    final = read_json(HERE / 'v0156-dflash2-auto-c08-repeat/final.json')
    assert final['error'] is None and final['fingerprints_identical']
    package = Path('F:/Kiara-tests/strata-0.1.56-cuda12/package')
    runtime = Path('F:/Kiara/moteurs/strata-0.1.56-cuda12')
    manifest = read_json(package / 'engine-component.json')
    for row in manifest['files']:
        verified_copy(package / row['path'], runtime / row['path'], row['sha256'])
    verified_copy(package / 'engine-component.json', runtime / 'engine-component.json', digest(package / 'engine-component.json'))
    drafter = Path('F:/Kiara/modeles/dflash2/qwen3.8-flash-next-dflash2.q4_0-selq4.pack')
    verified_copy(Path(arg(measured, '--draft-model')), drafter,
                  '4a42b98220ea7880664002c8edda1563aecbae754b762a2e2f31b2b91ee93ecd')
    cfg = copy.deepcopy(read_json(ROOT / 'strata-iq4-p100-hybride.json'))

    def remove(flag):
        while flag in cfg['args']:
            index = cfg['args'].index(flag)
            del cfg['args'][index:index + 2]

    def setarg(flag, value):
        remove(flag)
        cfg['args'].extend([flag, str(value)])

    remove('--mtp')
    remove('--layer-split')
    remove('--split-device')
    for flag, value in [('--expert-cache', 'auto'), ('--spec', 6), ('--draft', 'dflash2'),
                        ('--draft-model', drafter), ('--draft-fallback', 'none'),
                        ('--mtp-draft-vocab', arg(measured, '--mtp-draft-vocab')), ('--draft-conf', 0.8),
                        ('--expert-cache-device1', 'auto'), ('--expert-cache-device2', 'auto')]:
        setarg(flag, value)
    cfg['exe'] = str(runtime / 'strata.exe')
    cfg['lib_dirs'] = [str(runtime)]
    cfg['env']['CUDA_VISIBLE_DEVICES'] = measured['env']['CUDA_VISIBLE_DEVICES']
    cfg['env'].pop('STRATA_P100_DIAGNOSTIC_SYNC_FILE', None)
    settings = {}
    for name in names[2:5]:
        current = read_json(ROOT / name)
        current.update(exe=cfg['exe'], gpus=cfg['env']['CUDA_VISIBLE_DEVICES'], expert_cache='auto',
                       mtp_enabled=False, spec=6)
        settings[name] = validate(current, check_paths=True)
    cfg = build_config(cfg, settings['lanceur/reglages.json'], ROOT / 'strata-engine-iq4-rtx4080.log')
    assert arg(cfg, '--spec') == '6' and '--mtp' not in cfg['args']
    assert cfg.get('vision', {}).get('cuda_device') == 'GPU-97ca6406-8625-b829-b053-191c238ff046'
    assert build_config(cfg, defaults_from_config(cfg))['args'] == cfg['args']
    assert before == {name: digest(ROOT / name) for name in names}, 'Settings changed during preparation'
    for name in names[:2]:
        write_json(ROOT / name, cfg)
    for name in names[2:4]:
        write_json(ROOT / name, settings[name])
    # Last-known-good is promoted only after the production-like validation.
    write_json(OUT / 'candidate-last-good.json', settings['lanceur/derniers-reglages-valides.json'])
    write_json(OUT / 'status.json', {'phase': 'default_saved_validation_pending',
                                  'time': dt.datetime.now().astimezone().isoformat(),
                                  'engine': cfg['exe'], 'draft_model': str(drafter),
                                  'fingerprints_before': before,
                                  'fingerprints_saved': {name: digest(ROOT / name) for name in names}})
    print('RTX 4080 + two P100, DFlash2, automatic expert cache saved as default; validation pending.')


if __name__ == '__main__':
    main()
