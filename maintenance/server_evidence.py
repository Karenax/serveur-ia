"""Combine a completed full suite with explicit successful reruns of every failure."""
import hashlib
from pathlib import Path
import re


def evidence(log, rechecks=()):
    def read(path):
        path=Path(path).resolve()
        raw=path.read_bytes()
        return raw.decode('utf-8-sig',errors='replace'),{'log':str(path),'sha256':hashlib.sha256(raw).hexdigest()}
    text,base=read(log)
    counts=re.findall(r'^Ran (\d+) tests? in [\d.]+s\s*$',text,re.M)
    failures=set(re.findall(r'^(?:FAIL|ERROR): \w+ \(([^)]+)\)\s*$',text,re.M))
    failed=re.search(r'^FAILED \(([^)]+)\)\s*$',text,re.M)
    base_ok=bool(re.search(r'^OK(?: \([^\n]*\))?\s*$',text,re.M)) and not failed
    checks=[];resolved=set();all_ok=True
    for path in rechecks:
        value,record=read(path)
        record['passed']=bool(re.search(r'^OK(?: \([^\n]*\))?\s*$',value,re.M)) and not re.search(r'^FAILED\b',value,re.M)
        checks.append(record);all_ok=all_ok and record['passed']
        if record['passed']:
            resolved.update(re.findall(r'^test_\w+ \(([^)]+)\) \.\.\. ok\s*$',value,re.M))
    # A crash or truncated failure summary cannot be treated as a completed suite.
    listed=sum(int(value) for value in re.findall(r'(?:failures|errors)=(\d+)',failed[1])) if failed else 0
    complete=bool(counts) and (base_ok or bool(failed and listed==len(failures) and listed))
    passed=complete and all_ok and (base_ok or bool(rechecks and failures.issubset(resolved)))
    return {'check':'server','reused':True,'passed':bool(passed),'full_suite':base,
            'full_suite_count':int(counts[-1]) if counts else None,'base_passed':base_ok,
            'initial_failures':sorted(failures),'resolved_by_rechecks':sorted(failures&resolved),
            'rechecks':checks}
