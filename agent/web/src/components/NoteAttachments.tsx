import { useEffect, useRef, useState } from 'react';
import { message, useAlive } from './PlanningTasksPanel';
import { notesApi, noteUrl, type NoteAttachment } from '../lib/projectNotes';
import { AsyncDownloadLink } from './AsyncDownloadLink';
import { fileDigest, isTransferId, noteTransferApi, readUploadJournal, saveTransfer, uploadJournalKey, type UploadJournal } from '../lib/noteTransfers';

export function NoteAttachments({projectId,noteId,operatorId,revision,active,canEdit,selectedIds,onAttach,onImage}:{projectId:string;noteId:string;operatorId:string;revision:number;
  active:boolean;canEdit:boolean;selectedIds:string[];onAttach:(id:string)=>void;onImage:(id:string,filename:string)=>void}){
  const [items,setItems]=useState<NoteAttachment[]>([]),[error,setError]=useState(''),[notice,setNotice]=useState(''),[busy,setBusy]=useState(false),[tick,setTick]=useState(0);
  const [journal,setJournal]=useState<UploadJournal|null>(null),[journalError,setJournalError]=useState(''),[file,setFile]=useState<File|null>(null);
  const action=useRef<AbortController|null>(null),alive=useAlive(),generation=useRef(0),running=useRef(false);
  useEffect(()=>{const value=readUploadJournal(projectId,noteId,operatorId);setJournal(value.value);setJournalError(value.error);},[projectId,noteId,operatorId]);
  useEffect(()=>{if(!active)return;const controller=new AbortController();setError('');
    notesApi.attachments(projectId,noteId,controller.signal).then(value=>{if(!controller.signal.aborted){if(value.items.some(i=>i.project_id!==projectId||i.note_id!==noteId))throw new Error('Pièces reçues pour une autre note');setItems(value.items);}})
      .catch(e=>{if(!controller.signal.aborted)setError(message(e));});return()=>controller.abort();},[projectId,noteId,revision,active,tick]);
  useEffect(()=>()=>{generation.current++;action.current?.abort();},[]);
  useEffect(()=>{if(!active){generation.current++;action.current?.abort();}},[active]);
  async function upload(){
    if(!file||!canEdit||!active||running.current||journalError)return;
    running.current=true;setBusy(true);setError('');setNotice('Vérification du fichier…');const gen=++generation.current;
    const controller=new AbortController();action.current=controller;
    try{
      if(!file.size||file.size>5*1024*1024)throw new Error('Pièce jointe de 1 octet à 5 Mio requise');
      if(!file.name||file.name.length>255||/[\\/:\x00-\x1f]/.test(file.name))throw new Error('Nom de pièce jointe simple de 255 caractères maximum requis');
      const sha=await fileDigest(file);if(!alive.current||gen!==generation.current||controller.signal.aborted)return;
      if(journal&&(journal.filename!==file.name||journal.size_bytes!==file.size||journal.sha256!==sha))throw new Error('Resélectionnez le même fichier : nom, taille et contenu doivent correspondre à la commande en attente');
      const pending=journal||{format:1 as const,project_id:projectId,note_id:noteId,operator_id:operatorId,command_id:crypto.randomUUID(),filename:file.name,size_bytes:file.size,sha256:sha};
      saveTransfer(uploadJournalKey(projectId,noteId,operatorId),pending);setJournal(pending);setNotice('Copie de la pièce jointe…');
      const response=await noteTransferApi.upload(projectId,noteId,pending.command_id,file,controller.signal);
      if(!alive.current||controller.signal.aborted||gen!==generation.current)return;
      const item=response.attachment;if(item.project_id!==projectId||item.note_id!==noteId||!isTransferId(item.id)||item.filename!==pending.filename||item.size_bytes!==pending.size_bytes||item.sha256!==pending.sha256)
        throw new Error('Pièce reçue différente de la sélection ; commande conservée pour vérification');
      setItems(rows=>[...rows.filter(i=>i.id!==item.id),item]);onAttach(item.id);
      localStorage.removeItem(uploadJournalKey(projectId,noteId,operatorId));setJournal(null);setFile(null);setTick(n=>n+1);
      setNotice('Pièce copiée. Son association sera conservée lors de l’enregistrement de la note.');
    }catch(e){if(alive.current&&gen===generation.current&&!controller.signal.aborted){setError(message(e));setNotice('');}}
    finally{running.current=false;if(alive.current){setBusy(false);action.current=null;}}
  }
  return <section className="note-attachments" aria-label="Pièces jointes de la note" data-workspace-dirty={journal||busy?'true':undefined}>
    <h4>Pièces jointes</h4>{error&&<p role="alert" className="document-warning">{error}</p>}{notice&&<p role="status">{notice}</p>}
    {journalError&&<p role="alert">{journalError}</p>}
    {journal&&<p className="document-warning" role="status">Copie à reprendre : {journal.filename}. Resélectionnez ce même fichier ; la commande conservée évite un doublon.</p>}
    {canEdit&&<><label>Ajouter une pièce jointe<input className="input" type="file" disabled={!active||busy||!!journalError} onChange={e=>{setFile(e.target.files?.[0]||null);setError('');}}/></label>
      <p className="document-help">5 Mio par fichier ; 20 pièces et 25 Mio par note. Les anciennes pièces restent conservées dans l’historique.</p>
      <button type="button" className="button secondary" disabled={!active||busy||!file||!!journalError} onClick={()=>void upload()}>{journal?'Reprendre la copie':'Joindre le fichier'}</button></>}
    {!items.length&&!error&&<p className="document-help">Aucune pièce jointe.</p>}
    <ul>{items.map(item=><li key={item.id}><div><AsyncDownloadLink href={`${noteUrl(projectId,noteId)}/attachments/${encodeURIComponent(item.id)}/download`} filename={item.filename}>{item.filename}</AsyncDownloadLink>
      <small>{(item.size_bytes/1024).toLocaleString('fr-FR',{maximumFractionDigits:1})} Ko · {selectedIds.includes(item.id)?'Associée à cette version':'Conservée dans le projet'}</small></div>
      {canEdit&&<div className="note-actions">{!selectedIds.includes(item.id)&&<button type="button" className="button secondary sm" disabled={!active||busy||selectedIds.length>=20} onClick={()=>onAttach(item.id)}>Associer à cette note</button>}
        {['image/png','image/jpeg','image/webp'].includes(item.content_type)&&<button type="button" className="button secondary sm" disabled={!active||busy} onClick={()=>onImage(item.id,item.filename)}>Insérer l’image dans la note</button>}</div>}</li>)}</ul>
  </section>;
}
