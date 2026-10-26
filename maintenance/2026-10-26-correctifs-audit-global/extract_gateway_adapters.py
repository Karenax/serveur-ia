"""Recorded extraction of HTTP-only voice/embedding adapters from the gateway."""
import ast
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


class HandlerNames(ast.NodeTransformer):
    def visit_Name(self,node):
        if node.id=='self':return ast.copy_location(ast.Name(id='handler',ctx=node.ctx),node)
        return node


def main():
    path=ROOT/'lanceur/remote.py';source=path.read_text(encoding='utf-8-sig');tree=ast.parse(source)
    gateway=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='serve_gateway')
    handler=next(n for n in gateway.body if isinstance(n,ast.ClassDef) and n.name=='Handler')
    post=next(n for n in handler.body if isinstance(n,ast.FunctionDef) and n.name=='do_POST')
    command_paths={'/v1/agent/action','/v1/notifications/action','/v1/device','/v1/history','/v1/workspace/action'}
    remove=[];voice=[];embedding=None
    for node in post.body:
        if not isinstance(node,ast.If):continue
        paths={n.value for n in ast.walk(node.test) if isinstance(n,ast.Constant) and isinstance(n.value,str)}
        if paths&command_paths:remove.append(node)
        elif '/v1/embeddings' in paths:embedding=node;remove.append(node)
        elif '/v1/voice/max/test' in paths:voice.append(('max_voice',node));remove.append(node)
        elif '/v1/voice/speech' in paths:voice.append(('low_voice',node));remove.append(node)
    if len(remove)!=8 or len(voice)!=2 or embedding is None:raise ValueError('Unexpected gateway adapter structure')
    prefix='import json\nimport http.client\nfrom kiara_shared.http import json_body\nfrom workspace_types import Conflict, Denied\n\n'
    def function(name,node):
        body=[HandlerNames().visit(statement) for statement in node.body]
        statements='\n'.join(ast.unparse(ast.fix_missing_locations(statement)) for statement in body)
        return 'def '+name+'(handler,store):\n'+'\n'.join('    '+line for line in statements.splitlines())+'\n\n'
    text='"""Authenticated bounded voice streaming adapters, independent of inference routing."""\n'+prefix
    for name,node in voice:text+=function(name,node)
    text+="MAX_ROUTES=('/v1/voice/max/test','/v1/voice/max/warm','/v1/voice/max/end','/v1/voice/max/transcribe','/v1/voice/max/speech','/v1/voice/max/cancel')\nLOW_ROUTES=('/v1/voice/speech','/v1/voice/cancel')\n"
    (ROOT/'lanceur/gateway_voice.py').write_text(text,encoding='utf-8')
    (ROOT/'lanceur/gateway_embeddings.py').write_text('"""Bounded authenticated public embedding adapter."""\n'+prefix+function('handle',embedding),encoding='utf-8')
    lines=source.splitlines(keepends=True)
    for node in reversed(remove):lines[node.lineno-1:node.end_lineno]=[]
    source=''.join(lines)
    anchor='        def do_POST(self):\n'
    dispatch=('            from gateway_commands import ROUTES as COMMAND_ROUTES, handle as command\n'
              '            from gateway_voice import MAX_ROUTES, LOW_ROUTES, max_voice, low_voice\n'
              '            from gateway_embeddings import handle as embeddings\n'
              '            if self.path in COMMAND_ROUTES:return command(self,store)\n'
              '            if self.path in MAX_ROUTES:return max_voice(self,store)\n'
              '            if self.path in LOW_ROUTES:return low_voice(self,store)\n'
              "            if self.path=='/v1/embeddings':return embeddings(self,store)\n")
    if source.count(anchor)!=1:raise ValueError('Unexpected POST handler')
    source=source.replace(anchor,anchor+dispatch,1);ast.parse(source);path.write_text(source,encoding='utf-8')
    print('Gateway HTTP command, voice and embedding adapters extracted.')


if __name__=='__main__':main()
