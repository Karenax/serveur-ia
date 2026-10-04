import csv,subprocess,sys,time
from pathlib import Path
root=Path(__file__).resolve().parent
out=root/'huihui-gpu-thermique.csv'
fields='timestamp,uuid,name,memory.used,utilization.gpu,temperature.gpu,clocks.sm,power.draw,clocks_throttle_reasons.sw_thermal_slowdown'
with out.open('w',newline='',encoding='utf8') as f:
 f.write(fields+'\n')
 while not (root/'huihui-monitor-stop').exists():
  p=subprocess.run(['nvidia-smi','--query-gpu='+fields,'--format=csv,noheader,nounits'],capture_output=True,text=True)
  if p.returncode==0:f.write(p.stdout);f.flush()
  time.sleep(1)
