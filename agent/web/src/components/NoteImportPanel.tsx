import { useEffect, useRef, useState } from 'react';
import { api, type NetworkLink } from '../lib/api';
import { NoteHttpError, validNoteContent } from '../lib/projectNotes';
import { importJournalKey, isTransferId, noteTransferApi, readImportJournal, sameInventory, saveTransfer, selectNoteFiles,
  type ImportJournal, type ImportPreview, type ImportResult, type NoteSource, type UploadFileSelection } from '../lib/noteTransfers';
import { message, useAlive } from './PlanningTasksPanel';
import { NoteContentView } from './NoteRichEditor';

export function NoteImportPanel({projectId,operatorId,active,canEdit,onImported}:{projectId:string;operatorId:string;active:boolean;canEdit:boolean;onImported:(id:string)=>void}){
  const [source,setSource]=useState<NoteSource>({kind:'upload',link_id:null,relative_path:''}),[mode,setMode]=useState<'rich'|'plain'>('rich');
  const [selection,setSelection]=useState<UploadFileSelection|null>(null),[planned,setPlanned]=useState<string>(()=>crypto.randomUUID()),[preview,setPreview]=useState<ImportPreview|null>(null);
  const [pending,setPending]=useState<ImportJournal|null>(null),[journalError,setJournalError]=useState(''),[confirmed,setConfirmed]=useState(false),[needsSources,setNeedsSources]=useState(false);
  const [links,setLinks]=useState<NetworkLink[]>([]),[linkError,setLinkError]=useState(''),[error,setError]=useState(''),[status,setStatus]=useState('');
  const [busy,setBusy]=useState(false),[version,setVersion]=useState(0);
  const action=useRef<AbortController|null>(null),generation=useRef(0),alive=useAlive(),running=useRef(false);
  useEffect(()=>{const local=readImportJournal(projectId,operatorId);setPending(local.value);setJournalError(local.error);
    if(local.value){setSource(local.value.command.source);setMode(local.value.command.mode);setPlanned(local.value.command.planned_note_id);}
  },[projectId,operatorId]);
  useEffect(()=>{if(!active||source.kind!=='project_link')return;let ignore=false;setLinkError('');
    api.networkLinks(projectId).then(value=>{if(!ignore)setLinks(value);}).catch(e=>{if(!ignore)setLinkError(message(e));});return()=>{ignore=true;};
  },[projectId,active,source.kind]);
  useEffect(()=>()=>{generation.current++;action.current?.abort();},[]);
  useEffect(()=>{if(!active){generation.current++;action.current?.abort();}},[active]);
  const invalid=()=>{setPreview(null);setConfirmed(false);setError('');setVersion(0);};
  async function choose(files:File[]){if(running.current||!active||!canEdit||journalError)return;
    running.current=true;setBusy(true);setError('');setStatus('Vérification de la sélection…');const gen=++generation.current;
    try{const selected=await selectNoteFiles(files);if(!alive.current||gen!==generation.current)return;
      if(pending&&!sameInventory(pending.inventory,selected.inventory))throw new Error('La sélection doit contenir exactement les mêmes fichiers que l’import en attente');
      setSelection(selected);if(!pending)invalid();setStatus(`${selected.files.length} fichier(s) sélectionné(s) · originaux conservés lors de l’import`);
    }catch(e){if(alive.current&&gen===generation.current){setError(message(e));setStatus('');}}
    finally{running.current=false;if(alive.current)setBusy(false);}}
  async function inspect(){if(!active||!canEdit||running.current||pending||journalError)return;
    const controller=new AbortController();action.current=controller;running.current=true;setBusy(true);setError('');setStatus('Lecture et conversion de la note…');invalid();
    try{const value=await noteTransferApi.preview(projectId,planned,mode,source,selection,controller.signal);
      if(!alive.current||controller.signal.aborted)return;
      if(value.format!=='agent-note-source-preview'||value.version!==1||value.planned_note_id!==planned||!isTransferId(planned)||
        !/^[0-9a-f]{64}$/.test(value.preview_sha256)||!Array.isArray(value.versions)||value.versions.some(v=>v.content===null?value.can_apply:!validNoteContent(v.content))||
        (source.kind==='upload'&&!sameInventory(selection!.inventory,value.files)))throw new Error('Aperçu reçu différent de la sélection ou incompatible avec les notes');
      setPreview(value);setVersion(Math.max(0,value.versions.length-1));setStatus(value.can_apply?'Aperçu prêt · import à valider':'Import bloqué · consultez les points à vérifier');
    }catch(e){if(alive.current&&!controller.signal.aborted){setError(message(e));setStatus('');}}
    finally{running.current=false;if(alive.current){setBusy(false);action.current=null;}}}
  function accepted(response:ImportResult,journal:ImportJournal){
    if(response.command_id!==journal.command.command_id||response.note.project_id!==projectId||response.note.id!==journal.command.planned_note_id||!validNoteContent(response.note.content))
      throw new Error('Reçu d’import différent de la commande ; conserver la commande pour vérification');
    localStorage.removeItem(importJournalKey(projectId,operatorId));setPending(null);setSelection(null);setPreview(null);setConfirmed(false);setNeedsSources(false);
    setPlanned(crypto.randomUUID());setStatus('Note importée avec ses originaux et son historique.');onImported(response.note.id);
  }
  async function apply(retry=false){if(!active||!canEdit||running.current||journalError)return;
    if(!pending&&(!preview?.can_apply||!confirmed))return;
    running.current=true;const controller=new AbortController();action.current=controller;setBusy(true);setError('');setStatus(retry?'Reprise de l’import…':'Import de la note et de ses originaux…');
    try{
      const journal:ImportJournal=pending||{format:1,project_id:projectId,operator_id:operatorId,command:{command_id:crypto.randomUUID(),planned_note_id:planned,
        expected_preview_sha256:preview!.preview_sha256,mode,source},inventory:source.kind==='upload'?selection!.inventory:[]};
      saveTransfer(importJournalKey(projectId,operatorId),journal);setPending(journal);
      let files=selection;
      if(journal.command.source.kind==='upload'){
        if(!files)throw new Error('Resélectionnez les mêmes fichiers pour reprendre cet import');
        files=await selectNoteFiles(files.files);
        if(!alive.current||controller.signal.aborted)return;
        if(!sameInventory(journal.inventory,files.inventory))throw new Error('Les fichiers ont changé depuis l’aperçu ; la commande précédente est conservée');
      }
      const result=await noteTransferApi.apply(projectId,journal.command,files,controller.signal);
      if(alive.current&&!controller.signal.aborted)accepted(result,journal);
    }catch(e){if(alive.current&&!controller.signal.aborted){setError(message(e));setStatus('Commande conservée · vérifier la confirmation avant toute nouvelle tentative');}}
    finally{running.current=false;if(alive.current){setBusy(false);action.current=null;}}}
  async function confirmPrevious(){if(!pending||!canEdit||!active||running.current)return;
    running.current=true;const controller=new AbortController();action.current=controller;setBusy(true);setError('');setStatus('Vérification de la commande déjà envoyée…');
    try{const result=await noteTransferApi.replay(projectId,pending.command,controller.signal);if(alive.current&&!controller.signal.aborted)accepted(result,pending);}
    catch(e){if(alive.current&&!controller.signal.aborted){if(e instanceof NoteHttpError&&e.status===404){setNeedsSources(true);setStatus('Aucun import confirmé. Reprenez la même commande depuis les sources choisies.');}
      else{setError(message(e));setStatus('Commande conservée · aucun nouvel import lancé');}}}
    finally{running.current=false;if(alive.current){setBusy(false);action.current=null;}}}
  const disabled=!active||!canEdit||busy||!!journalError;
  const selectedVersion=preview?.versions[version];
  return <section className="note-import" aria-label="Importer une note" data-workspace-dirty={pending||busy?'true':undefined}>
    <header><h4>Importer une note</h4><p>Choisissez une source, vérifiez l’aperçu puis créez une copie dans ce projet.</p></header>
    {error&&<p role="alert" className="document-warning">{error}</p>}{journalError&&<p role="alert" className="document-warning">{journalError}</p>}{status&&<p role="status">{status}</p>}
    {pending&&<div className="note-recovery"><p>Une commande d’import attend confirmation. Elle reste conservée sur cet appareil.</p>
      <button type="button" className="button secondary" disabled={disabled} onClick={()=>void confirmPrevious()}>Vérifier l’import déjà envoyé</button></div>}
    <div className="note-import-fields"><label>Source de la note<select className="input" value={source.kind} disabled={disabled||!!pending}
      onChange={e=>{setSource({kind:e.target.value as NoteSource['kind'],link_id:null,relative_path:''});setSelection(null);invalid();}}>
      <option value="upload">Fichiers ou dossier sélectionnés</option><option value="project_link">Lien réseau de ce projet</option></select></label>
      <label>Mode d’import<select className="input" value={mode} disabled={disabled||!!pending} onChange={e=>{setMode(e.target.value as 'rich'|'plain');invalid();}}>
        <option value="rich">Conserver la mise en forme</option><option value="plain">Texte simple — sans mise en forme</option></select></label></div>
    {source.kind==='upload'?<><div key="upload" className="note-import-fields">
      <label>Fichier(s) de la note<input type="file" className="input" multiple disabled={disabled} onChange={e=>void choose(Array.from(e.target.files||[]))}/></label>
      <label>Dossier d’une note XPilot<input type="file" className="input" {...{webkitdirectory:''}} multiple disabled={disabled} onChange={e=>void choose(Array.from(e.target.files||[]))}/></label></div>
      <p className="document-help">HTML, TXT ou Markdown ; un fichier Office en consultation ; ou le dossier complet d’une note XPilot avec son historique et ses pièces. 200 fichiers et 50 Mio maximum.</p>
      {selection&&<ul className="note-source-files">{selection.inventory.map(file=><li key={file.relative_path}>{file.relative_path}<small>{(file.size_bytes/1024).toLocaleString('fr-FR',{maximumFractionDigits:1})} Ko</small></li>)}</ul>}</>:
      <><div key="network" className="note-import-fields"><label>Lien du projet<select className="input" value={source.link_id||''} disabled={disabled||!!pending} onChange={e=>{setSource({...source,link_id:e.target.value||null});invalid();}}>
        <option value="">Choisir un lien</option>{pending&&source.link_id&&!links.some(l=>l.id===source.link_id)&&<option value={source.link_id}>Lien de la commande conservée</option>}
        {links.map(l=><option key={l.id} value={l.id} disabled={!l.chemin}>{l.libelle||l.code} · {l.chemin||'Chemin non renseigné'}</option>)}</select></label>
        <label>Fichier ou dossier de note dans ce lien<input className="input" value={source.relative_path} maxLength={1024} disabled={disabled||!!pending}
          onChange={e=>{setSource({...source,relative_path:e.target.value});invalid();}} placeholder="Notes/Revue LED"/></label></div>
        {linkError&&<p role="alert">{linkError}</p>}<p className="document-help">Choisissez une seule note dans un lien déclaré du projet. L’accès dépend des dossiers autorisés sur le serveur ; aucun parcours du réseau n’est lancé automatiquement.</p></>}
    {!pending&&<button type="button" className="button secondary" disabled={disabled||(source.kind==='upload'?!selection:!source.link_id)} onClick={()=>void inspect()}>Afficher l’aperçu de l’import</button>}
    {needsSources&&pending&&<button type="button" className="button" disabled={disabled||(source.kind==='upload'?!selection:false)} onClick={()=>void apply(true)}>Reprendre le même import</button>}
    {preview&&<section className="note-import-preview" aria-label="Aperçu de l’import"><h4>{preview.title}</h4>
      <p>{preview.files.length} original(aux) conservé(s) · {preview.versions.length||1} version(s) · {preview.embedded_images?.length||0} image(s) intégrée(s).</p>
      {!preview.editable&&<p className="document-warning">Document Office conservé en consultation. Son original sera téléchargeable.</p>}
      {preview.versions.length>1&&<label>Version source à consulter<select className="input" value={version} onChange={e=>setVersion(Number(e.target.value))}>
        {preview.versions.map((v,i)=><option key={v.source_key} value={i}>{v.source_key==='current'?'Version courante':v.source_key} · {v.source_actor||'auteur non renseigné'}</option>)}</select></label>}
      {selectedVersion&&<><p className="document-help">Auteur source : {selectedVersion.source_actor||'non renseigné'}</p>{selectedVersion.content?<NoteContentView content={selectedVersion.content} projectId={projectId} noteId={planned} preview/>:<p className="document-warning">Cette version ne peut pas être convertie dans le mode choisi. Consultez les points ci-dessous ou choisissez le mode texte simple.</p>}
        {selectedVersion.issues?.map((issue,i)=><p key={i} className="document-warning">{issue.message} · {issue.path}</p>)}</>}
      {preview.issues?.map((issue,i)=><p key={i} className="document-warning">{issue.message} · {issue.path}</p>)}
      {!preview.can_apply&&<p role="alert">L’import est bloqué. Corrigez la sélection ou choisissez explicitement le mode texte simple pour obtenir un nouvel aperçu.</p>}
      {!pending&&<><label className="document-confirm"><input type="checkbox" checked={confirmed} disabled={disabled||!preview.can_apply} onChange={e=>setConfirmed(e.target.checked)}/>J’ai vérifié la note, ses versions et les originaux à conserver.</label>
        <button type="button" className="button" disabled={disabled||!confirmed||!preview.can_apply} onClick={()=>void apply()}>Importer cette note dans le projet</button></>}
    </section>}
  </section>;
}
