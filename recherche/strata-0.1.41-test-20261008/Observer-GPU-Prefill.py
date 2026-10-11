"""Read-only clock/temperature sampling during the trial, ending after recovery."""
import argparse,json,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--run',default='prefill-court-pin-20261009')
args=parser.parse_args()
assert Path(args.run).name==args.run and args.run not in ('.','..')
RUN=ROOT/'mesures'/args.run
query='timestamp,uuid,name,temperature.gpu,clocks.sm,clocks.mem,power.draw,clocks_throttle_reasons.active,utilization.gpu'
end=time.monotonic()+5400
with (RUN/'gpu-samples.jsonl').open('w',encoding='utf-8') as log:
    while time.monotonic()<end:
        if (RUN/'observer-stop').exists():break
        try:
            state=json.loads((RUN/'etat.json').read_text())
            if state.get('phase')=='production-retablie':break
            result=subprocess.run(['nvidia-smi','--query-gpu='+query,'--format=csv,noheader,nounits'],
                                   capture_output=True,text=True,timeout=8,creationflags=subprocess.CREATE_NO_WINDOW)
            log.write(json.dumps({'time':time.time(),'phase':state.get('phase'),'profile':state.get('profile'),
                                  'rows':result.stdout.strip().splitlines(),'returncode':result.returncode})+'\n')
            log.flush()
        except Exception as exc:
            log.write(json.dumps({'error':str(exc)})+'\n');log.flush()
        time.sleep(3)
