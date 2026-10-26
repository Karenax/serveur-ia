"""CPU-only Bolt benchmark: full prefill, fixed decode and short French dialogue."""
import argparse
import ctypes
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
MODELS = Path('D:/modèle')
RUNTIME = ROOT / 'toolchain/llama-bolt-b11854-cpu'
MODEL = MODELS / 'NVIDIA-Nemotron-3.5-Bolt-E4B-UD-Q4_K_XL.gguf'
DRAFT = MODELS / 'Nemotron-3.5-Bolt-E4B-DFlash-BF16.gguf'
PORT = 8099
BASE = f'http://127.0.0.1:{PORT}'
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def emit(value):
    print(json.dumps(value, ensure_ascii=True), flush=True)


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def request(path, body=None, timeout=600):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(BASE + path, data=data, headers={'Content-Type': 'application/json'})
    try:
        with OPENER.open(req, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f'HTTP {error.code}: {error.read().decode(errors="replace")}') from error


def stream_request(path, body, openai=False):
    req = urllib.request.Request(BASE + path, data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
                                 headers={'Content-Type': 'application/json'})
    start = time.perf_counter()
    first = None
    first_sentence = None
    text = ''
    final = {}
    frames = 0
    with OPENER.open(req, timeout=600) as response:
        for line in response:
            if not line.startswith(b'data: '):
                continue
            data = line[6:].strip()
            if data == b'[DONE]':
                break
            frame = json.loads(data)
            if frame.get('error'):
                raise RuntimeError(str(frame['error']))
            frames += 1
            if openai:
                delta = (frame.get('choices') or [{}])[0].get('delta', {})
                content = delta.get('content') or ''
            else:
                content = frame.get('content') or ''
            if content:
                text += content
                if first is None:
                    first = time.perf_counter() - start
                if first_sentence is None and any(character in text for character in '.!?'):
                    first_sentence = time.perf_counter() - start
            if frame.get('timings') or frame.get('usage') or frame.get('stop'):
                final.update(frame)
    return {'first_content_seconds': first, 'first_sentence_seconds': first_sentence,
            'wall_seconds': time.perf_counter() - start, 'text': text,
            'timings': final.get('timings'), 'usage': final.get('usage'),
            'tokens_evaluated': final.get('tokens_evaluated'), 'tokens_cached': final.get('tokens_cached'),
            'tokens_predicted': final.get('tokens_predicted'), 'truncated': final.get('truncated'),
            'stop_type': final.get('stop_type'), 'frames': frames}


def footprint(pid):
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    psapi = ctypes.WinDLL('psapi', use_last_error=True)
    class Counters(ctypes.Structure):
        _fields_ = [('cb', ctypes.c_ulong), ('PageFaultCount', ctypes.c_ulong)] + [
            (name, ctypes.c_size_t) for name in ('PeakWorkingSetSize', 'WorkingSetSize', 'QuotaPeakPagedPoolUsage',
                                               'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
                                               'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage', 'PrivateUsage')]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(Counters), ctypes.c_ulong]
    handle = kernel.OpenProcess(0x410, False, pid)
    if not handle:
        return None
    try:
        value = Counters()
        value.cb = ctypes.sizeof(value)
        if not psapi.GetProcessMemoryInfo(handle, ctypes.byref(value), value.cb):
            return None
        return {'working_set_gib': value.WorkingSetSize / 2**30, 'peak_working_set_gib': value.PeakWorkingSetSize / 2**30,
                'private_gib': value.PrivateUsage / 2**30}
    finally:
        kernel.CloseHandle(handle)


