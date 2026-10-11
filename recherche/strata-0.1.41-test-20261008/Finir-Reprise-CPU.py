"""Complete health and inference verification after the engine recovery was started."""
import json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
RUN=ROOT/'mesures/cpu-prefill-20261009'
PY=ROOT/'.venv/Scripts/python.exe'
with (RUN/'verification-reprise.log').open('w',encoding='utf-8') as log:
    subprocess.run([str(PY),str(ROOT/'Verifier-Reprise.py')],stdout=log,stderr=log,timeout=1300,check=True)
(RUN/'production-retablie.json').write_bytes((ROOT/'validation/production-retablie.json').read_bytes())
state=json.loads((RUN/'etat.json').read_text())
state.update(phase='production-retablie',production_version='0.1.35',
             recovery_note='Verification reprise terminee; console reconnectee apres apparition du processus moteur.')
(RUN/'etat.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
subprocess.run([str(PY),str(ROOT/'Rapport-CPU-Prefill.py')],check=True)
