import {afterEach, expect, it, vi} from 'vitest';
import {ProjectAudioDrafts} from './projectAudioDrafts';
import {projectAudioPrefix} from './projectAudioId';
import {pcmWave} from './pcmAudioRecorder';
import {projectChunkIdentity, type DurableAudioChunk, type IndexedAudioChunks, type ProjectChunkIdentity} from './meetingAudioStore';

const {webcrypto}=await vi.importActual<{webcrypto:Crypto}>('node:crypto');
afterEach(() => vi.unstubAllGlobals());

const read = (blob: Blob) => new Promise<ArrayBuffer>((resolve, reject) => {
  const reader=new FileReader();reader.onload=()=>resolve(reader.result as ArrayBuffer);reader.onerror=()=>reject(reader.error);reader.readAsArrayBuffer(blob);
});
const digest = async (blob: Blob) => Array.from(new Uint8Array(await webcrypto.subtle.digest('SHA-256',await read(blob))),
  value=>value.toString(16).padStart(2,'0')).join('');

class MemoryStore {
  records=new Map<string,DurableAudioChunk>();
  async ready() {}
  async addProjectChunk(chunk:DurableAudioChunk) {if(this.records.has(chunk.id))throw new Error('collision');this.records.set(chunk.id,chunk);}
  async list(sessionId?:string) {return [...this.records.values()].filter(chunk=>!sessionId||chunk.session_id===sessionId);}
  async listProjectSessions(prefix:string) {
    const counts=new Map<string,number>();
    for(const chunk of this.records.values())if(chunk.session_id.startsWith(prefix))counts.set(chunk.session_id,(counts.get(chunk.session_id)??0)+1);
    return [...counts].map(([sessionId,count])=>({sessionId,count}));
  }
  async deleteProjectIfUnchanged(sessionId:string, expected:readonly ProjectChunkIdentity[]) {
    const rows=(await this.list(sessionId)).sort((a,b)=>a.seq-b.seq);
    if(JSON.stringify(rows.map(projectChunkIdentity))!==JSON.stringify(expected))throw new Error('capture modifiée');
    for(const row of rows)this.records.delete(row.id);
  }
}
const create = () => {
  vi.stubGlobal('crypto',webcrypto);
  const store=new MemoryStore();
  const values=new Map<string,string>();
  const storage={getItem:(key:string)=>values.get(key)??null,setItem:(key:string,value:string)=>{values.set(key,value);},
    removeItem:(key:string)=>{values.delete(key);}} as Storage;
  return {store,storage,drafts:new ProjectAudioDrafts(store as unknown as IndexedAudioChunks,digest,()=>storage)};
};

it('conserve et reconstitue deux fragments PCM sans les confondre avec un autre compte ou projet',async()=>{
  const {store,drafts}=create();
  const id=drafts.create('compte:1','projet:1');
  await drafts.append('compte:1','projet:1',id,0,pcmWave([new Float32Array([-1,0.5])],16000),0,1000);
  await drafts.append('compte:1','projet:1',id,1,pcmWave([new Float32Array([0,1])],16000),1000,1000);
  expect(await drafts.list('compte:1','projet:1')).toEqual([{sessionId:id,count:2}]);
  expect(await drafts.list('compte','1:projet:1')).toEqual([]);
  await expect(drafts.read('autre','projet:1',id)).rejects.toThrow(/hors du projet ou du compte/);
  const result=await drafts.read('compte:1','projet:1',id);
  const view=new DataView(await read(result.blob));
  expect(result.count).toBe(2);expect(result.blob.type).toBe('audio/wav');expect(view.byteLength).toBe(52);
  expect(view.getUint32(24,true)).toBe(16000);expect(view.getUint32(40,true)).toBe(8);
  expect(Array.from({length:4},(_,i)=>view.getInt16(44+i*2,true))).toEqual([-32768,16384,0,32767]);
  expect(store.records.size).toBe(2);
});

