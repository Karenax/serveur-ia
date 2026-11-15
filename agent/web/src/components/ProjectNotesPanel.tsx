import { useEffect, useRef, useState } from 'react';
import { Pagination } from './IdentityPickers';
import { message, useAlive } from './PlanningTasksPanel';
import { NoteContentView, NoteRichEditor } from './NoteRichEditor';
import { NoteAttachments } from './NoteAttachments';
import { NoteImportPanel } from './NoteImportPanel';
import { NoteSourcePanel } from './NoteSourcePanel';
import { blankNote, boundVersionContent, NoteHttpError, noteDraftKey, notesApi, noteUrl, readNoteDraft, sameNote,
  validNoteContent, writeNoteDraft, type NoteContent, type NoteDetail, type NoteDraft, type NoteHistory,
  type NotePage, type NotePending, type NotesList, type NoteVersion } from '../lib/projectNotes';
import './project-notes.css';
import type {MarkdownDraftState} from '../lib/noteMarkdown';

const date=(value:string)=>new Date(value).toLocaleString('fr-FR');
export function ProjectNotesPanel(props:{projectId:string;active?:boolean}){return <NotesPanel key={props.projectId} {...props}/>;}
function NotesPanel({projectId,active=true}:{projectId:string;active?:boolean}){
  const [page,setPage]=useState<NotesList|null>(null),[query,setQuery]=useState(''),[offset,setOffset]=useState(0);
  const [selected,setSelected]=useState<string|null>(null),[error,setError]=useState(''),[loading,setLoading]=useState(false),[tick,setTick]=useState(0);
  const [importing,setImporting]=useState(false),[importVisited,setImportVisited]=useState(false);
  useEffect(()=>{if(!active)return;const controller=new AbortController();setLoading(true);setError('');
    const timer=window.setTimeout(()=>notesApi.list(projectId,query,offset,controller.signal).then(value=>{
      if(!controller.signal.aborted){if(value.items.some(n=>n.project_id!==projectId))throw new Error('Liste reçue pour un autre projet');setPage(value);}
    }).catch(e=>{if(!controller.signal.aborted)setError(message(e));}).finally(()=>{if(!controller.signal.aborted)setLoading(false);}),150);
    return()=>{window.clearTimeout(timer);controller.abort();};},[projectId,active,query,offset,tick]);
  const canEdit=!!page?.can_edit&&!error;
  return <section className="project-notes" aria-label="Notes du projet">
    <header className="planning-heading"><div><h3>Notes</h3><p>Comptes rendus, décisions et informations du projet.</p></div>
      {page?.available&&canEdit&&<div className="note-actions"><button type="button" className="button secondary" disabled={!active||loading} onClick={()=>{setImporting(v=>!v);setImportVisited(true);}}>{importing?'Fermer l’import':'Importer une note'}</button>
        <button type="button" className="button" disabled={!active||loading} onClick={()=>setSelected('new')}>Nouvelle note</button></div>}</header>
    {error&&<div role="alert" className="state-panel error"><p>{error}</p><button type="button" className="button secondary" onClick={()=>setTick(n=>n+1)}>Réessayer</button></div>}
    {loading&&<p role="status">Lecture des notes…</p>}
    {page&&!page.available&&<p className="state-panel" role="status">Les notes ne sont pas encore activées sur ce serveur.</p>}
    {page?.available&&page.operator_id&&importVisited&&<div hidden={!importing}><NoteImportPanel key={page.operator_id} projectId={projectId} operatorId={page.operator_id} active={active&&importing} canEdit={canEdit}
      onImported={id=>{setSelected(id);setImporting(false);setTick(n=>n+1);}}/></div>}
    {page?.available&&<div className="note-workspace"><aside className="note-index" aria-label="Liste des notes">
      <label>Rechercher une note<input className="input" maxLength={200} value={query} onChange={e=>{setQuery(e.target.value);setOffset(0);}}/></label>
      {!loading&&!page.total&&<p>{query?'Aucune note ne correspond.':'Aucune note pour ce projet.'}</p>}
      <ul>{page.items.map(note=><li key={note.id}><button type="button" className={selected===note.id?'selected':''} aria-pressed={selected===note.id} onClick={()=>setSelected(note.id)}>
        <strong>{note.title}</strong><span>{note.excerpt||'Note sans texte'}</span><small>Version {note.revision} · {date(note.updated_at)}</small></button></li>)}</ul>
      <Pagination offset={page.offset} limit={page.limit} total={page.total} disabled={loading} onChange={setOffset}/>
    </aside><div className="note-main">{selected&&page.operator_id?<NoteSession key={`${selected}:${page.operator_id}`} projectId={projectId} noteId={selected}
      operatorId={page.operator_id} canEdit={canEdit} active={active} onSaved={id=>{setSelected(id);setTick(n=>n+1);}}/>:
      <p className="state-panel" hidden={!page.total}>Sélectionnez une note pour la consulter{canEdit?' ou créez-en une.':'.'}</p>}</div></div>}
  </section>;
}
function makeDraft(projectId:string,noteId:string,operatorId:string,note:NoteDetail|null):NoteDraft{
  return {format:1,project_id:projectId,note_id:noteId,operator_id:operatorId,title:note?.title||'',content:note?.content||blankNote(),
    attachment_ids:note?.attachment_ids||[],expected_revision:note?.revision||0,pending:null,updated_at:new Date().toISOString()};
}
function exportDraft(projectId:string,noteId:string,operatorId:string,draft:NoteDraft|null){
  const raw=draft?JSON.stringify(draft,null,2):localStorage.getItem(noteDraftKey(projectId,noteId,operatorId));
  if(raw===null)throw new Error('Aucun brouillon accessible à exporter');
  const url=URL.createObjectURL(new Blob([raw],{type:'application/json'})),a=document.createElement('a');
  a.href=url;a.download='brouillon-note.json';a.click();window.setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function NoteSession({projectId,noteId,operatorId,canEdit,active,onSaved}:{projectId:string;noteId:string;operatorId:string;canEdit:boolean;active:boolean;onSaved:(id:string)=>void}){
  const [head,setHead]=useState<NoteDetail|null>(null),[draft,setDraft]=useState<NoteDraft|null>(null),[recovery,setRecovery]=useState<NoteDraft|null>(null);
  const [loading,setLoading]=useState(true),[status,setStatus]=useState(''),[error,setError]=useState(''),[storageError,setStorageError]=useState('');
  const [blocked,setBlocked]=useState(false);
  const [markdownDraft,setMarkdownDraft]=useState<MarkdownDraftState>({pending:false,valid:true});
  const [conflict,setConflict]=useState(false),[remote,setRemote]=useState<NoteDetail|null>(null),[busy,setBusy]=useState(false),[history,setHistory]=useState(false);
  const current=useRef<NoteDraft|null>(null),alive=useAlive(),action=useRef<AbortController|null>(null),headRef=useRef<NoteDetail|null>(null),inFlight=useRef(false);
  const writable=canEdit&&!head?.read_only&&active&&!loading&&!recovery;
  const dirty=!!draft&&(!!draft.pending||!head||!sameNote(draft,head));
  function persist(value:NoteDraft){
    try{writeNoteDraft(value);setStorageError('');return true;}
    catch{setStorageError('Brouillon non conservé sur cet appareil : espace indisponible. Exportez votre saisie avant de quitter.');return false;}
  }
  function apply(value:NoteDraft,store=true){current.current=value;setDraft(value);return store?persist(value):true;}
  function verify(value:NoteDetail){if(value.project_id!==projectId||(noteId!=='new'&&value.id!==noteId)||!validNoteContent(value.content))throw new Error('Note reçue incompatible avec le projet ou le contenu attendu');return value;}
  useEffect(()=>{const controller=new AbortController();setLoading(true);
    (noteId==='new'?Promise.resolve(null):notesApi.read(projectId,noteId,controller.signal)).then(note=>{
      if(controller.signal.aborted)return;
      if(note)verify(note);headRef.current=note;setHead(note);
      const local=readNoteDraft(projectId,noteId,operatorId),base=makeDraft(projectId,noteId,operatorId,note);
      current.current=base;setDraft(base);setRecovery(local.draft&&(!note||local.draft.pending||!sameNote(local.draft,note))?local.draft:null);
      setStorageError(local.error);setBlocked(!!local.error);setStatus(note?`Enregistrée · version ${note.revision}`:'Saisissez un titre pour créer la note.');
    }).catch(e=>{if(!controller.signal.aborted)setError(message(e));}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    return()=>{controller.abort();action.current?.abort();};},[projectId,noteId,operatorId]);
  useEffect(()=>{const guard=(e:BeforeUnloadEvent)=>{if(dirty||recovery||storageError||markdownDraft.pending){e.preventDefault();e.returnValue='';}};
    window.addEventListener('beforeunload',guard);return()=>window.removeEventListener('beforeunload',guard);},[dirty,recovery,storageError,markdownDraft.pending]);
  const executeRef=useRef<()=>void>(()=>{});
  useEffect(()=>{if(!writable||!dirty||busy||draft?.pending||conflict||storageError||markdownDraft.pending||!head||!draft?.title.trim()||!validNoteContent(draft.content))return;
    const timer=window.setTimeout(()=>executeRef.current(),1200);return()=>window.clearTimeout(timer);
  },[draft,writable,dirty,busy,conflict,storageError,head,markdownDraft.pending]);
  function edit(values:Partial<Pick<NoteDraft,'title'|'content'|'attachment_ids'>>){
    if(!current.current)return false;const next={...current.current,...values,updated_at:new Date().toISOString()};const stored=apply(next);
    if(!conflict)setStatus(inFlight.current?'Enregistrement en cours · nouvelles modifications en attente':'Brouillon local · enregistrement à venir');
    return stored;
  }
  async function execute(restoreId?:string){
    const value=current.current;if(!value||!canEdit||!active||headRef.current?.read_only||inFlight.current||recovery||markdownDraft.pending)return;
    const pending:NotePending=value.pending||(restoreId?{kind:'restore',payload:{command_id:crypto.randomUUID(),expected_revision:value.expected_revision,version_id:restoreId}}:
      noteId==='new'?{kind:'create',payload:{command_id:crypto.randomUUID(),title:value.title.trim(),content:value.content}}:
      {kind:'save',payload:{command_id:crypto.randomUUID(),expected_revision:value.expected_revision,title:value.title.trim(),content:value.content,attachment_ids:value.attachment_ids}});
    if(pending.kind!=='restore'&&(!pending.payload.title||!validNoteContent(pending.payload.content))){setError('Renseignez un titre et vérifiez le contenu de la note.');return;}
    const frozen={...value,pending};if(!persist(frozen))return;current.current=frozen;setDraft(frozen);
    const controller=new AbortController();action.current=controller;inFlight.current=true;setBusy(true);setError('');setStatus('Enregistrement en cours…');
    try{
      const response=await notesApi.execute(projectId,noteId,pending,controller.signal);
      if(!alive.current||controller.signal.aborted)return;
      const note=verify(response.note);if(response.command_id!==pending.payload.command_id)throw new Error('Accusé d’enregistrement différent de la commande envoyée');
      const live=current.current!;headRef.current=note;setHead(note);
      if(note.revision!==response.command_revision){
        if(noteId==='new'){
          const rebound={...live,note_id:note.id,expected_revision:response.command_revision,pending:null};
          if(!persist(rebound))return;
          localStorage.removeItem(noteDraftKey(projectId,'new',operatorId));onSaved(note.id);return;
        }
        setConflict(true);setRemote(note);apply({...live,pending:null});
        setStatus('La commande est enregistrée, puis la note a été modifiée ailleurs. Votre saisie est conservée.');return;}
      let next:NoteDraft;
      if(pending.kind==='restore')next=makeDraft(projectId,note.id,operatorId,note);
      else{
        const sent={title:pending.payload.title,content:pending.payload.content,attachment_ids:pending.kind==='save'?pending.payload.attachment_ids:[]};
        next=sameNote({...live,title:live.title.trim()},sent)?makeDraft(projectId,note.id,operatorId,note):
          {...live,note_id:note.id,pending:null,expected_revision:note.revision};
      }
      if(!persist(next))return;
      current.current=next;setDraft(next);setConflict(false);setRemote(null);
      setStatus(sameNote(next,note)?`Enregistrée · version ${note.revision}`:'Brouillon local · nouvelles modifications à enregistrer');
      if(noteId==='new')localStorage.removeItem(noteDraftKey(projectId,'new',operatorId));
      onSaved(note.id);
    }catch(e){if(alive.current&&!controller.signal.aborted){setError(message(e));setStatus('Enregistrement à reprendre · saisie conservée');
      if(e instanceof NoteHttpError&&e.status===409)setConflict(true);}}
    finally{inFlight.current=false;if(alive.current){setBusy(false);action.current=null;}}
  }
  executeRef.current=()=>{void execute();};
  async function compare(){const controller=new AbortController();action.current=controller;setBusy(true);setError('');
    try{const note=verify(await notesApi.read(projectId,noteId,controller.signal));if(alive.current&&!controller.signal.aborted)setRemote(note);}
    catch(e){if(alive.current&&!controller.signal.aborted)setError(message(e));}finally{if(alive.current){setBusy(false);action.current=null;}}}
  function recover(){if(!recovery)return;apply(recovery);setRecovery(null);const stale=!!head&&recovery.expected_revision!==head.revision;
    setConflict(stale);setStatus(recovery.pending?'Commande en attente : reprendre son enregistrement.':stale?'Brouillon repris · comparer avec la version enregistrée.':'Brouillon local repris.');}
  return <section className="note-session" aria-label="Note sélectionnée" data-workspace-dirty={dirty||recovery||storageError||markdownDraft.pending?'true':undefined}>
    {loading&&<p role="status">Ouverture de la note…</p>}
    {error&&<p role="alert" className="document-warning">{error}</p>}
    {storageError&&<div role="alert" className="document-warning"><p>{storageError}</p>
      <button type="button" className="button secondary sm" onClick={()=>{try{exportDraft(projectId,noteId,operatorId,blocked?null:draft);}catch(e){setError(message(e));}}}>Exporter le brouillon</button>
      <button type="button" className="button secondary sm" onClick={()=>{if(draft&&persist(draft))setBlocked(false);}}>{blocked?'Remplacer le brouillon illisible par la version affichée':'Réessayer la sauvegarde locale'}</button></div>}
    {recovery&&<div role="status" className="note-recovery"><strong>Brouillon retrouvé sur cet appareil</strong><p>{recovery.title||'Note sans titre'} · {date(recovery.updated_at)}</p>
      <div className="note-actions"><button type="button" className="button" onClick={recover}>Reprendre ce brouillon</button>
        <button type="button" className="button secondary" onClick={()=>{try{exportDraft(projectId,noteId,operatorId,recovery);}catch(e){setError(message(e));}}}>Exporter le brouillon</button>
        <button type="button" className="button secondary" onClick={()=>{if(draft&&persist(draft)){setRecovery(null);setStatus(head?`Enregistrée · version ${head.revision}`:'Saisissez un titre pour créer la note.');}}}>Écarter ce brouillon</button></div></div>}
    {draft&&!loading&&<><div className="note-title"><label>Titre de la note<input className="input" maxLength={255} value={draft.title} readOnly={!writable||blocked||(busy&&draft.pending?.kind==='restore')} onChange={e=>edit({title:e.target.value})}/></label>
      <div role="status" aria-live="polite" className={`note-save-status ${busy?'saving':''}`}>{status}</div>
      {head&&<small>Dernière version par {head.actor_id||'auteur non renseigné'} · {date(head.updated_at)}</small>}</div>
      {(!canEdit||head?.read_only)&&<p className="document-help">{head?.read_only?'Document Office en consultation. Son original reste conservé.':'Lecture seule : vous pouvez consulter la note et son historique.'}</p>}
      <NoteRichEditor content={draft.content} projectId={projectId} noteId={noteId} draftId={JSON.stringify([projectId,noteId,operatorId])}
        onMarkdownDraftState={setMarkdownDraft} disabled={!writable||blocked||(busy&&draft.pending?.kind==='restore')} onChange={content=>edit({content})}/>
      {!validNoteContent(draft.content)&&<p role="alert">Le contenu dépasse les limites de la note. Réduisez le texte ou le nombre de blocs avant l’enregistrement.</p>}
      <div className="note-actions">{canEdit&&!head?.read_only&&<button type="button" className="button" disabled={!active||busy||!!recovery||blocked||markdownDraft.pending||(!dirty&&!draft.pending)||(!draft.pending&&conflict)} onClick={()=>void execute()}>
        {draft.pending?'Reprendre l’enregistrement':noteId==='new'?'Créer la note':'Enregistrer maintenant'}</button>}
        <button type="button" className="button secondary" onClick={()=>{try{exportDraft(projectId,noteId,operatorId,draft);}catch(e){setError(message(e));}}}>Exporter le brouillon</button>
        {head&&<button type="button" className="button secondary" disabled={busy} onClick={()=>setHistory(v=>!v)}>{history?'Fermer l’historique':'Historique de la note'}</button>}
        {head&&(conflict||draft.pending)&&<button type="button" className="button secondary" disabled={busy||!active} onClick={()=>void compare()}>Comparer avec la version enregistrée</button>}
      </div>
      {remote&&<section className="note-comparison" aria-label="Version enregistrée à comparer"><h4>{remote.title} · version {remote.revision}</h4>
        <NoteContentView content={remote.content} projectId={projectId} noteId={noteId}/><p>Votre saisie reste affichée au-dessus.</p>
        {canEdit&&conflict&&<button type="button" className="button secondary" disabled={busy||remote.read_only} onClick={()=>{
          headRef.current=remote;setHead(remote);apply({...current.current!,expected_revision:remote.revision,pending:null});setRemote(null);setConflict(false);
          setStatus('Saisie conservée sur la dernière version · enregistrement à venir');}}>Reprendre ma saisie sur cette version</button>}
        <button type="button" className="button secondary" disabled={busy||!!draft.pending&&!conflict} onClick={()=>{
          headRef.current=remote;setHead(remote);apply(makeDraft(projectId,noteId,operatorId,remote));setRemote(null);setConflict(false);setError('');setStatus(`Enregistrée · version ${remote.revision}`);
        }}>Remplacer ma saisie par cette version</button></section>}
      {head&&<NoteAttachments projectId={projectId} noteId={noteId} operatorId={operatorId} revision={head.revision} active={active}
        canEdit={writable&&!blocked&&!busy&&!conflict&&!draft.pending&&!markdownDraft.pending} selectedIds={draft.attachment_ids}
        onAttach={id=>{const live=current.current!;if(!live.attachment_ids.includes(id))edit({attachment_ids:[...live.attachment_ids,id]});}}
        onImage={(id,filename)=>{const live=current.current!;edit({content:{...live.content,blocks:[...live.content.blocks,{type:'image',attachment_id:id,caption:filename}]},
          attachment_ids:[...new Set([...live.attachment_ids,id])]});}}/>}
      {head?.source_kind&&<NoteSourcePanel projectId={projectId} noteId={noteId} active={active}/>}
      {head&&history&&<NoteHistoryPanel key={head.revision} projectId={projectId} noteId={noteId} active={active} canRestore={writable&&!dirty&&!busy&&!conflict&&!draft.pending&&!storageError&&!markdownDraft.pending} onRestore={id=>void execute(id)}/>}</>}
  </section>;
}
function NoteHistoryPanel({projectId,noteId,active,canRestore,onRestore}:{projectId:string;noteId:string;active:boolean;canRestore:boolean;onRestore:(id:string)=>void}){
  const [page,setPage]=useState<NotePage<NoteHistory>|null>(null),[offset,setOffset]=useState(0),[version,setVersion]=useState<NoteVersion|null>(null);
  const [content,setContent]=useState<NoteContent|null>(null),[error,setError]=useState(''),[loading,setLoading]=useState(false);
  const request=useRef<AbortController|null>(null),alive=useAlive();
  useEffect(()=>{if(!active)return;const controller=new AbortController();setLoading(true);setError('');
    notesApi.history(projectId,noteId,offset,controller.signal).then(value=>{if(!controller.signal.aborted)setPage(value);}).catch(e=>{if(!controller.signal.aborted)setError(message(e));}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    return()=>{controller.abort();request.current?.abort();};},[projectId,noteId,offset,active]);
  async function inspect(id:string){request.current?.abort();const controller=new AbortController();request.current=controller;setError('');setVersion(null);setContent(null);
    try{const value=await notesApi.version(projectId,noteId,id,controller.signal);if(!alive.current||controller.signal.aborted)return;
      if(value.project_id!==projectId||value.note_id!==noteId||value.id!==id)throw new Error('Version reçue pour une autre note');
      const bound=boundVersionContent(value);if(!validNoteContent(bound))throw new Error('Contenu historique incompatible');setVersion(value);setContent(bound);
    }catch(e){if(alive.current&&!controller.signal.aborted)setError(message(e));}}
  return <section className="note-history" aria-label="Historique de la note"><h4>Historique</h4><p className="document-help">Restaurer crée une nouvelle version. Les versions précédentes restent consultables.</p>
    {loading&&<p role="status">Lecture de l’historique…</p>}{error&&<p role="alert">{error}</p>}
    <ul>{page?.items.map(v=><li key={v.id}><div><strong>Version {v.revision} · {v.title}</strong><small>{date(v.created_at)} · {v.actor_id||'auteur source non renseigné'}</small></div>
      <button type="button" className="button secondary sm" disabled={!active} onClick={()=>void inspect(v.id)}>Consulter la version {v.revision}</button></li>)}</ul>
    {page&&<Pagination offset={page.offset} total={page.total} limit={page.limit} disabled={loading} onChange={setOffset}/>}
    {version&&content&&<section aria-label="Aperçu de la version historique"><h4>Version {version.revision} · {version.value.title}</h4>
      <NoteContentView content={content} projectId={projectId} noteId={noteId}/><button type="button" className="button secondary" disabled={!canRestore} onClick={()=>onRestore(version.id)}>Restaurer cette version</button>
      {!canRestore&&<p className="document-help">La restauration nécessite une note enregistrée et un accès en modification.</p>}</section>}
  </section>;
}
