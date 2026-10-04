"""Benchmark Cafe IQ3 with the existing comparison prompts, without concurrency."""
import argparse
import ctypes
import datetime
import hashlib
import json
from pathlib import Path
import statistics
import time
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument('--mode', choices=['sans-mtp', 'mtp', 'cache-auto-mtp', 'hybride-mtp'], required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parent
out = root / 'comparatifs' / ('cafe-iq3-' + args.mode + '-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
out.mkdir(parents=True)
protocol = json.loads((root/'protocole-comparatif-q4.json').read_text(encoding='utf-8-sig'))
url = 'http://127.0.0.1:8080'
model = 'qwen3.8-flash-next-iq3-s'
server_pid = int((root/'cafe-iq3.pid').read_text(encoding='utf-8-sig'))
effective = json.loads((root/'cafe-iq3-configuration.json').read_text(encoding='utf-8-sig'))
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
kernel.OpenProcess.restype = ctypes.c_void_p
handle = kernel.OpenProcess(0x0400, False, server_pid)
kernel.GetProcessTimes.argtypes = [ctypes.c_void_p] + [ctypes.POINTER(ctypes.c_uint64)]*4
kernel.GetProcessTimes.restype = ctypes.c_int

def cpu_seconds():
    values = [ctypes.c_uint64() for _ in range(4)]
    if not kernel.GetProcessTimes(handle, *[ctypes.byref(value) for value in values]):
        raise ctypes.WinError(ctypes.get_last_error())
    return (values[2].value + values[3].value)/1e7

def save(name, data):
    (out/name).write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def complete(prompt, tokens):
    payload = dict(model=model, messages=[dict(role='user', content=prompt)], max_tokens=tokens,
                   temperature=0, seed=42, cache_prompt=False,
                   chat_template_kwargs=dict(enable_thinking=False))
    req = urllib.request.Request(url+'/v1/chat/completions', data=json.dumps(payload).encode(),
                                 headers={'Content-Type':'application/json'})
    cpu_before = cpu_seconds()
    start = time.monotonic()
    with urllib.request.urlopen(req, timeout=900) as response:
        answer = json.load(response)
    if not answer.get('usage',{}).get('completion_tokens',0):
        raise RuntimeError('No output tokens')
    elapsed = time.monotonic()-start
    cpu_elapsed = cpu_seconds()-cpu_before
    return dict(request=payload, response=answer, elapsed_seconds=elapsed,
                cpu_seconds=cpu_elapsed, average_cpu_cores=cpu_elapsed/elapsed)

deadline = time.monotonic()+1800
while time.monotonic() < deadline:
    try:
        with urllib.request.urlopen(url+'/health', timeout=5) as response:
            health = json.load(response)
        if health.get('status') == 'ok':
            break
    except Exception:
        pass
    time.sleep(3)
else:
    raise RuntimeError('Cafe startup timeout')
save('health.json', health)
save('protocole.json', protocol)
save('configuration.json', dict(mode=args.mode, server_pid=server_pid,
    effective=effective,
    launcher=(root/'Start-Cafe-IQ3-P100.ps1').read_text(encoding='utf-8-sig'),
    binary_sha256=hashlib.sha256(Path(effective.get('exe', str(root/'cafe-build-p100/bin/llama-server.exe'))).read_bytes()).hexdigest(),
    cuda_sha256=hashlib.sha256((Path(effective.get('exe', str(root/'cafe-build-p100/bin/llama-server.exe'))).parent/'ggml-cuda.dll').read_bytes()).hexdigest(),
    note='Two measured repetitions after a full warmup of both prompts; 256 output tokens requested. '
         'Cafe uses the shared Q8_0 MTP draft; Strata uses its converted draft.'))
for case, prompt in zip(('ciel','fibonacci'),protocol['prompts']):
    result = complete(prompt,256)
    save('warmup-'+case+'.json',result)
    print('Warmup '+case+': '+str(result['response'].get('timings')),flush=True)
rows=[]
for repeat in (1,2):
    cases=list(zip(('ciel','fibonacci'),protocol['prompts']))
    if repeat==2:
        cases.reverse()
    for case,prompt in cases:
        result=complete(prompt,256)
        save('r'+str(repeat)+'-'+case+'.json',result)
        answer=result['response']
        row=dict(mode=args.mode, repeat=repeat, case=case, tokens=answer['usage']['completion_tokens'],
                 average_cpu_cores=result['average_cpu_cores'],
                 finish_reason=answer['choices'][0]['finish_reason'], **answer['timings'])
        rows.append(row)
        save('mesures.json',rows)
        print(json.dumps(row),flush=True)
summary=[dict(mode=args.mode,case=case,median_tps=statistics.median(
    r['predicted_per_second'] for r in rows if r['case']==case),
    output_tokens=[r['tokens'] for r in rows if r['case']==case]) for case in ('ciel','fibonacci')]
save('synthese.json',summary)
print(json.dumps(summary),flush=True)
print('Archives: '+str(out),flush=True)
