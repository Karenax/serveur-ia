'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {webcrypto}=require('node:crypto');
const {localRecord,audioRecord,audioArchiveRecord,sourceRecords,indexedAudioSource,sendOne,sendAll,receiveOne,httpTransport,TransferConflict,TransferRestart,MAX_BYTES,INLINE_AUDIO_BYTES}=require('./portal_origin_transfer.js');
const audioArchive=require('./portal_audio_conflict_archive.js');

class Storage {
  constructor(initial=[]){this.values=new Map(initial);}
  getItem(key){return this.values.has(key)?this.values.get(key):null;}
  setItem(key,value){this.values.set(key,value);}
  get length(){return this.values.size;}
  key(index){return [...this.values.keys()][index]??null;}
}
class Chunks {
  constructor(initial=[]){this.records=new Map(initial.map(record=>[record.id,record]));}
  async get(id){return this.records.get(id);}
  async add(record){if(this.records.has(record.id))throw Object.assign(Error('existe'),{name:'ConstraintError'});this.records.set(record.id,record);}
  async keys(){return [...this.records.keys()];}
  close(){this.closed=true;}
}
async function audio(bytes=[1,8,9]){
  const data=new Uint8Array(bytes),sha=Buffer.from(await webcrypto.subtle.digest('SHA-256',data)).toString('hex');
  return {id:'fiction:microphone:1',session_id:'fiction',track:'microphone',seq:1,command_id:'commande-fictive',
    sha256:sha,start_ms:0,duration_ms:100,created_at:'2026-11-17T00:00:00Z',blob:new Blob([data],{type:'audio/wav'})};
}
class Broker {
  constructor(storage,store){this.storage=storage;this.store=store;this.pending=null;this.confirmed=null;this.count=0;this.state={audio:null};this.maxBody=0;}
  async stage(body){
    assert.equal(this.pending,null);this.count++;this.maxBody=Math.max(this.maxBody,body.length);
    const id=this.count.toString(16).padStart(32,'0'),sha256=Buffer.from(await webcrypto.subtle.digest('SHA-256',body)).toString('hex');
    this.pending={id,sha256,body:body.slice()};this.confirmed=null;return {id,sha256};
  }
  async read(){return this.pending;}
  async ack(text){
    const [id,sha256,status]=text.split(':');assert.equal(id,this.pending.id);assert.equal(sha256,this.pending.sha256);
    this.pending=null;this.confirmed={id,sha256,status};
  }
  async receipt(id){
    if(!this.confirmed&&this.pending)await receiveOne(this,this.storage,this.store,webcrypto.subtle,this.state);
    return this.confirmed?.id===id?this.confirmed:null;
  }
}
const opts={subtle:webcrypto.subtle,sleep:async()=>{},attempts:3};

test('le canal accepte seulement les empreintes de copie audio typées et bornées',async()=>{
  const calls=[],local='a'.repeat(64),audioId='audio-'+'b'.repeat(64),token='c'.repeat(64);
  const transport=httpTransport(async(path,options)=>{
    calls.push({path,options});return {ok:true,json:async()=>({review:true,preserve:false,required:[local,audioId]})};
  },token);
  assert.deepEqual((await transport.options()).required,[local,audioId]);
  const offer={id:'d'.repeat(32),sha256:'e'.repeat(64)};
  await transport.markArchive(offer,audioId);
  assert.equal(calls[1].options.body,offer.id+':'+offer.sha256+':'+audioId);
  await assert.rejects(transport.markArchive(offer,'audio-'+'F'.repeat(64)),/invalide/);
  const bad=httpTransport(async()=>({ok:true,json:async()=>({review:true,preserve:false,required:['audio-short']})}),token);
  await assert.rejects(bad.options(),/invalides/);
});

