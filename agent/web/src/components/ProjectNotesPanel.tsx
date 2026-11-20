import {createPortal} from 'react-dom';
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Pagination } from './IdentityPickers';
import { message, useAlive } from './PlanningTasksPanel';
import { NoteContentView, NoteRichEditor } from './NoteRichEditor';
import { NoteAttachments } from './NoteAttachments';
import { NoteImportPanel } from './NoteImportPanel';
import { NoteSourcePanel } from './NoteSourcePanel';
import { allNotesScope, blankNote, boundVersionContent, noteBackgrounds, NoteHttpError, noteDraftKey, notesApi, noteUrl, personalNotesScope, readNoteDraft, sameNote,
  validNoteContent, writeNoteDraft, type NoteContent, type NoteDetail, type NoteDraft, type NoteHistory,
  type NotePage, type NotePending, type NotesList, type NotesProject, type NoteVersion } from '../lib/projectNotes';
import {clearPendingImage, prepareClipboardImage, readPendingImage, rememberPendingImage, type PendingNoteImage} from '../lib/notePasteStore';
import './project-notes.css';
import type {MarkdownDraftState} from '../lib/noteMarkdown';

const date=(value:string)=>new Date(value).toLocaleString('fr-FR');
const newNoteHint='Ajoutez un titre ou collez une image dans la note.';
type NoteSelection={id:string;scope:string};
type NotesPanelProps={projectId:string;active?:boolean;workspace?:boolean;initialNote?:string;initialNoteScope?:string;
  toolbar?:HTMLElement|null;folderPicker?:ReactNode;listedProjects?:NotesProject[];onSelected?:(item:NoteSelection|null)=>void;
  copyProjects?:NotesProject[];onCopied?:(note:NoteDetail)=>void;onNotesChanged?:(scope:string)=>void};
