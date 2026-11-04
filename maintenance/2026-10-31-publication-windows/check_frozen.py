"""Inspect the built EXE and execute its actual frozen Unicode command writer."""
import io
import json
from pathlib import Path
import threading
import types
from PyInstaller.archive.readers import CArchiveReader

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
artifact=ROOT/'toolchain/releases-staging/windows-3.5.55/Accès serveur Fred.exe'
archive=CArchiveReader(str(artifact))
for name in ('conversation.js','ui.css'):
    assert archive.extract(name)==(ROOT/'client-qwen'/name).read_bytes(),'Wrong embedded UI: '+name
pyz=archive.open_embedded_archive('PYZ.pyz')
version=pyz.extract('kiara_shared.version')
assert '3.5.55' in version.co_consts
runtime=pyz.extract('kiara_shared.voice_runtime')
voice=next(code for code in runtime.co_consts if isinstance(code,types.CodeType) and code.co_name=='AdvancedVoice')
writer=next(code for code in voice.co_consts if isinstance(code,types.CodeType) and code.co_name=='_write')
method=types.FunctionType(writer,{'json':json})
text='Léa posa le plateau sur la table. Les dés colorés attendaient patiemment. Elle lança les dés, espérant un six. Son pion avança d’une case, puis d’une autre.'
buffer=io.BytesIO()
with io.TextIOWrapper(buffer,encoding='utf-8') as stdin:
    owner=types.SimpleNamespace(write_lock=threading.Lock(),processes={'tts':types.SimpleNamespace(stdin=stdin,poll=lambda:None)})
    method(owner,{'action':'speak','id':'a'*32,'text':text},'tts')
    wire=buffer.getvalue()
    assert wire.isascii()
    for encoding in ('utf-8','cp1252','cp850'):assert json.loads(wire.decode(encoding))['text']==text
packs=pyz.extract('kiara_shared.voice_packs')
installer=next(code for code in packs.co_consts if isinstance(code,types.CodeType) and code.co_name=='MaxInstallation')
assert any(isinstance(code,types.CodeType) and code.co_name=='choose_folder' for code in installer.co_consts)
result={'passed':True,'version':'3.5.55','ui_matches_sources':True,'folder_choice_included':True,
        'frozen_writer_tested':True,'accented_text_preserved':['utf-8','cp1252','cp850'],
        'text':text,'removed_open_chat_button':b'id="voice-back"' not in archive.extract('conversation.js')}
assert result['removed_open_chat_button']
(OUT/'frozen-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Frozen Windows 3.5.55 UI, folder choice and French Unicode writer verified.')