it('refuse une collision sans remplacer le fragment déjà conservé',async()=>{
  const {store,drafts}=create(), id=drafts.create('compte','projet');
  const first=pcmWave([new Float32Array([0.1])],16000);
  const stored=await drafts.append('compte','projet',id,0,first,0,1000);
  await expect(drafts.append('compte','projet',id,0,pcmWave([new Float32Array([0.9])],16000),0,1000)).rejects.toThrow('collision');
  expect(store.records.get(stored.id)).toBe(stored);
  expect((await drafts.read('compte','projet',id)).blob.size).toBe(first.size);
});

it('refuse les trous, les empreintes divergentes et les fréquences incompatibles sans supprimer de données',async()=>{
  const {store,drafts}=create(), id=drafts.create('compte','projet');
  const first=await drafts.append('compte','projet',id,0,pcmWave([new Float32Array([0.1])],16000),0,1000);
  const second=await drafts.append('compte','projet',id,1,pcmWave([new Float32Array([0.2])],44100),1000,1000);
  await expect(drafts.read('compte','projet',id)).rejects.toThrow(/Fréquences/);
  store.records.set(`${id}:mic:2`,{...second,seq:2,id:`${id}:mic:2`});store.records.delete(second.id);
  await expect(drafts.read('compte','projet',id)).rejects.toThrow(/incomplet/);
  store.records.delete(`${id}:mic:2`);store.records.set(second.id,{...second,blob:first.blob});
  await expect(drafts.read('compte','projet',id)).rejects.toThrow(/modifié/);
  expect(store.records.size).toBe(2);
});

it('reconstitue les fragments compressés dans leur ordre sans modifier leur contenu',async()=>{
  const {drafts}=create(), id=drafts.create('compte','projet');
  await drafts.append('compte','projet',id,0,new Blob(['début'],{type:'audio/webm'}),0,1000);
  await drafts.append('compte','projet',id,1,new Blob(['suite'],{type:'audio/webm'}),1000,1000);
  const result=await drafts.read('compte','projet',id);
  expect(new TextDecoder().decode(await read(result.blob))).toBe('débutsuite');
  expect(result.blob.type).toBe('audio/webm');
});

it('sépare les identifiants et refuse les captures mal formées',()=>{
  expect(projectAudioPrefix('a:b','c')).not.toBe(projectAudioPrefix('a','b:c'));
  expect(()=>projectAudioPrefix('','p')).toThrow();
  expect(()=>projectAudioPrefix('o','')).toThrow();
});

it('ne libère une capture terminée que si la copie serveur correspond exactement',async()=>{
  const {store,drafts}=create(), id=drafts.create('compte','projet'), other=drafts.create('compte','projet');
  await drafts.append('compte','projet',id,0,new Blob(['début'],{type:'audio/webm'}),0,1000);
  await drafts.append('compte','projet',id,1,new Blob(['suite'],{type:'audio/webm'}),1000,1000);
  await drafts.append('compte','projet',other,0,new Blob(['autre'],{type:'audio/webm'}),0,1000);
  const capture=await drafts.read('compte','projet',id);
  const receipt={recording_id:'audio1',source_id:'source1',sha256:await digest(capture.blob),size:capture.blob.size};
  await expect(drafts.releaseVerified('compte','projet',id,receipt,'audio1','source1',async()=>{})).rejects.toThrow(/fin.*confirmée/);
  await drafts.seal('compte','projet',id);expect(drafts.isSealed('compte','projet',id)).toBe(true);
  await expect(drafts.releaseVerified('compte','projet',id,{...receipt,sha256:'0'.repeat(64)},'audio1','source1',async()=>{})).rejects.toThrow(/ne correspondent pas/);
  await expect(drafts.releaseVerified('compte','projet',id,{...receipt,source_id:'autre'},'audio1','source1',async()=>{})).rejects.toThrow(/serveur/);
  await expect(drafts.releaseVerified('autre','projet',id,receipt,'audio1','source1',async()=>{})).rejects.toThrow(/hors du projet ou du compte/);
  expect(store.records.size).toBe(3);
  await drafts.releaseVerified('compte','projet',id,receipt,'audio1','source1',async()=>{});
  expect(store.records.size).toBe(1);expect((await drafts.read('compte','projet',other)).count).toBe(1);
  expect(drafts.isSealed('compte','projet',id)).toBe(false);
});

