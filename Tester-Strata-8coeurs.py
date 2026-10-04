"""Wait for complete loading, then benchmark compact and spread eight-core placements."""
import ctypes as c
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

root = Path(__file__).resolve().parent
archive = Path((root / 'comparatif-cpu8-courant.txt').read_text(encoding='utf-8-sig').strip())
config_path = root / 'strata-q4-p100-8coeurs.json'
engine_pid = 29604
# This driver records this already started test engine, and must not attach to another PID after a restart.
k = c.WinDLL('kernel32', use_last_error=True)
k.OpenProcess.argtypes = [c.c_ulong, c.c_int, c.c_ulong]; k.OpenProcess.restype = c.c_void_p
k.GetExitCodeProcess.argtypes = [c.c_void_p, c.POINTER(c.c_ulong)]
handle = k.OpenProcess(0x0400, False, engine_pid)
if not handle: raise c.WinError(c.get_last_error())
def alive():
    code = c.c_ulong()
    if not k.GetExitCodeProcess(handle, c.byref(code)): raise c.WinError(c.get_last_error())
    return code.value == 259
start = time.monotonic()
while time.monotonic() - start < 3600:
    if not alive(): raise RuntimeError('The selected Q4 engine has exited')
    try:
        health = json.load(urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3))
    except Exception:
        health = {}
    if (health.get('loaded') and health.get('model') == 'qwen3.8-flash-next'
            and not (root / 'strata-data' / 'cuda-debug.flag').exists()
            and not (archive / 'prelecture-en-cours.flag').exists()):
        break
    time.sleep(5)
else:
    raise RuntimeError('The engine has not become ready within one hour')
for placement, folder in [('compact', 'q4-8-compacts'), ('spread', 'q4-8-repartis')]:
    if placement == 'spread':
        result = subprocess.run([sys.executable, str(root / 'Limiter-Strata-8coeurs.py'),
                                 '--pid', str(engine_pid), '--out', str(archive / 'affinite-8-repartis.json'),
                                 '--apply', '--placement', 'spread'], check=True, capture_output=True, text=True)
        (archive / 'affinite-repartition.stdout.log').write_text(result.stdout, encoding='utf-8')
        (root / 'strata-affinite-8coeurs.json').write_bytes((archive / 'affinite-8-repartis.json').read_bytes())
    subprocess.run([sys.executable, str(root / 'Limiter-Strata-8coeurs.py'), '--pid', str(engine_pid),
                    '--out', str(archive / ('affinite-avant-' + placement + '.json'))], check=True,
                    stdout=subprocess.DEVNULL)
    print('Benchmark: ' + placement, flush=True)
    subprocess.run([sys.executable, str(root / 'Comparer-Q4-IQ4.py'), '--config', str(config_path),
                    '--out', str(archive / folder), '--label', 'Q4-8-' + placement,
                    '--pid', str(engine_pid), '--repeats', '2'], check=True)
    subprocess.run([sys.executable, str(root / 'Limiter-Strata-8coeurs.py'), '--pid', str(engine_pid),
                    '--out', str(archive / ('affinite-apres-' + placement + '.json'))], check=True,
                    stdout=subprocess.DEVNULL)
print('Twelve eight-core measurements completed; Q4 remains on eight spread cores.', flush=True)
