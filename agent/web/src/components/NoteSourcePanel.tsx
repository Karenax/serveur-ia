import { useEffect, useState } from 'react';
import { noteTransferApi, type ImportResult } from '../lib/noteTransfers';
import { noteUrl } from '../lib/projectNotes';
import { AsyncDownloadLink } from './AsyncDownloadLink';
import { message } from './PlanningTasksPanel';

export function NoteSourcePanel({projectId,noteId,active}:{projectId:string;noteId:string;active:boolean}){
  const [source,setSource]=useState<ImportResult|null>(null),[error,setError]=useState(''),[loading,setLoading]=useState(false),[tick,setTick]=useState(0);
  useEffect(()=>{if(!active)return;const controller=new AbortController();setLoading(true);setError('');
    noteTransferApi.source(projectId,noteId,controller.signal).then(value=>{if(!controller.signal.aborted){if(value.note.id!==noteId||value.note.project_id!==projectId)throw new Error('Originaux reçus pour une autre note');setSource(value);}})
      .catch(e=>{if(!controller.signal.aborted)setError(message(e));}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});return()=>controller.abort();},[projectId,noteId,active,tick]);
  return <section className="note-source" aria-label="Originaux et provenance de la note"><h4>Originaux et provenance</h4>
    {loading&&<p role="status">Lecture des originaux conservés…</p>}{error&&<div role="alert"><p>{error}</p><button type="button" className="button secondary sm" onClick={()=>setTick(n=>n+1)}>Relire les originaux</button></div>}
    {source&&<><p>{source.source_descriptor.kind==='project_link'?'Note choisie dans un lien réseau du projet':'Note importée depuis une sélection de fichiers'}.
      {source.source_descriptor.relative_path&&<> Chemin choisi : <span className="document-path">{source.source_descriptor.relative_path}</span>.</>}</p>
      {Object.entries(source.source_metadata).length>0&&<dl>{Object.entries(source.source_metadata).map(([key,value])=><div key={key}><dt>{({created_by:'Créée par (source)',updated_by:'Modifiée par (source)',created_at:'Création (source)',updated_at:'Modification (source)'} as Record<string,string>)[key]||key}</dt><dd>{value}</dd></div>)}</dl>}
      <ul className="note-source-files">{source.source_files.map(file=><li key={file.relative_path}><AsyncDownloadLink href={`${noteUrl(projectId,noteId)}/originals/download?relative_path=${encodeURIComponent(file.relative_path)}`} filename={file.relative_path}>{file.relative_path}</AsyncDownloadLink>
        <small>{(file.size_bytes/1024).toLocaleString('fr-FR',{maximumFractionDigits:1})} Ko</small></li>)}</ul>
      <details><summary>Versions conservées à l’import ({source.source_versions.length})</summary><ul>{source.source_versions.map(v=><li key={v.current_version_id}>{v.source_key==='current'?'Version courante':v.source_key} · {v.source_actor||'auteur source non renseigné'}</li>)}</ul></details>
      <p className="document-help">Ces fichiers sont les copies conservées à l’import. Leur consultation ne relit pas le réseau et ne modifie pas les originaux.</p></>}
  </section>;
}
