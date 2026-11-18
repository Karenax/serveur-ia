import {useEffect,useState} from 'react';
import { agentPath } from '../lib/agentRoutes';
import {citationSourceUrl,noteVersionIdentity,stagedNoteVersionIdentity,type CitationTarget} from '../lib/citationLinks';
import {boundVersionContent,notesApi,validNoteContent,type NoteContent} from '../lib/projectNotes';
import {meetingSessions} from '../lib/meetingSessions';
import {NoteContentView} from './NoteContentView';
import './project-notes.css';

type Target={kind:'erp';projectId:string;noteId:string;versionId:string;url:string}|{kind:'staging';sessionId:string;versionId:string;url:string};
type Preview={title:string;revision:number;date:string|null;content:NoteContent;projectId:string;noteId:string};
function targetOf(citation:CitationTarget):Target|null{
  const url=citationSourceUrl(citation),note=noteVersionIdentity(url);
  if(note&&url)return {kind:'erp',...note,url};
  const staging=stagedNoteVersionIdentity(url);
  if(staging&&url)return {kind:'staging',...staging,url};
  return null;
}
const message=(failure:unknown)=>failure instanceof Error?failure.message:String(failure);
export function NoteVersionPreview({citation,label='Lire la version citée'}:{citation:CitationTarget;label?:string}){
  const target=targetOf(citation);
  return target?<VersionPreview key={JSON.stringify(target)} target={target} label={label}/>:null;
}
function VersionPreview({target,label}:{target:Target;label:string}){
  const [open,setOpen]=useState(false),[preview,setPreview]=useState<Preview|null>(null),[loading,setLoading]=useState(false),[error,setError]=useState(''),[retry,setRetry]=useState(0);
  useEffect(()=>{
    if(!open)return;
    const controller=new AbortController();setLoading(true);setPreview(null);setError('');
    const load=async():Promise<Preview>=>{
      if(target.kind==='erp'){
        const value=await notesApi.version(target.projectId,target.noteId,target.versionId,controller.signal);
        if(!value||value.project_id!==target.projectId||value.note_id!==target.noteId||value.id!==target.versionId)
          throw new Error('La version reçue ne correspond pas à la note citée.');
        if(!Number.isInteger(value.revision)||value.revision<1||typeof value.value?.title!=='string'||!validNoteContent(value.value?.content)||
          typeof value.created_at!=='string'||!Number.isFinite(Date.parse(value.created_at))||!value.attachment_bindings||typeof value.attachment_bindings!=='object')
          throw new Error('Le contenu de cette version de note est incompatible avec l’aperçu.');
        const content=boundVersionContent(value);
        if(!validNoteContent(content))throw new Error('Les pièces de cette version ne peuvent pas être affichées.');
        return {title:value.value.title,revision:value.revision,date:value.created_at,content,projectId:target.projectId,noteId:target.noteId};
      }
      const note=await meetingSessions.noteVersion(target.sessionId,target.versionId,controller.signal);
      if(note?.session_id!==target.sessionId||note?.id!==target.versionId)
        throw new Error('La version reçue ne correspond pas au brouillon de séance cité.');
      if(typeof note.title!=='string'||!Number.isInteger(note.revision)||note.revision<1||!validNoteContent(note.content)||
        !/^[a-f0-9]{64}$/i.test(note.sha256)||typeof note.created_at!=='string'||!Number.isFinite(Date.parse(note.created_at)))
        throw new Error('Le contenu de cette version de brouillon est incompatible avec l’aperçu.');
      if(note.content.blocks.some(block=>block.type==='image'))throw new Error('Ce brouillon sans projet ne fournit pas de liaison exacte pour ses images.');
      return {title:note.title,revision:note.revision,date:note.created_at,content:note.content,projectId:'',noteId:''};
    };
    void load().then(value=>{if(!controller.signal.aborted)setPreview(value);})
      .catch(failure=>{if(!controller.signal.aborted)setError(message(failure));})
      .finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    return()=>controller.abort();
  },[open,retry,target.url,target.versionId]);
  return <div className="note-version-preview">
    <button type="button" className="button secondary sm" aria-expanded={open} onClick={()=>setOpen(value=>!value)}>{open?'Fermer l’aperçu de version':label}</button>
    {open&&<section aria-label="Aperçu de la version citée" className="note-history">
      {loading&&<p role="status">Chargement de la version citée…</p>}
      {error&&<div role="alert"><p>{error}</p><button type="button" onClick={()=>setRetry(value=>value+1)}>Relire cette version</button></div>}
      {preview&&<><h4>{preview.title} · version {preview.revision}</h4>
        <p>{preview.date?<time dateTime={preview.date}>{new Intl.DateTimeFormat('fr-FR',{dateStyle:'medium',timeStyle:'short'}).format(new Date(preview.date))}</time>:'Date de cette version de brouillon non fournie.'} · Lecture seule</p>
        <NoteContentView content={preview.content} projectId={preview.projectId} noteId={preview.noteId}/>
        <a href={agentPath(target.url)} download={`note-version-${target.versionId}.json`}>Télécharger cette version de note</a>
      </>}
    </section>}
  </div>;
}
