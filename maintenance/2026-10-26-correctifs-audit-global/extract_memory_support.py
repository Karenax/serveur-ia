"""Complete the memory domain boundary without changing its public adapters."""
import ast
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def main():
    path=ROOT/'lanceur/assistant_commands.py';source=path.read_text(encoding='utf-8');tree=ast.parse(source)
    repository={'encoded','digest','save'}
    memory={'words','suppress_old','suppression_rules','retire_legacy','suppressed','model_history',
            'global_preferences','epoch','memory_epoch','bump_memory'}
    functions={node.name:node for node in tree.body if isinstance(node,ast.FunctionDef)}
    support='"""Serialization and storage primitives for assistant domain records."""\nimport hashlib\nimport json\nimport time\n\n'
    support+='\n\n'.join(ast.get_source_segment(source,functions[name]) for name in sorted(repository))+'\n'
    (ROOT/'lanceur/assistant_repository.py').write_text(support,encoding='utf-8')
    memory_path=ROOT/'lanceur/memory_service.py';body=memory_path.read_text(encoding='utf-8')
    body=body.replace('import time\n','import time\nimport unicodedata\nfrom assistant_repository import encoded, digest, save\nfrom workspace_types import Conflict, Denied, identifier, text as validate_text\n',1)
    body=body.replace('    from assistant_commands import digest\n','')
    body=body.replace('    from assistant_commands import bump_memory, clean, digest, save, suppress_old, words\n','')
    body=body.replace('    from workspace import Conflict, Denied, identifier\n','')
    body=body.replace('    from workspace import Denied, identifier\n','')
    body=body.replace("value = clean(values.get('text'))","value = validate_text(values.get('text'),2000,'Texte')")
    body+='\n\n'+'\n\n'.join(ast.get_source_segment(source,functions[name]) for name in sorted(memory))+'\n'
    memory_path.write_text(body,encoding='utf-8')
    lines=source.splitlines(keepends=True)
    for node in reversed(tree.body):
        if isinstance(node,ast.FunctionDef) and node.name in repository|memory:
            lines[node.lineno-1:node.end_lineno]=[]
    source=''.join(lines)
    source=source.replace('from memory_service import memories, mutate_memory',
        'from memory_service import '+', '.join(sorted(memory|{'memories','mutate_memory'}))+'\nfrom assistant_repository import encoded, digest, save')
    source=source.replace('from workspace import text','from workspace_types import text')
    path.write_text(source,encoding='utf-8')
    journal=ROOT/'lanceur/command_journal.py';body=journal.read_text(encoding='utf-8').replace('from workspace import identifier','from workspace_types import identifier').replace('from workspace import Conflict','from workspace_types import Conflict').replace('from assistant_commands import encoded','from assistant_repository import encoded');journal.write_text(body,encoding='utf-8')
    print('Memory support no longer imports the assistant orchestrator or Workspace implementation.')


if __name__=='__main__':main()
