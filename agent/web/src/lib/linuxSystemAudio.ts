import {agentFetch} from './agentRoutes';

const path='/api/v1/kiara/linux-system-audio';
export const linuxSystemAudioAvailable=()=>document.body.dataset.kiaraLinuxSystemAudio==='true';

async function command(action:'start'|'stop',leaseId:string):Promise<Record<string,unknown>>{
  const controller=new AbortController();
  const timeout=window.setTimeout(()=>controller.abort(),30_000);
  try {
    // Local relay authorization uses its same-origin cookie. It must remain
    // possible to release the source when the remote server is offline.
    const response=await agentFetch(path,{method:'POST',credentials:'same-origin',signal:controller.signal,
      headers:{'Content-Type':'application/json'},body:JSON.stringify({action,lease_id:leaseId})});
    const value=await response.json();
    if(!response.ok)throw new Error(typeof value?.detail==='string'?value.detail:'Boucle audio indisponible.');
    if(!value||typeof value!=='object'||Array.isArray(value))throw new Error('Réponse audio locale invalide.');
    return value;
  } finally {window.clearTimeout(timeout);}
}

export const linuxSystemAudio={
  available:linuxSystemAudioAvailable,
  start:(leaseId:string)=>command('start',leaseId),
  stop:(leaseId:string)=>command('stop',leaseId),
};
