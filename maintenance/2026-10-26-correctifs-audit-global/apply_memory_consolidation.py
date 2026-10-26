"""Recorded one-shot extraction; refuses to apply to unexpected source shapes."""
from pathlib import Path
import ast
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def replace(path, before, after):
    target = ROOT / path
    source = target.read_text(encoding='utf-8-sig')
    if source.count(before) != 1:
        raise ValueError(f'Unexpected anchor: {path}: {before[:80]}')
    target.write_text(source.replace(before, after, 1), encoding='utf-8')


def main():
    changed = subprocess.check_output(['git', 'diff', '--name-only'], cwd=ROOT).decode().splitlines()
    (OUT/'preexisting-files.json').write_text(json.dumps({name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
        for name in changed}, indent=2), encoding='utf-8')
    target = ROOT/'lanceur/assistant_commands.py'
    source = target.read_text(encoding='utf-8-sig')
    tree = ast.parse(source)
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'memories')
    lines = source.splitlines(keepends=True)
    lines[function.lineno-1:function.end_lineno] = ['from memory_service import memories, mutate_memory\n']
    source = ''.join(lines)
    start = source.index("            table = 'memories' if project else 'personal_memories'", source.index('def execute('))
    end = source.index("        elif operation == 'note_create':", start)
    source = source[:start] + (
        '            result = mutate_memory(workspace, db, owner, project, operation, values,\n'
        '                                   origin=origin, request_text=request_text)\n'
    ) + source[end:]
    target.write_text(source, encoding='utf-8')

    target = ROOT/'lanceur/workspace.py'
    source = target.read_text(encoding='utf-8-sig')
    start = source.index("            elif action in ('personal_memory_create','personal_memory_save','personal_memory_delete'):")
    end = source.index("            elif action=='knowledge_search':", start)
    source = source[:start] + (
        "            elif action in ('personal_memory_create','personal_memory_save','personal_memory_delete',\n"
        "                            'memory_create','memory_save','memory_delete'):\n"
        "                from memory_service import legacy_action\n"
        "                result = legacy_action(self, db, owner, action, v)\n"
    ) + source[end:]
    start = source.index("            elif action=='memory_create':")
    end = source.index("            elif action=='conversation_save':", start)
    source = source[:start] + source[end:]
    start = source.index("            if action in ('memory_create','memory_save','memory_delete','personal_memory_create','personal_memory_save','personal_memory_delete'):")
    end = source.index('            self.event(', start)
    source = source[:start] + source[end:]
    source = source.replace('    def snapshot(self,owner):\n', '    def snapshot(self,owner):\n        from memory_service import memories\n', 1)
    source = source.replace("p['memories']=[dict(r) for r in db.execute('SELECT id,text FROM memories WHERE owner=? AND project=? ORDER BY updated',(owner,p['id']))]", "p['memories']=memories(db,owner,p['id'])", 1)
    source = source.replace("'personal_memories':[dict(r) for r in db.execute('SELECT id,text,updated FROM personal_memories WHERE owner=? ORDER BY updated DESC',(owner,))]", "'personal_memories':memories(db,owner,None)", 1)
    target.write_text(source, encoding='utf-8')

    path = 'client-qwen/workspace.html'
    replace(path, 'input.dataset.savedText=memory.text;\n', "input.dataset.savedText=memory.text;input.dataset.revision=memory.revision||'';\n")
    replace(path, "await wsAction('memory_save',{id:memory.id,text});input.dataset.savedText=text;", "const saved=await wsAction('memory_save',{id:memory.id,text,revision:input.dataset.revision});input.dataset.revision=saved.revision;input.dataset.savedText=text;")
    replace(path, "await wsAction('memory_delete',{id:memory.id});", "await wsAction('memory_delete',{id:memory.id,revision:input.dataset.revision});")
    replace(path, "const input=row.querySelector('textarea');if(input.dataset.dirty!=='true'&&input.value!==memory.text){input.value=memory.text;input.dataset.savedText=memory.text;}", "const input=row.querySelector('textarea');if(input.dataset.dirty!=='true'){input.value=memory.text;input.dataset.savedText=memory.text;input.dataset.revision=memory.revision||'';}")
    replace('lanceur/web/workspace.js', "action:'personal_memory_save',owner,id:m.id,text", "action:'personal_memory_save',owner,id:m.id,text,revision:m.revision")
    replace('lanceur/web/workspace.js', "action:'personal_memory_delete',owner,id:m.id}", "action:'personal_memory_delete',owner,id:m.id,revision:m.revision}")
    print('Canonical memory service and revision-aware adapters installed.')


if __name__ == '__main__':
    main()
