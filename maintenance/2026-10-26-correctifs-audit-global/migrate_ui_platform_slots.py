"""One-shot replacement of source-code substitutions by named platform slots."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
SOURCE=ROOT/'client-qwen'
MOBILE=ROOT/'client-android/mobile-ui'
GENERATOR=ROOT/'client-android/scripts/Prepare-Assets.py'
CODE_LITERALS={
    "['/v1/models','/client/integrations/apply'].includes(path)",
    "if(busy||!loggedIn||$('connection-choice').open)",
    "['access','connection','updates','api']",
    "if(!connected||busy||historySyncPending||conversationActionPending||wsDraggedConversation)",
    "if(name==='api')uiRefreshIntegrations();",'uiIntegrationButtons();',
}
ASSEMBLY={'markdown bootstrap','workspace bootstrap','style assembly'}


def main():
    spec=importlib.util.spec_from_file_location('old_assets',GENERATOR)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    originals={};annotated={};operations={};counter=0
    mobile={p.name:p.read_text(encoding='utf-8-sig') for p in MOBILE.iterdir() if p.is_file()}

    def replacement(value):
        for name,text in sorted(mobile.items(),key=lambda pair:-len(pair[1])):
            stripped=text.rstrip()
            if stripped and stripped in value:
                before,after=value.split(stripped,1)
                return {'file':name,'prefix':before,'suffix':after,'rstrip':True}
        return {'value':str(value)}

    def slot(origin,start,end,new,name,html=False):
        nonlocal counter
        counter+=1
        identity=re.sub('[^a-z0-9]+','-',name.lower()).strip('-')+'-'+str(counter)
        opening=f'<!-- kiara-slot:{identity} -->' if html else f'/* kiara-slot:{identity} */'
        closing=f'<!-- /kiara-slot:{identity} -->' if html else f'/* /kiara-slot:{identity} */'
        text=annotated[origin]
        annotated[origin]=text[:start]+opening+text[start:end]+closing+text[end:]
        operations.setdefault(origin,[]).append({'slot':identity,'html':html,**replacement(str(new))})

    class UI(str):
        def __new__(cls,value,origin):
            result=super().__new__(cls,value);result.origin=origin;return result
        def replace(self,old,new,count=-1):
            origin=self.origin
            if origin is not None and old!='</script' and str(self).count(old):
                if old in CODE_LITERALS:
                    remaining=count;cursor=0
                    while remaining!=0:
                        start=annotated[origin].find(old,cursor)
                        if start<0:break
                        slot(origin,start,start+len(old),new,'platform-expression')
                        cursor=annotated[origin].find(old,start)+len(old)+80
                        if remaining>0:remaining-=1
                else:
                    operations.setdefault(origin,[]).append({'label':old,**replacement(str(new))})
            return UI(str(self).replace(old,new,count),origin)

    def read(path):
        value=path.read_text(encoding='utf-8-sig')
        try:origin=path.relative_to(SOURCE).as_posix()
        except ValueError:origin=None
        if origin is not None:
            originals.setdefault(origin,value);annotated.setdefault(origin,value)
        return UI(value,origin)

    def replace_once(text,old,new,name):
        if str(text).count(old)!=1:raise ValueError('Unexpected original slot '+name)
        origin=text.origin
        if name not in ASSEMBLY:
            before=annotated[origin];start=before.find(old)
            if start<0:raise ValueError('Overlapping slot '+name)
            slot(origin,start,start+len(old),new,name,html=old.lstrip().startswith('<'))
        return UI(str(text).replace(old,str(new),1),origin)

    def sub_once(text,pattern,new,name):
        origin=text.origin
        match=re.search(pattern,annotated[origin],re.S)
        if match is None:raise ValueError('Missing original region '+name)
        slot(origin,match.start(),match.end(),new,name,html=match[0].lstrip().startswith('<'))
        value,count=re.subn(pattern,lambda _:str(new),str(text),count=1,flags=re.S)
        if count!=1:raise ValueError('Missing transformed region '+name)
        return UI(value,origin)

    module.read=read;module.replace_once=replace_once;module.sub_once=sub_once
    previous=str(module.prepare(SOURCE))
    data={'format':1,'capabilities':{'platform':'android','updates':'native','local_api':True,
          'settings':['access','connection','api'],'send_with_modifier':True,'native_selection':True},
          'sources':operations}
    for name,items in operations.items():
        covered=set()
        value=annotated[name]
        for parent in items:
            if 'slot' not in parent:continue
            identity=re.escape(parent['slot'])
            pattern=(r'<!-- kiara-slot:'+identity+r' -->(.*?)<!-- /kiara-slot:'+identity+r' -->') if parent['html'] else (r'/\* kiara-slot:'+identity+r' \*/(.*?)/\* /kiara-slot:'+identity+r' \*/')
            match=re.search(pattern,value,re.S)
            for child in items:
                if 'slot' in child and child is not parent and 'kiara-slot:'+child['slot'] in match[1]:covered.add(child['slot'])
        for identity in covered:
            value=re.sub(r'/\* /?kiara-slot:'+re.escape(identity)+r' \*/|<!-- /?kiara-slot:'+re.escape(identity)+r' -->','',value)
        annotated[name]=value
        operations[name]=[item for item in items if item.get('slot') not in covered]
    (MOBILE/'platform-adapters.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for name,value in annotated.items():
        if value!=originals[name]:(SOURCE/name).write_text(value,encoding='utf-8')
    source=GENERATOR.read_text(encoding='utf-8-sig')
    start=source.index('def prepare(source: Path) -> str:')
    end=source.index('\ndef validate(',start)
    source=source[:start]+'''def platform_source(source: Path, name: str, adapters: dict) -> str:
    value = read(source / name)
    for operation in adapters.get('sources', {}).get(name, []):
        if 'file' in operation:
            replacement = read(MOBILE / operation['file'])
            if operation.get('rstrip'): replacement = replacement.rstrip()
            replacement = operation.get('prefix', '') + replacement + operation.get('suffix', '')
        else:
            replacement = operation['value']
        if 'label' in operation:
            value = value.replace(operation['label'], replacement)
            continue
        identity = re.escape(operation['slot'])
        if operation.get('html'):
            pattern = r'<!-- kiara-slot:' + identity + r' -->(.*?)<!-- /kiara-slot:' + identity + r' -->'
        else:
            pattern = r'/\\* kiara-slot:' + identity + r' \\*/(.*?)/\\* /kiara-slot:' + identity + r' \\*/'
        value, count = re.subn(pattern, lambda _: replacement, value, flags=re.S)
        if count != 1:
            raise ValueError('Missing or duplicated platform slot: ' + operation['slot'])
    return value


def prepare(source: Path) -> str:
    adapters = json.loads(read(MOBILE / 'platform-adapters.json'))
    if adapters.get('format') != 1: raise ValueError('Unsupported UI platform contract')
    files = {name: platform_source(source, name, adapters) for name in SHARED}
    presentation = ''.join(script(files[name]) for name in ('ui.js', 'attachments.js', 'corrector.js',
        'selection.js', 'thinking.js', 'voice.js', 'conversation.js')) + script(read(MOBILE / 'android.js'))
    markdown = script(files['vendor/markdown-it.min.js']) + script(files['markdown.js'])
    chat = replace_once(files['chat.html'], '</head>', markdown + '</head>', 'markdown bootstrap')
    chat = replace_once(chat, '</body>', files['workspace.html'] + presentation + '</body>', 'workspace bootstrap')
    chat = replace_once(chat, '__UI_CSS__', files['ui.css'] + '\\n' + read(MOBILE / 'android.css'), 'style assembly')
    validate(chat)
    return chat

''' + source[end:]
    GENERATOR.write_text(source,encoding='utf-8')
    # Verify the mechanism change leaves the generated app byte-identical.
    spec=importlib.util.spec_from_file_location('new_assets',GENERATOR)
    new=importlib.util.module_from_spec(spec);spec.loader.exec_module(new)
    current=new.prepare(SOURCE)
    if current!=previous:
        import difflib
        (OUT/'platform-slot-difference.txt').write_text(''.join(difflib.unified_diff(previous.splitlines(True),current.splitlines(True))),encoding='utf-8')
        raise ValueError('Generated Android output changed; inspect platform-slot-difference.txt')
    (OUT/'platform-slots.json').write_text(json.dumps({'generated_sha256':hashlib.sha256(current.encode()).hexdigest(),
        'identical_output':True,'slots':counter,'source_files':sorted(operations)},indent=2),encoding='utf-8')
    print('Named slots installed:',counter,'; generated Android output is identical.')


if __name__=='__main__':main()
