import { useEffect, useRef, useState } from 'react';
import { documentApi, sharedDocumentPreferences, type DocumentPreferences, type DocumentSearchItem } from '../lib/projectDocuments';
import { DocumentVersionHistory } from './DocumentFormPersistence';
import { message } from './PlanningTasksPanel';
import './project-documents.css';

export function DocumentSettings({active,onBusy,shared=false}:{active:boolean;onBusy:(busy:boolean)=>void;shared?:boolean}) {
  const preferencesApi=shared?sharedDocumentPreferences:documentApi;
  const [saved,setSaved]=useState<DocumentPreferences|null>(null),[items,setItems]=useState<DocumentSearchItem[]>([]);
  const [remote,setRemote]=useState<DocumentPreferences|null>(null),[error,setError]=useState(''),[notice,setNotice]=useState('');
  const [busy,setBusy]=useState(false),[history,setHistory]=useState(false),[tick,setTick]=useState(0),[retry,setRetry]=useState(0);
  const initialized=useRef(false),action=useRef<AbortController|null>(null),busyCallback=useRef(onBusy);busyCallback.current=onBusy;
  const dirty=!!saved&&JSON.stringify(items)!==JSON.stringify(saved.items);
  const canEdit=saved?.can_edit!==false;
  useEffect(()=>{busyCallback.current(busy);return()=>busyCallback.current(false);},[busy]);
  useEffect(()=>{if(!active||initialized.current)return;const controller=new AbortController();action.current=controller;setBusy(true);setError('');
    preferencesApi.preferences(controller.signal).then(value=>{if(!controller.signal.aborted){initialized.current=true;setSaved(value);setItems(value.items);}})
      .catch(e=>{if(!controller.signal.aborted)setError(message(e));}).finally(()=>{if(!controller.signal.aborted){setBusy(false);action.current=null;}});
    return()=>controller.abort();},[active,retry,preferencesApi]);
  useEffect(()=>{if(!active){action.current?.abort();setBusy(false);}},[active]);
  useEffect(()=>()=>{action.current?.abort();busyCallback.current(false);},[]);
  const edit=(id:string,changes:Partial<DocumentSearchItem>)=>{setItems(previous=>previous.map(item=>item.document_id===id?{...item,...changes}:item));setNotice('');};
  async function run(kind:'save'|'compare'|'restore',versionId?:string){if(!saved||!canEdit||busy||!active)return;
    if(kind==='restore'&&dirty&&!window.confirm('Restaurer cette version et remplacer les réglages non enregistrés ?'))return;
    const controller=new AbortController();action.current=controller;setBusy(true);setError('');setNotice('');
    const prepared=items.map(item=>({...item,relative_paths:item.relative_paths.map(v=>v.trim()).filter(Boolean),
      filename_patterns:item.filename_patterns.map(v=>v.trim()).filter(Boolean),excluded_tokens:item.excluded_tokens.map(v=>v.trim()).filter(Boolean)}));
    try{const value=kind==='save'?await preferencesApi.savePreferences(saved.revision,prepared,controller.signal):kind==='restore'?
      await preferencesApi.restorePreferences(saved.revision,versionId!,controller.signal):await preferencesApi.preferences(controller.signal);
      if(controller.signal.aborted)return;
      if(kind==='compare'){setRemote(value);setNotice('Vos réglages sont conservés. Choisissez explicitement la version à utiliser.');}
      else{setSaved(value);setItems(value.items);setRemote(null);setTick(n=>n+1);setNotice(`Réglages enregistrés · version ${value.revision}.`);}}
    catch(e){if(!controller.signal.aborted)setError(message(e));}
    finally{if(action.current===controller){setBusy(false);action.current=null;}}}
  return <section className="project-documents" aria-label="Réglages documentaires" data-workspace-dirty={dirty?'true':undefined}>
    <header className="planning-heading"><div><h2>{shared?'Critères par défaut des trames':'Trames et recherches documentaires'}</h2>
      <p>{shared?'Ces critères s’appliquent aux comptes qui n’ont pas enregistré leurs propres critères.':'Définissez les noms, dossiers et indices de vos recherches. Vos critères personnels s’appliquent dans tous vos projets accessibles.'}</p></div></header>
    {busy&&<p role="status">Lecture ou enregistrement des réglages…</p>}
    {error&&<p role="alert">{error}{saved?' Vos réglages saisis sont conservés.':''}</p>}
    {!saved&&error&&<button className="button secondary" type="button" disabled={busy||!active} onClick={()=>setRetry(n=>n+1)}>Réessayer les réglages documentaires</button>}
    {saved&&<><p>{!shared&&saved.revision===0?'Critères par défaut de l’espace de travail':`Version enregistrée · ${saved.revision}`}{dirty?' · modifications à enregistrer':''}</p>
      {!saved.available&&<p className="document-warning">{shared
        ? 'L’installation documentaire protégée doit être activée avant d’enregistrer ces réglages.'
        : 'Le service Kiara ne peut pas encore enregistrer vos critères personnels.'}</p>}
      {!canEdit&&<p role="status">Vous pouvez consulter les critères communs. Le propriétaire de Kiara peut les modifier.</p>}
      <form onSubmit={e=>{e.preventDefault();void run('save');}} aria-label={canEdit?"Modifier les recherches des trames":"Consulter les recherches des trames"}>
        <fieldset disabled={busy||!active||!canEdit}><legend>{shared?'Critères par défaut':'Mes critères de recherche'}</legend><p className="document-help">Un critère par ligne. Les mots d’un nom sont tous requis. Chaque ligne propose une alternative. Les dossiers sont relatifs au lien choisi dans le projet.</p>
          {items.map(item=><fieldset className="document-setting" key={item.document_id}><legend>{item.label||item.document_id} · {item.format}</legend>
            <div className="document-field-grid"><label>Libellé<input className="input" required maxLength={255} value={item.label} onChange={e=>edit(item.document_id,{label:e.target.value})}/></label>
              <label>Ordre<input className="input" type="number" min={0} max={10000} step={1} required value={item.order} onChange={e=>edit(item.document_id,{order:Number(e.target.value)})}/></label>
              <label>Dossiers relatifs<textarea className="input" rows={3} value={item.relative_paths.join('\n')} onChange={e=>edit(item.document_id,{relative_paths:e.target.value.split('\n')})}/></label>
              <label>Mots du nom<textarea className="input" rows={3} value={item.filename_patterns.join('\n')} onChange={e=>edit(item.document_id,{filename_patterns:e.target.value.split('\n')})}/></label>
              <label>Exclusions<textarea className="input" rows={2} value={item.excluded_tokens.join('\n')} onChange={e=>edit(item.document_id,{excluded_tokens:e.target.value?e.target.value.split('\n'):[]})}/></label>
              <label>Indice préféré<input className="input" type="number" min={0} max={999} step={1} value={item.preferred_version??''} onChange={e=>edit(item.document_id,{preferred_version:e.target.value===''?null:Number(e.target.value)})}/></label>
              <label className="document-confirm"><input type="checkbox" checked={item.active} onChange={e=>edit(item.document_id,{active:e.target.checked})}/>Rechercher cette trame</label></div>
          </fieldset>)}
        </fieldset>{canEdit&&<div className="document-actions"><button className="button primary" type="submit" disabled={busy||!active||!dirty||!saved.available}>Enregistrer les réglages</button>
          <button className="button secondary" type="button" disabled={busy||!active} onClick={()=>void run('compare')}>Comparer avec les réglages enregistrés</button>
          <button className="button secondary" type="button" disabled={busy||!active} aria-expanded={history} onClick={()=>setHistory(v=>!v)}>Historique des réglages</button></div>}
      </form>
      {canEdit&&remote&&<section aria-label="Réglages enregistrés à comparer"><h3>Version serveur {remote.revision}</h3>
        {remote.items.map(item=><p key={item.document_id}>{item.label} · dossiers : {item.relative_paths.join(' ou ')} · noms : {item.filename_patterns.join(' ou ')}</p>)}
        <button className="button secondary" type="button" disabled={busy||!active} onClick={()=>{setSaved(remote);setItems(remote.items);setRemote(null);setError('');setTick(n=>n+1);setNotice('Réglages enregistrés chargés.');}}>Charger cette version et remplacer mes réglages</button></section>}
      {canEdit&&history&&<DocumentVersionHistory active={active} tick={tick} load={preferencesApi.preferencesHistory}
        onRestore={id=>void run('restore',id)} canRestore={saved.available} busy={busy}/>}
    </>}{notice&&<p role="status">{notice}</p>}
  </section>;
}
