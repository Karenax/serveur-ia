"""Create isolated profiles, preserving all earlier measurements and production files."""
import copy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
base=json.loads((ROOT/'config-reference.json').read_text(encoding='utf-8-sig'))
for profile in ('cpu-court','cpu-court-pin','cpu-court-pin-4096'):
    cfg=copy.deepcopy(base)
    cfg['env'].update(STRATA_PREFILL_CPU_SHARE='auto',STRATA_PREFILL_CPU_SHARE_MAX='1024',
                      STRATA_PREFILL_TIMING='1',STRATA_DBG_CPU_GATE='1')
    if 'pin' in profile:
        cfg['args'][cfg['args'].index('--resident-cpu-experts')]='--resident-experts'
    if '4096' in profile:
        cfg['args'][cfg['args'].index('--prefill')+1]='4096'
    cfg['log']=(ROOT/f'logs/engine-{profile}.log').as_posix()
    (ROOT/f'config-{profile}.json').write_text(json.dumps(cfg,indent=2)+'\n',encoding='utf-8')
print('Trois profils locaux crees, production intacte.')
