"""Mesure le lancement du cache Q4, le repos et une requête identique aux comparatifs."""
import ctypes as c
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import psutil

ROOT = Path(__file__).resolve().parent
OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
PDH = c.WinDLL('pdh')
query = c.c_void_p()
PDH.PdhOpenQueryW(None, 0, c.byref(query))
PDH.PdhAddEnglishCounterW.argtypes = [c.c_void_p, c.c_wchar_p, c.c_size_t, c.POINTER(c.c_void_p)]
class Value(c.Structure):
    _fields_ = [('status', c.c_ulong), ('value', c.c_double)]
PDH.PdhGetFormattedCounterValue.argtypes = [c.c_void_p, c.c_ulong, c.c_void_p, c.POINTER(Value)]
handles = {}
for key, path in {
    'C_busy': r'\PhysicalDisk(0 C:)\% Idle Time',
    'D_busy': r'\PhysicalDisk(1 D:)\% Idle Time',
    'C_queue': r'\PhysicalDisk(0 C:)\Current Disk Queue Length',
    'D_queue': r'\PhysicalDisk(1 D:)\Current Disk Queue Length',
    'page_reads_s': r'\Memory\Page Reads/sec',
    'page_writes_s': r'\Memory\Page Writes/sec',
}.items():
    handle = c.c_void_p()
    code = PDH.PdhAddEnglishCounterW(query, path, 0, c.byref(handle))
    if code == 0:
        handles[key] = handle
PDH.PdhCollectQueryData(query)
records = []
summary = {'configuration': 'Q4_K_XL cache C, 8 coeurs physiques repartis, MTP actif',
           'started': dt.datetime.now().astimezone().isoformat(), 'status': 'baseline'}
def save():
    temporary = OUT / 'etat.tmp'
    temporary.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
    temporary.replace(OUT / 'etat.json')
def health():
    try:
        with urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=1) as response:
            return json.load(response)
    except Exception:
        return {}
