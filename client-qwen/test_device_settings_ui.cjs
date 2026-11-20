'use strict';

const assert=require('node:assert/strict');
const {execFileSync,spawn}=require('node:child_process');
const fs=require('node:fs');
const http=require('node:http');
const os=require('node:os');
const path=require('node:path');
const {chromium,options}=require('./browser_test_support.cjs');

const python=process.env.PYTHON_EXE||path.join(__dirname,'../toolchain/build-python/Scripts/python.exe');
const pages=JSON.parse(execFileSync(python,['-B','-c',[
  'import json, sys',
  'from pathlib import Path',
  'root = Path(sys.argv[1])',
  'sys.path.insert(0, str(root.parent / "shared"))',
  'from kiara_shared.conversation_shell import DEVICE_SETTINGS, chat_contextual_help, device_settings, modern_chat',
  'read=lambda name:(root / name).read_text(encoding="utf-8")',
  'cfg=json.dumps({"key":"fixture","storage":"device-fixture","model":"fred-qwen","platform":"windows"})',
  'scripts=("vendor/markdown-it.min.js","markdown.js","ui.js","attachments.js","corrector.js","selection.js","thinking.js","voice.js","conversation.js","project-conversation.js")',
  'script=lambda name:\'<script nonce="recette">\'+read(name).replace("</script","<\\\\/script")+"</script>"',
  'chat=chat_contextual_help(modern_chat(read("chat.html"),read("kiara-shell.html"),native_settings=True),read)',
  'chat=chat.replace("</head>",script(scripts[0])+script(scripts[1])+"</head>").replace("</body>",read("workspace.html")+"".join(map(script,scripts[2:]))+"</body>")',
  'pages={"chat":chat.replace("__UI_CSS__",read("ui.css")).replace("__CONFIG__",cfg).replace("__NONCE__","recette")}',
  'for section in DEVICE_SETTINGS:',
  '    for recovery in (True,False):',
  '        pages[str(recovery)+section]=device_settings(read,"recette",section,key="fixture",recovery=recovery).decode()',
  'print(json.dumps(pages))',
].join('\n'),__dirname],{encoding:'utf8',maxBuffer:8e6}));

