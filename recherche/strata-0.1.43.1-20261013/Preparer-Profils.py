"""Prepare isolated Strata profiles; does not start or stop any service."""
import copy, json
from pathlib import Path
ROOT = Path(__file__).resolve().parent
OLD = ROOT.parent / 'strata-0.1.41-test-20261008'
base = json.loads((OLD/'config-reference.json').read_text(encoding='utf-8-sig'))
base.update(exe=str(ROOT/'engine-cuda12/strata.exe'), cwd=str(ROOT/'source/Strata-0.1.43.1'),
            model_name='qwen3.8-flash-next-iq4-xs-test-01431')
base['env'].update(STRATA_ROUTE_TAIL_SKIP='0', STRATA_ADAPT_OVERLAP='0', STRATA_PLE_AUTO_MMAP='0')
profiles = {
    'reference': {},
    'defaults': {'STRATA_ROUTE_TAIL_SKIP':'7'},
    'fp16': {'STRATA_BF16_TC':'2','STRATA_PREFILL_BF16X2':'0'},
    'trim': {'STRATA_STAGE_TRIM':'1'},
    'help': {'STRATA_PREFILL_HELP':'1'},
    'mtp-batch': {'STRATA_SPLIT_MTP_BATCH':'1'},
}
(ROOT/'logs').mkdir(exist_ok=True)
for name, env in profiles.items():
    cfg=copy.deepcopy(base)
    cfg['env'].update(env)
    cfg['log']=str(ROOT/f'logs/engine-{name}.log')
    (ROOT/f'config-{name}.json').write_text(json.dumps(cfg,indent=2)+'\n',encoding='utf-8')
print('Six profils isolés préparés sur 127.0.0.1:8081.')