test('le texte est vérifié, copié puis reconnu au rejeu sans effacer la source',async()=>{
  const source=new Storage([['draft','Brouillon fictif été']]),dest=new Storage(),broker=new Broker(dest,new Chunks());
  const item=localRecord('draft',source.getItem('draft'));
  assert.equal(await sendOne(item,broker,opts),'copied');assert.equal(await sendOne(item,broker,opts),'identical');
  assert.equal(dest.getItem('draft'),'Brouillon fictif été');assert.equal(source.getItem('draft'),'Brouillon fictif été');
});
test('un conflit de texte est signalé et conserve les deux versions',async()=>{
  const source=new Storage([['draft','Qt']]),dest=new Storage([['draft','Tauri']]),broker=new Broker(dest,new Chunks());
  await assert.rejects(sendOne(localRecord('draft',source.getItem('draft')),broker,opts),TransferConflict);
  assert.equal(source.getItem('draft'),'Qt');assert.equal(dest.getItem('draft'),'Tauri');assert.equal(broker.confirmed.status,'conflict');
});
test('une copie vérifiée peut confirmer un conflit sans remplacer la version courante',async()=>{
  const dest=new Storage([['draft','version courante']]),broker=new Broker(dest,new Chunks());
  const seen=[];broker.state.onLocalConflict=async (record,transfer)=>{
    seen.push({record,transfer});return 'archived';
  };
  const result=await sendAll([localRecord('draft','version source')],broker,opts);
  assert.deepEqual(result,{copied:0,identical:0,archived:1});
  assert.equal(dest.getItem('draft'),'version courante');
  assert.equal(seen[0].record.value,'version source');assert.match(seen[0].transfer.sha256,/^[0-9a-f]{64}$/);
});
test('une nouvelle copie demande le redémarrage avant toute confirmation finale',async()=>{
  const dest=new Storage([['draft','courant']]),broker=new Broker(dest,new Chunks());
  broker.state.onLocalConflict=async()=> 'restart';
  await assert.rejects(sendOne(localRecord('draft','source'),broker,opts),TransferRestart);
  assert.equal(dest.getItem('draft'),'courant');assert.equal(broker.confirmed.status,'restart');
});
test('un résultat de résolution inconnu signale une panne sans toucher aux valeurs',async()=>{
  const dest=new Storage([['draft','courant']]),broker=new Broker(dest,new Chunks());
  broker.state.onLocalConflict=async()=> 'copied';
  await assert.rejects(sendOne(localRecord('draft','source'),broker,opts),/vérifiée/);
  assert.equal(broker.confirmed.status,'unavailable');assert.equal(dest.getItem('draft'),'courant');
});
test('une ancienne version explicitement reconnue laisse la version courante et recopie les entrées manquantes',async()=>{
  class KnownSourceBroker extends Broker {
    async receipt(id){const value=await super.receipt(id);return value?.status==='conflict'?{...value,status:'preserved'}:value;}
  }
  const dest=new Storage([['draft','version courante']]),broker=new KnownSourceBroker(dest,new Chunks());
  const result=await sendAll([localRecord('draft','ancienne version'),localRecord('missing','à restaurer')],broker,opts);
  assert.deepEqual(result,{copied:1,identical:0,preserved:1});
  assert.equal(dest.getItem('draft'),'version courante');assert.equal(dest.getItem('missing'),'à restaurer');
});
test('les octets et métadonnées audio sont vérifiés et le rejeu reste identique',async()=>{
  const original=await audio(),dest=new Chunks(),broker=new Broker(new Storage(),dest),item=await audioRecord(original,webcrypto.subtle);
  assert.equal(await sendOne(item,broker,opts),'copied');assert.equal(await sendOne(item,broker,opts),'identical');
  const record=await dest.get(original.id);assert.deepEqual(Array.from(new Uint8Array(record.stableBytes)),[1,8,9]);
  assert.equal(record.command_id,'commande-fictive');assert.deepEqual(Array.from(new Uint8Array(await original.blob.arrayBuffer())),[1,8,9]);
});
test('le codage audio fonctionne à travers les limites de segments',async()=>{
  const data=Uint8Array.from({length:24577},(_,index)=>index%256),original=await audio(data),dest=new Chunks(),broker=new Broker(new Storage(),dest);
  const item=await audioRecord(original,webcrypto.subtle);
  assert.equal(item.data,Buffer.from(data).toString('base64'));
  assert.equal(await sendOne(item,broker,opts),'copied');
  assert.deepEqual(new Uint8Array((await dest.get(original.id)).stableBytes),data);
});
test('un audio de plus de 16 Mio est transmis par segments puis rejoué',async()=>{
  const data=new Uint8Array(16*1024*1024+17);for(let i=0;i<data.length;i++)data[i]=i%251;
  const original=await audio(data),dest=new Chunks(),broker=new Broker(new Storage(),dest),item=await audioRecord(original,webcrypto.subtle);
  assert.equal(item.type,'audio-stream');
  assert.deepEqual(await sendAll([item],broker,opts),{copied:1,identical:0});
  assert.ok(broker.maxBody<MAX_BYTES);assert.deepEqual(new Uint8Array((await dest.get(original.id)).stableBytes),data);
  assert.deepEqual(await sendAll([item],broker,opts),{copied:0,identical:1});
  assert.deepEqual(new Uint8Array(await original.blob.arrayBuffer()),data);
});
test('un segment réémis après perte de confirmation ne corrompt pas la copie',async()=>{
  const data=new Uint8Array(INLINE_AUDIO_BYTES+17).fill(7),item=await audioRecord(await audio(data),webcrypto.subtle);
  const dest=new Chunks(),broker=new Broker(new Storage(),dest),realAck=broker.ack.bind(broker);let interrupted=false;
  broker.ack=async text=>{
    const record=JSON.parse(new TextDecoder().decode(broker.pending.body));
    if(record.type==='audio-part'&&!interrupted){interrupted=true;throw Error('canal interrompu');}
    return realAck(text);
  };
  await assert.rejects(sendAll([item],broker,opts),/interrompu/);assert.equal(await dest.get(item.meta.id),undefined);
  broker.ack=realAck;
  assert.equal(await receiveOne(broker,broker.storage,dest,webcrypto.subtle,broker.state),'identical');
  assert.deepEqual(await sendAll([item],broker,opts),{copied:1,identical:0});
  assert.deepEqual(new Uint8Array((await dest.get(item.meta.id)).stableBytes),data);
});
test('un acquittement final perdu se reprend sans réécrire l’audio',async()=>{
  const data=new Uint8Array(INLINE_AUDIO_BYTES+17).fill(8),item=await audioRecord(await audio(data),webcrypto.subtle);
  const dest=new Chunks(),broker=new Broker(new Storage(),dest),realAck=broker.ack.bind(broker);let interrupted=false;
  broker.ack=async text=>{
    const record=JSON.parse(new TextDecoder().decode(broker.pending.body));
    if(record.type==='audio-end'&&!interrupted){interrupted=true;throw Error('confirmation perdue');}
    return realAck(text);
  };
  await assert.rejects(sendAll([item],broker,opts),/perdue/);assert.ok(await dest.get(item.meta.id));
  broker.ack=realAck;
  assert.equal(await receiveOne(broker,broker.storage,dest,webcrypto.subtle,broker.state),'identical');
  assert.deepEqual(await sendAll([item],broker,opts),{copied:0,identical:1});
  assert.deepEqual(new Uint8Array((await dest.get(item.meta.id)).stableBytes),data);
});
test('la fin prématurée d’un fragment ne crée aucun audio',async()=>{
  const data=new Uint8Array(INLINE_AUDIO_BYTES+5).fill(9),item=await audioRecord(await audio(data),webcrypto.subtle);
  const dest=new Chunks(),broker=new Broker(new Storage(),dest);
  await broker.stage(new TextEncoder().encode(JSON.stringify({type:'audio-begin',meta:item.meta,mime:item.mime,length:data.length})));
  assert.equal(await receiveOne(broker,broker.storage,dest,webcrypto.subtle,broker.state),'copied');
  await broker.stage(new TextEncoder().encode(JSON.stringify({type:'audio-end',id:item.meta.id})));
  await assert.rejects(receiveOne(broker,broker.storage,dest,webcrypto.subtle,broker.state),/incomplet/);
  assert.equal(await dest.get(item.meta.id),undefined);assert.ok(broker.pending);
});
test('un fragment incomplet ou un conflit ne remplace aucun audio existant',async()=>{
  const data=new Uint8Array(INLINE_AUDIO_BYTES+9).fill(7),item=await audioRecord(await audio(data),webcrypto.subtle);
  const existing=await audio([1,2,3]),dest=new Chunks([existing]),broker=new Broker(new Storage(),dest);
  await assert.rejects(sendAll([item],broker,opts),TransferConflict);
  assert.equal(await dest.get(existing.id),existing);assert.deepEqual(Array.from(new Uint8Array(await existing.blob.arrayBuffer())),[1,2,3]);
});
test('un conflit audio court peut être conservé puis vérifié au rejeu sans remplacer la cible',async()=>{
  const existing=await audio([1,2,3]),incoming=await audio([4,5,6]),dest=new Chunks([existing]);
  const journal=new Chunks(),broker=new Broker(new Storage(),dest),item=await audioRecord(incoming,webcrypto.subtle);
  let savedId;
  broker.state.onAudioConflict=async (value,transfer)=>{
    assert.match(transfer.sha256,/^[0-9a-f]{64}$/);
    const record={...value.meta,stableBytes:value.bytes.slice().buffer,stableMime:value.mime};
    savedId=await audioArchive.archive(journal,dest,record,webcrypto.subtle);
    return 'restart';
  };
  await assert.rejects(sendOne(item,broker,opts),TransferRestart);
  assert.equal(await dest.get(existing.id),existing);
  const saved=await audioArchive.read(journal,savedId,webcrypto.subtle);
  assert.deepEqual([...saved.current.bytes],[1,2,3]);assert.deepEqual([...saved.incoming.bytes],[4,5,6]);
  broker.state.onAudioConflict=async value=>{
    const record={...value.meta,stableBytes:value.bytes.slice().buffer,stableMime:value.mime};
    assert.equal(await audioArchive.find(journal,dest,record,webcrypto.subtle),savedId);
    return 'archived';
  };
  assert.deepEqual(await sendAll([item],broker,opts),{copied:0,identical:0,archived:1});
  assert.equal(await dest.get(existing.id),existing);
});
test('un conflit audio segmenté est présenté uniquement une fois le dernier segment vérifié',async()=>{
  const data=new Uint8Array(INLINE_AUDIO_BYTES+9).fill(7),item=await audioRecord(await audio(data),webcrypto.subtle);
  const existing=await audio([1,2,3]),dest=new Chunks([existing]),broker=new Broker(new Storage(),dest);
  let calls=0;
  broker.state.onAudioConflict=async(value,transfer)=>{
    calls++;assert.deepEqual(value.bytes,data);assert.match(transfer.sha256,/^[0-9a-f]{64}$/);return 'restart';
  };
  await assert.rejects(sendAll([item],broker,opts),TransferRestart);
  assert.equal(calls,1);assert.equal(broker.state.audio,null);assert.equal(await dest.get(existing.id),existing);
});
test('une résolution audio invalide ou échouée ne confirme aucune copie',async()=>{
  const existing=await audio([1]),incoming=await audio([2]),dest=new Chunks([existing]),item=await audioRecord(incoming,webcrypto.subtle);
  for (const callback of [async()=> 'copied',async()=>{throw Error('quota');}]) {
    const broker=new Broker(new Storage(),dest);broker.state.onAudioConflict=callback;
    await assert.rejects(sendOne(item,broker,opts),/vérifiée/);
    assert.equal(broker.confirmed.status,'unavailable');assert.equal(await dest.get(existing.id),existing);
  }
});
test('une archive de deux fragments est transférée par segments puis rejouée',async()=>{
  const data=new Uint8Array(INLINE_AUDIO_BYTES+17).fill(7),source=new Chunks(),destination=new Chunks();
  const id=await audioArchive.archive(source,new Chunks([await audio([1,2,3])]),await audio(data),webcrypto.subtle);
  const original=await audioArchive.read(source,id,webcrypto.subtle),item=audioArchiveRecord(original),broker=new Broker(new Storage(),new Chunks());
  broker.state.archiveAPI=audioArchive;broker.state.archiveStore=destination;
  assert.deepEqual(await sendAll([item],broker,opts),{copied:1,identical:0});
  assert.ok(broker.count>=5 && broker.maxBody<MAX_BYTES);
  assert.deepEqual((await audioArchive.read(destination,id,webcrypto.subtle)).incoming.bytes,data);
  assert.deepEqual(await sendAll([item],broker,opts),{copied:0,identical:1});
  assert.deepEqual((await audioArchive.read(source,id,webcrypto.subtle)).current.bytes,new Uint8Array([1,2,3]));
});
test('une archive segmentée interrompt sans copie partielle et reprend après perte de confirmation',async()=>{
  const data=new Uint8Array(INLINE_AUDIO_BYTES+3).fill(9),source=new Chunks(),destination=new Chunks();
  const id=await audioArchive.archive(source,new Chunks([await audio([1])]),await audio(data),webcrypto.subtle);
  const item=audioArchiveRecord(await audioArchive.read(source,id,webcrypto.subtle)),broker=new Broker(new Storage(),new Chunks());
  broker.state.archiveAPI=audioArchive;broker.state.archiveStore=destination;const ack=broker.ack.bind(broker);let interrupted=false;
  broker.ack=async text=>{
    const value=JSON.parse(new TextDecoder().decode(broker.pending.body));
    if(value.type==='audio-archive-part'&&!interrupted){interrupted=true;throw Error('canal interrompu');}
    return ack(text);
  };
  await assert.rejects(sendAll([item],broker,opts),/interrompu/);assert.equal(await destination.get(id),undefined);
  broker.ack=ack;assert.equal(await receiveOne(broker,broker.storage,broker.store,webcrypto.subtle,broker.state),'identical');
  assert.deepEqual(await sendAll([item],broker,opts),{copied:1,identical:0});
  assert.deepEqual((await audioArchive.read(destination,id,webcrypto.subtle)).incoming.bytes,data);
});
test('une archive altérée, incomplète ou non prise en charge ne reçoit pas de confirmation finale',async()=>{
  const source=new Chunks(),id=await audioArchive.archive(source,new Chunks([await audio([1])]),await audio([2]),webcrypto.subtle);
  const item=audioArchiveRecord(await audioArchive.read(source,id,webcrypto.subtle));
  const unsupported=new Broker(new Storage(),new Chunks());
  await assert.rejects(sendAll([item],unsupported,opts),/indisponibles/);assert.ok(unsupported.pending);
  const target=new Chunks(),broker=new Broker(new Storage(),new Chunks());broker.state.archiveAPI=audioArchive;broker.state.archiveStore=target;
  item.incoming.bytes[0]=0;
  await assert.rejects(sendAll([item],broker,opts));assert.equal(await target.get(id),undefined);
  assert.deepEqual((await audioArchive.read(source,id,webcrypto.subtle)).incoming.bytes,new Uint8Array([2]));
});
test('la perte de confirmation finale rejoue la copie audio sans écriture supplémentaire',async()=>{
  const source=new Chunks(),destination=new Chunks(),id=await audioArchive.archive(source,new Chunks([await audio([1])]),await audio([2]),webcrypto.subtle);
  const item=audioArchiveRecord(await audioArchive.read(source,id,webcrypto.subtle)),broker=new Broker(new Storage(),new Chunks());
  broker.state.archiveAPI=audioArchive;broker.state.archiveStore=destination;const ack=broker.ack.bind(broker);let interrupted=false;
  broker.ack=async text=>{const value=JSON.parse(new TextDecoder().decode(broker.pending.body));
    if(value.type==='audio-archive-end'&&!interrupted){interrupted=true;throw Error('confirmation perdue');}return ack(text);};
  await assert.rejects(sendAll([item],broker,opts),/confirmation perdue/);assert.ok(await destination.get(id));
  broker.ack=ack;assert.equal(await receiveOne(broker,broker.storage,broker.store,webcrypto.subtle,broker.state),'identical');
  assert.equal(broker.state.archive,null);assert.deepEqual(await sendAll([item],broker,opts),{copied:0,identical:1});
  assert.equal(destination.records.size,1);
});
test('une copie audio incomplète refuse les messages intercalés et toute confirmation',async()=>{
  const source=new Chunks(),destination=new Chunks(),id=await audioArchive.archive(source,new Chunks([await audio([1])]),await audio([2]),webcrypto.subtle);
  const item=audioArchiveRecord(await audioArchive.read(source,id,webcrypto.subtle)),broker=new Broker(new Storage(),new Chunks());
  broker.state.archiveAPI=audioArchive;broker.state.archiveStore=destination;
  const header=x=>({meta:x.meta,mime:x.mime,length:x.bytes.length});
  await sendOne({type:'audio-archive-begin',id,current:header(item.current),incoming:header(item.incoming)},broker,opts);
  await broker.stage(new TextEncoder().encode(JSON.stringify(localRecord('fictif','valeur'))));
  await assert.rejects(receiveOne(broker,broker.storage,broker.store,webcrypto.subtle,broker.state),/en cours/);
  assert.ok(broker.pending);assert.equal(await destination.get(id),undefined);
});
test('une origine contenant uniquement une archive est inventoriée puis copiée et revérifiée',async()=>{
  const source=new Chunks(),destination=new Chunks(),id=await audioArchive.archive(source,new Chunks([await audio([1])]),await audio([2]),webcrypto.subtle);
  const storage=new Storage(),chunks=new Chunks(),broker=new Broker(new Storage(),new Chunks());
  broker.state.archiveAPI=audioArchive;broker.state.archiveStore=destination;
  const inventory=async()=>({localEntries:0,audioChunks:0,audioArchives:1});
  const records=sourceRecords(storage,chunks,inventory,webcrypto.subtle,{archiveAPI:audioArchive,archiveStore:source});
  assert.deepEqual(await sendAll(records,broker,opts),{copied:1,identical:0});
  assert.deepEqual((await audioArchive.read(destination,id,webcrypto.subtle)).incoming.bytes,new Uint8Array([2]));
  assert.equal(source.closed,true);assert.equal(chunks.closed,true);
});
test('un changement ou une copie manquante pendant le transfert bloque la confirmation de la source',async()=>{
  const source=new Chunks(),id=await audioArchive.archive(source,new Chunks([await audio([1])]),await audio([2]),webcrypto.subtle);
  const chunks=new Chunks(),inventory=async()=>({localEntries:0,audioChunks:0,audioArchives:1});
  const records=sourceRecords(new Storage(),chunks,inventory,webcrypto.subtle,{archiveAPI:audioArchive,archiveStore:source});
  const first=await records.next();assert.equal(first.value.id,id);
  source.records.delete(id);
  await assert.rejects(records.next(),/copies audio|Copies audio/);
  assert.equal(source.closed,true);assert.equal(chunks.closed,true);
  const unavailable=sourceRecords(new Storage(),new Chunks(),inventory,webcrypto.subtle,{archiveAPI:audioArchive});
  await assert.rejects(unavailable.next(),/Copies audio indisponibles/);
});
test('une archive altérée sous le même identifiant bloque le résultat puis reprend sans doublon',async()=>{
  const source=new Chunks(),destination=new Chunks();
  const id=await audioArchive.archive(source,new Chunks([await audio([1])]),await audio([2]),webcrypto.subtle);
  const stored=await source.get(id),bytes=new Uint8Array(stored.incoming.bytes),original=bytes[0];
  const broker=new Broker(new Storage(),new Chunks());
  broker.state.archiveAPI=audioArchive;broker.state.archiveStore=destination;
  const receipt=broker.receipt.bind(broker);let altered=false;
  broker.receipt=async pendingId=>{
    const kind=broker.pending && JSON.parse(new TextDecoder().decode(broker.pending.body)).type;
    const result=await receipt(pendingId);
    if(kind==='audio-archive-end' && !altered){bytes[0]^=1;altered=true;}
    return result;
  };
  const inventory=async()=>({localEntries:0,audioChunks:0,audioArchives:1});
  const records=()=>sourceRecords(new Storage(),new Chunks(),inventory,webcrypto.subtle,{archiveAPI:audioArchive,archiveStore:source});
  await assert.rejects(sendAll(records(),broker,opts),/empreinte|audio/i);
  assert.equal(altered,true);assert.equal((await source.keys())[0],id);
  assert.deepEqual((await audioArchive.read(destination,id,webcrypto.subtle)).incoming.bytes,new Uint8Array([2]));
  assert.equal(bytes[0],original^1);
  bytes[0]=original;
  assert.deepEqual(await sendAll(records(),broker,opts),{copied:0,identical:1});
  assert.equal(destination.records.size,1);
  assert.deepEqual((await audioArchive.read(source,id,webcrypto.subtle)).incoming.bytes,new Uint8Array([2]));
});
test('une copie déjà écrite avant perte de confirmation se reprend sans doublon',async()=>{
  const store=new Chunks(),broker=new Broker(new Storage(),store),item=await audioRecord(await audio(),webcrypto.subtle);
  const ack=broker.ack.bind(broker);broker.ack=async()=>{throw Error('canal interrompu');};
  await assert.rejects(sendOne(item,broker,opts),/interrompu/);assert.ok(await store.get('fiction:microphone:1'));
  broker.ack=ack;assert.equal(await receiveOne(broker,broker.storage,store,webcrypto.subtle),'identical');
  assert.equal(broker.confirmed.status,'identical');
});
test('un message altéré ou inconnu ne reçoit aucun acquittement',async()=>{
  const broker=new Broker(new Storage(),new Chunks());await broker.stage(new TextEncoder().encode('{"type":"future"}'));
  await assert.rejects(receiveOne(broker,broker.storage,broker.store,webcrypto.subtle),/inconnu/);assert.ok(broker.pending);
  broker.pending.body[0]^=1;await assert.rejects(receiveOne(broker,broker.storage,broker.store,webcrypto.subtle),/Empreinte/);assert.ok(broker.pending);
});
test('un audio mal encodé est refusé avant écriture ou acquittement',async()=>{
  const broker=new Broker(new Storage(),new Chunks()),item=await audioRecord(await audio(),webcrypto.subtle);
  item.data='!!!!';await broker.stage(new TextEncoder().encode(JSON.stringify(item)));
  await assert.rejects(receiveOne(broker,broker.storage,broker.store,webcrypto.subtle),/audio invalide/);
  assert.ok(broker.pending);assert.equal(await broker.store.get('fiction:microphone:1'),undefined);
});
test('toutes les entrées sont énumérées et revérifiées sans suppression',async()=>{
  const first=await audio(),second={...await audio([3,4,5]),id:'fiction:microphone:2',seq:2};
  const storage=new Storage([['z','fin'],['draft','début']]),store=new Chunks([first,second]);
  const inventory=async()=>({localEntries:storage.length,audioChunks:store.records.size}),records=[];
  for await(const item of sourceRecords(storage,store,inventory,webcrypto.subtle))records.push(item);
  assert.deepEqual(records.map(item=>item.type),['local','local','audio','audio']);
  assert.deepEqual(records.slice(0,2).map(item=>item.key),['draft','z']);
  assert.deepEqual(records.slice(2).map(item=>item.meta.id),['fiction:microphone:1','fiction:microphone:2']);
  assert.equal(storage.getItem('draft'),'début');assert.equal(store.records.size,2);assert.equal(store.closed,true);
});
test('une modification pendant la copie empêche de confirmer l’inventaire',async()=>{
  const storage=new Storage([['draft','avant']]),store=new Chunks(),inventory=async()=>({localEntries:storage.length,audioChunks:store.records.size});
  const iterator=sourceRecords(storage,store,inventory,webcrypto.subtle);
  assert.equal((await iterator.next()).value.value,'avant');storage.setItem('draft','après');
  await assert.rejects(iterator.next(),/changé/);assert.equal(storage.getItem('draft'),'après');assert.equal(store.closed,true);
});
test('le transfert complet attend chaque confirmation et se rejoue sans doublon',async()=>{
  const storage=new Storage([['draft','Qt'],['notes','à préserver']]),store=new Chunks([await audio()]);
  const target=new Storage(),targetAudio=new Chunks(),broker=new Broker(target,targetAudio);
  const inventory=async()=>({localEntries:storage.length,audioChunks:store.records.size});
  const records=()=>sourceRecords(storage,store,inventory,webcrypto.subtle);
  assert.deepEqual(await sendAll(records(),broker,opts),{copied:3,identical:0});
  assert.deepEqual(await sendAll(records(),broker,opts),{copied:0,identical:3});
  assert.equal(target.getItem('notes'),'à préserver');assert.equal(targetAudio.records.size,1);
  assert.equal(storage.getItem('draft'),'Qt');assert.equal(store.records.size,1);
});
test('un conflit interrompt le transfert complet sans toucher aux autres sources',async()=>{
  const storage=new Storage([['a','source'],['b','autre']]),store=new Chunks();
  const target=new Storage([['a','cible']]),broker=new Broker(target,new Chunks());
  const inventory=async()=>({localEntries:storage.length,audioChunks:0});
  await assert.rejects(sendAll(sourceRecords(storage,store,inventory,webcrypto.subtle),broker,opts),TransferConflict);
  assert.equal(broker.count,1);assert.equal(target.getItem('a'),'cible');assert.equal(target.getItem('b'),null);
  assert.equal(storage.getItem('a'),'source');assert.equal(storage.getItem('b'),'autre');assert.equal(store.closed,true);
});
test('un stockage audio indisponible échoue sans créer de base',async()=>{
  const store=indexedAudioSource({open:()=>{throw Error('interdit');}});
  await assert.rejects(store.keys(),/indisponible/);store.close();
});
test('une donnée trop volumineuse ou une confirmation divergente arrêtent le transfert',async()=>{
  let called=false;const broker={stage:async()=>{called=true;}};
  await assert.rejects(sendOne(localRecord('draft','x'.repeat(MAX_BYTES)),broker,opts),/volumineuse/);assert.equal(called,false);
  const bad={stage:async()=>({id:'0'.repeat(32),sha256:'0'.repeat(64)})};
  await assert.rejects(sendOne(localRecord('draft','fictif'),bad,opts),/non vérifié/);
});
