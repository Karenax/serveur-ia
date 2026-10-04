"""Limit this Strata engine to eight spread physical cores, retaining one worker per core."""
import argparse
import ctypes as c
from ctypes import wintypes as w
import datetime as dt
import json
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--pid', type=int, required=True)
p.add_argument('--out', type=Path, required=True)
p.add_argument('--apply', action='store_true')
p.add_argument('--placement', choices=('compact', 'spread'), default='spread')
p.add_argument('--worker-ids', help='Explicit verified worker IDs, in pool creation order, for restoring lost thread affinities')
a = p.parse_args()
k = c.WinDLL('kernel32', use_last_error=True)
def api(name, types, result=w.BOOL):
    f = getattr(k, name); f.argtypes = types; f.restype = result; return f
close = api('CloseHandle', [w.HANDLE])
op = api('OpenProcess', [w.DWORD, w.BOOL, w.DWORD], w.HANDLE)
ot = api('OpenThread', [w.DWORD, w.BOOL, w.DWORD], w.HANDLE)
query = api('QueryFullProcessImageNameW', [w.HANDLE, w.DWORD, w.LPWSTR, c.POINTER(w.DWORD)])
getpm = api('GetProcessAffinityMask', [w.HANDLE, c.POINTER(c.c_size_t), c.POINTER(c.c_size_t)])
setpm = api('SetProcessAffinityMask', [w.HANDLE, c.c_size_t])
settm = api('SetThreadAffinityMask', [w.HANDLE, c.c_size_t], c.c_size_t)
class Group(c.Structure):
    _fields_ = [('mask', c.c_size_t), ('group', w.WORD), ('reserved', w.WORD * 3)]
gettm = api('GetThreadGroupAffinity', [w.HANDLE, c.POINTER(Group)])
class FileTime(c.Structure):
    _fields_ = [('low', w.DWORD), ('high', w.DWORD)]
get_times = api('GetThreadTimes', [w.HANDLE] + [c.POINTER(FileTime)] * 4)
class ThreadEntry(c.Structure):
    _fields_ = [('size', w.DWORD), ('usage', w.DWORD), ('tid', w.DWORD), ('owner', w.DWORD),
               ('base_priority', w.LONG), ('delta_priority', w.LONG), ('flags', w.DWORD)]
snapshot = api('CreateToolhelp32Snapshot', [w.DWORD, w.DWORD], w.HANDLE)
first = api('Thread32First', [w.HANDLE, c.POINTER(ThreadEntry)])
next_ = api('Thread32Next', [w.HANDLE, c.POINTER(ThreadEntry)])
topology = api('GetLogicalProcessorInformationEx', [c.c_int, c.c_void_p, c.POINTER(w.DWORD)])
def check(ok):
    if not ok: raise c.WinError(c.get_last_error())
def thread_rows():
    snap = snapshot(4, 0)
    if snap == c.c_void_p(-1).value: raise c.WinError(c.get_last_error())
    result = []
    try:
        e = ThreadEntry(); e.size = c.sizeof(e)
        more = first(snap, c.byref(e))
        while more:
            if e.owner == a.pid:
                th = ot(0x0040, False, e.tid)
                check(th)
                try:
                    g = Group(); check(gettm(th, c.byref(g)))
                    ft = [FileTime() for _ in range(4)]
                    check(get_times(th, *[c.byref(t) for t in ft]))
                    result.append(dict(tid=e.tid, mask=g.mask, group=g.group,
                                       created_ticks=(ft[0].high << 32) + ft[0].low))
                finally: close(th)
            more = next_(snap, c.byref(e))
    finally: close(snap)
    return result
size = w.DWORD()
topology(0, None, c.byref(size))
buf = c.create_string_buffer(size.value); check(topology(0, buf, c.byref(size)))
physical = []
offset = 0
while offset < size.value:
    relationship = w.DWORD.from_buffer(buf, offset).value
    length = w.DWORD.from_buffer(buf, offset + 4).value
    if relationship == 0:
        group_count = w.WORD.from_buffer(buf, offset + 30).value
        g = Group.from_buffer(buf, offset + 32)
        if group_count != 1 or g.group != 0: raise RuntimeError('Only one CPU group is supported by this local probe')
        bits = [i for i in range(64) if g.mask & (1 << i)]
        physical.append(dict(logical=bits, primary=bits[0], mask=g.mask))
    offset += length