it('conserve tous les fragments si la capture a changé après confirmation de fin',async()=>{
  const {store,drafts}=create(), id=drafts.create('compte','projet');
  await drafts.append('compte','projet',id,0,new Blob(['début'],{type:'audio/webm'}),0,1000);
  const original=await drafts.read('compte','projet',id);
  await drafts.seal('compte','projet',id);
  await drafts.append('compte','projet',id,1,new Blob(['fin'],{type:'audio/webm'}),1000,1000);
  const receipt={recording_id:'audio1',source_id:'source1',sha256:await digest(original.blob),size:original.blob.size};
  await expect(drafts.releaseVerified('compte','projet',id,receipt,'audio1','source1',async()=>{})).rejects.toThrow(/ne correspondent pas/);
  expect(store.records.size).toBe(2);
});

it('conserve les fragments si leur transaction de suppression échoue',async()=>{
  const {store,drafts}=create(), id=drafts.create('compte','projet');
  await drafts.append('compte','projet',id,0,new Blob(['audio'],{type:'audio/webm'}),0,1000);
  await drafts.seal('compte','projet',id);
  const original=await drafts.read('compte','projet',id);
  const receipt={recording_id:'audio1',source_id:'source1',sha256:await digest(original.blob),size:original.blob.size};
  vi.spyOn(store,'deleteProjectIfUnchanged').mockRejectedValueOnce(new Error('transaction interrompue'));
  await expect(drafts.releaseVerified('compte','projet',id,receipt,'audio1','source1',async()=>{})).rejects.toThrow(/transaction/);
  expect(store.records.size).toBe(1);expect(drafts.isSealed('compte','projet',id)).toBe(true);
});

it('conserve les fragments si le contrôle final du serveur échoue',async()=>{
  const {store,drafts}=create(), id=drafts.create('compte','projet');
  await drafts.append('compte','projet',id,0,new Blob(['audio'],{type:'audio/webm'}),0,1000);
  await drafts.seal('compte','projet',id);
  const original=await drafts.read('compte','projet',id);
  const receipt={recording_id:'audio1',source_id:'source1',sha256:await digest(original.blob),size:original.blob.size};
  await expect(drafts.releaseVerified('compte','projet',id,receipt,'audio1','source1',async()=>{throw new Error('serveur modifié');})).rejects.toThrow(/serveur modifié/);
  expect(store.records.size).toBe(1);expect(drafts.isSealed('compte','projet',id)).toBe(true);
});

it('refuse une modification arrivée entre la vérification et la transaction',async()=>{
  const {store,drafts}=create(), id=drafts.create('compte','projet');
  const first=await drafts.append('compte','projet',id,0,new Blob(['audio'],{type:'audio/webm'}),0,1000);
  await drafts.seal('compte','projet',id);
  const original=await drafts.read('compte','projet',id);
  const receipt={recording_id:'audio1',source_id:'source1',sha256:await digest(original.blob),size:original.blob.size};
  const perform=store.deleteProjectIfUnchanged.bind(store);
  vi.spyOn(store,'deleteProjectIfUnchanged').mockImplementation(async(sessionId,expected)=>{
    store.records.set(`${id}:mic:1`,{...first,id:`${id}:mic:1`,seq:1});
    await perform(sessionId,expected);
  });
  await expect(drafts.releaseVerified('compte','projet',id,receipt,'audio1','source1',async()=>{})).rejects.toThrow(/modifiée/);
  expect(store.records.size).toBe(2);expect(drafts.isSealed('compte','projet',id)).toBe(true);
});
