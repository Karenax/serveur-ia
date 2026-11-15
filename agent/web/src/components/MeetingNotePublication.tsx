import { agentPath } from '../lib/agentRoutes';
import { useEffect, useState } from 'react';
import { meetingSessions, sessionCommand, type MeetingSession, type NotesPublication, type NotesSummary } from '../lib/meetingSessions';
import type { NoteContent } from '../lib/projectNotes';
import {noteVersionUrl} from '../lib/citationLinks';
import {NoteVersionPreview} from './NoteVersionPreview';

const fail=(error:unknown)=>error instanceof Error?error.message:String(error);
const key=(id:string)=>`agent.meeting-publication.v1.${id}`;
const empty=():NotesSummary=>({overview:'',decisions:[],actions:[],open_points:[]});
type DraftFields={kind:'decisions'|'actions'|'open_points';text:string;blockIndex:string;quote:string;owner:string;due:string};
function saved(id:string){try{return JSON.parse(localStorage.getItem(key(id))||'null') as {summary:NotesSummary;pending:NotesPublication|null;version:string;fields?:DraftFields}|null;}catch{return null;}}
function blocks(content:NoteContent){return content.blocks.flatMap((block,index)=>{
  if(block.type!=='heading'&&block.type!=='paragraph')return [];
  const quote=block.runs.map(run=>run.text).join('');return quote.trim()?[{index,quote}]:[];
});}
export function MeetingNotePublication({session,dirty,unfinished,onPublished}:{session:MeetingSession;dirty:boolean;unfinished:boolean;
  onPublished:(session:MeetingSession)=>void;onOpenProject:(id:string,tab:string)=>void}){
  const [initial]=useState(()=>saved(session.id));
  const [summary,setSummary]=useState<NotesSummary>(initial?.summary||empty),[pending,setPending]=useState<NotesPublication|null>(initial?.pending||null);
  const [version,setVersion]=useState(initial?.version||session.note_version_id||''),[error,setError]=useState(''),[busy,setBusy]=useState(false),[reviewed,setReviewed]=useState(false);
  const [kind,setKind]=useState<'decisions'|'actions'|'open_points'>(initial?.fields?.kind||'decisions'),[text,setText]=useState(initial?.fields?.text||''),[blockIndex,setBlockIndex]=useState(initial?.fields?.blockIndex||''),[quote,setQuote]=useState(initial?.fields?.quote||'');
  const [owner,setOwner]=useState(initial?.fields?.owner||''),[due,setDue]=useState(initial?.fields?.due||'');
  const choices=blocks(session.note?.content||{version:1,blocks:[]});
  const persist=(value:NotesSummary,command:NotesPublication|null,nextVersion=version)=>{
    try{localStorage.setItem(key(session.id),JSON.stringify({summary:value,pending:command,version:nextVersion,fields:{kind,text,blockIndex,quote,owner,due}}));return true;}
    catch{setError('Le brouillon de publication ne peut pas être conservé. Gardez cette page ouverte et rétablissez le stockage du navigateur.');return false;}
  };
  useEffect(()=>{
    if(!session.published_meeting_id)persist(summary,pending);
  },[kind,text,blockIndex,quote,owner,due,session.id,session.published_meeting_id]);
  const hasDraft=!!summary.overview.trim()||summary.decisions.length>0||summary.actions.length>0||summary.open_points.length>0||
    kind!=='decisions'||!!(text||blockIndex||quote||owner||due);
  useEffect(()=>{
    const current=session.note_version_id||'';
    if(!pending&&!hasDraft&&version!==current){setVersion(current);setReviewed(false);persist(summary,null,current);}
  },[session.note_version_id,version,pending,hasDraft]);
  const edit=(value:NotesSummary)=>{setSummary(value);setReviewed(false);persist(value,pending);};
  const add=()=>{
    const block=choices.find(item=>item.index===Number(blockIndex));
    if(!text.trim()||blockIndex===''||!quote.trim()||!block?.quote.includes(quote))return;
    const item={text:text.trim(),block_index:Number(blockIndex),quote,...(kind==='actions'?{owner,due_date:due}:{})};
    edit({...summary,[kind]:[...summary[kind],item]});setText('');setQuote('');setBlockIndex('');setOwner('');setDue('');
  };
  const publish=async()=>{
    if(busy||dirty||unfinished||!session.note_version_id||!session.note_revision)return;setBusy(true);setError('');
    try{
      const command=pending||{...sessionCommand(session.revision),expected_note_revision:session.note_revision,
        expected_note_version_id:session.note_version_id,summary};
      if(!persist(summary,command))return;setPending(command);
      const result=await meetingSessions.publishNotes(session.id,command);
      localStorage.removeItem(key(session.id));setPending(null);onPublished(result.session);
    }catch(failure){setError(fail(failure));}finally{setBusy(false);}
  };
  if(session.published_meeting_id)return <section className="meeting-notes-publication"><h3>Compte rendu publié</h3>
    <p>La version relue des notes est conservée avec ses citations. Les actions peuvent être converties en tâches depuis le projet.</p>
    <a className="button secondary" href={agentPath(`/app/projects/${encodeURIComponent(session.project_id!)}/reviews?meeting=${encodeURIComponent(session.published_meeting_id)}`)}>Ouvrir le compte rendu</a>
    {session.project_id&&session.note_id&&session.published_note_version_id&&<><a href={agentPath(noteVersionUrl(session.project_id,session.note_id,session.published_note_version_id))} target="_blank" rel="noreferrer">Ouvrir la version des notes publiée</a>
      <NoteVersionPreview citation={{source_url:noteVersionUrl(session.project_id,session.note_id,session.published_note_version_id)}} label="Lire les notes publiées"/></>}</section>;
  const stale=version!==session.note_version_id;
  const validItems=['decisions','actions','open_points'].some(value=>summary[value as 'decisions'].length>0);
  return <section className="meeting-notes-publication" aria-label="Publication du compte rendu des notes">
    <h3>Compte rendu à partir des notes</h3><p>Relisez la synthèse et citez le bloc d’origine pour chaque décision, action ou point ouvert. La publication crée le compte rendu et ses actions ; la conversion en tâches reste explicite.</p>
    <p>Note enregistrée : version {session.note_revision ?? 'à enregistrer'}{dirty?' · corrections à enregistrer':''}</p>
    {session.project_id&&session.note_id&&version&&<><a href={agentPath(noteVersionUrl(session.project_id,session.note_id,version))} target="_blank" rel="noreferrer">Ouvrir la version citée des notes</a>
      <NoteVersionPreview citation={{source_url:noteVersionUrl(session.project_id,session.note_id,version)}}/></>}
    {unfinished&&<p role="status">{session.kind==='note'?'Terminez la prise de notes avant de publier : utilisez « Terminer la prise de notes » en haut de la séance.':'Terminez et conservez la séance avant de publier.'}</p>}
    {stale&&<p role="alert">La note a changé depuis la préparation du compte rendu. Relisez vos éléments et leurs citations.</p>}
    {error&&<p role="alert">{error}</p>}
    <fieldset disabled={busy||!!pending||dirty||unfinished||!session.note_id}>
      <label>Synthèse relue<textarea maxLength={12000} rows={5} value={summary.overview} onChange={event=>edit({...summary,overview:event.target.value})}/></label>
      <div className="meeting-publication-add"><label>Élément du compte rendu<select value={kind} onChange={event=>setKind(event.target.value as typeof kind)}>
        <option value="decisions">Décision</option><option value="actions">Action</option><option value="open_points">Point ouvert</option></select></label>
        <label>Formulation<input maxLength={kind==='actions'?255:2000} value={text} onChange={event=>setText(event.target.value)}/></label>
        <label>Bloc cité<select value={blockIndex} onChange={event=>{setBlockIndex(event.target.value);setQuote(choices.find(item=>item.index===Number(event.target.value))?.quote.slice(0,1500)||'');}}>
          <option value="">Choisir un paragraphe ou titre</option>{choices.map(item=><option key={item.index} value={item.index}>Bloc {item.index+1} · {item.quote.slice(0,75)}</option>)}</select></label>
        <label>Extrait exact de la note<textarea maxLength={1500} rows={2} value={quote} onChange={event=>setQuote(event.target.value)}/></label>
        {kind==='actions'&&<><label>Responsable<input maxLength={120} value={owner} onChange={event=>setOwner(event.target.value)}/></label>
          <label>Échéance<input type="date" value={due} onChange={event=>setDue(event.target.value)}/></label></>}
        <button type="button" disabled={!text.trim()||blockIndex===''||!quote.trim()||!choices.find(item=>item.index===Number(blockIndex))?.quote.includes(quote)} onClick={add}>Ajouter au compte rendu</button>
      </div>
      {(['decisions','actions','open_points'] as const).map(group=><div key={group}><h4>{({decisions:'Décisions',actions:'Actions',open_points:'Points ouverts'})[group]}</h4>
        <ul>{summary[group].map((item,index)=><li key={index}><strong>{item.text}</strong><blockquote>{item.quote}</blockquote><small>Bloc {item.block_index+1} de la version citée</small>
          <button type="button" onClick={()=>edit({...summary,[group]:summary[group].filter((_,i)=>i!==index)})}>Retirer cet élément</button></li>)}</ul></div>)}
      <label><input type="checkbox" checked={reviewed} onChange={event=>setReviewed(event.target.checked)}/>J’ai relu la synthèse, les éléments et leurs sources dans cette version des notes.</label>
    </fieldset>
    {stale&&!pending&&<button type="button" disabled={dirty||unfinished} onClick={()=>{setVersion(session.note_version_id||'');persist(summary,null,session.note_version_id||'');setReviewed(false);}}>Préparer sur la version actuelle après relecture</button>}
    <button type="button" disabled={busy||dirty||unfinished||(!pending&&(!reviewed||stale||(!summary.overview.trim()&&!validItems)))||!session.project_id||!session.note_id}
      onClick={()=>void publish()}>{busy?'Publication…':pending?'Reprendre la publication conservée':'Publier le compte rendu relu'}</button>
    {!!pending&&<p>La commande conserve la version approuvée. Une reprise utilise exactement cette publication, même si la note a été modifiée ensuite.</p>}
  </section>;
}
