import sys,json
from pathlib import Path
root=Path(r'D:\Serveur IA')
sys.path.insert(0,str(root/'lanceur'))
from core import matching_servers,stop_processes,same_process,read_json
ptr=read_json(root/'lanceur/session.json',{})
run=read_json(Path(ptr['directory'])/'state.json',{})
procs=matching_servers([str(Path(ptr['directory'])/'strata.json')])
for identity in (run.get('supervisor',{}),ptr.get('worker',{})):
 p=same_process(identity)
 if p:procs.append(p)
print('Arrêt des processus de production identifiés:',[p.pid for p in procs])
stop_processes(procs)
