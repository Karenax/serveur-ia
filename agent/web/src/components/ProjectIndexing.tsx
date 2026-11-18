import {useEffect,useState} from 'react';
import {request} from '../lib/http';
type Status={engine:string;model:string;server:string;compute:string;automatic:boolean;sources:number;indexed:number|null;passages:number|null;error:string|null;
  projects:{project_id:string;code:string;sources:number;indexed:number|null;passages:number|null;pending:number;failed:number;missing:number;without_text:number}[]};
export function ProjectIndexing({active=true,projectId}:{active?:boolean;projectId?:string}){
  const [status,setStatus]=useState<Status|null>(null),[error,setError]=useState('');
  useEffect(()=>{setStatus(null);setError('');},[projectId]);
  useEffect(()=>{if(!active)return;let stopped=false,pending=false,controller:AbortController|null=null,timer:ReturnType<typeof setTimeout>|undefined;
    const stop=()=>{clearTimeout(timer);timer=undefined;controller?.abort();controller=null;pending=false;};
    const read=async()=>{
      if(stopped||document.hidden||pending)return;
      controller?.abort();const current=new AbortController();controller=current;pending=true;
      try{const value=await request<Status>(`/api/v1/workspace/indexing${projectId?`?project_id=${encodeURIComponent(projectId)}`:''}`,{signal:current.signal,activity:false});
        if(!current.signal.aborted){setStatus(value);setError('');}}
      catch(cause){if(!current.signal.aborted)setError((cause as Error).message);}
      finally{if(controller===current){pending=false;if(!stopped&&!document.hidden)timer=setTimeout(()=>void read(),15000);}}
    };
    const visibility=()=>{if(document.hidden){stop();return;}clearTimeout(timer);timer=undefined;void read();};
    document.addEventListener('visibilitychange',visibility);if(!document.hidden)void read();
    return()=>{stopped=true;document.removeEventListener('visibilitychange',visibility);stop();};},[active,projectId]);
  return <section className="fusion-multimodal" aria-label="Indexation automatique des projets"><h2>Indexation automatique des projets</h2>
    <p>Quand vous classez un mail ou importez un document dans un projet, Kiara prépare automatiquement son texte pour la recherche avec EG2 sur le serveur configuré. Aucun dossier réseau n’est parcouru.</p>
    <p>Kiara indexe les passages utiles pour les retrouver dans la recherche et les réponses.</p>
    {error&&<p role="alert">{error}</p>}{status?.error&&<p role="alert">{status.error}</p>}
    {!status&&!error&&<p role="status">Vérification des index…</p>}
    {status&&<><p role="status">{status.compute==='network'?'Calcul sur le serveur réseau':'Calcul sur ce PC'} · {status.indexed??'Non vérifié'} / {status.sources} sources indexées</p>
      <div style={{overflowX:'auto'}}><table><thead><tr><th>Projet</th><th>Sources indexées</th><th>État</th></tr></thead><tbody>{status.projects.map(project=><tr key={project.project_id}><td>{project.code}</td><td>{project.indexed??'Non vérifié'} / {project.sources}</td><td>{status.error?'À vérifier':project.failed?`${project.failed} en échec`:project.pending?`${project.pending} en attente`:project.missing?`${project.missing} à compléter`:project.without_text?`${project.without_text} sans texte exploitable`:'À jour'}</td></tr>)}</tbody></table></div>
      <details><summary>Connexion EG2</summary><p>{status.model} · {status.server}</p><p>{status.passages??'Non vérifié'} passages disponibles. Seuls les contenus actuels et accessibles sont comptés.</p></details></>}
  </section>;
}
