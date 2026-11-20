import { useEffect, useRef, useState } from 'react';
import { documentApi, type DocumentWorkspace } from '../lib/projectDocuments';
import { publicationApi, publicationBlockerLabel, publicationStateLabel, pendingKey, readPending,
  type PublicationChoice, type PublicationCommand, type PublicationPreview, type Publications, type PublicationRecord } from '../lib/projectDocumentPublications';
import { Pagination } from './IdentityPickers';
import { message, useAlive } from './PlanningTasksPanel';

type Props={projectId:string;jobId:string;revision:number;artifactId:string;label:string;active:boolean;canEdit:boolean;
  executionBlocked:boolean;jobActive:boolean;disabled:boolean;onBusy:(value:boolean)=>void;onDirty:(value:boolean)=>void;onChanged:()=>void;
  suggestion?:PublicationChoice|null};
const empty:PublicationChoice={link_id:'',relative_directory:'',replace_existing:false};
export function DocumentPublicationPanel(props:Props){
  const {projectId,jobId,artifactId,revision,active,canEdit,executionBlocked,jobActive,disabled,onBusy,onDirty,onChanged}=props;
  const [choice,setChoice]=useState<PublicationChoice>(props.suggestion||empty),[preview,setPreview]=useState<PublicationPreview|null>(null),[reviewed,setReviewed]=useState(false);
  const [pending,setPending]=useState<PublicationCommand|null>(null),[localError,setLocalError]=useState('');
  const [links,setLinks]=useState<DocumentWorkspace['links']|null>(null),[linkOffset,setLinkOffset]=useState(0),[linkLabel,setLinkLabel]=useState('');
  const [history,setHistory]=useState<Publications|null>(null),[offset,setOffset]=useState(0),[tick,setTick]=useState(0);
  const [error,setError]=useState(''),[readError,setReadError]=useState(''),[notice,setNotice]=useState(''),[busy,setBusy]=useState(false);
  const [ack,setAck]=useState<string|null>(null);
  const [linkToProject,setLinkToProject]=useState(!!props.suggestion);
  const action=useRef<AbortController|null>(null),alive=useAlive();
  const editable=canEdit&&!executionBlocked&&!jobActive;
  const locked=disabled||busy||!active;
  const suggested=props.suggestion||empty;
  const dirty=!!pending||!!localError||!!preview||choice.link_id!==suggested.link_id||
    choice.relative_directory!==suggested.relative_directory||choice.replace_existing!==suggested.replace_existing;
  useEffect(()=>{try{setPending(readPending(projectId,artifactId));}catch(e){setLocalError(message(e));}},[projectId,artifactId]);
  useEffect(()=>{onDirty(dirty);},[dirty,onDirty]);
  useEffect(()=>()=>{action.current?.abort();onBusy(false);onDirty(false);},[onBusy,onDirty]);
  useEffect(()=>{if(!active){action.current?.abort();setBusy(false);onBusy(false);}},[active,onBusy]);
  useEffect(()=>{if(!active||!editable)return;const controller=new AbortController();
    documentApi.workspace(projectId,linkOffset,controller.signal).then(value=>{if(!controller.signal.aborted)setLinks(value.links);})
      .catch(e=>{if(!controller.signal.aborted)setError(message(e));});return()=>controller.abort();
  },[projectId,linkOffset,active,editable]);
  useEffect(()=>{if(!active)return;let stopped=false,loading=false,controller:AbortController|null=null,timer:number|undefined;
    const stop=()=>{window.clearTimeout(timer);timer=undefined;controller?.abort();controller=null;loading=false;};
    async function refresh(quiet=false){
      if(stopped||document.hidden||loading)return;
      controller?.abort();const current=new AbortController();controller=current;loading=true;let delay=5000;
      try{const value=await (quiet?publicationApi.list(projectId,jobId,artifactId,offset,current.signal,true):publicationApi.list(projectId,jobId,artifactId,offset,current.signal));
        if(current.signal.aborted)return;setHistory(previous=>previous&&previous.job_revision>value.job_revision?previous:value);setReadError('');
      }catch(e){if(!current.signal.aborted){setReadError(message(e));delay=10_000;}}
      finally{if(controller===current){loading=false;if(!stopped&&!document.hidden)timer=window.setTimeout(()=>void refresh(true),delay);}}
    }
    const visibility=()=>{if(document.hidden){stop();return;}window.clearTimeout(timer);timer=undefined;void refresh(true);};
    document.addEventListener('visibilitychange',visibility);if(!document.hidden)void refresh();
    return()=>{stopped=true;document.removeEventListener('visibilitychange',visibility);stop();};
  },[projectId,jobId,artifactId,active,offset,tick,revision]);
  useEffect(()=>{if(!pending||!history)return;const known=history.items.find(row=>row.command_id===pending.command_id);
    if(known&&['succeeded','abandoned'].includes(known.state)){
      try{localStorage.removeItem(pendingKey(projectId,artifactId));setPending(null);setChoice(suggested);setPreview(null);setReviewed(false);}
      catch(e){setLocalError(message(e));}
    }
  },[pending,history,projectId,artifactId,suggested]);
  function change(value:PublicationChoice){setChoice(value);setPreview(null);setReviewed(false);setError('');setNotice('');}
  async function run(fn:(signal:AbortSignal)=>Promise<void>){if(action.current||locked||!editable)return;
    const controller=new AbortController();action.current=controller;setBusy(true);onBusy(true);setError('');setNotice('');
    try{await fn(controller.signal);}catch(e){if(alive.current&&!controller.signal.aborted)setError(message(e));}
    finally{if(alive.current&&action.current===controller){action.current=null;setBusy(false);onBusy(false);setTick(value=>value+1);onChanged();}}}
  const current=(signal:AbortSignal)=>alive.current&&!signal.aborted;
  async function inspect(){await run(async signal=>{const value=await publicationApi.preview(projectId,jobId,artifactId,choice,signal);
    if(current(signal)){setPreview(value);setReviewed(false);}});}
  async function send(command:PublicationCommand){await run(async signal=>{
    // Store synchronously BEFORE the request. If storage fails, nothing is sent.
    localStorage.setItem(pendingKey(projectId,artifactId),JSON.stringify(command));setPending(command);
    const value=await publicationApi.publish(projectId,jobId,artifactId,command,signal);
    if(!current(signal))return;
    if(value.state==='succeeded'){localStorage.removeItem(pendingKey(projectId,artifactId));setPending(null);setChoice(suggested);setPreview(null);setReviewed(false);}
    setNotice(value.state==='succeeded'?(command.link_to_project?'Fichier publié et ajouté aux liens du projet.':'Reçu de publication enregistré. Les sauvegardes éventuelles sont conservées.'):'Relisez le reçu avant de poursuivre.');setOffset(0);
  });}
  function start(){if(!preview||!reviewed||!preview.can_publish||!preview.publication_command_available||pending||localError)return;
    void send({...choice,command_id:crypto.randomUUID(),expected_revision:preview.job_revision,expected_preview_sha256:preview.preview_sha256,
      reviewed:true,...(linkToProject?{link_to_project:true}:{})});}
  async function closeUncertain(row:PublicationRecord){if(!history||ack!==row.command_id||!row.can_abandon)return;
    const expected=history.job_revision;
    await run(async signal=>{const result=await publicationApi.abandon(projectId,jobId,artifactId,row.command_id,
      {expected_revision:expected,retain_files:true,reviewed:true},signal);
      if(!current(signal))return;
      if(pending?.command_id===row.command_id){localStorage.removeItem(pendingKey(projectId,artifactId));setPending(null);}
      setAck(null);setPreview(null);setReviewed(false);setNotice('Commande clôturée. Tous les fichiers restent conservés ; un nouvel aperçu est nécessaire.');
      setHistory(previous=>previous?{...previous,job_revision:result.job_revision,items:previous.items.map(item=>item.command_id===result.command_id?result:item)}:previous);
    });}
  function forgetLocal(){if(locked||!history||readError)return;
    if(!window.confirm('Cette action abandonne seulement la répétition locale. La publication peut déjà être enregistrée. Consultez les reçus et clôturez toute intention incertaine avant une nouvelle publication. Continuer ?'))return;
    try{localStorage.removeItem(pendingKey(projectId,artifactId));setPending(null);setLocalError('');setPreview(null);setReviewed(false);}
    catch(e){setError(message(e));}}
  return <section className="document-publication" aria-label={`Publication de ${props.label}`} data-workspace-dirty={dirty?'true':undefined}
    data-workspace-busy={busy?'true':undefined}>
    <h4>Publication · {props.label}</h4><p>Choisir un dossier du projet, relire la destination puis enregistrer la copie. Chaque publication garde un reçu.</p>
    {!editable&&<p className="document-help">{executionBlocked?'Historique importé ou restauré : consultation uniquement.':jobActive?'La publication sera disponible quand le lot sera terminé ou interrompu.':'Consultation uniquement.'}</p>}
    {editable&&!pending&&!localError&&<><div className="document-publication-fields">
      <label>Lien de destination<select className="input" value={choice.link_id} disabled={locked} onChange={e=>{
        setLinkLabel(links?.items.find(row=>row.id===e.target.value)?.label||e.target.value);change({...choice,link_id:e.target.value});}}>
        <option value="">Choisir un lien du projet</option>
        {choice.link_id&&!links?.items.some(row=>row.id===choice.link_id)&&<option value={choice.link_id}>{linkLabel} · sélection conservée</option>}
        {links?.items.map(row=><option value={row.id} key={row.id}>{row.label||row.code} · {row.path}</option>)}</select></label>
      <label>Sous-dossier existant<input className="input" value={choice.relative_directory} disabled={locked} maxLength={2048}
        placeholder="Vide pour le dossier du lien" onChange={e=>change({...choice,relative_directory:e.target.value})}/></label>
    </div>{links&&<Pagination {...links} disabled={locked} onChange={setLinkOffset}/>}
    <label className="document-review"><input type="checkbox" checked={choice.replace_existing} disabled={locked}
      onChange={e=>change({...choice,replace_existing:e.target.checked})}/>Remplacer le fichier existant en conservant une sauvegarde de l’original</label>
    <button type="button" className="button secondary" disabled={locked||!choice.link_id} onClick={()=>void inspect()}>Vérifier la destination</button>
    {preview&&<div className="document-publication-review"><strong>{preview.filename}</strong><p className="document-path">{preview.destination}</p>
      {preview.existing_receipt&&<p>Original à conserver : {(preview.existing_receipt.size_bytes/1024).toFixed(1)} Ko. Sa sauvegarde restera dans ce dossier.</p>}
      {preview.blockers.map(code=><p className="document-warning" key={code}>{publicationBlockerLabel(code)}</p>)}
      {!preview.publication_command_available&&<p className="document-warning">La publication n’est pas disponible sur cette version du serveur.</p>}
      <label className="document-review"><input type="checkbox" checked={linkToProject} disabled={locked||!preview.can_publish}
        onChange={e=>setLinkToProject(e.target.checked)}/>Ajouter ou actualiser le lien dans « Fichiers et dossiers »</label>
      <label className="document-review"><input type="checkbox" checked={reviewed} disabled={locked||!preview.can_publish} onChange={e=>setReviewed(e.target.checked)}/>
        J’ai relu la destination{choice.replace_existing?' et je confirme le remplacement avec sauvegarde de l’original':''}</label>
      <button type="button" className="button primary" disabled={locked||!reviewed||!preview.can_publish||!preview.publication_command_available} onClick={start}>
        {choice.replace_existing?'Sauvegarder l’original et publier':'Publier la copie'}</button></div>}</>}
    {pending&&<div className="document-warning"><p>Une commande est mémorisée. Après réponse perdue, répétez cette même demande pour vérifier son reçu et éviter une nouvelle publication.</p>
      <p>Sous-dossier : {pending.relative_directory||'dossier du lien'}{pending.replace_existing?' · remplacement avec sauvegarde':''}</p>
      {editable&&<button type="button" className="button primary" disabled={locked||!!localError} onClick={()=>void send(pending)}>Réessayer la même publication</button>}
    </div>}
    {localError&&<p role="alert" className="document-warning">{localError}</p>}
    {(pending||localError)&&editable&&<button type="button" className="button secondary" disabled={locked||!history||!!readError} onClick={forgetLocal}>Abandonner la répétition locale après vérification</button>}
    {busy&&<div className="document-actions"><p role="status" className="document-searching">Vérification ou enregistrement de la publication…</p>
      <button className="button secondary sm" type="button" onClick={()=>{action.current?.abort();setNotice('Attente interrompue. La commande peut continuer sur le serveur ; consultez les reçus ou répétez la même demande.');}}>Interrompre l’attente de publication</button></div>}
    {error&&<p role="alert" className="document-warning">{error}</p>}{notice&&<p role="status">{notice}</p>}
    {readError&&<p role="alert" className="document-warning">{readError} <button type="button" className="button secondary sm" onClick={()=>setTick(value=>value+1)}>Relire les reçus</button></p>}
    <h5>Reçus de cette copie</h5>{history&&!history.total&&<p>Aucune publication enregistrée pour cette copie.</p>}
    {history&&<><ul className="document-publication-history">{history.items.map(row=><li key={row.command_id}><strong>{publicationStateLabel(row.state)}</strong>
      <p className="document-path">{row.destination}</p>{row.backup&&<p>Sauvegarde conservée : <span className="document-path">{row.backup}</span></p>}
      {row.state==='succeeded'&&<p className="document-help">Reçu historique de succès ; le fichier réseau n’est pas revérifié lors de cette consultation.</p>}
      {row.needs_inspection&&<p className="document-warning">Aucun reçu préparé durable. Vérifiez la situation ; le candidat est conservé et ne sera pas adopté automatiquement.</p>}
      <details><summary>Preuves et fichier préparé</summary><p className="document-path">{row.candidate}</p>
        {row.receipt&&<p className="document-path">SHA-256 : {row.receipt.sha256}</p>}
        {row.backup_receipt&&<p className="document-path">Original : {row.backup_receipt.sha256}</p>}</details>
      {editable&&row.can_resume&&<button type="button" className="button secondary sm" disabled={locked||!!readError||!!localError||!!pending&&pending.command_id!==row.command_id}
        onClick={()=>void send(row.command)}>{row.state==='succeeded'?'Revérifier le reçu et les fichiers':'Reprendre cette publication'}</button>}
      {editable&&row.can_abandon&&<div><label className="document-review"><input type="checkbox" checked={ack===row.command_id} disabled={locked||!!readError}
        onChange={e=>setAck(e.target.checked?row.command_id:null)}/>Je confirme la clôture de cette intention en conservant tous les fichiers</label>
        <button type="button" className="button secondary sm" disabled={locked||!!readError||ack!==row.command_id} onClick={()=>void closeUncertain(row)}>Clôturer l’intention incertaine</button></div>}
    </li>)}</ul><Pagination {...history} disabled={locked} onChange={setOffset}/></>}
  </section>;
}
