"""Recorded AST extraction of existing operations into explicit domain modules."""
from pathlib import Path
import ast

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'lanceur/workspace.py'


class DomainNames(ast.NodeTransformer):
    def visit_Name(self,node):
        return ast.copy_location(ast.Name(id={'self':'workspace','v':'values'}.get(node.id,node.id),ctx=node.ctx),node)

    def visit_Return(self,node):
        return ast.copy_location(ast.Return(value=ast.Tuple(elts=[self.visit(node.value),ast.Constant(False)],ctx=ast.Load())),node)


def main():
    source=SOURCE.read_text(encoding='utf-8');tree=ast.parse(source)
    helpers=[node for node in tree.body if isinstance(node,(ast.FunctionDef,ast.ClassDef))
             and node.name in {'Conflict','Denied','identifier','text'}]
    types='"""Shared Workspace validation and domain errors, independent of transport."""\nimport re\nfrom kiara_shared.history_store import HISTORY_RESET_ID\nMAX_TEXT = 500000\n\n'
    types+='\n\n'.join(ast.unparse(node) for node in helpers)+'\n'
    (ROOT/'lanceur/workspace_types.py').write_text(types,encoding='utf-8')
    cls=next(node for node in tree.body if isinstance(node,ast.ClassDef) and node.name=='Workspace')
    action=next(node for node in cls.body if isinstance(node,ast.FunctionDef) and node.name=='_action')
    transaction=next(node for node in action.body if isinstance(node,ast.With))
    chain=next(node for node in transaction.body if isinstance(node,ast.If) and 'action' in ast.unparse(node.test))
    groups={name:[] for name in ('project','document','memory','knowledge','conversation','job')}
    while isinstance(chain,ast.If):
        names=[node.value for node in ast.walk(chain.test) if isinstance(node,ast.Constant) and isinstance(node.value,str)]
        if names[0].startswith('personal_memory') or names[0].startswith('memory_'):group='memory'
        elif names[0] in {'search','source_get','index_status'}:group='document'
        elif names[0]=='knowledge_search':group='knowledge'
        else:group=names[0].split('_')[0]
        groups[group].append((names,chain))
        chain=chain.orelse[0] if chain.orelse else None
    imports=[];dispatch=[]
    for domain,branches in groups.items():
        if not branches:continue
        imports.append(f'        from workspace_{domain} import execute as {domain}_action')
        actions=[name for names,_ in branches for name in names]
        dispatch.append(f'            {tuple(actions)!r}: {domain}_action,')
        root=None;tail=None
        for names,branch in branches:
            node=ast.If(test=ast.Compare(left=ast.Name(id='action',ctx=ast.Load()),ops=[ast.In()],
                comparators=[ast.Tuple(elts=[ast.Constant(value) for value in names],ctx=ast.Load())]),
                body=[DomainNames().visit(statement) for statement in branch.body],orelse=[])
            if root is None:root=node
            else:tail.orelse=[node]
            tail=node
        tail.orelse=[ast.Raise(exc=ast.Call(func=ast.Name(id='ValueError',ctx=ast.Load()),args=[ast.Constant('Action inconnue.')],keywords=[]))]
        module='"""'+domain.capitalize()+' operations; the caller owns the access and database transaction."""\n'
        module+='import base64\nimport json\nimport secrets\nfrom pathlib import Path\n'
        module+='from workspace_types import Conflict, Denied, identifier, text, MAX_TEXT, HISTORY_RESET_ID\n'
        module+='from kiara_shared.attachments import validate_message\n\n'
        module+='def execute(workspace, db, owner, values, now, prepared=None):\n    action = values.get("action")\n'
        module+='\n'.join('    '+line for line in ast.unparse(ast.fix_missing_locations(root)).splitlines())
        module+='\n    return result, True\n'
        ast.parse(module)
        (ROOT/f'lanceur/workspace_{domain}.py').write_text(module,encoding='utf-8')
    lines=source.splitlines(keepends=True)
    start=transaction.lineno-1;end=transaction.end_lineno
    replacement='\n'.join(imports)+'\n        domains = {\n'+'\n'.join(dispatch)+'\n        }\n'
    replacement+='        handler = next((handler for names, handler in domains.items() if action in names), None)\n'
    replacement+='        if handler is None:\n            raise ValueError("Action inconnue.")\n'
    replacement+='        with self.db(owner) as db:\n            if self.maintenance:\n                raise Denied("Serveur en maintenance.")\n'
    replacement+='            result, changed = handler(self, db, owner, v, now, prepared)\n'
    replacement+='            if changed:\n                self.event(db, owner, action, result.get("id", v.get("id", v.get("project", ""))))\n            return result\n'
    lines[start:end]=[replacement]
    source=''.join(lines)
    tree=ast.parse(source);lines=source.splitlines(keepends=True)
    for node in reversed(tree.body):
        if isinstance(node,(ast.FunctionDef,ast.ClassDef)) and node.name in {'Conflict','Denied','identifier','text'}:
            lines[node.lineno-1:node.end_lineno]=[]
    source=''.join(lines).replace('MAX_TEXT = 500000\n','').replace("HISTORY_RESET_ID = '20261006-remove-assistants'\n",'')
    source=source.replace('from kiara_shared.attachments import validate_message\n',
        'from kiara_shared.attachments import validate_message\nfrom workspace_types import Conflict, Denied, identifier, text, MAX_TEXT, HISTORY_RESET_ID\n',1)
    ast.parse(source);SOURCE.write_text(source,encoding='utf-8')
    print('Workspace domains extracted; transaction and event orchestration stay centralized.')


if __name__=='__main__':main()
