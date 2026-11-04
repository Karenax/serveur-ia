"""Isolated dense-on-3080 versus two-P100 text benchmark, without persistent changes."""
import argparse
import base64
import copy
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import urllib.request

import psutil

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
GPU0 = 'GPU-a39f1b57-5a26-b53d-e943-44ef8042a438'
GPU1 = 'GPU-486d5352-582e-2880-78bf-3dec4688e142'
RTX = 'GPU-c7ec5bca-5502-9e99-2ede-30270b7bde2f'


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def get(path):
    with HTTP.open('http://127.0.0.1:18080' + path, timeout=4) as response:
        return json.load(response)


def fingerprints():
    names = ['lanceur/base-strata.json', 'strata-iq4-p100-hybride.json', 'lanceur/reglages.json',
             'lanceur/reglages-par-defaut.json', 'lanceur/exploitation.json', 'lanceur/session.json',
             'lanceur/derniers-reglages-valides.json']
    return {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in names if (ROOT / n).exists()}


def gpu():
    query = 'index,uuid,name,memory.used,temperature.gpu,utilization.gpu,clocks.sm,power.draw,clocks_throttle_reasons.active'
    result = subprocess.run(['nvidia-smi', '--query-gpu=' + query, '--format=csv,noheader,nounits'],
                            capture_output=True, text=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
    result.check_returncode()
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('arm', choices=['p100', 'rtx3080', 'rtx4080'])
    parser.add_argument('--primary-gpu-uuid')
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--context', type=int, default=8192)
    parser.add_argument('--tag', default='run1')
    parser.add_argument('--prefill', type=int, default=2048)
    parser.add_argument('--engine-dir', type=Path)
    parser.add_argument('--draft-model', type=Path)
    parser.add_argument('--draft-conf', type=float, default=0.8)
    parser.add_argument('--profile-timing', action='store_true')
    parser.add_argument('--pool-workers', type=int)
    parser.add_argument('--pcie-frac', type=float)
    parser.add_argument('--decode-only', action='store_true')
    parser.add_argument('--extra-helper-gpu-uuid')
    parser.add_argument('--p100-count', type=int, choices=[0, 1, 2], default=2)
    parser.add_argument('--cublas-log', action='store_true')
    parser.add_argument('--bf16-tc', choices=['0', '1', '2'])
    parser.add_argument('--diagnostic', action='store_true')
    parser.add_argument('--with-vision', action='store_true')
    parser.add_argument('--keep-caches', action='store_true')
    parser.add_argument('--kv-resident', type=int)
    parser.add_argument('--vram-reserve', type=int)
    parser.add_argument('--kv', choices=['fp16', 'int8', 'q4_0', 'k8v4'])
    parser.add_argument('--expert-cache')
    parser.add_argument('--spec', type=int)
    parser.add_argument('--spec-min-p', type=float)
    parser.add_argument('--quality-suite', action='store_true')
    parser.add_argument('--long-prefill', action='store_true')
    parser.add_argument('--hold-vram-mib', type=int, default=0)
    parser.add_argument('--isolate-conversations', action='store_true')
    parser.add_argument('--prefill-head-alias', action='store_true')
    parser.add_argument('--mtp-q4', choices=['all', 'proj', 'head'])
    parser.add_argument('--smoke', action='store_true')
    args = parser.parse_args()
    if args.arm == 'rtx4080' and not args.primary_gpu_uuid:
        parser.error('rtx4080 requires --primary-gpu-uuid')
    if args.extra_helper_gpu_uuid and args.arm == 'p100':
        parser.error('extra helper requires an RTX primary')
    if args.extra_helper_gpu_uuid and args.p100_count != 2:
        parser.error('extra helper requires both P100 helper slots')
    out = args.output_dir.resolve() if args.output_dir else HERE / f'{args.arm}-ctx{args.context}-{args.tag}'
    out.mkdir(parents=True, exist_ok=False)
    before = fingerprints()
    cfg = json.loads((ROOT / 'strata-iq4-p100-hybride.json').read_text(encoding='utf-8-sig'))
    cfg = copy.deepcopy(cfg)
    if args.engine_dir:
        cfg['exe'] = str(args.engine_dir.resolve() / 'strata.exe')
        cfg['lib_dirs'] = [str(args.engine_dir.resolve())]
    if not args.with_vision:
        cfg.pop('vision', None)
    cfg['port'] = 18080
    cfg['host'] = '127.0.0.1'
    cfg['log'] = str(out / 'engine.log')
    cfg['env']['STRATA_P100_DIAGNOSTIC_SYNC_FILE'] = str(out / 'diagnostic.flag')
    if args.diagnostic:
        (out / 'diagnostic.flag').write_text('Synchronous CUDA diagnostic', encoding='utf-8')
        cfg['env'].update(CUDA_LAUNCH_BLOCKING='1', STRATA_TRACE='2')
    cfg['env']['CUDA_DEVICE_ORDER'] = 'PCI_BUS_ID'
    if args.profile_timing:
        cfg['env'].update(STRATA_VERIFY_PROFILE='1', STRATA_DECODE_TIMING='1')
    if args.bf16_tc is not None:
        cfg['env']['STRATA_BF16_TC'] = args.bf16_tc
    if args.cublas_log:
        cfg['env'].update(CUBLAS_LOGINFO_DBG='1', CUBLAS_LOGDEST_DBG=str(out / 'cublas.log'))
    cfg['env']['CUDA_VISIBLE_DEVICES'] = ','.join([GPU0, GPU1] if args.arm == 'p100' else [args.primary_gpu_uuid or RTX, GPU0, GPU1])
    if args.arm != 'p100':
        cfg['env']['CUDA_VISIBLE_DEVICES'] = ','.join([args.primary_gpu_uuid or RTX, *[GPU0, GPU1][:args.p100_count]])
    if args.extra_helper_gpu_uuid:
        cfg['env']['CUDA_VISIBLE_DEVICES'] += ',' + args.extra_helper_gpu_uuid

    def setarg(name, value=None):
        if name in cfg['args']:
            index = cfg['args'].index(name)
            del cfg['args'][index:index + (2 if value is not None else 1)]
        if value is not None:
            cfg['args'].extend([name, str(value)])

    if not args.with_vision:
        setarg('--vision')
    setarg('--max-context', args.context)
    setarg('--prefill', args.prefill)
    if args.pool_workers is not None:
        setarg('--pool-workers', args.pool_workers)
    if args.pcie_frac is not None:
        if not 0 <= args.pcie_frac <= 1:
            raise ValueError('--pcie-frac must be between 0 and 1')
        setarg('--pcie-frac', args.pcie_frac)
    if not args.keep_caches:
        setarg('--prompt-cache', 0)
        setarg('--conversation-cache-mib', 0)
    if args.kv_resident is not None:
        setarg('--kv-resident', args.kv_resident)
    if args.vram_reserve is not None:
        setarg('--vram-reserve-mib', args.vram_reserve)
    for name, value in [('--kv', args.kv), ('--expert-cache', args.expert_cache), ('--mtp-q4', args.mtp_q4),
                        ('--spec', args.spec), ('--spec-min-p', args.spec_min_p)]:
        if value is not None:
            setarg(name, value)
    if args.prefill_head_alias and '--prefill-head-alias' not in cfg['args']:
        cfg['args'].append('--prefill-head-alias')
    if args.draft_model:
        if '--mtp' in cfg['args']:
            index = cfg['args'].index('--mtp')
            vocab = Path(cfg['args'][index + 1]) / 'draft_vocab.bin'
            del cfg['args'][index:index + 2]
        elif '--mtp-draft-vocab' in cfg['args']:
            vocab = Path(cfg['args'][cfg['args'].index('--mtp-draft-vocab') + 1])
        else:
            raise ValueError('DFlash2 requires the existing draft vocabulary path')
        if not vocab.is_file() or not args.draft_model.is_file():
            raise FileNotFoundError('DFlash2 pack or draft vocabulary is missing')
        setarg('--draft', 'dflash2')
        setarg('--draft-model', args.draft_model.resolve())
        setarg('--draft-fallback', 'none')
        setarg('--mtp-draft-vocab', vocab)
        setarg('--draft-conf', args.draft_conf)
    if args.arm != 'p100':
        cfg['min_free_vram_mib'] = 8000
        for option in ('--layer-split', '--split-device'):
            if option in cfg['args']:
                index = cfg['args'].index(option)
                del cfg['args'][index:index + 2]
        setarg('--expert-cache-device1', 'auto')
        setarg('--expert-cache-device2', 'auto')
        for slot in range(args.p100_count + 1, 4):
            flag = '--expert-cache-device' + str(slot)
            if flag in cfg['args']:
                index = cfg['args'].index(flag)
                del cfg['args'][index:index + 2]
        if args.extra_helper_gpu_uuid:
            setarg('--expert-cache-device3', 'auto')
        if '--remote-expert-opt' not in cfg['args']:
            cfg['args'].append('--remote-expert-opt')
        if args.p100_count == 0:
            setarg('--remote-expert-opt')
    else:
        for option in ('--expert-cache-device1', '--expert-cache-device2'):
            if option in cfg['args']:
                index = cfg['args'].index(option)
                del cfg['args'][index:index + 2]
        setarg('--remote-expert-opt')
        setarg('--layer-split', 24)
        setarg('--split-device', 1)
    write(out / 'config.json', cfg)
    write(out / 'before.json', {'fingerprints': before, 'gpu': gpu(), 'utc': dt.datetime.now(dt.timezone.utc).isoformat(),
                              'memory': psutil.virtual_memory()._asdict(),
                              'engine_sha256': hashlib.sha256(Path(cfg['exe']).read_bytes()).hexdigest()})
    command = [sys.executable, '-u', '-m', 'serve.server', '--engine', 'strata', '--config', str(out / 'config.json'),
               '--host', '127.0.0.1', '--port', '18080']
    env = os.environ.copy()
    env.update(cfg.get('server_env', {}))
    env['PYTHONIOENCODING'] = 'utf-8'
    done = threading.Event()
    phase = ['loading']
    process = None
    holder = None
    samples = []
    results = []

    def observe():
        while not done.is_set():
            try:
                samples.append({'epoch': time.time(), 'phase': phase[0], 'gpu_csv': gpu(),
                                'ram_available_gib': psutil.virtual_memory().available / 2**30,
                                'system_cpu_percent': psutil.cpu_percent()})
                if psutil.virtual_memory().available < 6 * 2**30:
                    print('RAM below 6 GiB; ending benchmark', flush=True)
                    process.terminate()
                    return
            except Exception as error:
                samples.append({'epoch': time.time(), 'error': str(error)})
            done.wait(2)

    error = None
    started = time.monotonic()
    try:
        with (out / 'server.stdout.log').open('wb') as stdout, (out / 'server.stderr.log').open('wb') as stderr:
            process = subprocess.Popen(command, cwd=cfg['cwd'], env=env, stdout=stdout, stderr=stderr,
                                       stdin=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
        write(out / 'process.json', {'pid': process.pid, 'created': psutil.Process(process.pid).create_time(), 'command': command})
        worker = threading.Thread(target=observe, daemon=True)
        worker.start()
        next_print = 0
        while time.monotonic() - started < 1800:
            if process.poll() is not None:
                raise RuntimeError('Server exited: ' + str(process.returncode))
            try:
                if get('/health').get('loaded'):
                    break
            except (OSError, ValueError):
                pass
            elapsed = time.monotonic() - started
            if elapsed >= next_print:
                print(json.dumps({'arm': args.arm, 'loading_s': round(elapsed), 'available_gib': round(psutil.virtual_memory().available / 2**30, 1)}), flush=True)
                next_print = elapsed + 30
            time.sleep(2)
        else:
            raise TimeoutError('Model load exceeded 1800 s')
        write(out / 'ready.json', {'loaded_s': time.monotonic() - started, 'health': get('/health'), 'gpu': gpu()})
        print('READY ' + args.arm, flush=True)
        if args.hold_vram_mib:
            holder = subprocess.Popen([sys.executable, str(HERE / 'hold_vram.py'), '--mib', str(args.hold_vram_mib),
                '--report', str(out / 'vram-holder.json')], stdout=subprocess.DEVNULL,
                stderr=(out / 'vram-holder.stderr.log').open('wb'), creationflags=subprocess.CREATE_NO_WINDOW)
            deadline = time.monotonic() + 30
            while not (out / 'vram-holder.json').exists():
                if holder.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError('VRAM coexistence allocation failed')
                time.sleep(.2)
            print('VRAM HOLDER READY ' + str(args.hold_vram_mib), flush=True)

        def call(label, prompt, limit, expected=None):
            phase[0] = label
            messages = [{'role': 'user', 'content': prompt}]
            if args.isolate_conversations:
                messages.insert(0, {'role': 'system', 'content': label + '\nRéponds à la demande de l’utilisateur.'})
            payload = {'model': cfg['model_name'], 'messages': messages,
                       'max_tokens': limit, 'temperature': 0, 'seed': 42, 'stream': False,
                       'cache_prompt': False, 'chat_template_kwargs': {'enable_thinking': False}}
            write(out / (label + '-request.json'), payload)
            request = urllib.request.Request('http://127.0.0.1:18080/v1/chat/completions',
                                             data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
            begin = time.monotonic()
            with HTTP.open(request, timeout=600) as response:
                answer = json.load(response)
            write(out / (label + '-response.json'), answer)
            content = answer['choices'][0]['message'].get('content', '')
            if isinstance(expected, dict):
                try:
                    quality_pass = json.loads(content) == expected
                except ValueError:
                    quality_pass = False
            else:
                quality_pass = expected in content if expected else bool(content.strip())
            row = {'label': label, 'elapsed_s': time.monotonic() - begin, 'timings': answer.get('timings'),
                   'usage': answer.get('usage'), 'content': content, 'quality_pass': quality_pass,
                   'gpu_after': gpu()}
            results.append(row)
            write(out / 'results.json', results)
            print(json.dumps(row, ensure_ascii=True), flush=True)
            if (answer.get('timings') or {}).get('cache_n', 0):
                raise RuntimeError('Unexpected prompt cache reuse')
            phase[0] = 'between'

        def long_context():
            lines = [f'Dossier {i:04d}: le jardin contient des arbres, des fleurs et un chemin de pierre.' for i in range(1200)]
            expected = {'debut': 'AMBRE-2718', 'milieu': 'CEDRE-6402', 'fin': 'NACRE-9157'}
            for index, key in [(24, 'debut'), (600, 'milieu'), (1150, 'fin')]:
                lines[index] += f' Note importante : le code {key} est {expected[key]}.'
            call('long-context', '\n'.join(lines) + '\nRestitue les trois codes dans un objet JSON avec les clés debut, milieu et fin. Sans balises ni commentaire.',
                 128, expected)
            if results[-1]['timings']['prompt_n'] <= 20480:
                raise RuntimeError('Long-context validation did not cross the resident KV window')

        call('warmup', 'Calcule 143 + 158. Réponds uniquement avec le résultat.', 32, '301')
        if args.quality_suite:
            for label, prompt, expected in [
                ('multiply', 'Calcule 17 multiplié par 19. Réponds uniquement avec le nombre.', '323'),
                ('divide', 'Calcule (128 + 64) / 3. Réponds uniquement avec le nombre.', '64'),
                ('json', 'Réponds uniquement avec un objet JSON ayant ville égale à Lyon et stock égal au nombre 7. Sans balises.', {'ville': 'Lyon', 'stock': 7}),
                ('negation', 'Le colis rouge va à Paris. Le colis bleu va à Nantes. Quel colis ne va pas à Paris ? Réponds uniquement avec sa couleur.', 'bleu'),
            ]:
                call('quality-' + label, prompt, 64, expected)
        if args.with_vision:
            fixture = (ROOT / 'maintenance/2026-10-14-vision/vision-fixture.png').read_bytes()
            call('vision', [
                {'type': 'text', 'text': 'Lis le code en haut de l’image et indique la forme rouge et la forme bleue. Réponds en français.'},
                {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + base64.b64encode(fixture).decode()}},
            ], 128, '47')
        if args.smoke:
            if args.long_prefill:
                long_context()
            if not all(row['quality_pass'] for row in results):
                raise RuntimeError('Smoke quality check failed')
            return
        for rep in range(1, 4):
            call(f'decode-r{rep}', 'Explique en français pourquoi le ciel est bleu puis rouge au coucher du soleil. '
                 'Développe les phénomènes physiques en plusieurs paragraphes, avec des exemples.', 256)
        if args.decode_only:
            if not all(row['quality_pass'] for row in results):
                raise RuntimeError('Decode quality check failed')
            write(out / 'metrics.json', get('/metrics'))
            return
        for lines in (64, 256):
            document = '\n'.join(f'Ligne {i:04d}: le dossier décrit un jardin, des arbres et un chemin de pierre.' for i in range(lines))
            prompt = 'Lis ce dossier fictif.\n' + document + '\nLe code à retenir est LUMIERE-7429. Réponds uniquement avec ce code.'
            for rep in range(1, 3):
                call(f'prefill-{lines}-r{rep}', prompt, 32, 'LUMIERE-7429')
        if args.long_prefill:
            long_context()
        if not all(row['quality_pass'] for row in results):
            raise RuntimeError('Quality check failed')
        write(out / 'metrics.json', get('/metrics'))
    except Exception as exc:
        error = repr(exc)
        print('ERROR ' + error, flush=True)
    finally:
        done.set()
        if holder and holder.poll() is None:
            holder.terminate()
            try:
                holder.wait(timeout=10)
            except subprocess.TimeoutExpired:
                holder.kill()
        if process:
            try:
                parent = psutil.Process(process.pid)
                children = parent.children(recursive=True)
                for child in reversed(children):
                    try:
                        child.terminate()
                    except psutil.NoSuchProcess:
                        pass
                parent.terminate()
                _, alive = psutil.wait_procs(children + [parent], timeout=15)
                for child in alive:
                    child.kill()
            except psutil.NoSuchProcess:
                pass
        if 'worker' in locals():
            worker.join(12)
        write(out / 'telemetry.json', samples)
        after = fingerprints()
        write(out / 'final.json', {'error': error, 'fingerprints_identical': before == after,
                                 'fingerprints_after': after, 'gpu': gpu(), 'duration_s': time.monotonic() - started})
    if error:
        raise RuntimeError(error)


if __name__ == '__main__':
    main()