if len(physical) != 16: raise RuntimeError('This probe expects the measured 16-core 3955WX')
spread = physical[:8] if a.placement == 'compact' else [physical[j] for i in range(4) for j in (i, i + 8)]
selected_mask = sum(x['mask'] for x in spread)
process = op(0x0400 | (0x0200 if a.apply else 0), False, a.pid); check(process)
try:
    name = c.create_unicode_buffer(32768); n = w.DWORD(len(name)); check(query(process, 0, name, c.byref(n)))
    expected = Path(__file__).resolve().parent / 'strata-build-p100' / 'strata.exe'
    if Path(name.value).resolve() != expected.resolve(): raise RuntimeError('PID is not the expected Strata binary')
    pm = c.c_size_t(); sm = c.c_size_t(); check(getpm(process, c.byref(pm), c.byref(sm)))
    before = thread_rows()
    record = dict(pid=a.pid, executable=name.value, created=dt.datetime.now(dt.timezone.utc).isoformat(),
                  physical_topology=physical, placement=a.placement, selected_physical_cores=spread, selected_process_mask=selected_mask,
                  process_mask_before=pm.value, threads_before=before, applied=False,
                  note='Seven expert workers plus the host on eight physical cores. '
                       'SMT siblings remain allowed for auxiliary GPU/runtime threads; expert workers use one logical CPU per core.')
    if a.apply:
        host = min(before, key=lambda t: t['created_ticks'])
        plan = []
        explicit = list(map(int, a.worker_ids.split(','))) if a.worker_ids else None
        if explicit is not None and (len(explicit) != 7 or len(set(explicit)) != 7):
            raise RuntimeError('Exactly seven distinct verified worker IDs are required')
        for i, (old, new) in enumerate(zip(physical[1:8], spread[1:])):
            matches = [t for t in before if t['group'] == 0 and
                       (t['tid'] == explicit[i] if explicit else t['mask'] == (1 << old['primary']))]
            if len(matches) != 1: raise RuntimeError(f'Cannot identify exactly one worker on logical CPU {old["primary"]}: {matches}')
            plan.append(dict(tid=matches[0]['tid'], old_mask=matches[0]['mask'], new_mask=1 << new['primary']))
        changed = []
        original_process_mask = pm.value
        try:
            # Windows resets thread masks when the process mask changes: narrow the process FIRST,
            # then restore one logical processor per expert worker.
            check(setpm(process, selected_mask))
            th = ot(0x0020 | 0x0040, False, host['tid']); check(th)
            try: check(settm(th, 1 << physical[0]['primary']))
            finally: close(th)
            for item in plan:
                th = ot(0x0020 | 0x0040, False, item['tid']); check(th)
                try: check(settm(th, item['new_mask']))
                finally: close(th)
                changed.append(item)
        except BaseException:
            setpm(process, sm.value)
            for item in changed:
                th = ot(0x0020 | 0x0040, False, item['tid'])
                if th:
                    settm(th, item['old_mask']); close(th)
            setpm(process, original_process_mask)
            raise
        check(getpm(process, c.byref(pm), c.byref(sm)))
        after = thread_rows()
        if pm.value != selected_mask or any(t['mask'] & ~selected_mask for t in after):
            raise RuntimeError('Effective process/thread mask verification failed')
        masks = {t['tid']: t['mask'] for t in after}
        if any(masks.get(item['tid']) != item['new_mask'] for item in plan):
            raise RuntimeError('Effective worker mask verification failed')
        if masks.get(host['tid']) != 1 << physical[0]['primary']:
            raise RuntimeError('Effective host mask verification failed')
        record.update(applied=True, process_mask_after=pm.value, host_tid=host['tid'],
                      host_mask=1 << physical[0]['primary'], worker_mapping=plan, threads_after=after)
    a.out.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(record, ensure_ascii=False), flush=True)
finally: close(process)
