"""Wait for ongoing user work, then refresh preservation hashes and backup."""
import importlib.util
from pathlib import Path
import time

OUT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('delivery_prepare',OUT/'publish.py')
publisher=importlib.util.module_from_spec(spec);spec.loader.exec_module(publisher)
deadline=time.monotonic()+1800
while True:
    try:publisher.delivery.idle();break
    except AssertionError:
        if time.monotonic()>deadline:raise TimeoutError('User work still active; no restart performed')
        time.sleep(2)
archive=OUT/'initial-snapshot';archive.mkdir(exist_ok=True)
for name in ('avant-livraison.json','sauvegarde-avant.json'):
    source=OUT/name;target=archive/name
    assert not target.exists(),'Inspect the existing refreshed preparation'
    source.rename(target)
publisher.prepare()
print('Idle state reached. Fresh preservation snapshot and verified backup ready.',flush=True)