previous_disk = psutil.disk_io_counters(perdisk=True)
previous_time = time.monotonic()
previous_process = {}
def sample(phase):
    global previous_disk, previous_time, previous_process
    now = time.monotonic()
    elapsed = now - previous_time
    disks = psutil.disk_io_counters(perdisk=True)
    row = {'time': dt.datetime.now().astimezone().isoformat(), 'phase': phase,
           'interval_s': elapsed, 'available_GiB': psutil.virtual_memory().available / 2**30}
    for disk, label in [('PhysicalDrive0', 'C'), ('PhysicalDrive1', 'D')]:
        for kind in ['read_bytes', 'write_bytes']:
            row[label + '_' + kind + '_s'] = (getattr(disks[disk], kind) - getattr(previous_disk[disk], kind)) / elapsed
    PDH.PdhCollectQueryData(query)
    for key, handle in handles.items():
        value = Value()
        if PDH.PdhGetFormattedCounterValue(handle, 0x200, None, c.byref(value)) == 0 and value.status in (0, 1):
            row[key] = max(0, min(100, 100 - value.value)) if key.endswith('_busy') else value.value
    processes = []
    current = {}
    for process in psutil.process_iter(['pid', 'name']):
        try:
            io = process.io_counters()
            current[process.pid] = (io.read_bytes, io.write_bytes)
            before = previous_process.get(process.pid, current[process.pid])
            read, write = [(current[process.pid][i] - before[i]) / elapsed for i in range(2)]
            if read + write > 100000 or process.info['name'].lower() == 'strata.exe':
                memory = process.memory_info()
                processes.append({'pid': process.pid, 'name': process.info['name'],
                                  'read_B_s': read, 'write_B_s': write,
                                  'rss_GiB': memory.rss / 2**30, 'private_GiB': memory.private / 2**30,
                                  'page_faults_total': memory.num_page_faults})
        except (psutil.Error, OSError):
            pass
    row['process_io_including_non_disk'] = sorted(processes, key=lambda p: p['read_B_s'] + p['write_B_s'], reverse=True)[:12]
    with (OUT / 'mesures.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + '\n')
    records.append(row)
    previous_disk, previous_time, previous_process = disks, now, current
    return row
def period(seconds, phase):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        time.sleep(5)
        sample(phase)
def summarize():
    result = {}
    for phase in sorted(set(row['phase'] for row in records)):
        rows = [row for row in records if row['phase'] == phase]
        seconds = sum(row['interval_s'] for row in rows)
        result[phase] = {'seconds': seconds, 'samples': len(rows)}
        for key in ['C_read_bytes_s', 'C_write_bytes_s', 'D_read_bytes_s', 'D_write_bytes_s',
                    'C_busy', 'D_busy', 'page_reads_s', 'page_writes_s']:
            selected = [row for row in rows if key in row]
            if selected:
                result[phase][key + '_mean'] = sum(row[key] * row['interval_s'] for row in selected) / sum(row['interval_s'] for row in selected)
                result[phase][key + '_max'] = max(row[key] for row in selected)
    return result
try:
    save()
    period(30, 'baseline_serveur_arrete')
    summary['launch_time'] = dt.datetime.now().astimezone().isoformat()
    launched = time.monotonic()
    result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                             str(ROOT / 'Start-Strata-P100-Persistant.ps1'), '-CacheContigu', '-CpuCores', '8'],
                            capture_output=True, timeout=60)
    (OUT / 'lancement.stdout.txt').write_bytes(result.stdout)
    (OUT / 'lancement.stderr.txt').write_bytes(result.stderr)
    if result.returncode:
        raise RuntimeError('Echec du lancement, voir lancement.stderr.txt')
    summary['status'] = 'chargement'
    save()
    while time.monotonic() - launched < 90 * 60:
        time.sleep(5)
        sample('chargement')
        state = health()
        if state.get('loaded') and state.get('model') == 'qwen3.8-flash-next':
            if 'loaded_s' not in summary:
                summary['loaded_s'] = time.monotonic() - launched
                summary['loaded_time'] = dt.datetime.now().astimezone().isoformat()
                save()
            affinity = ROOT / 'strata-affinite-8coeurs.json'
            if not (ROOT / 'strata-data/cuda-debug.flag').exists() and affinity.exists() and affinity.stat().st_mtime >= dt.datetime.fromisoformat(summary['launch_time']).timestamp():
                break
    else:
        raise RuntimeError('Chargement incomplet apres 90 minutes')
    summary['ready_s'] = time.monotonic() - launched
    summary['ready_time'] = dt.datetime.now().astimezone().isoformat()
    summary['health'] = state
    summary['status'] = 'repos_avant_inference'
    save()
    period(120, 'repos_avant_inference')
    summary['status'] = 'inference'
    save()
    payload = {'model': 'qwen3.8-flash-next', 'messages': [{'role': 'user', 'content': 'creer une poésie sur les fourmis de 200 mots'}],
               'max_tokens': 512, 'temperature': 0, 'seed': 42, 'cache_prompt': False,
               'chat_template_kwargs': {'enable_thinking': False}}
    (OUT / 'requete.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    import concurrent.futures
    def infer():
        request = urllib.request.Request('http://127.0.0.1:8080/v1/chat/completions', data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(request, timeout=600) as response:
            return json.load(response)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        start = time.monotonic()
        future = pool.submit(infer)
        while not future.done():
            time.sleep(5)
            sample('inference')
        response = future.result()
    summary['inference_s'] = time.monotonic() - start
    (OUT / 'reponse.json').write_text(json.dumps(response, ensure_ascii=False, indent=2), encoding='utf-8')
    summary['status'] = 'repos_apres_inference'
    save()
    period(120, 'repos_apres_inference')
    summary['phases'] = summarize()
    summary['status'] = 'complete'
    summary['finished'] = dt.datetime.now().astimezone().isoformat()
    (OUT / 'engine-fin.log').write_bytes((ROOT / 'strata-engine-p100-cache.log').read_bytes())
    save()
except Exception as error:
    summary['status'] = 'erreur'
    summary['error'] = repr(error)
    summary['phases'] = summarize()
    save()
    raise
finally:
    PDH.PdhCloseQuery(query)
