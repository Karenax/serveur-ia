"""Wait for the IQ4 server, validate its first synchronized request, then benchmark."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--archive', required=True, type=Path)
parser.add_argument('--pid', required=True, type=int)
args = parser.parse_args()
config_path = args.archive / 'configuration-iq4.json'
config = json.loads(config_path.read_text(encoding='utf-8-sig'))
url = f"http://127.0.0.1:{config['port']}"
def save(name, data):
    (args.archive / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
deadline = time.monotonic() + 90*60
while time.monotonic() < deadline:
    try:
        health = json.load(urllib.request.urlopen(url + '/health', timeout=5))
        if health.get('loaded') and health.get('model') == config['model_name'] and not (
                args.archive / 'prelecture-en-cours.flag').exists():
            break
    except Exception:
        pass
    time.sleep(10)
else:
    raise RuntimeError('IQ4 startup did not complete within 90 minutes')
save('health-iq4.json', health)
historic = json.loads((Path(__file__).resolve().parent / 'protocole-comparatif-q4.json').read_text(encoding='utf-8-sig'))
payload = dict(model=config['model_name'],messages=[dict(role='user',content=historic['prompts'][0])],
               max_tokens=1,temperature=0,seed=42,cache_prompt=False,
               chat_template_kwargs=dict(enable_thinking=False))
request = urllib.request.Request(url + '/v1/chat/completions',
    data=json.dumps(payload,ensure_ascii=False).encode('utf-8'),
    headers={'Content-Type':'application/json; charset=utf-8'})
with urllib.request.urlopen(request,timeout=600) as response:
    answer = json.load(response)
save('warmup-iq4.json', answer)
if answer['usage']['completion_tokens'] != 1:
    raise RuntimeError('IQ4 startup request returned an unexpected number of tokens')
Path(config['env']['STRATA_P100_DIAGNOSTIC_SYNC_FILE']).unlink()
print('IQ4 startup request passed; diagnostic synchronization disabled.',flush=True)
command=[sys.executable,str(Path(__file__).resolve().parent / 'Comparer-Q4-IQ4.py'),
         '--config',str(config_path),'--out',str(args.archive / 'iq4'),
         '--label','IQ4_XS','--pid',str(args.pid)]
raise SystemExit(subprocess.call(command))
