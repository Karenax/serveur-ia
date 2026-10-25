'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
  const targets=await (await fetch('http://127.0.0.1:'+process.argv[2]+'/json')).json();
  const target=targets.find(p=>p.type==='page'&&p.url.startsWith('http://127.0.0.1:'));
  assert(target,'Real Android WebView');const socket=new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{socket.addEventListener('open',resolve,{once:true});socket.addEventListener('error',reject,{once:true});});
  let id=0;const pending=new Map();socket.addEventListener('message',event=>{const value=JSON.parse(event.data);if(!value.id)return;const request=pending.get(value.id);if(request){clearTimeout(request.timer);pending.delete(value.id);value.error?request.reject(new Error(value.error.message)):request.resolve(value.result);}});
  const call=(method,params={})=>new Promise((resolve,reject)=>{const next=++id;const timer=setTimeout(()=>reject(new Error('CDP timeout')),10000);pending.set(next,{resolve,reject,timer});socket.send(JSON.stringify({id:next,method,params}));});
  const evaluate=async expression=>{const result=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(result.exceptionDetails)throw new Error(result.exceptionDetails.text);return result.result.value;};
  try{
    assert.equal(await evaluate('config.model'),'fred-demo','Mutate only the local Android demo');
    await evaluate(`$('ui-sidebar-toggle').click();document.querySelector('[data-view-button="voice"]').click();true`);
    assert(await evaluate("!document.querySelector('.voice-view').hidden"));
    assert.equal(await evaluate("$('voice-quality').options.length"),1);
    assert.equal(await evaluate("$('voice-quality').value"),'low');
    assert.equal(await evaluate('typeof AndroidClient.conversationStatus'),'function');
    const capture=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});fs.writeFileSync(__dirname+'/native-android-vocal.png',Buffer.from(capture.data,'base64'));
    await evaluate("$('voice-back').click();true");
    assert(await evaluate("$('voice-start').getBoundingClientRect().height>0"));
    assert(!(await evaluate("$('conversation-start').getBoundingClientRect().height>0")));
    console.log(JSON.stringify({passed:true,checks:['Actual Android WebView opens Vocal through sidebar','Low only','Native conversation bridge available','Back to chat retains dictation']}));
  }finally{socket.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
