import { agentPath } from '../lib/agentRoutes';
import { useEffect, useRef, useState, type ClipboardEvent, type KeyboardEvent } from 'react';
import { noteUrl, safeNoteLink, validNoteContent, type NoteBlock, type NoteContent, type NoteMark, type NoteRun } from '../lib/projectNotes';
import {markdownDraftKey,noteToMarkdown,parseNoteMarkdown,readMarkdownDraft,type MarkdownDraft,type MarkdownDraftState} from '../lib/noteMarkdown';
import {NoteContentView} from './NoteContentView';
import './note-editor.css';
export {NoteContentView,renderNoteRuns} from './NoteContentView';

const tags:Record<NoteMark,string>={bold:'strong',italic:'em',underline:'u',strike:'s',code:'code'};
function paintRuns(element:HTMLElement,runs:NoteRun[]){
  const nodes=runs.map(run=>{
    let node:Node=document.createTextNode(run.text);
    for(const mark of run.marks){const next=document.createElement(tags[mark]);next.append(node);node=next;}
    if(run.href&&safeNoteLink(run.href)){const a=document.createElement('a');a.href=run.href;a.append(node);node=a;}
    if(run.color&&/^#[0-9a-f]{6}$/i.test(run.color)){const span=document.createElement('span');span.style.color=run.color;span.append(node);node=span;}
    return node;
  });
  element.replaceChildren(...nodes);
}
function color(value:string):string|null{
  if(/^#[0-9a-f]{6}$/i.test(value))return value;
  const rgb=value.match(/^rgb\(\s*(\d+),\s*(\d+),\s*(\d+)\s*\)$/);
  return rgb?'#'+rgb.slice(1).map(n=>Number(n).toString(16).padStart(2,'0')).join(''):null;
}
export function readNoteRuns(element:HTMLElement):NoteRun[]{
  const result:NoteRun[]=[];
  function append(text:string,style:Omit<NoteRun,'text'>){
    const normalized=text.replace(/[\x00-\x08\x0b-\x1f]/g,'');
    for(let i=0;i<normalized.length;i+=5000){const part=normalized.slice(i,i+5000),last=result[result.length-1];
      if(last&&JSON.stringify({...last,text:''})===JSON.stringify({...style,text:''})&&last.text.length+part.length<=5000)last.text+=part;
      else result.push({text:part,...style});}
  }
  function walk(node:Node,style:Omit<NoteRun,'text'>){
    if(node.nodeType===Node.TEXT_NODE){append(node.textContent||'',style);return;}
    if(!(node instanceof HTMLElement)||['SCRIPT','STYLE','IMG','IFRAME','OBJECT','INPUT'].includes(node.tagName))return;
    if(node.tagName==='BR'){append('\n',style);return;}
    const marks=new Set(style.marks);
    if(['B','STRONG'].includes(node.tagName)||['bold','700','800','900'].includes(node.style.fontWeight))marks.add('bold');
    if(['I','EM'].includes(node.tagName)||node.style.fontStyle==='italic')marks.add('italic');
    if(node.tagName==='U'||node.style.textDecoration.includes('underline'))marks.add('underline');
    if(['S','STRIKE','DEL'].includes(node.tagName)||node.style.textDecoration.includes('line-through'))marks.add('strike');
    if(node.tagName==='CODE')marks.add('code');
    const href=node.tagName==='A'?node.getAttribute('href'):null;
    const next={marks:[...marks],href:href&&safeNoteLink(href)?href:style.href,color:color(node.style.color)||color(node.getAttribute('color')||'')||style.color};
    if(['DIV','P'].includes(node.tagName)&&result.length&&!result[result.length-1].text.endsWith('\n'))append('\n',style);
    for(const child of node.childNodes)walk(child,next);
  }
  for(const child of element.childNodes)walk(child,{marks:[],href:null,color:null});
  return result;
}
function RunsInput({runs,onChange,label,onFocus,onKeyDown,inputId,disabled=false}:{runs:NoteRun[];onChange:(runs:NoteRun[])=>void;label:string;onFocus:()=>void;
  onKeyDown?:(event:KeyboardEvent<HTMLDivElement>)=>void;inputId:string;disabled?:boolean}){
  const ref=useRef<HTMLDivElement>(null),current=useRef(''),composing=useRef(false);
  useEffect(()=>{const signature=JSON.stringify(runs);if(ref.current&&current.current!==signature){paintRuns(ref.current,runs);current.current=signature;}},[runs]);
  useEffect(()=>{const input=ref.current;if(!input)return;const sync=()=>{current.current=JSON.stringify(readNoteRuns(input));};
    input.addEventListener('note-format-applied',sync);return()=>input.removeEventListener('note-format-applied',sync);},[]);
  const emit=()=>{if(ref.current&&!composing.current){const value=readNoteRuns(ref.current);current.current=JSON.stringify(value);onChange(value);}};
  return <div ref={ref} className="note-runs" data-note-input={inputId} contentEditable={!disabled} suppressContentEditableWarning role="textbox" aria-multiline="true"
    aria-label={label} aria-readonly={disabled} onFocus={onFocus} onInput={emit} onBlur={emit}
    onKeyDown={onKeyDown}
    onCompositionStart={()=>{composing.current=true;}} onCompositionEnd={()=>{composing.current=false;emit();}}
    onPaste={e=>{e.preventDefault();if(disabled)return;const value=e.clipboardData.getData('text/plain').replace(/[\x00-\x08\x0b-\x1f]/g,'');
      const selection=window.getSelection();if(!selection?.rangeCount||!ref.current?.contains(selection.anchorNode))return;
      const range=selection.getRangeAt(0);range.deleteContents();const text=document.createTextNode(value);range.insertNode(text);range.setStartAfter(text);range.collapse(true);selection.removeAllRanges();selection.addRange(range);emit();}}
    onDrop={e=>e.preventDefault()}/>;
}
type NoteEditorProps={content:NoteContent;onChange:(value:NoteContent)=>void|boolean;projectId:string;noteId:string;disabled?:boolean;
  draftId?:string;onMarkdownDraftState?:(state:MarkdownDraftState)=>void;onPasteImage?:(file:File,insertAt:number)=>void};
type EditorFocus={id:string;offset:number};
type EditorSnapshot={content:NoteContent;focus:EditorFocus|null};
export function NoteRichEditor(props:NoteEditorProps){
  const identity=props.draftId||JSON.stringify([props.projectId,props.noteId]);
  return <RichEditorSession key={identity} {...props} identity={identity}/>;
}
function RichEditorSession({content,onChange,projectId,noteId,disabled=false,draftId,onMarkdownDraftState,onPasteImage,identity}:NoteEditorProps&{identity:string}){
  const [focused,setFocused]=useState(0),[focusedItem,setFocusedItem]=useState(0),[link,setLink]=useState(''),[showLink,setShowLink]=useState(false),[notice,setNotice]=useState('');
  const [initial]=useState(()=>draftId||projectId||noteId?readMarkdownDraft(identity):{ok:true as const,value:null});
  const [markdown,setMarkdown]=useState<MarkdownDraft|null>(initial.ok?initial.value:null);
  const [markdownMode,setMarkdownMode]=useState(!!(!initial.ok||initial.value));
  const [markdownPending,setMarkdownPending]=useState(!!(!initial.ok||initial.value));
  const [journalError,setJournalError]=useState(initial.ok?'':initial.error),[storageError,setStorageError]=useState('');
  const converted=markdown?parseNoteMarkdown(markdown.text):null;
  const changedBase=!!markdown&&JSON.stringify(markdown.base)!==JSON.stringify(content);
  const markdownValid=!!converted?.ok&&!journalError&&!storageError&&!changedBase;
  useEffect(()=>{onMarkdownDraftState?.({pending:markdownPending,valid:!markdownPending||markdownValid});},[onMarkdownDraftState,markdownPending,markdownValid]);
  useEffect(()=>{const guard=(event:BeforeUnloadEvent)=>{if(markdownPending){event.preventDefault();event.returnValue='';}};
    window.addEventListener('beforeunload',guard);return()=>window.removeEventListener('beforeunload',guard);},[markdownPending]);
  function persistMarkdown(value:MarkdownDraft){
    try{localStorage.setItem(markdownDraftKey(identity),JSON.stringify(value));setStorageError('');return true;}
    catch{setStorageError('Brouillon Markdown non conservé sur cet appareil. Exportez la saisie avant de quitter ou réessayez sa conservation.');return false;}
  }
  function enterMarkdown(){
    if(disabled)return;
    if(!draftId&&!projectId&&!noteId){setNotice('Identité de note requise pour conserver un brouillon Markdown distinct.');return;}
    const value=noteToMarkdown(content);
    if(!value.ok){setNotice(value.error);return;}
    setMarkdown({format:1,text:value.value,base:content});setMarkdownPending(false);setMarkdownMode(true);setNotice('');
  }
  function closeMarkdown(apply:boolean){
    if(apply&&markdownPending){
      if(disabled||!markdownValid||!converted?.ok)return;
      if(onChange({...converted.value,background:content.background})===false){setStorageError('La note convertie n’a pas pu être conservée ; le brouillon Markdown reste disponible.');return;}
    }
    if(markdownPending){
      try{localStorage.removeItem(markdownDraftKey(identity));}catch{setStorageError('Impossible de fermer le brouillon local ; sa saisie reste conservée.');return;}
    }
    setMarkdown(null);setMarkdownPending(false);setMarkdownMode(false);setStorageError('');setJournalError('');setNotice('');
  }
  function exportMarkdown(){
    const text=markdown?.text??localStorage.getItem(markdownDraftKey(identity))??'';
    const url=URL.createObjectURL(new Blob([text],{type:'text/plain;charset=utf-8'})),anchor=document.createElement('a');
    anchor.href=url;anchor.download='brouillon-note.md';anchor.click();window.setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  const root=useRef<HTMLDivElement>(null),savedRange=useRef<Range|null>(null),pendingFocus=useRef<EditorFocus|null>(null);
  const toolbar=useRef<HTMLDivElement>(null),[toolbarWidth,setToolbarWidth]=useState(0);
  useEffect(()=>{
    const line=toolbar.current;if(!line||typeof ResizeObserver==='undefined')return;
    const observer=new ResizeObserver(([box])=>setToolbarWidth(box.contentRect.width));
    observer.observe(line);return()=>observer.disconnect();
  },[markdownMode,disabled]);
  const latest=useRef(content),lastAccepted=useRef(JSON.stringify(content.blocks)),history=useRef<{undo:EditorSnapshot[];redo:EditorSnapshot[]}>({undo:[],redo:[]});
  const typing=useRef<{id:string;time:number}|null>(null),[historyVersion,setHistoryVersion]=useState(0);
  useEffect(()=>{
    latest.current=content;
    if(JSON.stringify(content.blocks)!==lastAccepted.current){history.current={undo:[],redo:[]};typing.current=null;setHistoryVersion(v=>v+1);lastAccepted.current=JSON.stringify(content.blocks);}
    const target=pendingFocus.current;if(!target)return;
    const editable=root.current?.querySelector<HTMLElement>(`[data-note-input="${target.id}"]`);if(!editable)return;
    pendingFocus.current=null;editable.focus();const range=document.createRange(),walker=document.createTreeWalker(editable,NodeFilter.SHOW_TEXT);
    let left=target.offset,node=walker.nextNode(),last:Node|null=null;
    while(node){last=node;if(left<=node.textContent!.length){range.setStart(node,left);break;}left-=node.textContent!.length;node=walker.nextNode();}
    if(!node){range.selectNodeContents(editable);range.collapse(false);if(!last)range.setStart(editable,0);}
    range.collapse(true);const current=window.getSelection();current?.removeAllRanges();current?.addRange(range);
  },[content]);
  function currentFocus():EditorFocus|null{
    const selected=window.getSelection();if(!selected?.rangeCount)return null;
    const node=selected.anchorNode,element=node instanceof Element?node.closest<HTMLElement>('[data-note-input]'):node?.parentElement?.closest<HTMLElement>('[data-note-input]');
    if(!element||!root.current?.contains(element))return null;
    const range=selected.getRangeAt(0),before=range.cloneRange();if(!element.contains(range.startContainer))return null;
    before.selectNodeContents(element);before.setEnd(range.startContainer,range.startOffset);return {id:element.dataset.noteInput!,offset:before.toString().length};
  }
  function commit(value:NoteContent,typingId?:string){
    if(disabled||JSON.stringify(value)===JSON.stringify(latest.current))return true;
    if(!validNoteContent(value)){setNotice('La limite de contenu de la note est atteinte. Conservez la saisie et répartissez-la entre plusieurs notes.');return false;}
    if(onChange(value)===false){setNotice('La modification n’a pas pu être conservée. Réessayez avant de quitter la note.');return false;}
    const now=Date.now(),group=typingId&&typing.current?.id===typingId&&now-typing.current.time<750;
    if(!group){history.current.undo.push({content:latest.current,focus:currentFocus()});if(history.current.undo.length>100)history.current.undo.shift();}
    history.current.redo=[];typing.current=typingId?{id:typingId,time:now}:null;
    latest.current=value;lastAccepted.current=JSON.stringify(value.blocks);setHistoryVersion(v=>v+1);return true;
  }
  const change=(index:number,block:NoteBlock,typingId?:string)=>commit({...latest.current,blocks:latest.current.blocks.map((b,i)=>i===index?block:b)},typingId);
  const focus=(id:string,offset=0)=>{pendingFocus.current={id,offset};};
  function add(block:NoteBlock){
    if(latest.current.blocks.length>=500)return;
    const after=Math.min(focused+1,latest.current.blocks.length),blocks=[...latest.current.blocks];blocks.splice(after,0,block);
    focus(block.type==='list'?`l:${after}:0`:block.type==='table'?`t:${after}:0:0`:`p:${after}`);setFocused(after);commit({...latest.current,blocks});
  }
  function undo(redo=false){
    if(disabled)return;const from=redo?history.current.redo:history.current.undo,to=redo?history.current.undo:history.current.redo,snapshot=from[from.length-1];if(!snapshot)return;
    const value={...snapshot.content,background:latest.current.background},previousFocus=currentFocus();if(onChange(value)===false)return;from.pop();to.push({content:latest.current,focus:previousFocus});
    latest.current=value;lastAccepted.current=JSON.stringify(value.blocks);typing.current=null;savedRange.current=null;pendingFocus.current=snapshot.focus;
    const restored=snapshot.focus?.id.split(':');setFocused(restored?Number(restored[1]):Math.min(focused,Math.max(0,value.blocks.length-1)));
    if(restored?.[0]==='l')setFocusedItem(Number(restored[2]));setHistoryVersion(v=>v+1);
  }
  function parts(element:HTMLElement){
    const s=window.getSelection();if(!s?.rangeCount||!element.contains(s.anchorNode)||!element.contains(s.focusNode))return null;
    const selected=s.getRangeAt(0),before=selected.cloneRange(),after=selected.cloneRange();before.selectNodeContents(element);before.setEnd(selected.startContainer,selected.startOffset);
    after.selectNodeContents(element);after.setStart(selected.endContainer,selected.endOffset);
    const read=(range:Range)=>{const div=document.createElement('div');div.append(range.cloneContents());return readNoteRuns(div);};
    return {before:read(before),after:read(after),start:before.toString()==='',end:after.toString()==='',collapsed:selected.collapsed};
  }
  const length=(runs:NoteRun[])=>runs.reduce((sum,r)=>sum+r.text.length,0);
  function navigate(event:KeyboardEvent<HTMLDivElement>,part:{collapsed:boolean;start:boolean;end:boolean}){
    if(!part.collapsed||!((event.key==='ArrowUp'&&part.start)||(event.key==='ArrowDown'&&part.end)))return false;
    const inputs=Array.from(root.current?.querySelectorAll<HTMLElement>('[data-note-input]')||[]),index=inputs.indexOf(event.currentTarget);
    const next=inputs[index+(event.key==='ArrowUp'?-1:1)];if(!next)return false;event.preventDefault();next.focus();
    const range=document.createRange();range.selectNodeContents(next);range.collapse(event.key==='ArrowDown');const selected=window.getSelection();selected?.removeAllRanges();selected?.addRange(range);return true;
  }
  function paragraphKey(event:KeyboardEvent<HTMLDivElement>,index:number){
    if(disabled||event.nativeEvent.isComposing)return;const block=latest.current.blocks[index];if(!block||!('runs'in block))return;
    const part=parts(event.currentTarget);if(!part||navigate(event,part))return;
    const blocks=[...latest.current.blocks];
    if(event.key==='Enter'&&!event.shiftKey){
      if(blocks.length>=500)return;event.preventDefault();blocks.splice(index,1,{...block,runs:part.before},{type:'paragraph',align:'left',runs:part.after});
      focus(`p:${index+1}`);commit({...latest.current,blocks});
    }else if(event.key==='Backspace'&&part.collapsed&&part.start&&index>0){
      const prev=blocks[index-1];if(!('runs'in prev))return;event.preventDefault();focus(`p:${index-1}`,length(prev.runs));
      blocks.splice(index-1,2,{...prev,runs:[...prev.runs,...block.runs]});commit({...latest.current,blocks});
    }else if(event.key==='Delete'&&part.collapsed&&part.end){
      const next=blocks[index+1];if(!next||!('runs'in next))return;event.preventDefault();focus(`p:${index}`,length(block.runs));
      blocks.splice(index,2,{...block,runs:[...block.runs,...next.runs]});commit({...latest.current,blocks});
    }
  }
  function listKey(event:KeyboardEvent<HTMLDivElement>,index:number,itemIndex:number){
    if(disabled||event.nativeEvent.isComposing)return;const block=latest.current.blocks[index];if(block?.type!=='list')return;
    const item=block.items[itemIndex],part=parts(event.currentTarget);if(!part||navigate(event,part))return;
    const blocks=[...latest.current.blocks],items=[...block.items];
    if(event.key==='Enter'&&!event.shiftKey){
      event.preventDefault();
      if(!length(item.runs)){
        const replacement:NoteBlock[]=[];if(itemIndex)replacement.push({...block,items:items.slice(0,itemIndex)});
        replacement.push({type:'paragraph',align:'left',runs:[]});if(itemIndex<items.length-1)replacement.push({...block,items:items.slice(itemIndex+1)});
        if(blocks.length-1+replacement.length>500)return;blocks.splice(index,1,...replacement);focus(`p:${index+(itemIndex?1:0)}`);commit({...latest.current,blocks});
      }else if(items.length<500){items.splice(itemIndex,1,{...item,runs:part.before},{...item,runs:part.after,checked:false});focus(`l:${index}:${itemIndex+1}`);change(index,{...block,items});}
    }else if(event.key==='Tab'){
      event.preventDefault();items[itemIndex]={...item,indent:Math.max(0,Math.min(6,item.indent+(event.shiftKey?-1:1)))};change(index,{...block,items});
    }else if((event.key==='Delete'||event.key==='Backspace')&&part.collapsed&&block.kind==='checklist'&&!length(item.runs)){
      event.preventDefault();removeListItem(index,itemIndex);
    }else if(event.key==='Delete'&&part.collapsed&&part.end&&itemIndex<items.length-1){
      event.preventDefault();focus(`l:${index}:${itemIndex}`,length(item.runs));
      items.splice(itemIndex,2,{...item,runs:[...item.runs,...items[itemIndex+1].runs]});change(index,{...block,items});
    }else if(event.key==='Backspace'&&part.collapsed&&part.start){
      event.preventDefault();
      if(item.indent){items[itemIndex]={...item,indent:item.indent-1};change(index,{...block,items});}
      else if(itemIndex){const prev=items[itemIndex-1];focus(`l:${index}:${itemIndex-1}`,length(prev.runs));items.splice(itemIndex-1,2,{...prev,runs:[...prev.runs,...item.runs]});change(index,{...block,items});}
      else{const replacement:NoteBlock[]=[{type:'paragraph',align:'left',runs:item.runs}];if(items.length>1)replacement.push({...block,items:items.slice(1)});
        if(blocks.length-1+replacement.length>500)return;blocks.splice(index,1,...replacement);focus(`p:${index}`);commit({...latest.current,blocks});}
    }
  }
  function removeListItem(index:number,itemIndex:number){
    const block=latest.current.blocks[index];if(block?.type!=='list'||!block.items[itemIndex])return;
    const items=block.items.filter((_,row)=>row!==itemIndex);
    if(!items.length&&latest.current.blocks.length>1){
      const blocks=latest.current.blocks.filter((_,row)=>row!==index);
      const next=Math.min(index,blocks.length-1),target=blocks[next];
      setFocused(next);setFocusedItem(0);
      if(target.type!=='image')focus(target.type==='list'?`l:${next}:0`:target.type==='table'?`t:${next}:0:0`:`p:${next}`);
      commit({...latest.current,blocks});
      return;
    }
    const next=Math.min(itemIndex,items.length-1);
    setFocusedItem(Math.max(0,next));
    focus(items.length?`l:${index}:${next}`:`p:${index}`);
    change(index,items.length?{...block,items}:{type:'paragraph',align:'left',runs:[]});
  }
  function tableKey(event:KeyboardEvent<HTMLDivElement>,index:number,row:number,col:number){
    if(disabled||event.key!=='Tab')return;const block=latest.current.blocks[index];if(block?.type!=='table')return;
    event.preventDefault();const columns=block.rows[0].length,next=row*columns+col+(event.shiftKey?-1:1);if(next<0)return;
    if(next>=block.rows.length*columns){if(block.rows.length>=200)return;focus(`t:${index}:${block.rows.length}:0`);change(index,{...block,rows:[...block.rows,Array.from({length:columns},()=>[])]});}
    else{const input=root.current?.querySelector<HTMLElement>(`[data-note-input="t:${index}:${Math.floor(next/columns)}:${next%columns}"]`);input?.focus();}
  }
  function selection(){const s=window.getSelection();return s?.rangeCount&&root.current?.contains(s.anchorNode)?s.getRangeAt(0).cloneRange():null;}
  function format(command:string,value?:string){
    if(disabled)return;setNotice('');const range=savedRange.current&&root.current?.contains(savedRange.current.startContainer)?savedRange.current:selection();if(!range||!root.current?.contains(range.startContainer)){setNotice('Placez le curseur ou sélectionnez le texte à mettre en forme.');return;}
    const s=window.getSelection()!,collapsed=range.collapsed;s.removeAllRanges();s.addRange(range);
    if(command==='code'&&collapsed){setNotice('Sélectionnez le texte à présenter en code.');return;}
    const pieces=Array.from(root.current!.querySelectorAll<HTMLElement>('[data-note-input][contenteditable="true"]')).filter(input=>
      collapsed?input.contains(range.startContainer):range.intersectsNode(input)).map(input=>{
      const local=document.createRange();local.selectNodeContents(input);
      if(input.contains(range.startContainer))local.setStart(range.startContainer,range.startOffset);
      if(input.contains(range.endContainer))local.setEnd(range.endContainer,range.endOffset);
      const before=local.cloneRange();before.selectNodeContents(input);before.setEnd(local.startContainer,local.startOffset);
      return {input,range:local,start:before.toString().length,end:before.toString().length+local.toString().length};
    }).filter(piece=>collapsed||!piece.range.collapsed);
    if(!pieces.length)return;
    const toggled=pieces.length>1&&['bold','italic','underline','strikeThrough'].includes(command)&&typeof document.queryCommandState==='function'
      ?!document.queryCommandState(command):undefined;
    for(const piece of pieces){
      s.removeAllRanges();s.addRange(piece.range);
      if(command==='code'){const code=document.createElement('code');code.append(piece.range.extractContents());piece.range.insertNode(code);}
      else if(toggled===undefined||document.queryCommandState(command)!==toggled)document.execCommand(command,false,value);
    }
    const blocks=[...latest.current.blocks];
    for(const {input} of pieces){
      const [kind,index,item,column]=input.dataset.noteInput!.split(':'),i=Number(index),n=Number(item),c=Number(column),block=blocks[i],runs=readNoteRuns(input);
      if(kind==='p'&&(block.type==='paragraph'||block.type==='heading'))blocks[i]={...block,runs};
      else if(kind==='l'&&block.type==='list')blocks[i]={...block,items:block.items.map((entry,j)=>j===n?{...entry,runs}:entry)};
      else if(kind==='t'&&block.type==='table')blocks[i]={...block,rows:block.rows.map((row,r)=>r===n?row.map((cell,j)=>j===c?runs:cell):row)};
      input.dispatchEvent(new Event('note-format-applied'));
    }
    if(!collapsed){
      const point=(input:HTMLElement,offset:number):[Node,number]=>{
        const walker=document.createTreeWalker(input,NodeFilter.SHOW_TEXT);let node=walker.nextNode(),remaining=offset;
        while(node){if(remaining<=node.textContent!.length)return [node,remaining];remaining-=node.textContent!.length;node=walker.nextNode();}
        return [input,input.childNodes.length];
      };
      const first=pieces[0],last=pieces[pieces.length-1],restored=document.createRange();restored.setStart(...point(first.input,first.start));restored.setEnd(...point(last.input,last.end));
      s.removeAllRanges();s.addRange(restored);
    }
    commit({...latest.current,blocks});savedRange.current=null;
  }
  const b=content.blocks[focused];
  function pasteImage(event:ClipboardEvent<HTMLDivElement>){
    if(!onPasteImage||disabled)return;
    const files=Array.from(event.clipboardData.files??[]).filter(candidate=>candidate.type.startsWith('image/'));
    if(!files.length)for(const item of Array.from(event.clipboardData.items??[])){
      if(item.kind==='file'&&item.type.startsWith('image/')){
        const file=item.getAsFile();if(file)files.push(file);
      }
    }
    if(!files.length)return;
    event.preventDefault();
    event.stopPropagation();
    if(files.length>1){setNotice('Collez une image à la fois.');return;}
    const field=(event.target as HTMLElement).closest<HTMLElement>('[data-note-input]');
    const at=field?Number(field.dataset.noteInput?.split(':')[1]):focused;
    setNotice('');onPasteImage(files[0],Math.min(at+1,content.blocks.length));
  }
  function styleBlock(value:string){
    if(!b)return;
    if(b.type==='paragraph'||b.type==='heading')change(focused,value==='paragraph'?{type:'paragraph',align:'left',runs:b.runs}:{type:'heading',level:Number(value.slice(1)),runs:b.runs});
  }
  function list(kind:'bullet'|'ordered'|'checklist'){
    if(b?.type==='paragraph'||b?.type==='heading'){focus(`l:${focused}:0`);change(focused,{type:'list',kind,items:[{runs:b.runs,checked:false,indent:0}]});}
    else if(b?.type==='list'){
      if(b.kind!==kind)change(focused,{...b,kind,items:b.items.map(item=>({...item,checked:kind==='checklist'?item.checked:false}))});
      else{const blocks=[...latest.current.blocks],replacement:NoteBlock[]=b.items.map(item=>({type:'paragraph',align:'left',runs:item.runs}));
        if(blocks.length-1+replacement.length>500)return;blocks.splice(focused,1,...replacement);focus(`p:${focused}`);commit({...latest.current,blocks});}
    }else add({type:'list',kind,items:[{runs:[],checked:false,indent:0}]});
  }
  function move(delta:number){const blocks=[...latest.current.blocks],next=focused+delta;if(next<0||next>=blocks.length)return;
    [blocks[focused],blocks[next]]=[blocks[next],blocks[focused]];setFocused(next);commit({...latest.current,blocks});}
  const table=()=>add({type:'table',header:true,rows:[[[],[],[]],[[],[],[]],[[],[],[]]]});
  const paragraph=()=>add({type:'paragraph',align:'left',runs:[]});
  const linkTool=()=>{savedRange.current=selection()??savedRange.current;setShowLink(value=>!value);};
  const formatTools=[['Souligné','underline','U'],['Barré','strikeThrough','S'],['Code','code','<>'],['Sans mise en forme','removeFormat','Tx']] as const;
  const toolsInBar=toolbarWidth>=755?formatTools.length:toolbarWidth>=525?2:0;
  const insertsInBar=toolbarWidth>=525;
  const fullToolbar=toolbarWidth>=820;
  const alignment=b?.type==='paragraph'&&<select aria-label="Alignement du bloc" title="Alignement du bloc" value={b.align}
    onChange={event=>change(focused,{...b,align:event.target.value as typeof b.align})}>
    <option value="left">Gauche</option><option value="center">Centré</option><option value="right">Droite</option></select>;
  function closeFormatMenu(menu:HTMLDetailsElement){
    if(menu.contains(document.activeElement))menu.querySelector<HTMLElement>('summary')?.focus({preventScroll:true});
    menu.open=false;
  }
  const icon=(name:'bullet'|'ordered'|'checklist'|'undo'|'redo'|'plus')=><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {name==='bullet'?<><circle cx="4" cy="6" r="1"/><circle cx="4" cy="12" r="1"/><circle cx="4" cy="18" r="1"/><path d="M9 6h11M9 12h11M9 18h11"/></>:
      name==='ordered'?<><path d="M3 4h1v4M3 8h2M3 12c3-2 3 1 0 4h3M10 6h10M10 12h10M10 18h10"/></>:
      name==='checklist'?<><rect x="3" y="5" width="15" height="15" rx="2"/><path d="m7 10 4 4L21 3"/></>:
      name==='undo'?<path d="m8 5-5 5 5 5M3 10h12a5 5 0 0 1 0 10"/>:
      name==='redo'?<path d="m16 5 5 5-5 5M21 10H9a5 5 0 0 0 0 10"/>:<path d="M12 5v14M5 12h14"/>}</svg>;
  if(markdownMode)return <div className="note-rich-editor note-markdown-editor" data-workspace-dirty={markdownPending?'true':undefined}>
    <p>Markdown réversible : paragraphes, titres 1–3, listes, gras, italique, code.</p>
    <p>Liens HTTP(S) et mailto sûrs ; tableaux, images et autres mises en forme restent dans l'éditeur riche.</p>
    {journalError&&<p role="alert">{journalError}</p>}
    {markdown&&<label>Texte Markdown<textarea className="input" style={{width:'100%',minHeight:180,fontFamily:'monospace'}} value={markdown.text} readOnly={disabled}
      onChange={event=>{const next={...markdown,text:event.target.value};setMarkdown(next);setMarkdownPending(true);persistMarkdown(next);}}/></label>}
    {converted&&!converted.ok&&<p role="alert">{converted.error} La saisie reste visible ; la note riche n’est pas remplacée.</p>}
    {storageError&&<p role="alert">{storageError}</p>}
    {changedBase&&<div role="alert"><p>La note riche a changé depuis ce brouillon. Votre Markdown reste conservé ; comparez les deux versions avant de l’appliquer.</p>
      <details><summary>Comparer avec la note riche actuelle</summary><NoteContentView content={content} projectId={projectId} noteId={noteId}/></details>
      <button type="button" className="button secondary sm" disabled={disabled||!!journalError} onClick={()=>{if(markdown){const next={...markdown,base:content};setMarkdown(next);persistMarkdown(next);}}}>Reprendre ce Markdown sur la note affichée</button></div>}
    <p role="status">{markdownPending?'Brouillon Markdown à appliquer avant l’enregistrement, l’enrichissement ou la publication.':'Le texte n’a pas encore été modifié.'}</p>
    <div className="note-actions"><button type="button" className="button secondary sm" disabled={disabled||(markdownPending&&!markdownValid)} onClick={()=>closeMarkdown(true)}>Valider et revenir à l’éditeur riche</button>
      {markdownPending&&<><button type="button" className="button secondary sm" onClick={exportMarkdown}>Exporter le brouillon Markdown</button>
        {storageError&&markdown&&<button type="button" className="button secondary sm" onClick={()=>persistMarkdown(markdown)}>Réessayer la conservation Markdown</button>}
        <button type="button" className="button secondary sm" onClick={()=>closeMarkdown(false)}>Écarter ce brouillon Markdown</button></>}</div>
    {converted?.ok&&<details><summary>Aperçu de la conversion</summary><NoteContentView content={converted.value} projectId={projectId} noteId={noteId}/></details>}
  </div>;
  return <div className="note-rich-editor note-document-editor" ref={root} data-history-version={historyVersion}
    onKeyDown={event=>{if((event.ctrlKey||event.metaKey)&&!event.altKey&&['z','y'].includes(event.key.toLowerCase())){
      event.preventDefault();undo(event.key.toLowerCase()==='y'||event.shiftKey);}}}>
    {!disabled&&<><div className="note-toolbar note-document-toolbar" ref={toolbar} role="toolbar" aria-label="Mise en forme de la note">
      <select className="note-style-select" aria-label="Style du bloc" value={b?.type==='heading'?`h${b.level}`:'paragraph'} disabled={!b||!('runs'in b)} onChange={event=>styleBlock(event.target.value)}>
        <option value="paragraph">Paragraphe</option><option value="h1">Titre 1</option><option value="h2">Titre 2</option><option value="h3">Titre 3</option></select>
      <span className="note-toolbar-divider" aria-hidden="true"/>
      <button type="button" className="note-tool" aria-label="Gras" title="Gras · Ctrl+B" onMouseDown={e=>e.preventDefault()} onClick={()=>format('bold')}><strong>B</strong></button>
      <button type="button" className="note-tool" aria-label="Italique" title="Italique · Ctrl+I" onMouseDown={e=>e.preventDefault()} onClick={()=>format('italic')}><em>I</em></button>
      {formatTools.slice(0,toolsInBar).map(([label,command,glyph])=><button type="button" key={command} className="note-tool"
        aria-label={label} title={label} onMouseDown={event=>event.preventDefault()} onClick={()=>format(command)}>{glyph}</button>)}
      <span className="note-toolbar-divider" aria-hidden="true"/>
      {(['bullet','ordered','checklist'] as const).map(kind=><button type="button" key={kind} className="note-tool" aria-label={{bullet:'Liste à puces',ordered:'Liste numérotée',checklist:'Liste à cocher'}[kind]}
        title={{bullet:'Liste à puces',ordered:'Liste numérotée',checklist:'Liste à cocher'}[kind]} aria-pressed={b?.type==='list'&&b.kind===kind} onMouseDown={e=>e.preventDefault()} onClick={()=>list(kind)}>{icon(kind)}</button>)}
      <input type="color" className="note-tool note-text-color" aria-label="Couleur du texte" title="Couleur du texte"
        defaultValue="#203345" onPointerDown={()=>{savedRange.current=selection()??savedRange.current;}}
        onFocus={()=>{savedRange.current=selection()??savedRange.current;}} onChange={event=>format('foreColor',event.target.value)}/>
      {insertsInBar&&<>
        <button type="button" className="note-tool" aria-label="Insérer un tableau" title="Insérer un tableau" disabled={content.blocks.length>=500}
          onMouseDown={event=>event.preventDefault()} onClick={table}>▦</button>
        <button type="button" className="note-tool" aria-label="Lien" title="Lien" onMouseDown={event=>event.preventDefault()} onClick={linkTool}>↗</button>
      </>}
      {fullToolbar&&<><button type="button" className="note-tool" aria-label="Insérer un paragraphe" title="Insérer un paragraphe"
        disabled={content.blocks.length>=500} onMouseDown={event=>event.preventDefault()} onClick={paragraph}>¶</button>{alignment}</>}
      <details data-dismiss-outside className="note-format-menu" onClick={event=>{
        if((event.target as HTMLElement).closest('.note-format-popover button'))closeFormatMenu(event.currentTarget);
      }} onChange={event=>closeFormatMenu(event.currentTarget)} onKeyDown={event=>{
        if(event.key==='Escape'&&event.currentTarget.open){event.stopPropagation();closeFormatMenu(event.currentTarget);}
      }}><summary aria-label="Insérer et formater" title="Insérer et formater" onMouseDown={()=>{savedRange.current=selection()??savedRange.current;}}>{icon('plus')}<span className="sr-only">+ Insérer / format</span></summary>
        <div className="note-format-popover">
          <div className="note-menu-section"><span>Insérer</span><button type="button" disabled={content.blocks.length>=500} onClick={paragraph}>Paragraphe</button>
            <button type="button" disabled={content.blocks.length>=500} onClick={table}>Tableau</button></div>
          {(toolsInBar<formatTools.length||!insertsInBar||!fullToolbar&&alignment)&&<div className="note-menu-section"><span>Texte</span>{formatTools.slice(toolsInBar).map(([label,command])=>
            <button type="button" key={command} onMouseDown={e=>e.preventDefault()} onClick={()=>format(command)}>{label}</button>)}
            {!insertsInBar&&<button type="button" onMouseDown={e=>e.preventDefault()} onClick={linkTool}>Lien</button>}
            {!fullToolbar&&alignment&&<label>Alignement{alignment}</label>}</div>}
          {b?.type==='list'&&<div className="note-menu-section"><span>Liste</span><button type="button" disabled={b.items.length>=500} onClick={()=>{focus(`l:${focused}:${b.items.length}`);change(focused,{...b,items:[...b.items,{runs:[],checked:false,indent:0}]});}}>Ajouter un élément</button>
            <button type="button" onClick={()=>removeListItem(focused,focusedItem)}>Supprimer la ligne</button>
            <label>Retrait<select aria-label={`Retrait de l’élément ${focusedItem+1} du bloc ${focused+1}`} value={b.items[focusedItem]?.indent||0}
              onChange={e=>change(focused,{...b,items:b.items.map((item,n)=>n===focusedItem?{...item,indent:Number(e.target.value)}:item)})}>
              {Array.from({length:7},(_,n)=><option key={n} value={n}>{n}</option>)}</select></label></div>}
          {b?.type==='table'&&<div className="note-menu-section"><span>Tableau</span><label><input type="checkbox" checked={b.header} onChange={e=>change(focused,{...b,header:e.target.checked})}/> Première ligne d’en-tête</label>
            <button type="button" disabled={b.rows.length>=200} onClick={()=>change(focused,{...b,rows:[...b.rows,b.rows[0].map(()=>[])]})}>Ajouter une ligne</button>
            <button type="button" disabled={b.rows[0].length>=20} onClick={()=>change(focused,{...b,rows:b.rows.map(row=>[...row,[]])})}>Ajouter une colonne</button></div>}
          {b&&<div className="note-menu-section"><span>Élément sélectionné</span><button type="button" disabled={!focused} onClick={()=>move(-1)}>Monter</button>
            <button type="button" disabled={focused>=content.blocks.length-1} onClick={()=>move(1)}>Descendre</button>
            <button type="button" className="note-menu-remove" onClick={()=>{const blocks=content.blocks.filter((_,n)=>n!==focused);if(!blocks.length)blocks.push({type:'paragraph',align:'left',runs:[]});setFocused(Math.min(focused,blocks.length-1));commit({...content,blocks});}}>Retirer l’élément</button></div>}
        </div></details>
      <span className="note-toolbar-divider" aria-hidden="true"/>
      <button type="button" className="note-tool" aria-label="Annuler" title="Annuler · Ctrl+Z" disabled={!history.current.undo.length} onMouseDown={e=>e.preventDefault()} onClick={()=>undo()}>{icon('undo')}</button>
      <button type="button" className="note-tool" aria-label="Rétablir" title="Rétablir · Ctrl+Y" disabled={!history.current.redo.length} onMouseDown={e=>e.preventDefault()} onClick={()=>undo(true)}>{icon('redo')}</button>
      <button type="button" className="note-tool note-markdown-tool" aria-label="Éditer en Markdown" title="Éditer en Markdown" onClick={enterMarkdown}>MD</button>
    </div>
    {showLink&&<div className="note-link-form"><label>Adresse du lien<input className="input" value={link} onChange={e=>setLink(e.target.value)} placeholder="https://…"/></label>
      <button type="button" className="button secondary sm" disabled={!safeNoteLink(link)} onClick={()=>{format('createLink',link);setShowLink(false);setLink('');}}>Appliquer le lien</button>
      <button type="button" className="button secondary sm" onClick={()=>{format('unlink');setShowLink(false);}}>Retirer le lien</button></div>}
    {notice&&<p className="note-editor-notice" role="status">{notice}</p>}</>}
    <div className="note-blocks note-document-page" aria-label="Document de la note" onPasteCapture={pasteImage} onClick={event=>{if(event.target===event.currentTarget){const inputs=root.current?.querySelectorAll<HTMLElement>('.note-runs'),last=inputs?.[inputs.length-1];if(!last)return;last.focus();const range=document.createRange();range.selectNodeContents(last);range.collapse(false);const selected=window.getSelection();selected?.removeAllRanges();selected?.addRange(range);}}} onKeyDown={event=>{if(event.target===event.currentTarget&&(event.key==='Enter'||event.key===' ')){event.preventDefault();const inputs=root.current?.querySelectorAll<HTMLElement>('.note-runs'),last=inputs?.[inputs.length-1];last?.focus();}}}>
      {content.blocks.map((block,i)=><div key={i} className={`note-block ${block.type}${block.type==='heading'?` level-${block.level}`:''}`}>
        {(block.type==='paragraph'||block.type==='heading')&&<div style={block.type==='paragraph'?{textAlign:block.align}:undefined}>
          <RunsInput runs={block.runs} inputId={`p:${i}`} disabled={disabled} label={`Texte du bloc ${i+1}`} onFocus={()=>{setFocused(i);setFocusedItem(0);}}
            onKeyDown={e=>paragraphKey(e,i)} onChange={runs=>change(i,{...block,runs},`p:${i}`)}/></div>}
        {block.type==='list'&&<ol className={`note-list ${block.kind}`}>{block.items.map((item,n)=><li key={n} style={{marginLeft:item.indent*20}}>
          {block.kind==='checklist'&&<input type="checkbox" aria-label={`Case ${n+1} du bloc ${i+1}`} disabled={disabled} checked={item.checked}
            onKeyDown={event=>{if(!disabled&&(event.key==='Delete'||event.key==='Backspace')){event.preventDefault();removeListItem(i,n);}}}
            onFocus={()=>{setFocused(i);setFocusedItem(n);}} onChange={e=>change(i,{...block,items:block.items.map((it,j)=>j===n?{...it,checked:e.target.checked}:it)})}/>}
          <RunsInput runs={item.runs} inputId={`l:${i}:${n}`} disabled={disabled} label={`Élément ${n+1} du bloc ${i+1}`} onFocus={()=>{setFocused(i);setFocusedItem(n);}}
            onKeyDown={e=>listKey(e,i,n)} onChange={runs=>change(i,{...block,items:block.items.map((it,j)=>j===n?{...it,runs}:it)},`l:${i}:${n}`)}/>
        </li>)}</ol>}
        {block.type==='table'&&<div className="note-table-scroll"><table><tbody>{block.rows.map((row,r)=><tr key={r}>{row.map((cell,c)=>{
          const Cell=r===0&&block.header?'th':'td';return <Cell key={c}><RunsInput runs={cell} inputId={`t:${i}:${r}:${c}`} disabled={disabled} label={`Ligne ${r+1}, colonne ${c+1} du bloc ${i+1}`}
            onFocus={()=>setFocused(i)} onKeyDown={e=>tableKey(e,i,r,c)} onChange={runs=>change(i,{...block,rows:block.rows.map((rw,ri)=>ri===r?rw.map((cl,ci)=>ci===c?runs:cl):rw)},`t:${i}:${r}:${c}`)}/></Cell>;
        })}</tr>)}</tbody></table></div>}
        {block.type==='image'&&<figure onClick={()=>setFocused(i)}><img src={agentPath(`${noteUrl(projectId,noteId)}/attachments/${encodeURIComponent(block.attachment_id)}/image`)} alt={block.caption||'Image dans la note'}/>
          <label>Légende<input className="input" maxLength={1000} value={block.caption} readOnly={disabled} onFocus={()=>setFocused(i)} onChange={e=>change(i,{...block,caption:e.target.value},`image:${i}`)}/></label></figure>}
      </div>)}
      {!content.blocks.length&&!disabled&&<button type="button" className="note-empty-page" onClick={()=>{focus('p:0');commit({...content,blocks:[{type:'paragraph',align:'left',runs:[]}]});}}>Commencez à écrire…</button>}
    </div>
  </div>;
}
