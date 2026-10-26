"""Recorded extraction of the common protocol from both supported worker families."""
import ast
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]


def main():
    for name in ('max_worker.py','max_pack_worker.py'):
        path=ROOT/'client-voice'/name;source=path.read_text(encoding='utf-8-sig')
        tree=ast.parse(source);serve=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='serve')
        reader=next(n for n in serve.body if isinstance(n,ast.FunctionDef) and n.name=='read')
        first=next(n for n in serve.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='commands' for t in n.targets))
        lines=source.splitlines(keepends=True)
        lines[first.lineno-1:reader.end_lineno]=['    inbox=CommandInbox(engine)\n    commands,stop,closed=inbox.commands,inbox.stop,inbox.closed\n']
        source=''.join(lines)
        source=source.replace('threading.Thread(target=read, daemon=True).start()','inbox.start()')
        pattern=r"(?m)^( +)with guard:\n\1    current\['id'\] = identifier\n\1    stop.clear\(\)\n\1    if identifier in cancelled_ids:\n\1        stop.set\(\)"
        source,count=re.subn(pattern,lambda m:m[1]+'inbox.begin(identifier)',source)
        if count!=1:raise ValueError('Unexpected begin block: '+name)
        pattern=r"(?m)^( +)with guard:\n\1    current\['id'\] = None"
        source,count=re.subn(pattern,lambda m:m[1]+'inbox.finish()',source)
        if count!=1:raise ValueError('Unexpected completion block: '+name)
        source=source.replace('def serve(configuration,','from worker_protocol import CommandInbox\n\n\ndef serve(configuration,',1)
        ast.parse(source);path.write_text(source,encoding='utf-8')
    path=ROOT/'client-voice/prepare_max.py';source=path.read_text(encoding='utf-8-sig')
    needle="    worker = Path(__file__).with_name('max_worker.py')\n"
    if source.count(needle)!=1:raise ValueError('Legacy installer anchor changed')
    source=source.replace(needle,needle+"    shutil.copy2(worker.with_name('worker_protocol.py'),home/'worker_protocol.py')\n")
    path.write_text(source,encoding='utf-8')
    print('Voice workers now share their bounded command/cancellation protocol.')


if __name__=='__main__':main()
