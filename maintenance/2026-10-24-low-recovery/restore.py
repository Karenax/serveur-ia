"""Restore the released Phonon Low controller, keeping Max's controller separate."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[2]
path=ROOT/'client-qwen/conversation.js'
source=subprocess.check_output(['git','show','75e8eb8:client-qwen/conversation.js'],cwd=ROOT).decode('utf-8')
blocks={
 'splitSpeech':source[source.index('  function splitSpeech('):source.index('  async function pcm(')],
 'speak':source[source.index('  async function speak('):source.index('  async function pump(')],
 'refresh':source[source.index('  async function refresh('):source.index('  button.onclick=')],
}
stable='\n  // Low: retain the Phonon controller released in 3.5.39.\n'
for name,block in blocks.items():
    block=block.replace('function '+name+'(', 'function classicLow'+name[0].upper()+name[1:]+'(')
    block=block.replace("await api('/client/conversation')",'await transportConversation()').replace('Fred','Kiara')
    stable+=block
text=path.read_text(encoding='utf-8')
text=text.replace('  function splitSpeech(final=false){', stable+'  function splitSpeech(final=false){\n    if(native.quality!==\'max\')return classicLowSplitSpeech(final);',1)
text=text.replace('  async function speak(text,token){', "  async function speak(text,token){\n    if(native.quality!=='max')return classicLowSpeak(text,token);",1)
text=text.replace('    syncAndroidPlayback();if(polling||acting||muting)return;polling=true;', "    syncAndroidPlayback();if(quality.value==='low')return classicLowRefresh();if(polling||acting||muting)return;polling=true;",1)
text=text.replace("native=await command('start',{quality:quality.value,execution:quality.value==='max'?execution.value:'pc'});", "native=await command('start',quality.value==='max'?{quality:'max',execution:execution.value}:{});")
text=text.replace('    const locked=active||window.conversationBusy||acting||native.phase===\'installing\';', "    const locked=active||window.conversationBusy||acting||native.phase==='installing';\n    options.hidden=quality.value==='low';")
text=text.replace("const playing=!!responding()||Date.now()<listenAfter,key=session+':'+playing+':'+allowInterruptions.checked;", "const classic=quality.value==='low',interruptions=classic?native.aec_supported===true:allowInterruptions.checked;\n    const playing=classic?!!(speechRunning||sources.size||speechQueue.length):!!responding()||Date.now()<listenAfter,key=session+':'+playing+':'+interruptions;")
text=text.replace("command('playback',{playing,interruptions:allowInterruptions.checked})", "command('playback',{playing,interruptions})")
path.write_text(text,encoding='utf-8')
Path(__file__).with_name('restored-controller.json').write_text(json.dumps({'commit':'75e8eb8','version':'3.5.39','blocks':{name:hashlib.sha256(block.encode()).hexdigest() for name,block in blocks.items()},'recognition':'unchanged','tts':'Phonon /v1/voice/speech','max_controller':'unchanged'},indent=2),encoding='utf-8')
print('Low Phonon sentence playback and recognized-turn loop restored from 3.5.39.')
