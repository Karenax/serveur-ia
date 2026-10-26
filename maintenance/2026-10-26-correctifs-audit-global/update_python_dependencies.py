"""Apply reviewed pure-Python security updates with verified rollback wheels."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'lanceur'))
spec=importlib.util.spec_from_file_location('runtime_locks',ROOT/'maintenance/verrous_runtime.py')
locks=importlib.util.module_from_spec(spec);spec.loader.exec_module(locks)


def main():
    targets={name:record['latest'] for name,record in json.loads((OUT/'pypi-targets.json').read_text()).items()}
    environments=locks.environments()
    saved=OUT/'packages-before.json'
    before=json.loads(saved.read_text()) if saved.exists() else {name:locks.inventory(python) for name,python in environments.items()}
    if not saved.exists():saved.write_text(json.dumps(before,indent=2),encoding='utf-8')
    wheelhouse=ROOT/'toolchain/audit-security-wheels-20261026';wheelhouse.mkdir(exist_ok=True)
    pairs={(package,version) for packages in before.values() for package,version in packages.items() if package in targets}
    pairs.update(targets.items())
    downloads=[]
    for package,version in sorted(pairs):
        with urllib.request.urlopen(f'https://pypi.org/pypi/{package}/{version}/json',timeout=30) as response:
            metadata=json.load(response)
        wheels=[value for value in metadata['urls'] if value['filename'].endswith('none-any.whl') and not value.get('yanked')]
        if not wheels:raise ValueError('Reviewed pure-Python wheel missing: '+package+' '+version)
        value=wheels[0];path=wheelhouse/value['filename']
        if not path.exists():urllib.request.urlretrieve(value['url'],path)
        actual=hashlib.sha256(path.read_bytes()).hexdigest()
        if actual!=value['digests']['sha256']:raise ValueError('Wheel hash mismatch: '+path.name)
        downloads.append({'package':package,'version':version,'file':path.name,'sha256':actual,'url':value['url']})
    (OUT/'verified-wheels.json').write_text(json.dumps(downloads,indent=2),encoding='utf-8')
    uv=Path(os.environ['LOCALAPPDATA'])/'hermes/bin/uv.exe'
    # The old Strata venv inherited the Codex tooling installation. Materialize
    # its public locked dependencies locally before disabling that inheritance.
    strata=environments['strata']
    cfg=strata.parents[1]/'pyvenv.cfg'
    original_cfg=cfg.read_text(encoding='utf-8')
    if 'include-system-site-packages = true' in original_cfg:
        (OUT/'strata-pyvenv-before.cfg').write_text(original_cfg,encoding='utf-8')
        code="import importlib.metadata as m,json,sys;from pathlib import Path;print(json.dumps({d.metadata['Name'].lower().replace('_','-'):d.version for d in m.distributions(path=[str(Path(sys.prefix)/'Lib/site-packages')])}))"
        local=json.loads(subprocess.check_output([str(strata),'-c',code],text=True))
        missing=[f'{name}=={targets.get(name,version)}' for name,version in before['strata'].items()
                 if name not in local and name not in {'artifact-tool-v2','hermes-agent'}]
        with (OUT/'strata-isolation.txt').open('w',encoding='utf-8') as log:
            result=subprocess.run([str(uv),'pip','install','--python',str(strata),*missing],stdout=log,stderr=subprocess.STDOUT)
            if result.returncode:raise RuntimeError('Strata isolation preparation failed')
        cfg.write_text(original_cfg.replace('include-system-site-packages = true','include-system-site-packages = false'),encoding='utf-8')
    results=[]
    for name,python in environments.items():
        current=locks.inventory(python)
        changes=[f'{package}=={version}' for package,version in targets.items()
                 if package in before[name] and current.get(package)!=version]
        with (OUT/f'dependencies-{name}.txt').open('w',encoding='utf-8') as log:
            if changes:
                result=subprocess.run([str(uv),'pip','install','--python',str(python),'--no-index',
                    '--find-links',str(wheelhouse),*changes],stdout=log,stderr=subprocess.STDOUT)
                if result.returncode:raise RuntimeError('Dependency update failed: '+name)
            check=subprocess.run([str(uv),'pip','check','--python',str(python)],stdout=log,stderr=subprocess.STDOUT)
            if check.returncode:raise RuntimeError('Dependency validation failed: '+name)
        results.append({'runtime':name,'updates':changes,'check_passed':True})
        (OUT/'dependency-updates.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
        print(json.dumps(results[-1]),flush=True)
    (OUT/'dependency-updates.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    (OUT/'packages-after.json').write_text(json.dumps({name:locks.inventory(python) for name,python in environments.items()},indent=2),encoding='utf-8')


if __name__=='__main__':main()
