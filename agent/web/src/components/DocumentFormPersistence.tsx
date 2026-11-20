import { useEffect, useRef, useState } from 'react';
import { documentApi, type DocumentDraft, type DocumentFormChoice, type DocumentId, type DocumentJournal, type DocumentPage } from '../lib/projectDocuments';
import { Pagination } from './IdentityPickers';
import { message } from './PlanningTasksPanel';

const normalized=(choice:DocumentFormChoice)=>JSON.stringify([choice.link_id,choice.relative_path.trim().split('\\').join('/'),
  Object.entries(choice.overrides).sort(([a],[b])=>a.localeCompare(b))]);

export function DocumentVersionHistory({active,tick,load,onRestore,canRestore,busy,fieldLabels={}}:{active:boolean;tick:number;
  load:(offset:number,signal:AbortSignal)=>Promise<DocumentPage<DocumentJournal>>;onRestore:(id:string)=>void;canRestore:boolean;busy:boolean;fieldLabels?:Record<string,string>}) {
  const [offset,setOffset]=useState(0),[page,setPage]=useState<DocumentPage<DocumentJournal>|null>(null),[error,setError]=useState(''),[loading,setLoading]=useState(false);
  const loadRef=useRef(load);loadRef.current=load;
  useEffect(()=>{setOffset(0);},[tick]);
  useEffect(()=>{if(!active)return;const controller=new AbortController();setLoading(true);setError('');
    loadRef.current(offset,controller.signal).then(value=>{if(!controller.signal.aborted)setPage(value);})
      .catch(e=>{if(!controller.signal.aborted)setError(message(e));}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    return()=>controller.abort();},[active,offset,tick]);
  return <section aria-label="Historique documentaire"><h4>Versions enregistrées</h4>
    {loading&&<p role="status">Lecture de l’historique…</p>}{error&&<p role="alert">{error}</p>}
    {page&&<><Pagination {...page} onChange={setOffset} disabled={loading||busy}/>
      <ol className="document-version-list">{page.items.map(row=><li key={row.id}><div><strong>Version {row.revision}</strong>
        <small>{new Date(row.created_at).toLocaleString('fr-FR')} · Opérateur : {row.value.actor_id}</small>
        <details><summary>Choix conservés dans cette version</summary>
          {row.value.choice&&<><p>Fichier : {row.value.choice.relative_path||'Lien direct ou non renseigné'}</p>
            {Object.entries(row.value.choice.overrides).map(([key,value])=><p key={key}>{fieldLabels[key]||key} : {value||'Vide'}</p>)}</>}
          {row.value.items?.map(item=><p key={item.document_id}>{item.label} · recherche {item.active?'active':'désactivée'} · dossiers : {item.relative_paths.join(' ou ')}</p>)}
        </details></div>{canRestore&&<button type="button" className="button secondary sm" disabled={busy||loading} onClick={()=>onRestore(row.id)}>Restaurer la version {row.revision}</button>}</li>)}</ol>
      {!page.total&&<p>Aucune version enregistrée.</p>}</>}
  </section>;
}

type Props={projectId:string;documentId:DocumentId;
  active:boolean;installed:boolean;canEdit:boolean;disabled:boolean;choice:DocumentFormChoice;onApply:(draft:DocumentDraft,initial?:boolean)=>void;
  onBusy:(busy:boolean)=>void;onDirty:(dirty:boolean)=>void;fieldLabels?:Record<string,string>};
export function DocumentFormPersistence(props:Props){return <StoredDocumentForm key={`${props.projectId}/${props.documentId}`} {...props}/>;}
function StoredDocumentForm({projectId,documentId,active,installed,canEdit,disabled,choice,onApply,onBusy,onDirty,fieldLabels={}}:Props) {
  const [saved,setSaved]=useState<DocumentDraft|null>(null),[remote,setRemote]=useState<DocumentDraft|null>(null);
  const [error,setError]=useState(''),[notice,setNotice]=useState(''),[busy,setBusy]=useState(false),[retry,setRetry]=useState(0);
  const [history,setHistory]=useState(false),[tick,setTick]=useState(0);
  const action=useRef<AbortController|null>(null),callbacks=useRef({onApply,onBusy,onDirty});callbacks.current={onApply,onBusy,onDirty};
  const initialized=useRef(false);
  const dirty=!!saved&&normalized(choice)!==normalized(saved);
  useEffect(()=>{callbacks.current.onDirty(dirty);},[dirty]);
  useEffect(()=>{callbacks.current.onBusy(busy);return()=>callbacks.current.onBusy(false);},[busy]);
  useEffect(()=>{if(!active||!installed||initialized.current)return;const controller=new AbortController();action.current=controller;setBusy(true);setError('');
    documentApi.draft(projectId,documentId,controller.signal).then(value=>{if(!controller.signal.aborted){initialized.current=true;setSaved(value);callbacks.current.onApply(value,true);}})
      .catch(e=>{if(!controller.signal.aborted)setError(message(e));}).finally(()=>{if(!controller.signal.aborted){setBusy(false);action.current=null;}});
    return()=>controller.abort();},[active,installed,projectId,documentId,retry]);
  useEffect(()=>{if(!active){action.current?.abort();setBusy(false);}},[active]);
  useEffect(()=>()=>{action.current?.abort();callbacks.current.onBusy(false);callbacks.current.onDirty(false);},[]);
  async function run(kind:'save'|'compare'|'restore',versionId?:string){if(!saved||busy||!active)return;
    if(kind==='restore'&&dirty&&!window.confirm('Restaurer cette version et remplacer les choix non enregistrés de cette trame ?'))return;
    const controller=new AbortController();action.current=controller;setBusy(true);setError('');setNotice('');
    try{const value=kind==='save'?await documentApi.saveDraft(projectId,documentId,saved.revision,choice,controller.signal):kind==='restore'?
      await documentApi.restoreDraft(projectId,documentId,saved.revision,versionId!,controller.signal):await documentApi.draft(projectId,documentId,controller.signal);
      if(controller.signal.aborted)return;
      if(kind==='compare'){setRemote(value);setNotice('Votre saisie est conservée. Comparez-la à la version enregistrée avant de choisir.');}
      else{setSaved(value);setRemote(null);callbacks.current.onApply(value);setTick(n=>n+1);setNotice(`Choix enregistrés · version ${value.revision}.`);}}
    catch(e){if(!controller.signal.aborted)setError(message(e));}
    finally{if(action.current===controller){setBusy(false);action.current=null;}}}
  if(!installed)return <p className="document-help">Les choix restent dans cette vue. La sauvegarde documentaire sera disponible après activation du lot.</p>;
  return <section className="document-saved-form" aria-label="Sauvegarde des choix documentaires">
    <p role="status">{busy?'Lecture ou enregistrement des choix…':saved?`Version enregistrée : ${saved.revision}${dirty?' · modifications à enregistrer':''}`:'Lecture du formulaire…'}</p>
    {saved?.warnings.includes('selected_link_missing')&&<p className="document-warning">Le lien enregistré n’existe plus dans ce projet. Choisissez un lien actuel avant de préparer ou restaurer cette trame.</p>}
    {error&&<p role="alert">{error} Votre saisie est conservée.</p>}
    {!saved&&error&&<button className="button secondary" type="button" disabled={busy||!active} onClick={()=>setRetry(n=>n+1)}>Réessayer la lecture du formulaire</button>}
    {saved&&<div className="document-actions">{canEdit&&<button className="button secondary" type="button" disabled={busy||disabled||!active||!saved.available||!dirty}
      onClick={()=>void run('save')}>Enregistrer les choix</button>}
      <button className="button secondary" type="button" disabled={busy||disabled||!active} onClick={()=>void run('compare')}>Comparer avec la version enregistrée</button>
      <button className="button secondary" type="button" disabled={busy||!active} aria-expanded={history} onClick={()=>setHistory(v=>!v)}>Historique des choix</button></div>}
    {remote&&<section aria-label="Version enregistrée à comparer"><h4>Version serveur {remote.revision}</h4><p>Lien : {remote.selected_link?.label||(remote.link_id?'Lien absent':'Non renseigné')} · fichier : {remote.relative_path||'Non renseigné'}</p>
      {Object.entries(remote.overrides).map(([key,value])=><p key={key}>{fieldLabels[key]||key} : {value||'Vide'}</p>)}
      <button className="button secondary" type="button" disabled={busy||!active} onClick={()=>{setSaved(remote);callbacks.current.onApply(remote);setRemote(null);setError('');setTick(n=>n+1);setNotice('Version enregistrée chargée.');}}>Charger cette version et remplacer ma saisie</button></section>}
    {notice&&<p role="status">{notice}</p>}
    {history&&<DocumentVersionHistory active={active} tick={tick} load={(offset,signal)=>documentApi.draftHistory(projectId,documentId,offset,signal)}
      onRestore={id=>void run('restore',id)} canRestore={canEdit} busy={busy||disabled} fieldLabels={fieldLabels}/>}
  </section>;
}
