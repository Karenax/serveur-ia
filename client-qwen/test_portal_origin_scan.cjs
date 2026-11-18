const test = require('node:test');
const assert = require('node:assert/strict');
const {advance,run} = require('./portal_origin_scan.js');

function fixture(responses, overrides = {}) {
  const calls = [], moves = [], messages = [];
  return {calls, moves, messages, args: {
    port: 17841, safe: () => true, inventory: async () => ({localEntries: 1, audioChunks: 0}),
    post: async (path, body) => {calls.push({path, body}); return responses.shift();},
    navigate: url => moves.push(url), display: text => messages.push(text), ...overrides,
  }};
}

test('inventorie seulement l’origine attendue puis passe à la suivante', async () => {
  const f = fixture([{state:'scanning', nextPort:17841}, {state:'scanning', nextPort:17842}]);
  await advance(f.args);
  assert.deepEqual(f.calls.map(call => call.path), ['/recovery/status','/recovery/inventory']);
  assert.deepEqual(f.moves, ['http://127.0.0.1:17842/recovery/scan']);
});
test('retrouve le bon port après une interruption avant de lire les données', async () => {
  const f = fixture([{state:'scanning', nextPort:17844}], {inventory: () => {throw Error('inutile');}});
  await advance(f.args); assert.deepEqual(f.moves, ['http://127.0.0.1:17844/recovery/scan']);
});
test('confirme seulement sur le port sélectionné', async () => {
  let f = fixture([{state:'ready', port:17844}]); await advance(f.args);
  assert.equal(f.moves[0], 'http://127.0.0.1:17844/recovery/scan');assert.equal(f.calls.length,1);
  f = fixture([{state:'ready', port:17844}, {}], {port:17844}); await advance(f.args);
  assert.deepEqual(f.calls.map(call=>call.path), ['/recovery/status','/recovery/complete']);
});
test('signale un stockage illisible sans inventer un stockage vide', async () => {
  const f = fixture([{state:'scanning', nextPort:17841}, {state:'unavailable'}], {inventory: async()=>{throw Error('bloqué');}});
  await advance(f.args);assert.deepEqual(f.calls[1].body,{unavailable:true});assert.equal(f.moves.length,0);
  assert.match(f.messages.at(-1),/conservées/);
});
test('plusieurs jeux ne sont ni sélectionnés ni modifiés', async () => {
  const f = fixture([{state:'needsRecovery'}]);await advance(f.args);
  assert.equal(f.calls.length,1);assert.equal(f.moves.length,0);assert.match(f.messages[0],/récupération/);
});
test('navigation non sûre ou port inattendu arrêtent le parcours', async () => {
  let f=fixture([], {safe:()=>false});await assert.rejects(advance(f.args));assert.equal(f.calls.length,0);
  f=fixture([{state:'scanning',nextPort:42}]);await assert.rejects(advance(f.args));assert.equal(f.moves.length,0);
});
test('l’inventaire étendu transmet aussi les empreintes des copies audio',async()=>{
  const calls=[],audioArchive={},root={__kiaraRecoveryReady:Promise.resolve(true),__kiaraRecoveryNavigationSafe:true,
    __kiaraRecoveryToken:'a'.repeat(64),location:{port:'17841',assign:()=>{}},document:{getElementById:()=>({})},
    localStorage:{},indexedDB:{},kiaraPortalAudioConflictArchive:audioArchive,
    kiaraPortalOriginInventory:{inventory:async(_storage,_db,_timeout,options)=>{
      assert.equal(options.audioArchive,audioArchive);assert.equal(options.audioArchiveIds,true);
      return {localEntries:0,audioChunks:0,audioArchives:1,audioArchiveIds:['b'.repeat(64)]};}},
    fetch:async(path,options)=>{calls.push([path,options.body]);return {ok:true,json:async()=>
      path.endsWith('status')?{state:'scanning',nextPort:17841}:{state:'needsRecovery'}};}};
  await run(root);assert.equal(calls.length,2);
  assert.deepEqual(JSON.parse(calls[1][1]).audioArchiveIds,['b'.repeat(64)]);
});