export function ProjectNotesPanel(props:NotesPanelProps){return <NotesPanel key={props.projectId} {...props}/>;}
function NotesPanel({projectId,active=true,workspace=false,initialNote,initialNoteScope,toolbar,folderPicker,listedProjects,onSelected,copyProjects,onCopied,onNotesChanged}:NotesPanelProps){
  const personal=projectId===personalNotesScope;
  const aggregate=projectId===allNotesScope;
  const [page,setPage]=useState<NotesList|null>(null),[query,setQuery]=useState(''),[offset,setOffset]=useState(0);
  const [selected,setSelected]=useState<NoteSelection|null>(initialNote?{id:initialNote,scope:initialNoteScope??projectId}:null);
  const [error,setError]=useState(''),[loading,setLoading]=useState(false),[tick,setTick]=useState(0);
  const [importing,setImporting]=useState(false),[importVisited,setImportVisited]=useState(false);
  const panel=useRef<HTMLElement>(null);
  const [selectionNotice,setSelectionNotice]=useState('');
  const projectFilter=aggregate?(listedProjects??[]).map(project=>project.id).join(','):'';
  useEffect(()=>{setOffset(0);},[projectFilter]);
  useEffect(()=>{
    if(aggregate&&selected&&selected.scope!==personalNotesScope&&!projectFilter.split(',').includes(selected.scope))setSelected(null);
  },[aggregate,projectFilter,selected]);
  useEffect(()=>{if(!active)return;const controller=new AbortController();setLoading(true);setError('');
    const projects=projectFilter?projectFilter.split(','):[];
    const scopes=aggregate?[personalNotesScope,...projects]:[projectId];
    const timer=window.setTimeout(()=>{
      const request=aggregate?notesApi.all(projects,query,offset,controller.signal):notesApi.list(projectId,query,offset,controller.signal);
      void request.then(value=>{
        if(controller.signal.aborted)return;
        if(value.items.some(note=>!scopes.includes(note.project_id)))throw new Error('Liste reçue pour un autre carnet');
        setPage(value);
        if(value.offset>0&&!value.items.length)setOffset(Math.max(0,value.offset-value.limit));
      }).catch(e=>{if(!controller.signal.aborted)setError(message(e));}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    },150);
    return()=>{window.clearTimeout(timer);controller.abort();};},[projectId,active,aggregate,projectFilter,query,offset,tick]);
  const canEdit=!!page?.can_edit;
  function selectNote(id:string,scope=aggregate?personalNotesScope:projectId){
    if(selected?.id===id&&selected.scope===scope)return;
    if(panel.current?.querySelector('[data-note-volatile="true"]')){
      setSelectionNotice('Terminez l’enregistrement de cette note avant d’en ouvrir une autre.');return;
    }
    setSelectionNotice('');
    const item={id,scope};setSelected(item);
    if(id!=='new')onSelected?.(item);
  }
  function saved(note:NoteDetail){
    const item={id:note.id,scope:note.project_id};
    if(selected?.id==='new'){
      setSelected(item);setTick(n=>n+1);onSelected?.(item);onNotesChanged?.(note.project_id);
      return;
    }
    setPage(previous=>previous&&({...previous,items:previous.items.map(row=>row.id===note.id&&row.project_id===note.project_id
      ?{...row,title:note.title,revision:note.revision,version_id:note.version_id,updated_at:note.updated_at,
        actor_id:note.actor_id,background:note.content.background,excerpt:note.plain_text?.slice(0,240)??row.excerpt}
      :row)}));
  }
  function deleted(){
    setSelected(null);onSelected?.(null);
    setPage(previous=>previous&&({...previous,items:previous.items.filter(row=>row.id!==selected?.id||row.project_id!==selected?.scope)}));
    setTick(n=>n+1);if(selected)onNotesChanged?.(selected.scope);
    panel.current?.querySelector<HTMLInputElement>('.note-index input')?.focus({preventScroll:true});
  }
  const creation=<>
    {page?.available&&canEdit&&<button type="button" className="button primary" disabled={!active} onClick={()=>selectNote('new')}>Nouvelle note</button>}
    {folderPicker}
    {page?.available&&canEdit&&!personal&&!aggregate&&<button type="button" className="button secondary" disabled={!active}
      onClick={()=>{setImporting(value=>!value);setImportVisited(true);}}>{importing?'Fermer l’import':'Importer une note'}</button>}
  </>;
  return <section ref={panel} className={workspace?"project-notes project-notes-workspace":"project-notes"} aria-label={aggregate?'Toutes les notes':personal?'Notes personnelles':'Notes du projet'}>
    {workspace ? toolbar&&createPortal(creation,toolbar)
      : <header className="planning-heading"><div><h3>Notes</h3><p>Comptes rendus, décisions et informations du projet.</p></div>
        <div className="note-actions">{creation}</div></header>}
    {error&&<div role="alert" className="state-panel error"><p>{error}</p><button type="button" className="button secondary" onClick={()=>setTick(n=>n+1)}>Réessayer</button></div>}
    {selectionNotice&&<p role="status">{selectionNotice}</p>}
    {loading&&!page&&<p role="status">Lecture des notes…</p>}
    {page&&!page.available&&<p className="state-panel" role="status">Les notes ne sont pas encore activées sur ce serveur.</p>}
    {page?.available&&page.operator_id&&importVisited&&<div hidden={!importing}><NoteImportPanel key={page.operator_id} projectId={projectId} operatorId={page.operator_id} active={active&&importing} canEdit={canEdit}
      onImported={id=>{selectNote(id);setImporting(false);setTick(n=>n+1);onNotesChanged?.(projectId);}}/></div>}
    {page?.available&&<div className="note-workspace"><aside className="note-index" aria-label="Liste des notes">
      <label>{workspace&&!aggregate?'Rechercher dans ce carnet':'Rechercher une note'}<input className="input" maxLength={200} value={query} onChange={e=>{setQuery(e.target.value);setOffset(0);}}/></label>
      {!loading&&!page.total&&<div className="notes-list-empty">
        <p>{query?'Aucune note ne correspond.':aggregate?'Aucune note à afficher.':personal?'Aucune note personnelle.':'Aucune note pour ce projet.'}</p>
        {query&&<button type="button" className="button secondary sm" onClick={()=>{setQuery('');setOffset(0);}}>Effacer la recherche</button>}
      </div>}
      <ul>{page.items.map(note=>{
        const current=selected?.id===note.id&&selected.scope===note.project_id;
        const project=aggregate?listedProjects?.find(p=>p.id===note.project_id):undefined;
        const origin=aggregate&&note.project_id===personalNotesScope?'Personnel':project?.code||project?.title;
        return <li key={`${note.project_id}:${note.id}`}><button type="button" className={current?'selected':''} data-note-background={note.background||undefined}
          aria-label={`Ouvrir la note ${note.title}${origin?` · ${origin}`:''}`} aria-pressed={current} onClick={()=>selectNote(note.id,note.project_id)}>
          <strong>{note.title}</strong><span>{note.excerpt.trim()||'Note sans texte'}</span><small>{origin&&`${origin} · `}Version {note.revision} · {date(note.updated_at)}</small></button></li>;
      })}</ul>
      <Pagination offset={page.offset} limit={page.limit} total={page.total} disabled={loading} onChange={setOffset}/>
    </aside><div className="note-main">{selected&&page.operator_id?<NoteSession key={`${selected.scope}:${selected.id}:${page.operator_id}`} projectId={selected.scope} noteId={selected.id}
      operatorId={page.operator_id} canEdit={canEdit} active={active} workspace={workspace} copyProjects={copyProjects} onCopied={onCopied}
      onSaved={saved} onDeleted={deleted}/>:
      <div className="note-opening-hint">
        <p>{page.total>0?'Sélectionnez une note.':'Les notes apparaîtront ici.'}</p>
      </div>}</div></div>}
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
function NoteSession({projectId,noteId,operatorId,canEdit,active,onSaved,onDeleted,copyProjects,onCopied,workspace}:{projectId:string;noteId:string;workspace:boolean;
  operatorId:string;canEdit:boolean;active:boolean;onSaved:(note:NoteDetail)=>void;onDeleted:()=>void;copyProjects?:NotesProject[];onCopied?:(note:NoteDetail)=>void}){
  const [head,setHead]=useState<NoteDetail|null>(null),[draft,setDraft]=useState<NoteDraft|null>(null),[recovery,setRecovery]=useState<NoteDraft|null>(null);
  const [loading,setLoading]=useState(true),[status,setStatus]=useState(''),[error,setError]=useState(''),[storageError,setStorageError]=useState('');
  const [blocked,setBlocked]=useState(false);
  const [markdownDraft,setMarkdownDraft]=useState<MarkdownDraftState>({pending:false,valid:true});
  const [conflict,setConflict]=useState(false),[remote,setRemote]=useState<NoteDetail|null>(null),[busy,setBusy]=useState(false),[history,setHistory]=useState(false);
  const current=useRef<NoteDraft|null>(null),alive=useAlive(),action=useRef<AbortController|null>(null),headRef=useRef<NoteDetail|null>(null),inFlight=useRef(false);
  const [pendingImage,setPendingImage]=useState<PendingNoteImage>(),[pasteReady,setPasteReady]=useState(false);
  const [pasteError,setPasteError]=useState(''),[pasteBusy,setPasteBusy]=useState(false);
  const [deleting,setDeleting]=useState(false);
  const deleteCommand=useRef<{command_id:string;expected_revision:number}|null>(null);
  const imageKey=noteDraftKey(projectId,noteId,operatorId);
  const section=useRef<HTMLElement>(null);
  const imageLocked=pasteBusy||!!pendingImage;
  const writable=canEdit&&!head?.read_only&&active&&!loading&&!recovery&&!deleting;
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
      setStorageError(local.error);setBlocked(!!local.error);setStatus(note?`Enregistrée · version ${note.revision}`:newNoteHint);
    }).catch(e=>{if(!controller.signal.aborted)setError(message(e));}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    return()=>{controller.abort();action.current?.abort();};},[projectId,noteId,operatorId]);
  useEffect(()=>{let cancelled=false;
    readPendingImage(imageKey).then(job=>{if(!cancelled){setPendingImage(job);setPasteReady(true);}})
      .catch(()=>{if(!cancelled)setPasteError('Impossible de lire les images en attente sur cet appareil.');});
    return()=>{cancelled=true;};},[imageKey]);
  useEffect(()=>{const guard=(e:BeforeUnloadEvent)=>{if(dirty||recovery||storageError||markdownDraft.pending||pendingImage||pasteBusy){e.preventDefault();e.returnValue='';}};
    window.addEventListener('beforeunload',guard);return()=>window.removeEventListener('beforeunload',guard);},[dirty,recovery,storageError,markdownDraft.pending,pendingImage,pasteBusy]);
  const executeRef=useRef<()=>void>(()=>{});
  useEffect(()=>{if(!writable||!dirty||busy||pendingImage||draft?.pending||conflict||storageError||markdownDraft.pending||!head||!draft?.title.trim()||!validNoteContent(draft.content))return;
    const timer=window.setTimeout(()=>executeRef.current(),1200);return()=>window.clearTimeout(timer);
  },[draft,writable,dirty,busy,pendingImage,conflict,storageError,head,markdownDraft.pending]);
  function edit(values:Partial<Pick<NoteDraft,'title'|'content'|'attachment_ids'>>){
    if(!current.current)return false;const next={...current.current,...values,updated_at:new Date().toISOString()};const stored=apply(next);
    if(!conflict)setStatus(inFlight.current?'Enregistrement…':'Brouillon local');
    return stored;
  }
  async function execute(restoreId?:string){
    const value=current.current;if(!value||!canEdit||!active||headRef.current?.read_only||inFlight.current||pendingImage||recovery||markdownDraft.pending)return;
    const pending:NotePending=value.pending||(restoreId?{kind:'restore',payload:{command_id:crypto.randomUUID(),expected_revision:value.expected_revision,version_id:restoreId}}:
      noteId==='new'?{kind:'create',payload:{command_id:crypto.randomUUID(),title:value.title.trim(),content:value.content}}:
      {kind:'save',payload:{command_id:crypto.randomUUID(),expected_revision:value.expected_revision,title:value.title.trim(),content:value.content,attachment_ids:value.attachment_ids}});
    if(pending.kind!=='restore'&&(!pending.payload.title||!validNoteContent(pending.payload.content))){setError('Renseignez un titre et vérifiez le contenu de la note.');return;}
    const frozen={...value,pending};if(!persist(frozen))return;current.current=frozen;setDraft(frozen);
    const controller=new AbortController();action.current=controller;inFlight.current=true;setBusy(true);setError('');setStatus('Enregistrement…');
    try{
      const response=await notesApi.execute(projectId,noteId,pending,controller.signal);
      if(!alive.current||controller.signal.aborted)return;
      const note=verify(response.note);if(response.command_id!==pending.payload.command_id)throw new Error('Accusé d’enregistrement différent de la commande envoyée');
      const live=current.current!;headRef.current=note;setHead(note);
      if(note.revision!==response.command_revision){
        if(noteId==='new'){
          const rebound={...live,note_id:note.id,expected_revision:response.command_revision,pending:null};
          if(!persist(rebound))return;
          localStorage.removeItem(noteDraftKey(projectId,'new',operatorId));onSaved(note);return;
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
      setStatus(sameNote(next,note)?`Enregistrée · version ${note.revision}`:'Brouillon local');
      if(noteId==='new')localStorage.removeItem(noteDraftKey(projectId,'new',operatorId));
      onSaved(note);
    }catch(e){if(alive.current&&!controller.signal.aborted){setError(message(e));setStatus('Enregistrement à reprendre · saisie conservée');
      if(e instanceof NoteHttpError&&e.status===409)setConflict(true);}}
    finally{inFlight.current=false;if(alive.current){setBusy(false);action.current=null;}}
  }
  executeRef.current=()=>{void execute();};
  async function sendImage(job:PendingNoteImage,store:boolean){
    if(inFlight.current||!active||!canEdit||headRef.current?.read_only)return;
    const controller=new AbortController();action.current=controller;inFlight.current=true;
    setBusy(true);setPasteBusy(true);setPasteError('');setStatus('Enregistrement de l’image…');
    try{
      if(store){
        try{await rememberPendingImage(imageKey,job);}
        catch{
          const existing=await readPendingImage(imageKey).catch(()=>undefined);
          if(alive.current&&!controller.signal.aborted&&existing)setPendingImage(existing);
          throw new Error(existing?'Reprenez le collage déjà en attente.':'Impossible de garder l’image sur cet appareil. Recollez-la pour réessayer.');
        }
        if(!alive.current||controller.signal.aborted)return;
        setPendingImage(job);
      }
      const response=await notesApi.paste(projectId,noteId,job.payload,job.file,controller.signal);
      if(!alive.current||controller.signal.aborted)return;
      const note=verify(response.note);
      if(response.command_id!==job.payload.command_id)throw new Error('La réponse ne correspond pas à l’image collée. Réessayez.');
      const next=makeDraft(projectId,note.id,operatorId,note);
      if(!persist(next)){setStatus('Image enregistrée sur le serveur. Reprenez le collage pour actualiser la note.');return;}
      await clearPendingImage(imageKey,job.payload.command_id);
      if(!alive.current||controller.signal.aborted)return;
      headRef.current=note;setHead(note);current.current=next;setDraft(next);setRecovery(null);setConflict(false);setRemote(null);
      setPendingImage(undefined);
      if(noteId==='new')localStorage.removeItem(imageKey);
      setStatus(note.revision===response.command_revision?'Image enregistrée.':'Image enregistrée dans l’historique. Une version plus récente est affichée.');
      onSaved(note);
    }catch(e){
      if(!alive.current||controller.signal.aborted)return;
      const stale=e instanceof NoteHttpError&&e.status===409&&e.message.startsWith('La note a changé');
      setPasteError(stale?'La note a changé. Écartez le collage local, comparez les versions et recollez l’image.':message(e));
      if(noteId!=='new'&&stale)setConflict(true);
      setStatus('');
    }finally{inFlight.current=false;if(alive.current){setBusy(false);setPasteBusy(false);action.current=null;}}
  }
  function pasteImage(file:File,insertAt:number){
    const value=current.current;
    if(!value||!writable||!pasteReady||blocked||conflict||inFlight.current||pendingImage||value.pending||
      section.current?.querySelector('.note-attachments[aria-busy="true"]')){
      setPasteError('Terminez l’enregistrement ou la reprise de la note, puis recollez l’image.');return;
    }
    try{
      if(!validNoteContent(value.content)||value.content.blocks.length>=500||value.attachment_ids.length>=20)
        throw new Error('La note ne dispose plus de place pour cette image.');
      const job={file:prepareClipboardImage(file),payload:{command_id:crypto.randomUUID(),title:value.title.trim()||'Note sans titre',
        content:value.content,expected_revision:value.expected_revision,attachment_ids:value.attachment_ids,insert_at:insertAt}};
      void sendImage(job,true);
    }catch(e){setPasteError(message(e));}
  }
  async function discardImage(){
    if(!pendingImage||inFlight.current)return;
    try{await clearPendingImage(imageKey,pendingImage.payload.command_id);setPendingImage(undefined);setPasteError('');}
    catch{setPasteError('Impossible de retirer l’image locale. Réessayez.');}
  }
  async function compare(){const controller=new AbortController();action.current=controller;setBusy(true);setError('');
    try{const note=verify(await notesApi.read(projectId,noteId,controller.signal));if(alive.current&&!controller.signal.aborted)setRemote(note);}
    catch(e){if(alive.current&&!controller.signal.aborted)setError(message(e));}finally{if(alive.current){setBusy(false);action.current=null;}}}
  function recover(){if(!recovery)return;apply(recovery);setRecovery(null);const stale=!!head&&recovery.expected_revision!==head.revision;
    setConflict(stale);setStatus(recovery.pending?'Commande en attente : reprendre son enregistrement.':stale?'Brouillon repris · comparer avec la version enregistrée.':'Brouillon local repris.');}
  const canDelete=!!head&&canEdit&&active&&!dirty&&!blocked&&!busy&&!deleting&&!recovery&&!conflict&&!imageLocked&&!markdownDraft.pending;
  async function removeNote(){
    if(!canDelete||!head||inFlight.current||section.current?.querySelector('.note-attachments[aria-busy="true"]'))return;
    if(!window.confirm(`Supprimer la note « ${head.title} » ?`))return;
    const controller=new AbortController();action.current=controller;inFlight.current=true;
    setDeleting(true);setError('');
    const command=deleteCommand.current?.expected_revision===head.revision?deleteCommand.current:
      {command_id:crypto.randomUUID(),expected_revision:head.revision};
    deleteCommand.current=command;
    try{
      const result=await notesApi.remove(projectId,noteId,command,controller.signal);
      if(!alive.current||controller.signal.aborted)return;
      if(result.deleted!==true)throw new Error('La suppression n’a pas été confirmée.');
      try{localStorage.removeItem(imageKey);}catch{/* The saved version was removed on the server. */}
      onDeleted();
    }catch(e){
      if(alive.current&&!controller.signal.aborted){
        if(e instanceof NoteHttpError&&e.status===409){setConflict(true);setError('La note a été modifiée. Comparez les versions avant de la supprimer.');}
        else setError(message(e));
      }
    }finally{inFlight.current=false;if(alive.current){setDeleting(false);action.current=null;}}
  }
  const saveButton=canEdit&&!head?.read_only&&<button type="button" className="button primary"
    disabled={!active||busy||imageLocked||!!recovery||blocked||markdownDraft.pending||(!dirty&&!draft?.pending)||(!draft?.pending&&conflict)}
    onClick={()=>void execute()}>
    {draft?.pending&&!busy?'Reprendre l’enregistrement':noteId==='new'?'Créer la note':'Enregistrer maintenant'}
  </button>;
  const secondaryActions=draft&&<>
    <div className="note-actions">
      <button type="button" className="button secondary" onClick={()=>{
        try{exportDraft(projectId,noteId,operatorId,draft);}catch(error){setError(message(error));}
      }}>Exporter le brouillon</button>
      {head&&<button type="button" className="button secondary" disabled={busy}
        onClick={()=>setHistory(value=>!value)}>{history?'Fermer l’historique':'Historique de la note'}</button>}
      {head&&canEdit&&<button type="button" className="button secondary note-delete" disabled={!canDelete}
        onClick={()=>void removeNote()}>Supprimer la note</button>}
    </div>
    {projectId===personalNotesScope&&head&&canEdit&&!!copyProjects?.length&&onCopied&&
      <CopyNote note={head} projects={copyProjects} disabled={!writable||dirty||busy||imageLocked||markdownDraft.pending} onCopied={onCopied}/>}
  </>;
  return <section ref={section} className="note-session" aria-label="Note sélectionnée" data-note-background={draft?.content.background}
    data-workspace-dirty={dirty||recovery||storageError||markdownDraft.pending||imageLocked||deleting?'true':undefined}
    data-note-volatile={storageError||pasteBusy||deleting?'true':undefined}>
    {loading&&<p role="status">Ouverture de la note…</p>}
    {error&&<p role="alert" className="document-warning">{error}</p>}
    {pasteError&&<p role="alert" className="document-warning">{pasteError}</p>}
    {pendingImage&&!pasteBusy&&<div className="note-recovery"><p role="status">Une image collée attend d’être enregistrée.</p><div className="note-actions">
      {canEdit&&<button className="button" type="button" disabled={!active||busy} onClick={()=>void sendImage(pendingImage,false)}>Reprendre le collage</button>}
      <button className="button secondary" type="button" disabled={busy} onClick={()=>void discardImage()}>Écarter le collage local</button></div></div>}
    {storageError&&<div role="alert" className="document-warning"><p>{storageError}</p>
      <button type="button" className="button secondary sm" onClick={()=>{try{exportDraft(projectId,noteId,operatorId,blocked?null:draft);}catch(e){setError(message(e));}}}>Exporter le brouillon</button>
      <button type="button" className="button secondary sm" onClick={()=>{if(draft&&persist(draft))setBlocked(false);}}>{blocked?'Remplacer le brouillon illisible par la version affichée':'Réessayer la sauvegarde locale'}</button></div>}
    {recovery&&<div role="status" className="note-recovery"><strong>Brouillon retrouvé sur cet appareil</strong><p>{recovery.title||'Note sans titre'} · {date(recovery.updated_at)}</p>
      <div className="note-actions"><button type="button" className="button" onClick={recover}>Reprendre ce brouillon</button>
        <button type="button" className="button secondary" onClick={()=>{try{exportDraft(projectId,noteId,operatorId,recovery);}catch(e){setError(message(e));}}}>Exporter le brouillon</button>
        <button type="button" className="button secondary" onClick={()=>{if(draft&&persist(draft)){setRecovery(null);setStatus(head?`Enregistrée · version ${head.revision}`:newNoteHint);}}}>Écarter ce brouillon</button></div></div>}
    {draft&&!loading&&<><div className="note-title"><div className="note-title-line"><label>Titre de la note<input className="input" maxLength={255} value={draft.title} autoFocus={workspace&&noteId==='new'} readOnly={!writable||blocked||imageLocked||(busy&&draft.pending?.kind==='restore')} onChange={e=>edit({title:e.target.value})}/></label>
      {writable&&<div className="note-background-picker" role="group" aria-label="Couleur de fond de la note">
        {Object.entries(noteBackgrounds).map(([background,label])=><button key={background} type="button"
          data-note-background={background} aria-label={`Fond ${label.toLowerCase()}`} title={`Fond ${label.toLowerCase()}`}
          aria-pressed={draft.content.background===background} disabled={blocked||imageLocked||markdownDraft.pending}
          onClick={()=>edit({content:{...draft.content,background:draft.content.background===background?undefined:background as NoteContent['background']}})}/>)}
      </div>}
      {(!head||!workspace||!!draft.pending&&!busy)&&saveButton}</div>
      <div className="note-title-meta">
      <div role="status" className="note-save-status">{deleting?'Suppression…':status}</div>
      {head&&<small>{projectId===personalNotesScope?'Dernière modification':`Dernière version par ${head.actor_id||'auteur non renseigné'}`} · {date(head.updated_at)}</small>}
      {workspace&&<details data-dismiss-outside className="note-secondary-actions"><summary>Actions de la note</summary>
        <div className="note-actions-popover">{secondaryActions}</div></details>}
      </div></div>
      {(!canEdit||head?.read_only)&&<p className="document-help">{head?.read_only?'Document Office en consultation. Son original reste conservé.':'Lecture seule : vous pouvez consulter la note et son historique.'}</p>}
      <NoteRichEditor content={draft.content} projectId={projectId} noteId={noteId} draftId={JSON.stringify([projectId,noteId,operatorId])}
        onMarkdownDraftState={setMarkdownDraft} disabled={!writable||blocked||imageLocked||(busy&&draft.pending?.kind==='restore')}
        onPasteImage={pasteImage} onChange={content=>edit({content})}/>
      {!validNoteContent(draft.content)&&<p role="alert">Le contenu dépasse les limites de la note. Réduisez le texte ou le nombre de blocs avant l’enregistrement.</p>}
      {head&&(conflict||!busy&&draft.pending)&&<div className="note-actions">
        <button type="button" className="button secondary" disabled={busy||!active} onClick={()=>void compare()}>Comparer avec la version enregistrée</button>
      </div>}
      {!workspace&&<div className="note-actions">{secondaryActions}</div>}
      {remote&&<section className="note-comparison" aria-label="Version enregistrée à comparer"><h4>{remote.title} · version {remote.revision}</h4>
        <NoteContentView content={remote.content} projectId={projectId} noteId={noteId}/><p>Votre saisie reste affichée au-dessus.</p>
        {canEdit&&conflict&&<button type="button" className="button secondary" disabled={busy||remote.read_only} onClick={()=>{
          headRef.current=remote;setHead(remote);apply({...current.current!,expected_revision:remote.revision,pending:null});setRemote(null);setConflict(false);
          setStatus('Saisie conservée sur la dernière version · enregistrement à venir');}}>Reprendre ma saisie sur cette version</button>}
        <button type="button" className="button secondary" disabled={busy||!!draft.pending&&!conflict} onClick={()=>{
          headRef.current=remote;setHead(remote);apply(makeDraft(projectId,noteId,operatorId,remote));setRemote(null);setConflict(false);setError('');setStatus(`Enregistrée · version ${remote.revision}`);
        }}>Remplacer ma saisie par cette version</button></section>}
      {head&&projectId!==personalNotesScope&&<NoteAttachments projectId={projectId} noteId={noteId} operatorId={operatorId} revision={head.revision} active={active}
        canEdit={writable&&!blocked&&!busy&&!imageLocked&&!conflict&&!draft.pending&&!markdownDraft.pending} selectedIds={draft.attachment_ids}
        onAttach={id=>{const live=current.current!;if(!live.attachment_ids.includes(id))edit({attachment_ids:[...live.attachment_ids,id]});}}
        onImage={(id,filename)=>{const live=current.current!;edit({content:{...live.content,blocks:[...live.content.blocks,{type:'image',attachment_id:id,caption:filename}]},
          attachment_ids:[...new Set([...live.attachment_ids,id])]});}}/>}
      {head?.source_kind&&<NoteSourcePanel projectId={projectId} noteId={noteId} active={active}/>}
      {head&&history&&<NoteHistoryPanel revision={head.revision} projectId={projectId} noteId={noteId} active={active} canRestore={writable&&!dirty&&!busy&&!imageLocked&&!conflict&&!draft.pending&&!storageError&&!markdownDraft.pending} onRestore={id=>void execute(id)}/>}</>}
  </section>;
}

function CopyNote({note,projects,disabled,onCopied}:{note:NoteDetail;projects:NotesProject[];disabled:boolean;onCopied:(note:NoteDetail)=>void}){
  const [target,setTarget]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const request=useRef<AbortController|null>(null);
  useEffect(()=>()=>request.current?.abort(),[]);
  async function copy(){
    if(disabled||!target||request.current)return;
    const controller=new AbortController();request.current=controller;setBusy(true);setError('');
    try{
      const result=await notesApi.copy(note.id,target,note.version_id,controller.signal);
      if(!controller.signal.aborted){
        if(result.project_id!==target)throw new Error('Le projet de la note copiée ne correspond pas à la sélection.');
        onCopied(result);
      }
    }catch(e){if(!controller.signal.aborted)setError(message(e));}
    finally{request.current=null;if(!controller.signal.aborted)setBusy(false);}
  }
  return <details className="note-project-picker" data-note-volatile={busy?'true':undefined}>
    <summary>Copier vers un projet</summary>
    <form onSubmit={e=>{e.preventDefault();void copy();}}>
      <label>Projet de destination<select className="input" value={target} disabled={busy} onChange={e=>setTarget(e.target.value)}>
        <option value="">Choisir un projet</option>{projects.map(project=><option key={project.id} value={project.id}>
          {project.code?`${project.code} — `:''}{project.title}</option>)}
      </select></label>
      <p>Les personnes qui ont accès au projet pourront lire la copie. L’original reste dans Personnel.</p>
      <button type="submit" className="button" disabled={!target||disabled||busy}>{busy?'Copie en cours…':'Copier la note'}</button>
      {error&&<p role="alert" className="document-warning">{error}</p>}
    </form>
  </details>;
}
function NoteHistoryPanel({projectId,noteId,revision,active,canRestore,onRestore}:{projectId:string;noteId:string;revision:number;active:boolean;canRestore:boolean;onRestore:(id:string)=>void}){
  const [page,setPage]=useState<NotePage<NoteHistory>|null>(null),[offset,setOffset]=useState(0),[version,setVersion]=useState<NoteVersion|null>(null);
  const [content,setContent]=useState<NoteContent|null>(null),[error,setError]=useState(''),[loading,setLoading]=useState(false);
  const request=useRef<AbortController|null>(null),alive=useAlive();
  useEffect(()=>{if(!active)return;const controller=new AbortController();setLoading(true);setError('');
    notesApi.history(projectId,noteId,offset,controller.signal).then(value=>{if(!controller.signal.aborted)setPage(value);}).catch(e=>{if(!controller.signal.aborted)setError(message(e));}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    return()=>controller.abort();},[projectId,noteId,revision,offset,active]);
  useEffect(()=>()=>request.current?.abort(),[projectId,noteId,active]);
  async function inspect(id:string){request.current?.abort();const controller=new AbortController();request.current=controller;setError('');setVersion(null);setContent(null);
    try{const value=await notesApi.version(projectId,noteId,id,controller.signal);if(!alive.current||controller.signal.aborted)return;
      if(value.project_id!==projectId||value.note_id!==noteId||value.id!==id)throw new Error('Version reçue pour une autre note');
      const bound=boundVersionContent(value);if(!validNoteContent(bound))throw new Error('Contenu historique incompatible');setVersion(value);setContent(bound);
    }catch(e){if(alive.current&&!controller.signal.aborted)setError(message(e));}}
  return <section className="note-history" aria-label="Historique de la note"><h4>Historique</h4><p className="document-help">Restaurer crée une nouvelle version. Les versions précédentes restent consultables.</p>
    {loading&&!page&&<p role="status">Lecture de l’historique…</p>}{error&&<p role="alert">{error}</p>}
    <ul>{page?.items.map(v=><li key={v.id}><div><strong>Version {v.revision} · {v.title}</strong><small>{date(v.created_at)} · {v.actor_id||'auteur source non renseigné'}</small></div>
      <button type="button" className="button secondary sm" disabled={!active} onClick={()=>void inspect(v.id)}>Consulter la version {v.revision}</button></li>)}</ul>
    {page&&<Pagination offset={page.offset} total={page.total} limit={page.limit} disabled={loading} onChange={setOffset}/>}
    {version&&content&&<section aria-label="Aperçu de la version historique"><h4>Version {version.revision} · {version.value.title}</h4>
      <NoteContentView content={content} projectId={projectId} noteId={noteId}/><button type="button" className="button secondary" disabled={!canRestore} onClick={()=>onRestore(version.id)}>Restaurer cette version</button>
      {!canRestore&&<p className="document-help">La restauration nécessite une note enregistrée et un accès en modification.</p>}</section>}
  </section>;
}
