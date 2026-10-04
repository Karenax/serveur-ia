"""Screen request-scoped IQ3 tunings without changing server defaults."""
import argparse
import datetime
import json
from pathlib import Path
import time
import urllib.request

root = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--confirm', action='store_true')
args = parser.parse_args()
out = root / 'comparatifs' / ('audit-iq3-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
out.mkdir(parents=True)
prompts = json.loads((root/'protocole-comparatif-q4.json').read_text(encoding='utf-8-sig'))['prompts'][:2]
config = json.loads((root/'strata-iq3-p100-hybride.json').read_text(encoding='utf-8-sig'))
(out/'configuration.json').write_text(json.dumps(config, indent=2), encoding='utf-8')
log = Path(config['log'])
settings = [('reference', 0, .5), ('gpu-12pc', .125, .5), ('gpu-25pc', .25, .5),
            ('mtp-seuil-30', 0, .3), ('mtp-seuil-70', 0, .7), ('reference-fin', 0, .5)]
if args.confirm:
    settings = [('r1-seuil70', 0, .7), ('r1-reference', 0, .5),
                ('r2-reference', 0, .5), ('r2-seuil70', 0, .7)]
rows = []
for label, fraction, threshold in settings:
    for case, prompt in zip(('ciel', 'fibonacci'), prompts):
        payload = dict(model=config['model_name'], messages=[dict(role='user',content=prompt)],
                       max_tokens=256, temperature=0, seed=42, cache_prompt=False,
                       chat_template_kwargs=dict(enable_thinking=False),
                       strata_tune=dict(pcie_frac=fraction, spec_min_p=threshold))
        before = log.stat().st_size
        request = urllib.request.Request('http://127.0.0.1:8080/v1/chat/completions',
            data=json.dumps(payload).encode(), headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request, timeout=600) as response:
            answer = json.load(response)
        if answer['usage']['completion_tokens'] != 256:
            raise RuntimeError('Unexpected completion length')
        result = dict(setting=label, case=case, request=payload, response=answer)
        (out/(label+'-'+case+'.json')).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        with log.open('rb') as stream:
            stream.seek(before)
            (out/(label+'-'+case+'-engine.log')).write_bytes(stream.read())
        row = dict(setting=label, case=case, pcie_frac=fraction, spec_min_p=threshold,
                   **answer['timings'])
        rows.append(row)
        (out/'mesures.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
        print(json.dumps(row), flush=True)
print('Archives: '+str(out), flush=True)
