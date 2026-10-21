import json
import sys
import time
from pathlib import Path
import psutil

from deployer import ROOT, OUT, DEST, FILES, read, write, get, sha, HTTP
import urllib.request

def main():
    pointer = read(ROOT / 'lanceur/session.json')
    folder = Path(pointer['directory'])
    state = read(folder / 'state.json')
    print(json.dumps({'session': str(folder), 'state': state}, ensure_ascii=False), flush=True)
    if state.get('status') != 'pret':
        sys.exit(2)
    cfg = read(folder / 'strata.json')
    assert cfg['exe'] == str(DEST / 'strata.exe')
    assert cfg['lib_dirs'] == [str(DEST)]
    engine = [p for p in psutil.process_iter(['name']) if p.info['name'] == 'strata.exe'
              and p.exe().lower() == str(DEST / 'strata.exe').lower()]
    assert len(engine) == 1
    changes = {}
    for name in FILES:
        original = read(OUT / 'avant' / name)
        actual = read(ROOT / name)
        changed = sorted(k for k in set(original) | set(actual) if original.get(k) != actual.get(k))
        assert changed == (['exe', 'lib_dirs'] if 'lib_dirs' in original else ['exe']), (name, changed)
        assert actual['exe'] == str(DEST / 'strata.exe')
        changes[name] = changed
    assert read(ROOT / 'lanceur/reglages.json') == read(ROOT / 'lanceur/reglages-par-defaut.json') == read(ROOT / 'lanceur/derniers-reglages-valides.json')
    assert read(ROOT / 'lanceur/exploitation.json') == {'autoload': True, 'restart': True}
    protected = read(OUT / 'empreintes-avant.json')
    unchanged = {p: sha(p) == expected for p, expected in protected.items()}
    critical = {'acces-distants.json', 'connexions.json', 'exploitation.json',
                'hermes-integration.json', 'voix.json', 'wireguard.json', 'wireguard-fw.json'}
    assert all(ok for p, ok in unchanged.items() if Path(p).name in critical), unchanged
    request = urllib.request.Request('http://127.0.0.1:8080/v1/chat/completions',
        data=json.dumps({'model': cfg['model_name'], 'messages': [
            {'role': 'user', 'content': 'Calcule 143 + 158. Réponds uniquement par le résultat.'}],
            'max_tokens': 64, 'temperature': 0, 'chat_template_kwargs': {'enable_thinking': False}}).encode(),
        headers={'Content-Type': 'application/json'})
    response = json.load(HTTP.open(request, timeout=180))
    content = response['choices'][0]['message']['content']
    assert '301' in content, response
    health = get('http://127.0.0.1:8080/health')
    assert health['loaded'] and health['images']
    console = get('http://127.0.0.1:8765/health')
    connections = psutil.net_connections(kind='inet')
    ports = {port: any(c.laddr and c.laddr.port == port and c.status == 'LISTEN' for c in connections)
             for port in [8080, 8765, 8766, 8643, 8768]}
    ports['wireguard_udp_51820'] = any(c.laddr and c.laddr.port == 51820 and c.type == 2 for c in connections)
    assert all(ports.values()), ports
    result = {'version': '0.1.45.3', 'engine_exe': engine[0].exe(), 'engine_pid': engine[0].pid,
              'engine_sha256': sha(DEST / 'strata.exe'), 'session': str(folder), 'state': state,
              'health': health, 'console': console, 'ports': ports, 'calculation_response': content,
              'persistent_config_changes': changes, 'protected_files_unchanged': unchanged,
              'autoload': True, 'restart': True}
    write(OUT / 'production.json', result)
    print('Production vérifiée : moteur nouveau, calcul 301, vision disponible, démarrage automatique et reprise activés.', flush=True)

if __name__ == '__main__':
    main()
