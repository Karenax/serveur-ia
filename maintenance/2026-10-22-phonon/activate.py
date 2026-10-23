"""Switch Fred only after real French synthesis/cancellation/recovery pass; retain rollback."""
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / 'lanceur'), str(ROOT / 'maintenance'), str(OUT)]
from validate import source_hashes
from phonon_model import verify as verify_checkpoint
from validate_live_lots6_8 import get, models, preserved_files, content_fingerprints, backup_config
import verrous_runtime


def write(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def replacement(path, old, new):
    data = path.read_text(encoding='utf-8')
    assert data.count(old) == 1, 'Unexpected source: ' + str(path)
    return data.replace(old, new)


def restart():
    path = ROOT / 'maintenance/2026-10-21-api-embeddings/livrer.py'
    spec = importlib.util.spec_from_file_location('fred_previous_delivery', path)
    delivery = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(delivery)
    delivery.OUT = OUT
    delivery.restart()


def main():
    verify_checkpoint()
    proof = json.loads((OUT / 'native-validation.json').read_text(encoding='utf-8'))
    assert proof['passed'] and proof['source_sha256'] == source_hashes(), 'Real native tests required'
    assert get('/api/state')['queue']['active'] == 0 and not get('/api/voice')['busy']
    assert get('/api/voice')['enabled'], 'Preserve the existing enabled voice configuration'
    assert not (OUT / 'avant-livraison.json').exists(), 'Existing activation: inspect before retrying'
    service = ROOT / 'lanceur/voice.py'
    service_text = replacement(service, "'engine':'Pocket TTS 3.3.0','language':'fr','voice':'Estelle'",
                                "'engine':'Phonon 0.4.1','language':'fr','voice':'default'")
    assert service_text.count('toolchain/voice-server-python/Scripts/python.exe') == 1
    assert service_text.count("str(ROOT/'lanceur/voice_worker.py')") == 1
    service_text = service_text.replace('toolchain/voice-server-python/Scripts/python.exe',
                                        'toolchain/phonon-server-python/Scripts/python.exe')
    service_text = service_text.replace("str(ROOT/'lanceur/voice_worker.py')", "str(ROOT/'lanceur/phonon_worker.py')")
    lock_script = ROOT / 'maintenance/verrous_runtime.py'
    lock_text = replacement(lock_script, "'voix-serveur':ROOT/'toolchain/voice-server-python/Scripts/python.exe'",
                            "'voix-serveur':ROOT/'toolchain/phonon-server-python/Scripts/python.exe'")
    ui = ROOT / 'lanceur/web/voice.js'
    ui_text = replacement(ui, 'Synthèse française Pocket TTS · Estelle', 'Synthèse française Phonon · voix par défaut')
    # Lock only the new isolated environment. Other validated runtime locks stay intact.
    packages = verrous_runtime.inventory(ROOT / 'toolchain/phonon-server-python/Scripts/python.exe')
    lines = ['# Runtime Phonon validé le 22 octobre 2026 ; installation avec --require-hashes.']
    for pair in sorted(packages.items()):
        _, record = verrous_runtime.public_hashes(pair)
        lines.append(pair[0] + '==' + pair[1] + ' \\\n' +
                     ' \\\n'.join('    --hash=sha256:' + value for value in record['hashes']))
    lock_data = '\n'.join(lines) + '\n'
    lock_path = ROOT / 'dependances/verrous/voix-serveur.requirements.txt'
    manifest_path = ROOT / 'dependances/verrous/manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['environments']['voix-serveur'] = {'packages': packages,
                                               'sha256': hashlib.sha256(lock_data.encode()).hexdigest()}
    changes = {service: service_text, ui: ui_text, lock_script: lock_text, lock_path: lock_data,
               manifest_path: json.dumps(manifest, ensure_ascii=False, indent=2) + '\n',
               ROOT / 'lanceur/requirements-voice.txt': (ROOT / 'lanceur/requirements-phonon.txt').read_text(encoding='utf-8')}
    for relative in ('client-voice/licenses/CONVERSATION-NOTICES.txt',
                     'client-qwen/voice/licenses/CONVERSATION-NOTICES.txt'):
        path = ROOT / relative
        changes[path] = path.read_text(encoding='utf-8') + (
            '\nServeur de synthèse remplacé le 22 octobre 2026 : Phonon / ptts 0.4.1, Gradium.\n'
            'Runtime MIT OR Apache-2.0 : https://github.com/gradium-ai/xn-ptts\n'
            'Modèle phonon-40m-fr, voix fournie default, CC BY-NC 4.0.\n'
            'https://huggingface.co/gradium/phonon-40m-fr\n'
            'https://creativecommons.org/licenses/by-nc/4.0/\n'
            'Pocket TTS décrit ci-dessus est le moteur historique, conservé pour retour arrière.\n')
    guide = ROOT / 'client-voice/CONVERSATION-WINDOWS.md'
    changes[guide] = guide.read_text(encoding='utf-8') + (
        '\n## Synthèse serveur remplacée le 22 octobre 2026\n\n'
        'Le moteur actif est désormais Phonon 0.4.1, modèle phonon-40m-fr q8, voix fournie default, '
        'quatre threads CPU. Le runtime est `toolchain/phonon-server-python` et le checkpoint local '
        'épinglé est sous `toolchain/phonon-models`. Les références Pocket TTS et ses mesures '
        'ci-dessus décrivent les validations historiques. Reconnaissance et protocole client conservés. '
        'Voir [la migration et les mesures natives](../maintenance/2026-10-22-phonon/README.md).\n')
    before = {'models': models(), 'files': preserved_files(), 'users': content_fingerprints(),
              'backups': backup_config(get('/api/backups'))}
    previous = ROOT / 'toolchain/releases-staging/phonon-20261022/previous'
    for path in changes:
        saved = previous / path.relative_to(ROOT)
        saved.parent.mkdir(parents=True, exist_ok=True)
        assert not saved.exists(), 'Rollback already exists'
        shutil.copy2(path, saved)
    write('avant-livraison.json', before)
    try:
        for path, text in changes.items():
            path.write_text(text, encoding='utf-8', newline='\n')
        restart()
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            voice = get('/api/voice')
            if voice['ready'] and voice['engine'] == 'Phonon 0.4.1': break
            time.sleep(1)
        else: raise ValueError('Phonon failed to become ready')
        assert models() == before['models'] and preserved_files() == before['files']
        assert content_fingerprints() == before['users']
        assert backup_config(get('/api/backups')) == before['backups']
        assert get('/api/state')['health']['loaded']
        importlib.reload(verrous_runtime).check()
        write('production.json', {'passed': True, 'voice': voice, 'model_processes_preserved': True,
              'keys_settings_data_backups_preserved': True, 'client_rebuild_required': False,
              'previous_sources': str(previous)})
        print('Phonon français actif ; Qwen, données, clés et sauvegardes conservés.')
    except Exception:
        for path in changes:
            shutil.copy2(previous / path.relative_to(ROOT), path)
        restart()
        write('rollback.json', {'restored': True, 'voice': get('/api/voice')})
        raise


if __name__ == '__main__':
    main()
