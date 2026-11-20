import { useCallback, useEffect, useRef, useState } from 'react';
import { documentApi, type DocumentChoice, type DocumentPage, type DocumentPreview, type DocumentTemplate } from '../lib/projectDocuments';
import { documentJobApi, documentJobLabel, documentEventLabel, type BatchCommand, type BatchItem,
  type DocumentJob, type DocumentJobs, type DocumentEvent, type DocumentAttempt } from '../lib/projectDocumentJobs';
import { Pagination } from './IdentityPickers';
import { useAlive, message } from './PlanningTasksPanel';
import { DocumentPublicationPanel } from './DocumentPublicationPanel';
import type { PublicationChoice } from '../lib/projectDocumentPublications';

type Selection={item:BatchItem;label:string;filename:string};
type Props={projectId:string;active:boolean;canEdit:boolean;disabled:boolean;choice:DocumentChoice|null;
  preview:DocumentPreview|null;reviewed:boolean;templates:DocumentTemplate[];onBusy:(value:boolean)=>void};
export function DocumentBatchPanel({projectId,active,canEdit,disabled,choice,preview,reviewed,templates,onBusy}:Props) {
  const [pool,setPool]=useState<Selection[]>([]),[pending,setPending]=useState<BatchCommand|null>(null);
  const [jobs,setJobs]=useState<DocumentJobs|null>(null),[offset,setOffset]=useState(0),[selected,setSelected]=useState<string|null>(null);
  const [detail,setDetail]=useState<DocumentJob|null>(null),[tick,setTick]=useState(0),[busy,setBusy]=useState<string|null>(null);
  const [error,setError]=useState(''),[readError,setReadError]=useState(''),[notice,setNotice]=useState('');
  const [journal,setJournal]=useState(false),[eventOffset,setEventOffset]=useState(0),[attemptOffset,setAttemptOffset]=useState(0);
  const [events,setEvents]=useState<DocumentPage<DocumentEvent>|null>(null),[attempts,setAttempts]=useState<DocumentPage<DocumentAttempt>|null>(null);
  const [download,setDownload]=useState<{url:string;name:string;sha256:string}|null>(null);
  const [publication,setPublication]=useState<{artifactId:string;label:string;suggestion?:PublicationChoice|null}|null>(null),[publicationBusy,setPublicationBusy]=useState(false),[publicationDirty,setPublicationDirty]=useState(false);
  const publicationChanged=useCallback(()=>setTick(value=>value+1),[]);
  useEffect(()=>{onBusy(!!busy||publicationBusy);},[busy,publicationBusy,onBusy]);
  const action=useRef<AbortController|null>(null),alive=useAlive();
  useEffect(()=>()=>action.current?.abort(),[]);
  useEffect(()=>{if(!active){action.current?.abort();setBusy(null);onBusy(false);}},[active,onBusy]);
  useEffect(()=>{if(!active)return;let stopped=false,loading=false,controller:AbortController|null=null,timer:number|undefined;
    const stop=()=>{window.clearTimeout(timer);timer=undefined;controller?.abort();controller=null;loading=false;};
    async function refresh(quiet=false){
      if(stopped||document.hidden||loading)return;
      const request=new AbortController();controller=request;loading=true;let delay=10_000;
      try{const value=await (quiet?documentJobApi.list(projectId,offset,request.signal,true):documentJobApi.list(projectId,offset,request.signal));
        if(request.signal.aborted)return;
        const current=selected?await (quiet?documentJobApi.detail(projectId,selected,request.signal,true):documentJobApi.detail(projectId,selected,request.signal)):null;
        if(request.signal.aborted)return;setJobs(value);setReadError('');if(current)setDetail(previous=>
          previous?.id===current.id&&previous.revision>current.revision?previous:current);
        delay=value.items.some(row=>['queued','running'].includes(row.status))||
          current&&['queued','running'].includes(current.status)?2000:10_000;
      }catch(e){if(!request.signal.aborted)setReadError(message(e));}
      finally{if(controller===request){loading=false;if(!stopped&&!document.hidden)timer=window.setTimeout(()=>void refresh(true),delay);}}
    }
    const visibility=()=>{if(document.hidden){stop();return;}window.clearTimeout(timer);timer=undefined;void refresh(true);};
    document.addEventListener('visibilitychange',visibility);if(!document.hidden)void refresh();
    return()=>{stopped=true;document.removeEventListener('visibilitychange',visibility);stop();};
  },[projectId,active,offset,selected,tick]);
  useEffect(()=>{if(!active||!selected||!journal)return;const controller=new AbortController();
    Promise.all([documentJobApi.events(projectId,selected,eventOffset,controller.signal),
      documentJobApi.attempts(projectId,selected,attemptOffset,controller.signal)]).then(([e,a])=>{
        if(!controller.signal.aborted){setEvents(e);setAttempts(a);}}).catch(e=>{if(!controller.signal.aborted)setError(message(e));});
    return()=>controller.abort();},[projectId,active,selected,journal,eventOffset,attemptOffset,detail?.revision]);
  function choose(id:string){if(busy||publicationBusy)return;if(publicationDirty&&!window.confirm('Quitter la publication en cours de préparation ? Les commandes mémorisées restent conservées.'))return;
    setPublication(null);setSelected(id);setDetail(null);setEvents(null);setAttempts(null);setEventOffset(0);setAttemptOffset(0);setDownload(null);setError('');}
  async function execute(name:string,fn:(signal:AbortSignal)=>Promise<void>){if(action.current||busy||publicationBusy||!active)return;
    const controller=new AbortController();action.current=controller;setBusy(name);onBusy(true);setError('');setNotice('');
    try{await fn(controller.signal);}catch(e){if(alive.current&&!controller.signal.aborted)setError(message(e));}
    finally{if(alive.current&&action.current===controller){setBusy(null);action.current=null;onBusy(false);}}
  }
  async function add(){if(!choice||!preview||!reviewed||!preview.can_prepare||!preview.can_prepare_copy||!canEdit||pending)return;
    const captured=structuredClone(choice),approved=preview;
    await execute('selection',async signal=>{
      if(approved.source.project_id!==projectId||approved.document_id!==captured.document_id||
        approved.source.link_id!==captured.link_id||approved.source.relative_path!==captured.relative_path)
        throw new Error('La sélection ne correspond plus à l’aperçu vérifié. Affichez un nouvel aperçu.');
      const draft=await documentApi.draft(projectId,captured.document_id,signal);
      if(signal.aborted||!alive.current)return;
      const selection:Selection={item:{...captured,expected_draft_revision:draft.revision,
        expected_source_sha256:approved.source_sha256,expected_link_sha256:approved.link_sha256,expected_values_sha256:approved.values_sha256,
        expected_identity_revision:approved.field_values.identity_revision,expected_planning_revision:approved.field_values.planning_revision},
        label:templates.find(row=>row.id===captured.document_id)?.label||captured.document_id,filename:approved.output_filename||approved.source.filename};
      setPool(previous=>[...previous.filter(row=>row.item.document_id!==captured.document_id),selection]);
      setNotice('Trame vérifiée ajoutée au lot. Vous pouvez choisir et vérifier la suivante.');
    });
  }
  async function submit(){if(!pool.length||!canEdit||!jobs?.worker.can_submit||readError)return;
    const command=pending||{command_id:crypto.randomUUID(),items:pool.map(row=>structuredClone(row.item))};
    setPending(command);
    await execute('submit',async signal=>{const result=await documentJobApi.submit(projectId,command,signal);
      if(signal.aborted||!alive.current)return;setPool([]);setPending(null);setSelected(result.id);setDetail(result);setOffset(0);
      setEvents(null);setAttempts(null);setEventOffset(0);setAttemptOffset(0);setDownload(null);
      setTick(value=>value+1);setNotice('Lot enregistré. Le traitement se poursuit sur le serveur.');});
  }
  async function command(kind:'cancel'|'retry'){if(!detail||!canEdit||readError||kind==='retry'&&!jobs?.worker.can_submit)return;
    const expected=detail;
    await execute(kind,async signal=>{try{const result=await documentJobApi[kind](projectId,expected,signal);
        if(signal.aborted||!alive.current)return;setDetail(result);setTick(value=>value+1);
        setNotice(kind==='cancel'?'Arrêt demandé. La lecture système en cours peut finir.':'Reprise demandée ; les copies réussies sont conservées.');
      }catch(e){if(alive.current&&!signal.aborted)setTick(value=>value+1);throw e;}});
  }
  async function file(artifactId:string){await execute('download',async signal=>{
    const result=await documentJobApi.download(projectId,artifactId,signal);
    if(!signal.aborted&&alive.current)setDownload({url:result.url,name:result.filename,sha256:result.sha256});});}
  const unavailable=disabled||!!busy||publicationBusy||!active,replace=pool.some(row=>row.item.document_id===choice?.document_id);
  const addReady=!unavailable&&!pending&&canEdit&&reviewed&&preview?.can_prepare&&preview.can_prepare_copy&&choice&&(replace||pool.length<8);
  const label=(doc:string)=>templates.find(row=>row.id===doc)?.label||doc;
  const state=jobs?.worker.state;
  return <section className="document-batch" aria-label="Préparation par lot" data-workspace-dirty={pool.length?'true':undefined} data-workspace-busy={busy?'true':undefined}>
    <header className="planning-heading"><div><h3>Préparation par lot</h3><p>Réunir les trames vérifiées puis suivre chaque copie, même après une interruption.</p></div>
      <span className={`document-worker ${jobs?.worker.can_submit?'ready':''}`}>{jobs?.worker.can_submit?'Traitement disponible':
        state==='lease_busy'?'Traitement pris en charge par une autre instance':state==='disabled'?'Traitement désactivé':'Traitement indisponible'}</span></header>
    {jobs?.worker.error&&<p className="document-warning">{jobs.worker.error}</p>}
    {canEdit&&<><button type="button" className="button secondary" disabled={!addReady} onClick={()=>void add()}>
      {replace?'Remplacer cette trame dans le lot':'Ajouter la trame vérifiée au lot'}</button>
      {!reviewed&&<p className="document-help">Affichez l’aperçu et confirmez les informations avant d’ajouter une trame.</p>}
      <h4>{pool.length} / 8 trame(s) sélectionnée(s)</h4>
      {!!pool.length&&<ul className="document-batch-selections">{pool.map(row=><li key={row.item.document_id}><div><strong>{row.label}</strong>
        <small>{row.filename}</small><small>{row.item.relative_path||'Fichier désigné par le lien'}</small></div>
        <button type="button" className="button secondary sm" disabled={unavailable||!!pending} onClick={()=>setPool(value=>value.filter(item=>item!==row))}
          aria-label={`Retirer ${row.label} du lot`}>Retirer</button></li>)}</ul>}
      {pending&&<p className="document-warning">La soumission peut déjà avoir été enregistrée. Réessayez avec la même commande pour éviter un doublon.
        Pour modifier les trames, abandonnez explicitement cette soumission puis vérifiez l’historique des lots.</p>}
      <div className="document-actions"><button type="button" className="button primary" disabled={unavailable||!pool.length||!jobs?.worker.can_submit||!!readError}
        onClick={()=>void submit()}>{pending?'Réessayer la même soumission':`Lancer le lot de ${pool.length} fichier(s)`}</button>
        {!!pool.length&&<button type="button" className="button secondary" disabled={unavailable} onClick={()=>{
          if(pending&&!window.confirm('La soumission peut être enregistrée. Abandonner sa répétition et vérifier l’historique avant un nouveau lot ?'))return;
          setPool([]);setPending(null);setError('');}}>Vider la sélection</button>}</div></>}
    {busy&&<div className="document-actions"><p role="status" className="document-searching">{busy==='selection'?'Vérification de la révision du formulaire…':busy==='submit'?'Enregistrement du lot…':
      busy==='download'?'Vérification du téléchargement…':'Enregistrement de la commande…'}</p>
      <button type="button" className="button secondary sm" onClick={()=>{
        action.current?.abort();setNotice(busy==='submit'?'Attente interrompue. Le lot peut être enregistré : consultez l’historique ou répétez la même soumission.':
          busy==='cancel'||busy==='retry'?'Attente interrompue. Relisez le lot pour vérifier si la commande a été enregistrée.':'Attente interrompue.');
        setTick(value=>value+1);
      }}>Interrompre l’attente</button></div>}
    {error&&<p role="alert" className="document-warning">{error}</p>}{notice&&<p role="status">{notice}</p>}
    {readError&&<p role="alert" className="document-warning">{readError} <button className="button secondary sm" type="button" onClick={()=>setTick(value=>value+1)}>Relire les lots</button></p>}
    <h4>Lots enregistrés</h4>{jobs&&!jobs.total&&<p>Aucun lot enregistré dans ce projet.</p>}
    {jobs&&<><ul className="document-job-list">{jobs.items.map(row=><li key={row.id}><button type="button" disabled={unavailable} className={selected===row.id?'selected':''}
      aria-pressed={selected===row.id} onClick={()=>choose(row.id)}><strong>{row.processed} / {row.total} fichier(s) traité(s)</strong>
      <span>{documentJobLabel(row.status)}{row.execution_blocked?' · Historique suspendu':''}</span><small>{new Date(row.created_at).toLocaleString('fr-FR')}</small></button></li>)}</ul>
      <Pagination {...jobs} disabled={unavailable} onChange={setOffset}/></>}
    {selected&&!detail&&!readError&&<p role="status">Lecture du lot…</p>}
    {detail&&<section className="document-job-detail" aria-label="Suivi du lot sélectionné"><h4>{documentJobLabel(detail.status)} · {detail.processed} / {detail.total} fichier(s) traité(s)</h4>
      <progress max={detail.total} value={detail.processed} aria-label="Avancement du lot documentaire"/>
      {detail.execution_blocked&&<p className="document-help">Historique importé ou restauré : ces générations sont suspendues. Pour préparer de nouveaux fichiers, vérifiez de nouveaux aperçus puis créez un nouveau lot.</p>}
      {detail.cancel_requested&&<p role="status">Arrêt demandé. Une opération système active peut encore se terminer.</p>}
      <ul className="document-file-list">{detail.items.map(item=><li key={item.id}><div><strong>{label(item.document_id)}</strong>
        <span className={item.status==='running'?'document-searching':''}>{documentJobLabel(item.status)}</span>{item.error&&<p className="document-warning">{item.error}</p>}</div>
        {item.artifact_id&&<div className="document-actions"><button type="button" className="button secondary sm" disabled={unavailable} onClick={()=>void file(item.artifact_id!)}>Préparer le téléchargement · {label(item.document_id)}</button>
          <button type="button" className="button secondary sm" disabled={unavailable} onClick={()=>{
            if(publicationDirty&&publication?.artifactId!==item.artifact_id&&!window.confirm('Changer de copie ? La commande mémorisée reste conservée.'))return;
            setPublication({artifactId:item.artifact_id!,label:label(item.document_id),suggestion:item.publication_suggestion});
          }}>{canEdit&&!detail.execution_blocked?'Publier ou consulter les reçus':'Consulter les publications'} · {label(item.document_id)}</button></div>}</li>)}</ul>
      {publication&&<DocumentPublicationPanel key={publication.artifactId} projectId={projectId} jobId={detail.id} artifactId={publication.artifactId}
        label={publication.label} suggestion={publication.suggestion} revision={detail.revision} active={active} canEdit={canEdit} executionBlocked={detail.execution_blocked}
        jobActive={['queued','running'].includes(detail.status)} disabled={disabled||!!busy} onBusy={setPublicationBusy} onDirty={setPublicationDirty} onChanged={publicationChanged}/>}
      <div className="document-actions">{canEdit&&detail.can_cancel&&<button type="button" className="button secondary" disabled={unavailable||!!readError} onClick={()=>void command('cancel')}>Arrêter ce lot</button>}
        {canEdit&&detail.can_retry&&<button type="button" className="button primary" disabled={unavailable||!jobs?.worker.can_submit||!!readError} onClick={()=>void command('retry')}>Reprendre les fichiers non réussis</button>}
        <button type="button" className="button secondary" disabled={unavailable} onClick={()=>setJournal(value=>!value)}>{journal?'Fermer le journal du lot':'Ouvrir le journal du lot'}</button></div>
      {download&&<div className="document-download"><a className="button primary" href={download.url} download={download.name}>Télécharger {download.name}</a>
        <details><summary>Vérification de la copie</summary><p className="document-path">SHA-256 : {download.sha256}</p></details></div>}
      {journal&&<div className="document-job-journal"><h5>Tentatives par fichier</h5>{attempts&&<><ol>{attempts.items.map(row=><li key={row.id}>
        {label(detail.items.find(item=>item.id===row.item_id)?.document_id||'Fichier')} · Essai {row.number} · {documentJobLabel(row.outcome)}
        <small>{new Date(row.created_at).toLocaleString('fr-FR')}</small>{row.error&&<p>{row.error}</p>}</li>)}</ol>
        <Pagination {...attempts} onChange={setAttemptOffset} disabled={unavailable}/></>}
        <h5>Événements du lot</h5>{events&&<><ol>{events.items.map(row=><li key={row.id}>{documentEventLabel(row.kind)}
          <small>{new Date(row.created_at).toLocaleString('fr-FR')} · Révision {row.revision}</small></li>)}</ol>
          <Pagination {...events} onChange={setEventOffset} disabled={unavailable}/></>}</div>}
    </section>}
  </section>;
}
