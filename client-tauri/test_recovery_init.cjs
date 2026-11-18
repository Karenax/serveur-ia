'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const template=fs.readFileSync(path.join(__dirname,'src/recovery_init.js'),'utf8');
function setup({required=true, navigation=true, workers, timer=setTimeout}={}) {
 let handler;const window={navigator:workers === undefined ? {} : {serviceWorker:workers}};
 if(navigation)window.navigation={addEventListener:(name,fn)=>{assert.equal(name,'navigate');handler=fn;}};
 const source=template.replace('__TOKEN__','a'.repeat(64)).replace('__PORTS__',Array.from({length:10},(_,i)=>17841+i).join(',')).replace('__REQUIRE_NAVIGATION__',String(required));
 vm.runInNewContext(source,{window,URL,setTimeout:timer,clearTimeout});
 return {window,navigate:(url,cancelable=true)=>{let canceled=false;handler({destination:{url},cancelable,preventDefault:()=>{canceled=true;}});return canceled;}};
}
test('autorise seulement les pages des dix ports réservés',async()=>{
 const app=setup();assert.equal(await app.window.__kiaraRecoveryReady,true);assert.equal(app.window.__kiaraRecoveryNavigationSafe,true);
 for(let port=17841;port<=17850;port++)for(const path of ['/recovery','/recovery/scan','/recovery/transfer'])assert.equal(app.navigate(`http://127.0.0.1:${port}${path}`),false);
 for(const url of ['http://127.0.0.1:17840/recovery','http://localhost:17841/recovery','https://127.0.0.1:17841/recovery',
  'http://127.0.0.1:17841/chat','http://127.0.0.1:17841/recovery?x=1','http://127.0.0.1:17841/recovery#x',
  'http://127.0.0.1:17841/recovery?','http://127.0.0.1:17841/recovery#',
  'http://user@127.0.0.1:17841/recovery','https://example.test','malformed'])assert.equal(app.navigate(url),true,url);
});
test('garde un jeton immuable et interdit le mode requis sans API',async()=>{
 const app=setup();await app.window.__kiaraRecoveryReady;assert.equal(app.window.__kiaraRecoveryToken,'a'.repeat(64));
 assert.throws(()=>{app.window.__kiaraRecoveryToken='replace'},TypeError);
 let other=setup({navigation:false,required:true});assert.equal(await other.window.__kiaraRecoveryReady,false);assert.equal(other.window.__kiaraRecoveryNavigationSafe,false);
 other=setup({navigation:false,required:false});assert.equal(await other.window.__kiaraRecoveryReady,true);assert.equal(other.window.__kiaraRecoveryNavigationSafe,true);
});
test('un refus impossible à annuler rend la session non vérifiée',async()=>{
 const app=setup();await app.window.__kiaraRecoveryReady;assert.equal(app.navigate('https://example.test',false),true);
 assert.equal(app.window.__kiaraRecoveryNavigationSafe,false);
 app.navigate('http://127.0.0.1:17841/recovery');assert.equal(app.window.__kiaraRecoveryNavigationSafe,false);
});
test('un service worker existant ou illisible bloque le jeton sans le supprimer',async()=>{
 for(const workers of [
  {controller:{},getRegistrations:async()=>[]},
  {controller:null,getRegistrations:async()=>[{}]},
  {controller:null,getRegistrations:async()=>{throw Error('indisponible');}},
  {controller:null},
 ]){
  const app=setup({workers});assert.equal(await app.window.__kiaraRecoveryReady,false);
  assert.equal(app.window.__kiaraRecoveryNavigationSafe,false);assert.equal(app.window.__kiaraRecoveryToken,undefined);
 }
 const app=setup({workers:{controller:null,getRegistrations:async()=>[]}});
 assert.equal(await app.window.__kiaraRecoveryReady,true);assert.equal(app.window.__kiaraRecoveryToken,'a'.repeat(64));
 const stalled=setup({workers:{controller:null,getRegistrations:()=>new Promise(()=>{})},timer:callback=>{queueMicrotask(callback);return 0;}});
 assert.equal(await stalled.window.__kiaraRecoveryReady,false);assert.equal(stalled.window.__kiaraRecoveryToken,undefined);
});
