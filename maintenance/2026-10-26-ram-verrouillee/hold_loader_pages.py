"""Hold one half of the read-only source pages while the cold loader copies it."""
import ctypes as c
from ctypes import wintypes as w
import json
from pathlib import Path
import re
import sys
import time

import psutil

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'dependances/strata-0.1.43.1/source'))
sys.path.insert(0, str(ROOT / 'lanceur'))
from tools.gguf_reader import GGUFFile
from ram_residency import LockedTensor
from startup_memory import reclaim_loader


def main():
    pointer = json.loads((ROOT / 'lanceur/session.json').read_text())
    directory = Path(pointer['directory'])
    state = json.loads((directory / 'state.json').read_text())
    cfg = json.loads((directory / 'strata.json').read_text())
    if state['status'] != 'chargement' or '--resident-experts' not in cfg['args']:
        raise RuntimeError('Réservé au chargement des experts verrouillés.')
    server = psutil.Process(state['server']['pid'])
    if abs(server.create_time() - state['server']['created']) >= .01:
        raise RuntimeError('Identité serveur modifiée.')
    engines = [p for p in server.children(recursive=True) if Path(p.exe()).resolve() == Path(cfg['exe']).resolve()]
    if len(engines) != 1:
        raise RuntimeError('Un seul moteur du chargement est attendu.')
    engine = engines[0]
    log = directory / 'engine.log'

    def copied():
        values = re.findall(r'copied cache complement through layer (\d+)/48', log.read_text(encoding='utf-8'))
        return int(values[-1]) if values else 0

    paths = sorted(Path(cfg['args'][cfg['args'].index('--native') + 1]).parent.glob('*-of-00003.gguf'))
    banks = [(path, gguf.data_start + tensor.offset, tensor.expected_bytes(), int(tensor.name.split('.')[1]))
             for path in paths for gguf in [GGUFFile(path)] for tensor in sorted(gguf.tensors, key=lambda t: t.offset)
             if tensor.name.endswith('_exps.weight')]
    kernel = c.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = w.HANDLE
    kernel.SetProcessWorkingSetSizeEx.argtypes = [w.HANDLE, c.c_size_t, c.c_size_t, w.DWORD]
    budget = max(sum(size + 8192 for _, _, size, layer in banks if low <= layer < low + 24) for low in (0, 24))
    if not kernel.SetProcessWorkingSetSizeEx(kernel.GetCurrentProcess(), budget + 2**30, budget + 2 * 2**30, 2 | 8):
        raise c.WinError(c.get_last_error())
    report = {'engine_pid': engine.pid, 'phases': [], 'started': time.time()}
    held, suspended = [], False
    try:
        for low in (0, 24):
            if copied() >= low + 24:
                continue
            engine.suspend(); suspended = True
            reclaimed = reclaim_loader(cfg, state['server'])
            phase = {'layers': [low, low + 23], 'reclaim': reclaimed, 'locked_bytes': 0}
            print(json.dumps({'locking_layers': phase['layers']}), flush=True)
            for path, offset, size, layer in banks:
                if low <= layer < low + 24:
                    held.append(LockedTensor(path, offset, size))
                    phase['locked_bytes'] += size
                    if len(held) % 12 == 0:
                        print(json.dumps({'locked_source_gib': round(phase['locked_bytes'] / 2**30, 2)}), flush=True)
            engine.resume(); suspended = False
            print(json.dumps({'resumed': True, 'waiting_for_layers': low + 24}), flush=True)
            deadline = time.monotonic() + 300
            while copied() < low + 24:
                if not engine.is_running() or time.monotonic() >= deadline:
                    raise RuntimeError('La copie des pages conservées en RAM ne se termine pas.')
                time.sleep(2)
            phase['copied_layers'] = copied()
            report['phases'].append(phase)
            for item in held:
                item.close()
            held.clear()
    finally:
        if suspended and engine.is_running():
            engine.resume()
        for item in held:
            item.close()
        report['seconds'] = round(time.time() - report['started'], 1)
        (OUT / 'sources-temporaires.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
