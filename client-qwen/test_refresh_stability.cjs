'use strict';
const assert=require('node:assert/strict'),path=require('node:path'),{spawn}=require('node:child_process');
const {chromium,options}=require('./browser_test_support.cjs');
const android=process.argv.includes('--android'),measure=process.argv.includes('--measure');
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
(async()=>{
  const child=spawn(process.execPath,[path.join(__dirname,'test_conversation_ui.cjs'),'--preview',...(android?['--android']:[])],{windowsHide:true,stdio:['ignore','pipe','pipe']});
  let browser;try{
    const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(new Error('Fixture startup timeout')),15000);child.stdout.on('data',chunk=>{const match=String(chunk).match(/http:\/\/127\.0\.0\.1:\d+/);if(match){clearTimeout(timer);resolve(match[0]);}});child.on('exit',code=>reject(new Error('Fixture exit '+code)));});
    browser=await chromium.launch(options);const page=await browser.newPage({viewport:android?{width:390,height:844}:{width:1440,height:1000}});
    const errors=[];let catalogueRequests=0;page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.url().endsWith('/v1/models'))catalogueRequests++;});
    await page.route('**/v1/models',async route=>{await sleep(400);await route.continue();});
    await page.goto(url);await page.waitForFunction(()=>connected&&historyReady&&!historySyncPending&&ws.bootstrapDone);
    await sleep(500);
    await page.evaluate(async()=>{
      window.__workspaceFixture={projects:[{id:'orion',title:'Projet Orion',instructions:'Préparer la livraison',revision:1,archived:false,documents:[{id:'note',title:'Note de préparation'}],memories:[],conversations:[]}],jobs:[{id:'task',project:'orion',title:'Préparation de la livraison',state:'queued',due:1800000000,repeat_hours:0}],personal_memories:[]};
      await api('/__fixture',{workspace:window.__workspaceFixture});await wsRefresh();await wsSelectProject('orion');
      uiConnectionStatus({checking:true,transport:'https'});if(!$('connection').classList.contains('online')||!$('connection').textContent.includes('Connecté'))throw new Error('Healthy connection must stay visible during a probe');
    });
    await page.evaluate(()=>{
      const c=library.find(c=>c.id===currentId);c.title='Projet Orion';c.messages=[{role:'user',content:'Préparons le projet.'},{role:'assistant',content:Array.from({length:70},(_,i)=>'Paragraphe '+i+' du projet Orion. Une longue réponse pour tester le défilement et la lecture.').join('\n\n'),reasoning_content:'Une explication à garder ouverte.'}];messages=c.messages;
      for(let i=0;i<40;i++)library.push({id:'fixture-'+i,title:'Discussion '+i,messages:[]});
      render();drawLibrary();document.querySelector('.message details').open=true;
      const scroller=$('messages');scroller.scrollTop=280;
      window.__stable={message:document.querySelector('.message'),reasoning:document.querySelector('.message details'),nav:document.querySelector('[data-view-button="chat"] .nav-text'),conversation:document.querySelector('#conversation-list button'),documentButton:$('ws-documents').firstChild,job:$('ws-jobs').firstChild,scroll:scroller.scrollTop,mutations:{messages:0,library:0,navigation:0,thinking:0},statusTexts:new Set(),renders:0};
      const old=render;render=function(){window.__stable.renders++;return old();};window.__stable.libraryCalls=[];const oldLibrary=drawLibrary;drawLibrary=function(){window.__stable.libraryCalls.push(new Error().stack.split('\n').slice(1,5));return oldLibrary();};
      for(const [name,node]of Object.entries({messages:$('messages'),library:$('conversation-list'),navigation:$('client-navigation'),thinking:$('thinking-bar')}))new MutationObserver(list=>window.__stable.mutations[name]+=list.filter(m=>m.type==='childList').length).observe(node,{childList:true,subtree:true});
      new MutationObserver(()=>window.__stable.statusTexts.add($('model').textContent)).observe($('model'),{childList:true,subtree:true});
      $('prompt').value='Un brouillon à conserver';$('prompt').focus();$('prompt').setSelectionRange(4,12);
    });
    // Exercise two real catalogue periods and the intervening state/workspace polls.
    await sleep(process.argv.includes('--long')?32500:1400);
    if(!process.argv.includes('--long'))await page.evaluate(async()=>{await models();await models();});
    await page.evaluate(async()=>{render();await wsRefresh();});
    const result=await page.evaluate(()=>({mutations:window.__stable.mutations,renders:window.__stable.renders,libraryCalls:window.__stable.libraryCalls,messageSame:document.querySelector('.message')===window.__stable.message,reasoningSame:document.querySelector('.message details')===window.__stable.reasoning,reasoningOpen:window.__stable.reasoning.open,navigationSame:document.querySelector('[data-view-button="chat"] .nav-text')===window.__stable.nav,conversationSame:document.querySelector('#conversation-list button')===window.__stable.conversation,scrollBefore:window.__stable.scroll,scrollAfter:$('messages').scrollTop,focus:document.activeElement.id,draft:$('prompt').value,selection:[$('prompt').selectionStart,$('prompt').selectionEnd],statusTexts:[...window.__stable.statusTexts]}));
    console.log(JSON.stringify({platform:android?'android':'windows',...result,errors},null,2));
    if(measure)return;
    assert.deepEqual(errors,[]);assert(result.messageSame&&result.reasoningSame&&result.reasoningOpen);assert(result.navigationSame&&result.conversationSame,'Background checks must preserve navigation nodes');assert.equal(result.scrollAfter,result.scrollBefore);assert.equal(result.focus,'prompt');assert.deepEqual(result.selection,[4,12]);assert.equal(result.draft,'Un brouillon à conserver');assert(!result.statusTexts.includes('Actualisation des modèles…'),'Healthy background checks must not flash a loading label');assert.equal(result.mutations.library,0);assert.equal(result.mutations.navigation,0);
    assert(catalogueRequests>=3,'Initial request and two catalogue checks ran');
    assert(await page.evaluate(()=>$('ws-documents').firstChild===window.__stable.documentButton&&$('ws-jobs').firstChild===window.__stable.job),'Unchanged project documents and tasks preserve their controls');
    await page.evaluate(async()=>{window.__workspaceFixture.jobs[0].state='completed';await api('/__fixture',{workspace:window.__workspaceFixture});await wsRefresh();});
    assert((await page.textContent('#ws-jobs')).includes('Terminé'),'Real task changes still refresh');
  }finally{await browser?.close();child.kill();}
})().catch(error=>{console.error(error);process.exitCode=1;});
