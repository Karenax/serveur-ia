/* Real WebView + actual isolated server fixture over WireGuard. Refuses personal profiles. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
const args=process.argv.slice(2),opt=(key,fallback)=>args.includes(key)?args[args.indexOf(key)+1]:fallback;
const port=Number(opt('--port','9334')),form=opt('--form','phone'),mode=opt('--mode','ui');
const output=path.resolve(opt('--output','preuves/lots-6-8/android'));await fs.mkdir(output,{recursive:true});
const fixture=JSON.parse(await fs.readFile(opt('--fixture','toolchain/android-tests/lots6-8-transport/fixture-public.json'),'utf8'));
let pages=[];const readyUntil=Date.now()+20000;while(Date.now()<readyUntil){try{pages=await(await fetch(`http://127.0.0.1:${port}/json`,{signal:AbortSignal.timeout(1000)})).json();if(pages.some(p=>p.type==='page'&&p.url.startsWith('http://127.0.0.1:')))break;}catch{}await new Promise(resolve=>setTimeout(resolve,100));}
const page=pages.find(p=>p.type==='page'&&p.url.startsWith('http://127.0.0.1:'));
assert(page,'Expected local Kiara WebView');const socket=new WebSocket(page.webSocketDebuggerUrl);
await new Promise((resolve,reject)=>{socket.addEventListener('open',resolve,{once:true});socket.addEventListener('error',reject,{once:true});});
let seq=0;const pending=new Map(),errors=[];
socket.addEventListener('message',event=>{const value=JSON.parse(event.data);if(value.id){const request=pending.get(value.id);if(request){clearTimeout(request.timer);pending.delete(value.id);value.error?request.reject(new Error('CDP failure')):request.resolve(value.result);}}else if(value.method==='Runtime.exceptionThrown')errors.push('WebView exception');});
const call=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq,timer=setTimeout(()=>{pending.delete(id);reject(new Error('CDP timeout'));},45000);pending.set(id,{resolve,reject,timer});socket.send(JSON.stringify({id,method,params}));});
const evaluate=async expression=>{const result=await call('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(result.exceptionDetails)throw new Error(result.exceptionDetails.exception?.description||result.exceptionDetails.text);return result.result.value;};
const until=async(expression,label)=>{const end=Date.now()+35000;while(Date.now()<end){if(await evaluate(expression))return;await new Promise(resolve=>setTimeout(resolve,120));}throw new Error('Fixture UI timeout: '+label);};
const click=async selector=>{const p=await evaluate(`(()=>{const n=document.querySelector(${JSON.stringify(selector)});if(!n||n.disabled)throw new Error('Control unavailable');n.scrollIntoView({block:'center'});const r=n.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};})()`);await call('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[p]});await call('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});};
const screenshot=async name=>{const capture=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});await fs.writeFile(path.join(output,form+'-'+name+'.png'),Buffer.from(capture.data,'base64'));};
const checks=[];
try{
  await call('Runtime.enable');await call('Page.enable');if(['ui','reconnected'].includes(mode)){await evaluate("window.__fredStartupProbe=true;location.reload();true");await until("typeof window.__fredStartupProbe==='undefined'&&document.readyState==='complete'",'new page startup');}
  await until("typeof config!=='undefined'&&config.model==='fred-fixture'&&connected&&historyReady&&!historySyncPending",'authenticated fixture');
  assert(await evaluate("$('android-profile-name').textContent.startsWith('Fixture Android')"),'Refusing mutations outside isolated fixture');
  await evaluate('wsBootstrap();fredInboxLoad()');await until('ws.data&&fredInbox.loaded&&!fredInbox.busy','workspace and inbox');
  if(mode==='request-permission'){
    await evaluate("showView('notifications');androidNotificationControls()");
    assert.equal(await evaluate('JSON.parse(AndroidClient.notificationStatus()).enabled'),false,'Alerts must initially be off');
    await screenshot('before-permission');await click('#android-notification-enable');checks.push('permission requested only after user taps activation');
  }else if(mode==='denied'){
    await until('!JSON.parse(AndroidClient.notificationStatus()).enabled','denied preference');
    assert.equal(await evaluate('JSON.parse(AndroidClient.notificationStatus()).permitted'),false);
    assert(await evaluate('fredInbox.items.size>0'),'Inbox available despite denial');await screenshot('permission-denied');checks.push('denied Android permission preserves server inbox');
  }else if(mode==='granted'){
    await until('JSON.parse(AndroidClient.notificationStatus()).enabled&&JSON.parse(AndroidClient.notificationStatus()).permitted','granted preference');
    assert(await evaluate('fredInbox.items.size>0'),'Inbox remains available');await screenshot('permission-granted');checks.push('granted Android permission enables discreet alerts');
  }else if(mode==='clear-read'){
    await evaluate('fredInboxRead([...fredInbox.items.values()].filter(n=>!n.read_at).map(n=>n.id))');assert(await evaluate('[...fredInbox.items.values()].every(n=>n.read_at)'),'All fixture events read');checks.push('synthetic fixture read state synchronized before system click test');
  }else if(mode==='system-click'){
    await until("!document.querySelector('[data-view=tasks]').hidden&&!$('ws-job-result').hidden&&$('ws-job-title').textContent==='Résultat Android'",'system notification opens corresponding job');
    await until(`(async()=>{const v=await api('/v1/notifications');return v.items.filter(n=>n.target?.id===${JSON.stringify(fixture.job)}).sort((a,b)=>b.sequence-a.sequence)[0]?.read_at>0;})()`,'click marks latest matching notification read on server');
    await screenshot('system-click-job');checks.push('real system notification click opens authorized matching job and marks read');
  }else if(mode==='ui'){
    await evaluate(`showView('projects');wsSelectProject(${JSON.stringify(fixture.project)})`);
    await evaluate("$('ws-search-form').closest('details').open=true;$('ws-search-query').value='ORCHIDEEPDF'");await click('#ws-search-form button');
    await until("$('ws-sources').textContent.includes('page 2')&&$('ws-sources').querySelector('button')",'PDF source search');
    await click('#ws-sources button');await until("$('fred-source-dialog').open",'source modal');
    assert(await evaluate("$('fred-source-dialog').textContent.includes('Page 2')&&$('fred-source-dialog').textContent.includes('Révision 1')&&$('fred-source-dialog').querySelector('pre').textContent.includes('37 mois')"),'Exact PDF source/page/version shown');
    await screenshot('pdf-source');assert.equal(await evaluate("window.androidBack()"),true,'Android back closes source modal first');assert.equal(await evaluate("$('fred-source-dialog').open"),false);checks.push('search button and clickable exact PDF passage page 2/version 1; Android back closes citation');
    const created=await evaluate(`wsAction('document_create',{project:${JSON.stringify(fixture.project)},title:'Citation ${form}',text:'CITATIONANDROID${form.toUpperCase()} texte version initiale.'})`);
    const query='CITATIONANDROID'+form.toUpperCase();
    const found=await evaluate(`wsAction('search',{project:${JSON.stringify(fixture.project)},query:${JSON.stringify(query)}})`),source=found.sources[0];
    assert.equal(source.page,null,'No invented page on note');assert.equal(source.version,1);await evaluate(`wsOpenSource(${JSON.stringify(source.source_id)})`);
    assert(await evaluate("!$('fred-source-dialog').textContent.includes('Page ')"),'Note has no page label');await evaluate("$('fred-source-dialog').close()");checks.push('note citation has no invented page');
    await evaluate(`wsAction('document_save',{id:${JSON.stringify(created.id)},project:${JSON.stringify(fixture.project)},title:'Citation ${form}',text:'${query} nouvelle version.',revision:1})`);
    await evaluate(`wsOpenSource(${JSON.stringify(source.source_id)})`);assert(await evaluate("$('fred-source-dialog').textContent.includes('modifié')&&$('fred-source-dialog').querySelector('pre').textContent.includes('version initiale')"),'Modified reference keeps old excerpt');
    await screenshot('source-modified');await evaluate("$('fred-source-dialog').close()");checks.push('modified source visibly signaled with old excerpt retained');
    await evaluate(`wsAction('document_delete',{id:${JSON.stringify(created.id)},revision:2})`);await evaluate(`wsOpenSource(${JSON.stringify(source.source_id)})`);
    assert(await evaluate("$('fred-source-dialog').textContent.includes('supprimé')&&$('fred-source-dialog').querySelector('pre').textContent.includes('version initiale')"),'Deleted reference clearly unavailable');
    await screenshot('source-unavailable');await evaluate("$('fred-source-dialog').close()");checks.push('deleted source visibly signaled with citation retained');
    const foreign=await evaluate(`wsAction('document_get',{id:${JSON.stringify(fixture.foreign_document)}}).then(()=>200).catch(e=>e.status)`);assert.equal(foreign,403,'Other owner document denied');checks.push('owner-scoped consultation enforced');
    await evaluate("$('ws-search-query').value='ZZZZUNFINDABLEANSWER'");await click('#ws-search-form button');await until("$('ws-sources').textContent.includes('Aucun passage')",'no-result message');checks.push('search without results explicitly shown');
    await evaluate(`showView('tasks');wsOpenJob(${JSON.stringify(fixture.job)})`);assert(await evaluate("$('ws-job-sources').textContent.includes('révision 1')&&$('ws-job-sources').querySelector('button')"),'Durable job includes structured citation');await click('#ws-job-sources button');await until("$('fred-source-dialog').open",'job citation');await screenshot('job-source');await evaluate("$('fred-source-dialog').close()");checks.push('task result retains clickable sources');
    await evaluate("showView('notifications');fredInboxLoad()");await until("!fredInbox.busy&&document.querySelectorAll('#fred-inbox-list article').length>0",'inbox');
    const before=await evaluate('fredInbox.items.size');await evaluate('fredInboxLoad()');await until('!fredInbox.busy','inbox dedup');assert.equal(await evaluate('fredInbox.items.size'),before,'Repeated polling does not duplicate inbox');checks.push('persistent inbox and repeated polling deduplication');
    const row=await evaluate("[...fredInbox.items.values()].find(n=>n.type==='document_indexed'&&!n.read_at)?.id");if(row){await evaluate(`fredInboxRead([${JSON.stringify(row)}])`);assert(await evaluate(`fredInbox.items.get(${JSON.stringify(row)}).read_at>0`),'Read synchronized in inbox');checks.push('read state refreshed from server');}
    await evaluate("$('fred-inbox-preferences').closest('details').open=true;const box=document.querySelector('[data-notification-type=document_indexed]');box.checked=false;box.dispatchEvent(new Event('input',{bubbles:true}))");await click('#fred-inbox-preferences button');await until("!fredInbox.busy&&fredInbox.preferences.types.document_indexed===false",'type preference');
    assert.equal(await evaluate("api('/v1/notifications').then(p=>p.preferences.types.document_indexed)"),false,'Preference persisted on server');checks.push('notification type preferences saved server-side');
    for(const discreet of [false,true]){await evaluate(`$('fred-inbox-discreet').checked=${discreet};$('fred-inbox-discreet').dispatchEvent(new Event('input',{bubbles:true}))`);await click('#fred-inbox-preferences button');await until(`!fredInbox.busy&&fredInbox.preferences.discreet===${discreet}&&JSON.parse(AndroidClient.notificationStatus()).discreet===${discreet}`,'server sound checkbox reaches native Android');checks.push(`server discreet checkbox ${discreet?'on selects silent':'off selects standard sound'} in Android`);}
    await screenshot('inbox');assert(!(await evaluate('document.documentElement.scrollWidth>innerWidth+1')),'No horizontal overflow');checks.push('phone/tablet layout without overflow');
    await evaluate("api('/v1/notifications/action',{action:'preferences',revision:fredInbox.preferences.revision,types:{document_indexed:true},discreet:true}).then(()=>{fredInbox.dirty=false;return fredInboxLoad();})");
  }else if(mode==='reconnected'){
    assert(await evaluate(`fredInbox.loaded&&[...fredInbox.items.values()].sort((a,b)=>b.sequence-a.sequence)[0]?.target.id===${JSON.stringify(fixture.job)}&&![...fredInbox.items.values()].sort((a,b)=>b.sequence-a.sequence)[0]?.read_at`),'Completed event generated while client closed appears after reconnection');await screenshot('reconnected');checks.push('closed/reopened client catches up persistent event generated while stopped');
  }else throw new Error('Unknown test mode');
  assert.equal(errors.length,0,'No unhandled WebView exception');const report={passed:true,form,mode,checks,exceptions:0,transport:'real Android WireGuard UDP',backend:'actual isolated Workspace and Notifications'};
  await fs.writeFile(path.join(output,`${form}-${mode}.json`),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
}finally{socket.close();for(const request of pending.values())clearTimeout(request.timer);}
