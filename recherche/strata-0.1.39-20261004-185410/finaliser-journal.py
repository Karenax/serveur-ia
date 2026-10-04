import datetime as dt
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
def read(name):
    return json.loads((ROOT/name).read_text(encoding='utf-8-sig'))
journal=read('journal-recherche.json')
journal.pop('pending',None)
journal.update(date_fin=dt.datetime.now().astimezone().isoformat(),
    ssd_copy=read('copie-ssd.json'),completed_benchmarks=read('comparaison.json'),
    production_restored=read('verification-production-prete.json'),
    production_ngram_ram_check=read('production-ngram-ram-verifie.json'),
    production_hash_checks=read('verification-production.json'),
    production_external_edits_note='app.py and core.py changed during the research session outside this work; they were not edited or restored by the research task. Production engine/config/settings hashes are unchanged.',
    adapted_cpu_gpu_parity='Both Tesla P100: native_expert_parity iq4_xs/iq4_nl and prefill_p100_test passed',
    adapted_ngram_ram_check=read('adapte-262144/ngram-ram-verifie.json'),
    reference_ngram_ram_check=read('reference-production-262144/ngram-ram-verifie.json'))
journal['ple_ram']['code']='Official: --ple-io mmap, external read-only locked pages of the same SSD shard; adapted/reference: complete private VirtualLock RAM copy.'
(ROOT/'journal-recherche.json').write_text(json.dumps(journal,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Journal finalise; production restauree et essais archives.',flush=True)
