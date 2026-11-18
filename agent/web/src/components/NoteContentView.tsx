import {type ReactNode} from 'react';
import {agentPath} from '../lib/agentRoutes';
import {noteUrl,safeNoteLink,type NoteContent,type NoteRun} from '../lib/projectNotes';
import './note-editor.css';

export function renderNoteRuns(runs:NoteRun[]):ReactNode{return runs.map((run,i)=>{
  let node:ReactNode=run.text;
  for(const mark of run.marks)node=mark==='bold'?<strong>{node}</strong>:mark==='italic'?<em>{node}</em>:
    mark==='underline'?<u>{node}</u>:mark==='strike'?<s>{node}</s>:<code>{node}</code>;
  if(run.href&&safeNoteLink(run.href))node=<a href={run.href} target="_blank" rel="noopener noreferrer">{node}</a>;
  return <span key={i} style={run.color&&/^#[0-9a-f]{6}$/i.test(run.color)?{color:run.color}:undefined}>{node}</span>;
});}

export function NoteContentView({content,projectId,noteId,preview=false}:{content:NoteContent;projectId:string;noteId:string;preview?:boolean}){
  return <div className="note-content-view">{content.blocks.map((b,i)=>b.type==='paragraph'?<p key={i} style={{textAlign:b.align}}>{renderNoteRuns(b.runs)}</p>:
    b.type==='heading'?<div key={i} role="heading" aria-level={b.level} className={`note-heading level-${b.level}`}>{renderNoteRuns(b.runs)}</div>:
    b.type==='image'?<figure key={i}>{preview?<p className="note-image-placeholder">Image conservée à l’import : {b.caption||'sans légende'}</p>:<img src={agentPath(`${noteUrl(projectId,noteId)}/attachments/${encodeURIComponent(b.attachment_id)}/image`)} alt={b.caption}/>}<figcaption>{b.caption}</figcaption></figure>:
    b.type==='table'?<div key={i} className="note-table-scroll"><table><tbody>{b.rows.map((row,r)=><tr key={r}>{row.map((cell,c)=>r===0&&b.header?<th key={c}>{renderNoteRuns(cell)}</th>:<td key={c}>{renderNoteRuns(cell)}</td>)}</tr>)}</tbody></table></div>:
    <ol key={i} className={`note-list ${b.kind}`}>{b.items.map((item,n)=><li key={n} style={{marginLeft:item.indent*16}}>{b.kind==='checklist'&&<input type="checkbox" checked={item.checked} disabled aria-label={`Case ${n+1}`}/>}<span>{renderNoteRuns(item.runs)}</span></li>)}</ol>)}</div>;
}
