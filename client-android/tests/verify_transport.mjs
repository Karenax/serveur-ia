// Test only the synthetic transport_fixture.py profile; refuse personal accounts.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const args=process.argv.slice(2),opt=(key,fallback)=>args.includes(key)?args[args.indexOf(key)+1]:fallback;
const port=Number(opt('--port','9223'));
let pages=[];
const readyUntil=Date.now()+20000;
while(Date.now()<readyUntil){
  try{pages=await(await fetch(`http://127.0.0.1:${port}/json`)).json();if(pages.some(p=>p.type==='page'))break;}catch{}
  await new Promise(resolve=>setTimeout(resolve,100));
}
const page=pages.find(p=>p.type==='page'&&p.url.startsWith('http://127.0.0.1:'));
assert(page,'Expected local WebView');
const socket=new WebSocket(page.webSocketDebuggerUrl);
await new Promise((resolve,reject)=>{socket.addEventListener('open',resolve,{once:true});socket.addEventListener('error',reject,{once:true});});
let seq=0;const pending=new Map(),errors=[];
socket.addEventListener('message',event=>{const value=JSON.parse(event.data);if(value.id){const request=pending.get(value.id);if(request){clearTimeout(request.timer);pending.delete(value.id);value.error?request.reject(new Error('CDP failure')):request.resolve(value.result);}}else if(value.method==='Runtime.exceptionThrown')errors.push('WebView exception');});
const call=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq,timer=setTimeout(()=>{pending.delete(id);reject(new Error('CDP timeout'));},40000);pending.set(id,{resolve,reject,timer});socket.send(JSON.stringify({id,method,params}));});
const evaluate=async expression=>{const result=await call('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});assert(!result.exceptionDetails,'WebView evaluation failed');return result.result.value;};
const until=async expression=>{const end=Date.now()+30000;while(Date.now()<end){if(await evaluate(expression))return;await new Promise(resolve=>setTimeout(resolve,100));}throw new Error('Fixture UI timeout');};
const output=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../toolchain/android-tests');
try{
  await call('Runtime.enable');await call('Page.enable');
  await until("typeof config!=='undefined'&&config.model==='fred-fixture'&&typeof historyReady!=='undefined'&&historyReady&&!historySyncPending");
  assert(await evaluate("document.getElementById('android-profile-name').textContent.startsWith('Fixture Android')"),'Refusing mutations outside isolated fixture');
  const state=await evaluate("api('/client/state').then(s=>({transport:s.connection.transport,hasProfile:!s.profile_required}))");
  assert(state.hasProfile,'Imported fixture');
  const expectedTransport=args.includes('--https')?'https':'wireguard';
  assert.equal(state.transport,expectedTransport,'Expected native transport selected');
  const projectReply='Réponse de projet reçue par '+(expectedTransport==='https'?'HTTPS':'WireGuard');
  if(args.includes('--project-chat')){
    const setPrompt=text=>evaluate(`(()=>{const input=$('prompt');input.value=${JSON.stringify(text)};input.dispatchEvent(new Event('input',{bubbles:true}));})()`);
    await until("connected && !conversationLocked() && !document.querySelector('.project-conversation-switch button').hidden");
    if(args.includes('--read-only')){
      assert(await evaluate("$('prompt').value==='Brouillon personnel de recette'"),'Personal draft restored after restart');
    }else{
      await setPrompt('Brouillon personnel de recette');
    }
    await evaluate("document.querySelector('.project-conversation-switch button').click()");
    await until("kiaraProjectConversation.active && !document.querySelector('.project-conversation-switch button').disabled");
    await evaluate("(()=>{const select=document.querySelector('.project-conversation-controls select');select.value='brain-fixture';select.dispatchEvent(new Event('change'));})()");
    const finished="!document.querySelector('.project-conversation-switch button').disabled";
    const openRecorded=async()=>{
      await until("Array.from(document.querySelectorAll('.project-conversation-controls select')[1].options).some(option=>option.value==='fil-recette')");
      await evaluate("(()=>{const select=document.querySelectorAll('.project-conversation-controls select')[1];select.value='fil-recette';select.dispatchEvent(new Event('change'));})()");
      await until("document.querySelector('.project-conversation-messages').textContent.includes('Ancienne réponse') && "+finished);
      assert(await evaluate("document.querySelectorAll('.project-conversation-controls select')[1].value==='fil-recette'"),'Reopened thread selected in history');
    };
    assert(await evaluate("document.querySelector('.project-conversation-controls input[type=checkbox]').checked"),'Ephemeral mode enabled by default');
    if(args.includes('--read-only')){
      assert(await evaluate("!document.querySelector('.project-conversation-messages').textContent.includes('Échange éphémère de recette')"),'Ephemeral exchange discarded on restart');
      await openRecorded();
      assert(await evaluate("document.querySelector('.project-conversation-messages').textContent.includes('Suite conservée de recette')"),'Recorded thread survives restart');
      assert(await evaluate("$('prompt').value==='Brouillon de projet de recette'"),'Recorded project draft restored after restart');
    }else{
      await setPrompt('Échange éphémère de recette');
      await evaluate("$('composer').requestSubmit()");
      await until("document.querySelector('.project-conversation-messages').textContent.includes("+JSON.stringify(projectReply)+") && "+finished);
      await evaluate("(()=>{const source=document.querySelector('.project-conversation-messages details button');source.closest('details').open=true;source.click();})()");
      await until("wsSourceDialog.open && wsSourceDialog.textContent.includes('Texte indexé de la notice.')");
      await evaluate('wsSourceDialog.close()');
      assert(await evaluate("api('/client/state').then(s=>!JSON.stringify(s.preferences).includes('Échange éphémère de recette'))"));
      await openRecorded();
      await setPrompt('Suite conservée de recette');
      await evaluate("$('composer').requestSubmit()");
      await until("document.querySelector('.project-conversation-messages').textContent.includes("+JSON.stringify(projectReply)+") && "+finished);
      await setPrompt('Brouillon de projet de recette');
      await evaluate('uiPersistPreferences()');
    }
    const capture=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
    const evidence=args.includes('--capture')?opt('--capture'):path.join(output,'wireguard-project-chat.png');
    await fs.mkdir(path.dirname(evidence),{recursive:true});
    await fs.writeFile(evidence,Buffer.from(capture.data,'base64'));
    if(args.includes('--download-original')){
      await evaluate("(()=>{const source=document.querySelector('.project-conversation-messages details button');source.closest('details').open=true;source.click();})()");
      await until("wsSourceDialog.open && wsSourceDialog.textContent.includes('Texte indexé de la notice.')");
      await evaluate("Array.from(wsSourceDialog.querySelectorAll('button')).find(button=>button.textContent==='Télécharger l’original').click()");
      await until("!wsSourceDialog.textContent.includes('Préparation du fichier…')");
    }else{
      await evaluate("document.querySelector('.project-conversation-switch button').click()");
      assert(await evaluate("$('prompt').value==='Brouillon personnel de recette'"));
    }
    assert.equal(errors.length,0);
    console.log(JSON.stringify({passed:true,transport:expectedTransport,projectChat:true,reopened:args.includes('--read-only')}));
  }else{
  if(args.includes('--oversize-check')){
    for(const route of ['/v1/context','/v1/chat/completions']){
      const rejected=await evaluate(`api(${JSON.stringify(route)},{messages:[{role:'user',content:'A'.repeat(2*1024*1024)}]}).then(()=>({status:200})).catch(e=>({status:e.status,message:e.message}))`);
      assert.equal(rejected.status,413,'Large tunnel request rejected before sending');
      assert(rejected.message.includes('2 Mo')&&rejected.message.includes('WireGuard'),'Actionable structured error');
    }
  }
  if(!args.includes('--read-only')){
    await evaluate("showView('chat');document.getElementById('new').click()");
    await until('!conversationLocked()');
    await evaluate("(()=>{const input=document.getElementById('prompt');input.value='Vérifie le tunnel Android.';input.dispatchEvent(new Event('input',{bubbles:true}));document.getElementById('send').click();})()");
    await until("busy&&messages.some(m=>m.role==='assistant'&&m.content.length>5)");
    await until("!busy&&messages.some(m=>m.role==='assistant'&&m.content.includes('WireGuard vérifiée'))");
    assert(await evaluate('window.androidFlush()'),'Encrypted local history saved');
  }else assert(await evaluate("messages.some(m=>m.role==='assistant'&&m.content.includes('WireGuard vérifiée'))"),'Conversation persisted after restart');
  assert(await evaluate("document.getElementById('messages').querySelector('strong')?.textContent.includes('Réponse de test')"),'Markdown rendered across real tunnel');
  assert.equal(errors.length,0,'No WebView exception');
  if(args.includes('--export-history'))await evaluate("androidSaveFile('verification-fred.json',JSON.stringify({version:1,conversations:library},null,2),'application/json')");
  const capture=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
  await fs.writeFile(path.join(output,'wireguard-transport.png'),Buffer.from(capture.data,'base64'));
  const result={passed:true,checks:['installed WireGuard executable','authenticated UDP tunnel','incremental chat SSE','Markdown','encrypted history persistence'],reopened:args.includes('--read-only')};
  if(args.includes('--oversize-check'))result.checks.push('structured tunnel size errors for chat/context');
  await fs.writeFile(path.join(output,'wireguard-ui-result.json'),JSON.stringify(result,null,2));
  console.log(JSON.stringify(result));
  }
}finally{socket.close();}