def synthetic_messages(target):
    records = []
    for index in range(max(6, target // 25)):
        day = index % 28 + 1
        records.append(f'Dossier fictif {index + 1}: rendez-vous le {day} novembre, '
                       f'{(index * 17) % 240 + 15} minutes de trajet. '
                       f'Contact: {("Alice", "Marc", "Nora", "Luc")[index % 4]}. '
                       f'Priorité: {("normale", "urgente", "basse")[index % 3]}. '
                       'Confirmer la disponibilité et préparer les documents avant le départ.')
    text = '\n'.join(records)
    # Character sizing is only an initial approximation; actual tokenizer count is reported.
    return [{'role': 'system', 'content': 'Tu es Kiara. Réponds en français. Explique les informations fournies sans inventer de faits.'},
            {'role': 'user', 'content': text[:target * 3] + '\nExplique en détail comment organiser ces rendez-vous et préparer les déplacements.'}]


def run(mode, args):
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1', PORT)) == 0:
            raise RuntimeError(f'Port {PORT} already in use; no existing process stopped')
    executable = next(RUNTIME.rglob('llama-server.exe'))
    command = [str(executable), '-m', str(MODEL), '--alias', 'bolt-cpu', '--host', '127.0.0.1', '--port', str(PORT),
               '-ngl', '0', '-t', str(args.threads), '-tb', str(args.threads), '-c', '8192', '-np', '1',
               '-b', '512', '-ub', '512', '--load-mode', 'none', '--lazy-mode', 'off',
               '--jinja', '--no-webui', '--metrics', '--perf',
               '--chat-template-kwargs', '{"enable_thinking":false,"conversational_mode":true}']
    if mode == 'dflash':
        command += ['-md', str(DRAFT), '--spec-type', 'draft-dflash', '--spec-draft-n-max', '7',
                    '--spec-draft-ngl', '0', '--threads-draft', str(args.threads), '--threads-batch-draft', str(args.threads)]
    label = f'{mode}-t{args.threads}'
    report_path = OUT / f'{label}.json'
    report = {'mode': mode, 'command': command, 'cpu_only': True, 'context_capacity': 8192, 'threads': args.threads,
              'cache_prompt': False, 'fixed_decode_tokens': 128, 'rows': [], 'conversation': [],
              'limits': 'Synthetic CPU-only local tests; fixed decode ignores EOS for comparable work. No ASR, TTS, client network, Kiara memory retrieval or production routing. Qwen stays loaded.'}
    logs = OUT / f'{label}.log'
    started = time.perf_counter()
    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
    env = {**os.environ, 'CUDA_VISIBLE_DEVICES': '-1'}
    with logs.open('wb') as log:
        process = subprocess.Popen(command, cwd=str(executable.parent), stdout=log, stderr=subprocess.STDOUT,
                                   env=env, creationflags=creationflags)
        report['pid'] = process.pid
        emit({'starting': label, 'pid': process.pid})
        try:
            while time.perf_counter() - started < 300:
                if process.poll() is not None:
                    raise RuntimeError(f'Server exited {process.returncode}; see {logs}')
                try:
                    if request('/health', timeout=3).get('status') == 'ok':
                        break
                except (OSError, RuntimeError):
                    pass
                time.sleep(0.5)
            else:
                raise TimeoutError('Model load exceeded 300 seconds')
            report['load_ready_seconds'] = time.perf_counter() - started
            report['memory_after_load'] = footprint(process.pid)
            write_json(OUT / 'active-test.json', {'pid': process.pid, 'port': PORT, 'mode': mode, 'command': command})
            write_json(OUT / f'{label}-props.json', request('/props'))
            emit({'ready': label, 'load_seconds': report['load_ready_seconds'], 'memory': report['memory_after_load']})
            # Excluded warm-up: populate mapped pages, settle graph allocation and CPU kernels.
            report['warmup'] = stream_request('/v1/chat/completions', {
                'model': 'bolt-cpu', 'messages': [{'role': 'user', 'content': 'Dis simplement bonjour.'}],
                'max_tokens': 16, 'temperature': 0, 'stream': True, 'cache_prompt': False,
                'chat_template_kwargs': {'enable_thinking': False, 'conversational_mode': True},
                'stream_options': {'include_usage': True}} , openai=True)
            emit({'warmup_complete': label, 'seconds': report['warmup']['wall_seconds'], 'text': report['warmup']['text']})
            write_json(report_path, report)
            prompts_path = OUT / 'fixed-prompts.json'
            if prompts_path.exists():
                prompts = json.loads(prompts_path.read_text(encoding='utf-8'))
            else:
                prompts = []
                for target in args.lengths:
                    formatted = request('/apply-template', {'messages': synthetic_messages(target),
                        'chat_template_kwargs': {'enable_thinking': False, 'conversational_mode': True}})['prompt']
                    tokens = request('/tokenize', {'content': formatted, 'add_special': False, 'parse_special': True})['tokens']
                    prompts.append({'nominal_tokens': target, 'actual_tokens': len(tokens), 'prompt': formatted, 'token_ids': tokens})
                write_json(prompts_path, prompts)
            for prompt in prompts:
                if prompt['nominal_tokens'] not in args.lengths:
                    continue
                for repeat in range(args.repeats):
                    emit({'begin': label, 'input_tokens': prompt['actual_tokens'], 'repeat': repeat + 1})
                    row = stream_request('/completion', {'prompt': prompt['token_ids'], 'n_predict': 128,
                        'temperature': 0, 'seed': 42, 'stream': True, 'cache_prompt': False,
                        'ignore_eos': True, 'return_tokens': True})
                    row.update(nominal_input_tokens=prompt['nominal_tokens'], actual_input_tokens=prompt['actual_tokens'], repeat=repeat + 1)
                    row['memory'] = footprint(process.pid)
                    report['rows'].append(row)
                    write_json(report_path, report)
                    emit({'result': label, 'input_tokens': prompt['actual_tokens'], 'repeat': repeat + 1,
                          'ttft_seconds': row['first_content_seconds'], 'wall_seconds': row['wall_seconds'], 'timings': row['timings']})
            for prompt in ('Bonjour Kiara, tu m’entends ?',
                           'À quelle heure faut-il partir pour arriver à une réunion à neuf heures si le trajet dure trente minutes ?'):
                row = stream_request('/v1/chat/completions', {'model': 'bolt-cpu', 'messages': [
                    {'role': 'system', 'content': 'Tu es Kiara. Réponds en français naturel, en deux phrases courtes au maximum.'},
                    {'role': 'user', 'content': prompt}], 'max_tokens': 96, 'temperature': 0,
                    'seed': 42, 'stream': True, 'cache_prompt': False,
                    'chat_template_kwargs': {'enable_thinking': False, 'conversational_mode': True},
                    'stream_options': {'include_usage': True}}, openai=True)
                row['prompt'] = prompt
                report['conversation'].append(row)
                write_json(report_path, report)
                emit({'conversation': label, 'prompt': prompt, 'ttft_seconds': row['first_content_seconds'],
                      'wall_seconds': row['wall_seconds'], 'text': row['text'], 'timings': row['timings']})
            with OPENER.open(BASE + '/metrics', timeout=10) as response:
                (OUT / f'{label}-metrics.txt').write_bytes(response.read())
            report['memory_final'] = footprint(process.pid)
            report['passed'] = True
        except Exception as error:
            report['error'] = str(error)
            report['passed'] = False
            emit({'failed': label, 'error': str(error)})
        finally:
            # Stop only the benchmark child created here, never any existing server.
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
            report['server_stopped'] = True
            report['elapsed_seconds'] = time.perf_counter() - started
            write_json(report_path, report)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=('baseline', 'dflash', 'both'), default='both')
    parser.add_argument('--threads', type=int, default=16)
    parser.add_argument('--repeats', type=int, default=2)
    parser.add_argument('--lengths', nargs='+', type=int, default=[256, 1024, 4096])
    args = parser.parse_args()
    modes = ('baseline', 'dflash') if args.mode == 'both' else (args.mode,)
    results = [run(mode, args) for mode in modes]
    write_json(OUT / 'benchmark-summary.json', results)
    emit({'complete': True, 'passed': all(report['passed'] for report in results)})


if __name__ == '__main__':
    main()
