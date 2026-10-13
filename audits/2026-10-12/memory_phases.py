"""Isolated RSS sampling of the existing realistic document volume contract."""
import json
from pathlib import Path
import sys
import threading
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'lanceur'))
import psutil
from test_backups import BackupsTests

case=BackupsTests('test_16_mib_original_document_backup_restore_volume_and_resource_evidence')
case.setUp()
phase=['setup'];peaks={};halt=threading.Event()
def sample():
    while not halt.wait(.005):
        name=phase[-1];peaks[name]=max(peaks.get(name,0),psutil.Process().memory_info().rss)
def wrap(object,name):
    original=getattr(object,name)
    def measured(*args,**kwargs):
        phase.append(name)
        try:return original(*args,**kwargs)
        finally:phase.pop()
    setattr(object,name,measured)
for obj,names in [(case.b,('_capture','_create','_decode','_summary','inspect')),
                  (case.c.operations,('_restore_legacy','backup')),
                  (case.c.operations.restorations,('_restore',)),
                  (case.w,('validate_backup','backup','restore'))]:
    for name in names:wrap(obj,name)
worker=threading.Thread(target=sample);worker.start()
try:case.test_16_mib_original_document_backup_restore_volume_and_resource_evidence()
finally:
    halt.set();worker.join();case.tearDown()
print('PHASE_PEAKS',json.dumps(peaks,sort_keys=True))
