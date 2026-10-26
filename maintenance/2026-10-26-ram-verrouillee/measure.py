"""Disk/page-fault counters during two synthetic text calculations, written afterwards."""
import ctypes as c
import datetime
import json
from pathlib import Path
import threading
import time
import urllib.request

import psutil

OUT = Path(__file__).resolve().parent
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def live():
    with HTTP.open('http://127.0.0.1:8080/metrics', timeout=5) as response:
        return json.load(response)['live']


class Value(c.Structure):
    _fields_ = [('status', c.c_uint32), ('value', c.c_double)]


def main():
    state = live()
    if state['state'] != 'idle' or state.get('queued'):
        raise RuntimeError('Le moteur est occupé ; mesure différée.')
    engines = [p for p in psutil.process_iter(['name']) if (p.info['name'] or '').lower() == 'strata.exe']
    if len(engines) != 1:
        raise RuntimeError('Un seul moteur est attendu pour la mesure.')
    engine = engines[0]
    api = c.WinDLL('pdh.dll')
    handle = c.c_void_p()
    api.PdhOpenQueryW.argtypes = [c.c_wchar_p, c.c_size_t, c.POINTER(c.c_void_p)]
    api.PdhAddEnglishCounterW.argtypes = [c.c_void_p, c.c_wchar_p, c.c_size_t, c.POINTER(c.c_void_p)]
    api.PdhCollectQueryData.argtypes = [c.c_void_p]
    api.PdhGetFormattedCounterValue.argtypes = [c.c_void_p, c.c_uint32, c.c_void_p, c.POINTER(Value)]
    api.PdhCloseQuery.argtypes = [c.c_void_p]
    names = {'c_read': r'\LogicalDisk(C:)\Disk Read Bytes/sec',
             'd_read': r'\LogicalDisk(D:)\Disk Read Bytes/sec',
             'd_write': r'\LogicalDisk(D:)\Disk Write Bytes/sec',
             'd_idle': r'\LogicalDisk(D:)\% Idle Time',
             'pages_in': r'\Memory\Pages Input/sec',
             'strata_read': r'\Process(strata)\IO Read Bytes/sec'}
    if api.PdhOpenQueryW(None, 0, c.byref(handle)):
        raise RuntimeError('Compteurs disque indisponibles.')
    counters, samples, outcomes = {}, [], []
    stop, phase = threading.Event(), ['baseline']
    started = time.monotonic()
    before = engine.memory_info()._asdict()
    io_before = engine.io_counters()._asdict()
    try:
        for name, path in names.items():
            counter = c.c_void_p()
            if api.PdhAddEnglishCounterW(handle, path, 0, c.byref(counter)):
                raise RuntimeError('Compteur indisponible : ' + name)
            counters[name] = counter
        api.PdhCollectQueryData(handle)

        def sample():
            while not stop.wait(.5):
                api.PdhCollectQueryData(handle)
                row = {'t': round(time.monotonic() - started, 3), 'phase': phase[0]}
                for name, counter in counters.items():
                    value = Value()
                    status = api.PdhGetFormattedCounterValue(counter, 0x200, None, c.byref(value))
                    row[name] = round(value.value, 3) if status == 0 and value.status in (0, 1) else None
                samples.append(row)

        thread = threading.Thread(target=sample, daemon=True)
        thread.start()
        time.sleep(4)
        prompts = ['Calcule 143 + 158. Réponds en une phrase.',
                   'Voici un inventaire fictif. ' + ' '.join(f"Le lot {i} contient {i + 2} pièces." for i in range(1, 41)) +
                   ' Combien de pièces contiennent les lots 1 et 2 ensemble ? Explique en une phrase.']
        for index, prompt in enumerate(prompts):
            state = live()
            if state['state'] != 'idle' or state.get('queued'):
                raise RuntimeError('Une conversation a commencé ; mesure interrompue.')
            phase[0] = f'inference_{index + 1}'
            call_start = time.monotonic()
            body = {'model': 'qwen3.8-flash-next-iq4-xs', 'messages': [{'role': 'user', 'content': prompt}],
                    'max_tokens': 32, 'temperature': 0, 'stream': False,
                    'chat_template_kwargs': {'enable_thinking': False}}
            request = urllib.request.Request('http://127.0.0.1:8080/v1/chat/completions',
                                             json.dumps(body).encode(), {'Content-Type': 'application/json'})
            with HTTP.open(request, timeout=300) as response:
                answer = json.load(response)
            outcomes.append({'phase': phase[0], 'seconds': round(time.monotonic() - call_start, 3),
                             'usage': answer.get('usage'), 'answer': answer['choices'][0]['message']['content']})
            phase[0] = f'after_{index + 1}'
            time.sleep(3)
        stop.set()
        thread.join(2)
        summary = {}
        for label in dict.fromkeys(row['phase'] for row in samples):
            rows = [row for row in samples if row['phase'] == label]
            summary[label] = {'samples': len(rows)}
            for name in names:
                values = [row[name] for row in rows if row[name] is not None]
                if values:
                    summary[label][name] = {'mean': round(sum(values) / len(values), 3), 'max': max(values)}
        report = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'pid': engine.pid,
                  'outcomes': outcomes, 'summary': summary, 'samples': samples,
                  'memory_before': before, 'memory_after': engine.memory_info()._asdict(),
                  'io_before': io_before, 'io_after': engine.io_counters()._asdict(), 'live_after': live()}
        (OUT / 'measurement.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'outcomes': outcomes, 'summary': summary, 'live_after': report['live_after']}), flush=True)
    finally:
        stop.set()
        api.PdhCloseQuery(handle)


if __name__ == '__main__':
    main()