async function verify(){
  const requests=[];
  let offline=false, endpoint='example.test:51820', revision=0, failSave=false, installed=false;
  let preferences={voice_volume:65}, update={busy:false,available:false}, integration=null;
  let history={currentId:'synthetic',conversations:[{id:'synthetic',title:'Recette',messages:[]}]};
  const server=http.createServer(async(req,res)=>{
    const url=new URL(req.url,'http://127.0.0.1');
    function send(data,status=200){res.writeHead(status,{'Content-Type':'application/json'});res.end(JSON.stringify(data));}
    const section=url.searchParams.get('section');
    if(url.pathname==='/chat'||['/device-settings','/device-recovery'].includes(url.pathname)){
      const document=url.pathname==='/chat'?pages.chat:pages[String(url.pathname==='/device-recovery').replace(/^./,v=>v.toUpperCase())+section];
      res.writeHead(200,{'Content-Type':'text/html; charset=utf-8',
        'Content-Security-Policy':"default-src 'none'; script-src 'nonce-recette'; style-src 'nonce-recette'; connect-src 'self'; img-src data:"});
      return res.end(document);
    }
    let body='';for await(const chunk of req)body+=chunk;
    const data=JSON.parse(body||'{}');
    requests.push(url.pathname);
    const connection={connected:!offline,checking:false,checked_at:Date.now()/1000,endpoint,automatic:false,
      model:'fred-qwen',models:offline?[]:['fred-qwen','hermes'],transport:'wireguard',error:offline?'Serveur injoignable.':''};
    if(url.pathname==='/client/device-state')return send({endpoint,internet_endpoint:'example.test:51820',
      voice_preferences:preferences,connection,update,local_api:'http://127.0.0.1:12345/v1'});
    if(url.pathname==='/client/state')return send({endpoint,internet_endpoint:'example.test:51820',preferences,connection,update,version:'4.0.fixture'});
    if(url.pathname==='/client/preferences'){
      if(failSave){failSave=false;return send({error:{message:'Enregistrement simulé refusé.'}},503);}
      preferences={...preferences,...data};return send({saved:true});
    }
    if(url.pathname==='/client/endpoint'){endpoint=data.endpoint||'example.test:51820';return send({endpoint});}
    if(url.pathname==='/client/device-reconnect')return send({checking:true});
    if(url.pathname==='/client/device-session')return send({url:'/device-recovery'});
    if(url.pathname==='/client/project-session')return send({error:{message:'Projets indisponibles.'}},503);
    if(url.pathname==='/client/update/check'){
      update=offline?{error:true,message:'Vérification indisponible hors connexion.'}:{available:true,message:'Version de recette disponible.'};
      return send(update);
    }
    if(url.pathname==='/client/update/apply'){update={busy:true,message:'Téléchargement et vérification…'};return send(update);}
    if(url.pathname==='/client/voice'){
      if(data.action==='install')installed=true;
      if(data.action==='remove')installed=false;
      return send({installed,phase:'idle'});
    }
    if(url.pathname==='/client/voice/max')return send({pc:{installed:true,available:true,message:'Prêt'},server:{available:false}});
    if(url.pathname==='/client/conversation')return send({phase:'idle',installed});
    if(url.pathname==='/client/integrations')return send({apps:{opencode:{installed:true},hermes:{installed:true},codex:{installed:true}}});
    if(url.pathname==='/client/integrations/apply'){integration=data;return send({message:'Intégration enregistrée.'});}
    if(url.pathname==='/client/history'){
      if(req.method==='POST'){history=data.history;return send({revision:String(++revision)});}
      return send({history,revision:String(revision),server_synced:true,pending:false});
    }
    if(url.pathname==='/client/history/sync')return send({history,revision:String(revision),server_synced:true,pending:false});
    if(url.pathname==='/v1/models')return send({data:offline?[]:[{id:'fred-qwen',available:true,capabilities:{}}]});
    if(url.pathname==='/v1/workspace')return send({projects:[],jobs:[]});
    if(url.pathname==='/v1/notifications/action')return send({items:[],cursor:0,generation:'fixture',preferences:{types:{}},subscription:{}});
    return send({});
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const root='http://127.0.0.1:'+server.address().port;
  let browser,shell;
  const native=process.env.KIARA_UX_WINDOWS_EXE;
  try{
    if(native){
      const port=http.createServer();
      await new Promise(resolve=>port.listen(0,'127.0.0.1',resolve));
      const debugPort=port.address().port;
      await new Promise(resolve=>port.close(resolve));
      const profile=fs.mkdtempSync(path.join(os.tmpdir(),'kiara-device-webview-'));
      const env={...process.env,WEBVIEW2_USER_DATA_FOLDER:profile,
        WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS:'--remote-debugging-port='+debugPort};
      shell=spawn(native,['--local-url',root+'/chat','--hidden'],{env,windowsHide:true});
      const debugUrl='http://127.0.0.1:'+debugPort;
      const deadline=Date.now()+10000;
      while(!await fetch(debugUrl+'/json/version').then(response=>response.ok).catch(()=>false)){
        if(shell.exitCode!==null||Date.now()>deadline)throw new Error('WebView2 de recette indisponible.');
        await new Promise(resolve=>setTimeout(resolve,100));
      }
      browser=await chromium.connectOverCDP(debugUrl,{timeout:5000});
    }else browser=await chromium.launch(options);
    const page=native?(browser.contexts()[0].pages()[0]||await browser.contexts()[0].waitForEvent('page')):await browser.newPage();
    page.setDefaultTimeout(10000);
    const errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    page.on('dialog',dialog=>dialog.accept());
    const proof=process.env.UI_PROOF_DIRECTORY;
    if(proof)fs.mkdirSync(proof,{recursive:true});
    for(const viewport of [{width:1280,height:720},{width:1920,height:1080},{width:2560,height:1440}]){
      await page.setViewportSize(viewport);
      for(const section of ['vocal','dictee','connexion','mises-a-jour','api-locale']){
        await page.goto(root+'/device-settings?section='+section);
        await page.getByRole('heading',{level:2}).waitFor();
        assert.equal(await page.locator('nav,dialog,#composer').count(),0);
        assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
        if(proof){
          const ready={vocal:()=>page.locator('.voice-settings:not([inert])').waitFor(),
            dictee:()=>page.getByText('Modèle à installer.',{exact:true}).waitFor(),
            connexion:()=>page.getByText('Serveur Kiara accessible.',{exact:false}).waitFor(),
            'mises-a-jour':()=>page.getByText('Vérifiez si une nouvelle version est disponible.').waitFor(),
            'api-locale':()=>page.getByText('http://127.0.0.1:12345/v1',{exact:true}).waitFor()};
          await ready[section]();
          await page.screenshot({path:path.join(proof,section+'-'+viewport.width+'.png')});
        }
      }
    }
    await page.goto(root+'/device-settings?section=vocal');
    const quality=page.getByLabel('Qualité vocale');
    failSave=true;
    await quality.selectOption('max');
    await page.getByText('Réglages non enregistrés.',{exact:false}).waitFor();
    assert.equal(await quality.inputValue(),'max');
    await page.getByRole('button',{name:'Réessayer l’enregistrement'}).click();
    await page.getByText('Réglages enregistrés',{exact:true}).waitFor();
    await page.reload();
    await page.waitForFunction(()=>document.getElementById('voice-quality').value==='max');
    assert.equal(preferences.voice_quality,'max');
    assert.equal(preferences.voice_volume,65);

    await page.goto(root+'/device-settings?section=dictee');
    await page.getByRole('button',{name:'Installer / réparer'}).click();
    await page.getByText('Modèle installé.',{exact:true}).waitFor();
    await page.reload();
    await page.getByRole('button',{name:'Désinstaller le modèle'}).click();
    await page.getByText('Modèle à installer.',{exact:true}).waitFor();

    await page.goto(root+'/device-settings?section=api-locale');
    await page.getByRole('button',{name:'Afficher la clé'}).click();
    assert.equal(await page.getByLabel('Clé API locale').getAttribute('type'),'text');
    await page.getByLabel('Modèle à ajouter').selectOption('hermes');
    await page.getByRole('button',{name:'Ajouter à Hermes'}).click();
    await page.getByText('Intégration enregistrée.').waitFor();
    assert.deepEqual(integration,{app:'hermes',model:'hermes'});

    await page.goto(root+'/device-settings?section=mises-a-jour');
    await page.getByRole('button',{name:'Vérifier les mises à jour'}).click();
    await page.getByText('Version de recette disponible.').waitFor();
    await page.getByRole('button',{name:'Mettre à jour le client'}).click();
    await page.getByText('Téléchargement et vérification…').waitFor();
    assert(requests.indexOf('/client/history/flush')<requests.indexOf('/client/update/apply'));

    await page.goto(root+'/chat');
    const help = page.getByRole('button',{name:'Aide',exact:true});
    const guide = page.getByRole('dialog',{name:'Aide Kiara'});
    await page.locator('#prompt').fill('Un brouillon de recette');
    await help.press('Enter');
    await guide.getByRole('heading',{name:'Conversations',exact:true}).waitFor();
    await page.keyboard.press('Escape');
    await guide.waitFor({state:'hidden'});
    assert(await help.evaluate(button=>button===document.activeElement));
    assert.equal(await page.locator('#prompt').inputValue(),'Un brouillon de recette');
    await page.getByRole('button',{name:'Correcteur',exact:true}).click();
    await help.click();
    await guide.getByRole('heading',{name:'Correcteur',exact:true}).waitFor();
    await guide.getByRole('combobox',{name:'Rubrique'}).selectOption('settings-dictee');
    await guide.getByRole('heading',{name:'Réglages de la dictée',exact:true}).waitFor();
    await guide.getByRole('button',{name:'Fermer l’aide'}).click();

    offline=true;
    update={busy:false};
    await page.goto(root+'/chat');
    await page.getByRole('button',{name:'Réglages',exact:true}).click();
    await page.waitForURL('**/device-recovery?section=connexion');
    const nav=page.getByRole('navigation',{name:'Réglages de cet appareil'});
    await nav.getByRole('link',{name:'Connexion au serveur'}).waitFor();
    await page.getByText('Serveur injoignable.',{exact:false}).waitFor();
    await help.click();
    await guide.getByRole('heading',{name:'Connexion au serveur',exact:true}).waitFor();
    await guide.getByRole('button',{name:'Fermer l’aide'}).click();
    await page.getByLabel('Adresse du serveur').fill('example.test:51821');
    await page.getByRole('button',{name:'Appliquer la connexion'}).click();
    await page.getByText('Connexion enregistrée.').waitFor();
    await page.reload();
    await page.waitForFunction(()=>document.getElementById('endpoint').value==='example.test:51821');
    await page.getByRole('button',{name:'Réessayer la connexion'}).click();
    await page.getByText('Nouvelle vérification lancée.',{exact:true}).waitFor();
    await nav.getByRole('link',{name:'Mises à jour'}).press('Enter');
    await page.getByRole('button',{name:'Vérifier les mises à jour'}).press('Enter');
    await page.getByText('Vérification indisponible hors connexion.').waitFor();
    if(proof){
      await page.setViewportSize({width:1280,height:720});
      await page.emulateMedia({colorScheme:'dark'});
      await page.evaluate(()=>localStorage.setItem('fred-theme','system'));
      await page.reload();
      await page.getByText('Vérification indisponible hors connexion.').waitFor();
      await page.screenshot({path:path.join(proof,'recuperation-sombre-1280.png')});
    }
    assert.deepEqual(errors,[]);
    console.log(JSON.stringify({passed:true,sections:5,offlineRecovery:true,viewports:3,webview2:!!native}));
  }finally{
    await browser?.close();
    shell?.kill();
    server.closeAllConnections();
    await new Promise(resolve=>server.close(resolve));
  }
}

verify().catch(error=>{console.error(error);process.exitCode=1;});
