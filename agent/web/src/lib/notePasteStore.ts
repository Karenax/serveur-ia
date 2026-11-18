import type {NotePaste} from './projectNotes';

export type PendingNoteImage={payload:NotePaste;file:File};

const imageExtensions:Record<string,string>={'image/png':'png','image/jpeg':'jpg','image/webp':'webp'};

export function prepareClipboardImage(file:File){
  const extension=imageExtensions[file.type];
  if(!extension)throw new Error('Collez une image PNG, JPEG ou WebP.');
  if(!file.size||file.size>5*1024*1024)throw new Error('Choisissez une image de 5 Mio maximum.');
  return new File([file],`Image collée.${extension}`,{type:file.type});
}

async function openStore(){
  return new Promise<IDBDatabase>((resolve,reject)=>{
    const request=indexedDB.open('kiara-note-images',1);
    request.onupgradeneeded=()=>request.result.createObjectStore('pending');
    request.onsuccess=()=>resolve(request.result);
    request.onerror=()=>reject(request.error);
    request.onblocked=()=>reject(new Error('Le stockage local des images est occupé.'));
  });
}

async function access<T>(mode:IDBTransactionMode,operation:(store:IDBObjectStore)=>IDBRequest<T>){
  const db=await openStore();
  try{
    return await new Promise<T>((resolve,reject)=>{
      const transaction=db.transaction('pending',mode);
      const request=operation(transaction.objectStore('pending'));
      transaction.oncomplete=()=>resolve(request.result);
      transaction.onabort=()=>reject(transaction.error||request.error);
    });
  }finally{db.close();}
}

export function readPendingImage(key:string):Promise<PendingNoteImage|undefined>{
  if(typeof indexedDB==='undefined')return Promise.resolve(undefined);
  return access('readonly',store=>store.get(key));
}

export function rememberPendingImage(key:string,value:PendingNoteImage){
  return access('readwrite',store=>store.add(value,key));
}

export async function clearPendingImage(key:string,commandId:string){
  await access('readwrite',store=>{
    const request=store.get(key);
    request.onsuccess=()=>{if(request.result?.payload.command_id===commandId)store.delete(key);};
    return request;
  });
}
