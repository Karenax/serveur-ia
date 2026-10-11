'use strict';
const {chromium}=require('C:/Users/karen/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=__dirname;
const fixture='<style>p.MsoNormal{font-family:Calibri;font-size:12pt;line-height:1.5}</style><p class="MsoNormal" style="text-align:center"><span style="color:#0057b8;font-family:Arial;font-size:20pt"><b>Bonjours,</b></span></p><p class="MsoNormal"><span style="font-family:Georgia;font-size:11pt">Je vous envoi les </span><u style="color:#7c3aed">documents demmandés</u><span>. Pouvez-vous confirmer leur reçeption ?</span></p><ul><li><i style="color:#15803d">Merci pour votre aide.</i></li></ul><p><a href="https://example.org/document" style="color:#b91c1c">Consulter le dossier</a></p><table style="border-collapse:collapse"><tbody><tr><th style="background-color:#e5e7eb;border:1px solid #555">Document</th><td style="border:1px solid #555"><b>Compte rendu</b></td></tr></tbody></table>';
let browser;
(async()=>{
  browser=await chromium.launch({headless:true,executablePath:'C:/Users/karen/AppData/Local/ms-playwright/chromium_headless_shell-1228/chrome-headless-shell-win64/chrome-headless-shell.exe'});
  const context=await browser.newContext({viewport:{width:1440,height:1000},permissions:['clipboard-read','clipboard-write']});
  const page=await context.newPage(),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:8098/chat');
  await page.getByRole('button',{name:'Correcteur',exact:true}).click();
  await page.waitForFunction(()=>!document.getElementById('corrector-correct').disabled,{timeout:30000});
  const unit=await page.evaluate(()=>{
    const results=[];
    const safe=FredRichText.sanitize('<p onclick="alert(1)" style="color:red;background-image:url(https://example.org/pixel);position:fixed">OK<script>alert(1)</script><img src="https://example.org/pixel"><a href="javascript:alert(1)">Lien</a></p>');
    results.push(!safe.querySelector('script,img')&&!safe.querySelector('p').hasAttribute('onclick')&&!safe.querySelector('a').hasAttribute('href'));
    results.push(safe.querySelector('p').style.color==='red'&&!safe.querySelector('p').style.backgroundImage&&!safe.querySelector('p').style.position);
    const snap=FredRichText.snapshot('<p><b style="color:red">Bon</b><i style="color:blue">jours</i> à tous.</p>');
    const corrected=FredRichText.apply(snap,{fragments:[{id:'f2',text:' à tous.'},{id:'f0',text:'Bon'},{id:'f1',text:'jour'}]});
    results.push(corrected.text==='Bonjour à tous.'&&corrected.root.querySelector('b').style.color==='red'&&corrected.root.querySelector('i').style.color==='blue');
    const cases=[{fragments:[]},{fragments:[{id:'f0',text:'A'},{id:'f0',text:'B'},{id:'f2',text:'C'}]},
      {fragments:[{id:'f0',text:'A'},{id:'f1',text:''},{id:'f2',text:'C'}]},
      {fragments:[{id:'f0',text:'A'},{id:'f1',text:'B'},{id:'unknown',text:'C'}]}];
    for(const value of cases){let rejected=false;try{FredRichText.apply(snap,value);}catch{rejected=true;}results.push(rejected);}
    const hostile=FredRichText.apply(FredRichText.snapshot('<p>texte</p>'),{fragments:[{id:'f0',text:'<img src=x onerror=alert(1)>'}]});
    results.push(!hostile.root.querySelector('img')&&hostile.text.includes('<img'));
    const spaces=FredRichText.apply(FredRichText.snapshot('<b> un </b>texte'),{fragments:[{id:'f0',text:'mot'},{id:'f1',text:'texte'}]});
    results.push(spaces.text===' mot texte');
    results.push(FredRichText.plain(FredRichText.sanitize('\n  <p>Premier</p>\n  <p>Second</p>\n'))==='Premier\nSecond');
    results.push(FredRichText.plain(FredRichText.sanitize('<p><b>Premier</b> <i>second</i></p>'))==='Premier second');
    return results;
  });assert.ok(unit.every(Boolean),JSON.stringify(unit));
  await page.locator('#corrector-text').fill('');
  await page.locator('#corrector-text').focus();
  await page.evaluate(html=>{
    const data=new DataTransfer();data.setData('text/html',html);data.setData('text/plain','Bonjours, Je vous envoi les documents demmandés.');
    document.getElementById('corrector-text').dispatchEvent(new ClipboardEvent('paste',{clipboardData:data,bubbles:true,cancelable:true}));
  },fixture);
  const source=await page.locator('#corrector-text').innerHTML();
  const canonicalSource=await page.evaluate(()=>FredRichText.sanitize(document.getElementById('corrector-text').innerHTML).innerHTML);
  await page.locator('#corrector-correct').click();
  await page.waitForFunction(()=>document.getElementById('corrector-status').textContent.includes('terminé'),{timeout:30000});
  assert.equal(await page.locator('#corrector-text').innerHTML(),source,'Original was modified');
  const styles=await page.evaluate(()=>{
    const source=document.getElementById('corrector-text'),result=document.getElementById('corrector-result');
    const tags=['p','span','b','u','i','a','th','td'];
    const props=['fontFamily','fontSize','fontWeight','fontStyle','color','backgroundColor','textDecorationLine','textAlign','borderTopWidth','lineHeight'];
    const mismatches=[];
    for(const tag of tags){const a=source.querySelectorAll(tag),b=result.querySelectorAll(tag);if(a.length!==b.length)mismatches.push(tag+' count');
      for(let i=0;i<a.length;i++){const left=getComputedStyle(a[i]),right=getComputedStyle(b[i]);for(const prop of props)if(left[prop]!==right[prop])mismatches.push(tag+' '+i+' '+prop+': '+left[prop]+' / '+right[prop]);}}
    return {mismatches,text:result.innerText,href:result.querySelector('a').href,html:result.innerHTML};
  });assert.deepEqual(styles.mismatches,[]);assert.match(styles.text,/Bonjour/);assert.match(styles.text,/Je vous envoie/);assert.match(styles.text,/documents demandés/);assert.equal(styles.href,'https://example.org/document');
  const request=JSON.parse(fs.readFileSync(path.join(root,'derniere-requete.json'),'utf8'));
  assert.doesNotMatch(request.messages[1].content,/<(?:p|span|style)|font-family|#0057b8/);
  assert.equal(JSON.parse(request.messages[1].content).fragments[0].id,'f0');
  await page.evaluate(()=>{window.testCopy=null;document.addEventListener('copy',e=>{if(e.clipboardData)window.testCopy={html:e.clipboardData.getData('text/html'),text:e.clipboardData.getData('text/plain')};});});
  await page.locator('#corrector-copy').click();
  const copied=await page.evaluate(()=>window.testCopy);assert.ok(copied?.html.includes('color: rgb(0, 87, 184)'));assert.match(copied.text,/documents demandés/);
  await page.screenshot({path:path.join(root,'correcteur-enrichi.png'),fullPage:true});
  const resultBefore=await page.locator('#corrector-result').innerHTML();
  await page.waitForTimeout(1000);await page.reload();await page.getByRole('button',{name:'Correcteur',exact:true}).click();
  await page.waitForFunction(()=>document.getElementById('corrector-result').textContent.includes('documents demandés'),{timeout:30000});
  assert.equal(await page.locator('#corrector-result').innerHTML(),resultBefore,'Rich result not restored');
  assert.equal(await page.evaluate(()=>FredRichText.sanitize(document.getElementById('corrector-text').innerHTML).innerHTML),canonicalSource,'Rich source not restored');
  fs.writeFileSync(path.join(root,'mode-reponse.txt'),'bad');
  await page.locator('#corrector-correct').click();await page.waitForFunction(()=>document.getElementById('corrector-status').textContent.includes('original est conservé'),{timeout:30000});
  assert.equal(await page.locator('#corrector-result').innerHTML(),resultBefore,'Invalid response overwrote valid result');
  fs.writeFileSync(path.join(root,'mode-reponse.txt'),'normal');
  await page.route('**/v1/chat/completions',route=>route.fulfill({status:200,contentType:'text/event-stream',body:'data: '+JSON.stringify({choices:[{delta:{content:'{"fragments":['}}]})+'\n\n'}));
  await page.locator('#corrector-correct').click();await page.waitForFunction(()=>/incomplète|ne permet pas/.test(document.getElementById('corrector-status').textContent),{timeout:30000});
  await page.unroute('**/v1/chat/completions');
  assert.equal(await page.locator('#corrector-result').innerHTML(),resultBefore);
  fs.writeFileSync(path.join(root,'mode-reponse.txt'),'normal');
  await page.locator('#corrector-reuse').click();assert.equal(await page.locator('#corrector-text').innerHTML(),resultBefore);
  await page.evaluate(()=>{window.testCopy=null;document.addEventListener('copy',e=>{if(e.clipboardData)window.testCopy={html:e.clipboardData.getData('text/html'),text:e.clipboardData.getData('text/plain')};});});
  const selection=await page.evaluate(()=>{const el=document.getElementById('corrector-text'),range=document.createRange();range.selectNodeContents(el);window.getSelection().removeAllRanges();window.getSelection().addRange(range);return FredRichText.selectionDocument();});
  assert.ok(selection.html.includes('color: rgb(0, 87, 184)'));
  const partial=await page.evaluate(()=>{const node=document.querySelector('#corrector-text b').firstChild,range=document.createRange();range.setStart(node,0);range.setEnd(node,7);window.getSelection().removeAllRanges();window.getSelection().addRange(range);return FredRichText.selectionDocument();});
  assert.match(partial.html,/color: rgb\(0, 87, 184\)/);assert.match(partial.html,/font-weight: 700/);
  await page.keyboard.press('Control+c');
  const partialCopy=await page.evaluate(()=>window.testCopy);assert.match(partialCopy.html,/color: rgb\(0, 87, 184\)/);assert.equal(partialCopy.text,'Bonjour');
  await page.evaluate(()=>copyText('Copie de chat indépendante'));
  const plainCopy=await page.evaluate(()=>window.testCopy);assert.equal(plainCopy.text,'Copie de chat indépendante');assert.equal(plainCopy.html,'');
  assert.deepEqual(errors,[]);
  fs.writeFileSync(path.join(root,'validation-navigateur.json'),JSON.stringify({passed:true,browser:'Chromium',unitChecks:unit.length,originalPreserved:true,stylesCompared:true,richCopy:true,partialSelectionRichCopy:true,plainChatCopyUnaffected:true,persistence:true,invalidResponsePreservesResult:true,truncatedResponsePreservesResult:true,reuse:true,pageErrors:errors},null,2));
  console.log('Prototype rich corrector: all browser checks passed.');
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{fs.writeFileSync(path.join(root,'mode-reponse.txt'),'normal');if(browser)await browser.close();});
