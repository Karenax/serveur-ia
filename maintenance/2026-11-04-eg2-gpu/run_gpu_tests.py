"""Bounded GPU experiments, with monitoring limited to our own child processes."""
import json
import argparse
from pathlib import Path
import subprocess
import time
import psutil

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
PYTHON=ROOT/'toolchain/eg2-gpu-benchmark-python-20261104/Scripts/python.exe'
HIDDEN=getattr(subprocess,'CREATE_NO_WINDOW',0)


def status():
    raw=subprocess.check_output(['nvidia-smi','--query-gpu=uuid,memory.free,utilization.gpu',
        '--format=csv,noheader,nounits'],text=True,creationflags=HIDDEN)
    return {parts[0].strip():{'free_mib':int(parts[1]),'utilization':int(parts[2])}
        for line in raw.strip().splitlines() if (parts:=line.split(','))}


def terminate_owned(process):
    try:
        parent=psutil.Process(process.pid)
        victims=parent.children(recursive=True)+[parent]
        for child in reversed(victims):
            try:child.terminate()
            except psutil.NoSuchProcess:pass
        _,alive=psutil.wait_procs(victims,timeout=3)
        for child in alive:
            try:child.kill()
            except psutil.NoSuchProcess:pass
    except psutil.NoSuchProcess:pass


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--p2200-batch4',action='store_true')
    args=parser.parse_args()
    configurations=[
        ('p2200_fp32','GPU-97ca6406-8625-b829-b053-191c238ff046','float32',2200,1024),
        ('rtx4080_fp16','GPU-7d35736d-3ef5-1304-0e9e-1d26021be1a0','float16',720,512),
    ]
    if args.p2200_batch4:
        configurations=[('p2200_fp32_batch4','GPU-97ca6406-8625-b829-b053-191c238ff046','float32',2200,1024)]
    for name,uuid,dtype,budget,headroom in configurations:
        before=status()[uuid]
        record={'name':name,'before':before,'allocator_budget_mib':budget,
            'stop_below_free_mib':headroom,'minimum_observed_free_mib':before['free_mib']}
        started=time.monotonic()
        with (OUT/(name+'.log')).open('w',encoding='utf-8') as log:
            command=[str(PYTHON),str(OUT/'benchmark.py'),'--name',name,'--gpu',uuid,
                '--dtype',dtype,'--attention','sdpa','--batch','4' if args.p2200_batch4 else '1','--budget-mib',str(budget)]
            process=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,creationflags=HIDDEN)
            try:
                while process.poll() is None:
                    current=status()[uuid]
                    record['minimum_observed_free_mib']=min(record['minimum_observed_free_mib'],current['free_mib'])
                    if current['free_mib']<headroom:
                        record['stopped_reason']='Free VRAM below the experiment headroom'
                        terminate_owned(process);break
                    if time.monotonic()-started>480:
                        record['stopped_reason']='Experiment exceeded eight minutes'
                        terminate_owned(process);break
                    time.sleep(.25)
                record['exit_code']=process.wait(timeout=10)
            finally:
                if process.poll() is None:terminate_owned(process)
        record['seconds']=round(time.monotonic()-started,2)
        time.sleep(2)
        record['after']=status()[uuid]
        (OUT/(name+'-monitor.json')).write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
        print(name+': '+json.dumps(record),flush=True)


if __name__=='__main__':main()
