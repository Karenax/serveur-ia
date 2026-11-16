'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {chromium,options}=require('./browser_test_support.cjs');

(async()=>{
 const browser=await chromium.launch(options),page=await browser.newPage({viewport:{width:900,height:800}});
 const script=fs.readFileSync(path.join(__dirname,'../lanceur/web/agent-access.js'),'utf8');
 await page.setContent('<button id="agent-access-open" data-service-endpoint="/api/project-service">Gérer les droits</button><div id="agent-access-panel" hidden></div>');
 await page.evaluate(()=>{
  window.fixture={calls:[],policy:null,running:true};
  window.request=async(path,data)=>{
   if(path==='/api/project-service/catalogue')return {projects:[{id:'p1',code:'P1',title:'Projet fictif'},{id:'p2',code:'P2',title:'Autre projet'}],sessions:[{operator_id:'ancien',title:'Réunion fictive',date:'2026-10-01',audio_chunks:2}]};
   if(path==='/api/remote')return {clients:[{id:'device',name:'PC fictif',revoked:false,suspended:false}]};
   if(path.startsWith('/api/project-service?'))return {operator:window.fixture.policy};
   if(path==='/api/project-service'&&data){window.fixture.calls.push(data);window.fixture.policy=data.action==='revoke'?null:{id:data.agent_operator_id||data.owner,role:data.role,project_ids:data.project_ids,person_id:data.person_id};return {saved:true};}
   if(path==='/api/project-service')return {configured:true,running:window.fixture.running};
   throw new Error('Route inconnue');
  };
 });
 await page.addScriptTag({content:script});
 await page.getByRole('button',{name:'Gérer les droits'}).click();
 await page.getByLabel('Client').selectOption('device');
 await page.getByText('Ce client n’a accès à aucun projet.').waitFor();
 await page.getByLabel('Niveau d’accès').selectOption('reader');
 await page.getByLabel('P1 · Projet fictif').check();
 await page.getByRole('button',{name:'Enregistrer les droits'}).click();
 await page.getByText('Droits enregistrés.').waitFor();
 let calls=await page.evaluate(()=>window.fixture.calls);
 assert.deepEqual(calls[0],{action:'access',owner:'device',role:'reader',project_ids:['p1'],person_id:null,agent_operator_id:null,expected:null});
 await page.getByLabel('Séance personnelle à retrouver').selectOption('ancien');
 await page.getByRole('button',{name:'Enregistrer les droits'}).click();
 await page.getByText('Pour retrouver une séance personnelle, autorisez tous les projets.').waitFor();
 assert.equal((await page.evaluate(()=>window.fixture.calls)).length,1);
 await page.getByLabel('Accès à tous les projets').check();
 await page.getByRole('button',{name:'Enregistrer les droits'}).click();
 await page.getByText('Droits enregistrés.').waitFor();
 calls=await page.evaluate(()=>window.fixture.calls);
 assert.equal(calls[1].agent_operator_id,'ancien');assert.equal(calls[1].project_ids,null);
 assert.deepEqual(calls[1].expected,{id:'device',role:'reader',project_ids:['p1'],person_id:null});
 await page.getByLabel('Niveau d’accès').selectOption('none');
 await page.getByRole('button',{name:'Enregistrer les droits'}).click();
 await page.getByText('Accès aux projets retiré.').waitFor();
 calls=await page.evaluate(()=>window.fixture.calls);
 assert.equal(calls[2].action,'revoke');assert.equal(calls[2].expected.id,'ancien');
 await page.getByRole('button',{name:'Fermer'}).click();
 await page.evaluate(()=>{window.fixture.running=false;window.fixture.policy={id:'device',role:'reader',project_ids:['p1'],person_id:null};});
 await page.getByRole('button',{name:'Gérer les droits'}).click();
 await page.getByLabel('Client').selectOption('device');
 await page.getByText('Le service Projets est arrêté. Choisissez « Aucun accès » pour retirer ces droits.').waitFor();
 await page.getByLabel('Niveau d’accès').selectOption('none');
 await page.getByRole('button',{name:'Enregistrer les droits'}).click();
 await page.getByText('Accès aux projets retiré.').waitFor();
 calls=await page.evaluate(()=>window.fixture.calls);assert.equal(calls[3].action,'revoke');assert.equal(calls[3].expected.role,'reader');
 await browser.close();console.log('Project access UI: project scope, personal-session association and revocation passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
