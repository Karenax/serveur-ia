import {blankNote,safeNoteLink,validNoteContent,type NoteBlock,type NoteContent,type NoteMark,type NoteRun} from './projectNotes';

/** A reversible note subset, deliberately independent of HTML/CommonMark rendering. */
export type MarkdownResult<T>={ok:true;value:T}|{ok:false;error:string};
const failed=(error:unknown):MarkdownResult<never>=>({ok:false,error:error instanceof Error?error.message:String(error)});
const escape=(text:string)=>text.replace(/[\\`*_\[\]()#!<>|~+.\-]/g,'\\$&');
const punctuation=(value:string)=>/[!-/:-@\[-`{-~]/.test(value);
const style=(run:NoteRun)=>JSON.stringify([Array.from(new Set(run.marks)).sort(),run.href,run.color]);
function append(runs:NoteRun[],text:string,marks:NoteMark[]=[],href:string|null=null,color:string|null=null){
  const next={marks:Array.from(new Set(marks)).sort() as NoteMark[],href,color};
  for(let start=0;start<text.length;start+=5000){
    const part=text.slice(start,start+5000),last=runs[runs.length-1];
    if(last&&style(last)===style({...next,text:''})&&last.text.length+part.length<=5000)last.text+=part;
    else runs.push({...next,text:part});
    if(runs.length>500)throw new Error('Plus de 500 fragments dans un bloc : réduisez sa mise en forme.');
  }
}
function closing(text:string,marker:string,start:number){
  for(let at=start;at<text.length;at++){
    if(text[at]==='\\'&&marker[0]!=='`'){at++;continue;}
    if(text[at]==='`'&&marker[0]!=='`'){
      const code=text.slice(at).match(/^`+/)![0],end=closing(text,code,at+code.length);
      if(end<0)throw new Error('Code Markdown non fermé.');at=end+code.length-1;continue;
    }
    if(text.startsWith(marker,at)&&(marker[0]!=='`'||(text[at-1]!=='`'&&text[at+marker.length]!=='`')))return at;
  }
  return -1;
}
function inline(text:string,marks:NoteMark[]=[],href:string|null=null,depth=0):NoteRun[]{
  if(depth>10)throw new Error('Mise en forme Markdown trop imbriquée.');
  const runs:NoteRun[]=[];let plain='';
  const flush=()=>{append(runs,plain,marks,href);plain='';};
  for(let at=0;at<text.length;){
    const char=text[at];
    if(char==='\\'){
      if(at+1<text.length&&punctuation(text[at+1])){plain+=text[at+1];at+=2;}
      else {plain+='\\';at++;}continue;
    }
    if(char==='<'&&/^<\/?[A-Za-z!]/.test(text.slice(at)))throw new Error('HTML non pris en charge ; échappez < et > pour les conserver comme texte.');
    if(char==='!'&&text[at+1]==='[')throw new Error('Images Markdown non prises en charge ; utilisez l’éditeur riche.');
    if(char==='|'||text.startsWith('~~',at))throw new Error('Tableaux ou barré non pris en charge ; échappez le symbole pour le conserver comme texte.');
    if(char==='['){
      flush();const end=closing(text,']',at+1);
      if(end<0||text[end+1]!=='(')throw new Error('Lien Markdown incomplet : [texte](https://…).');
      let cursor=end+2,target='',nesting=0,complete=false;
      for(;cursor<text.length;cursor++){
        const value=text[cursor];
        if(value==='\\'&&cursor+1<text.length&&punctuation(text[cursor+1])){target+=text[++cursor];continue;}
        if(value==='(')nesting++;
        if(value===')'){if(!nesting){complete=true;break;}nesting--;}
        target+=value;
      }
      if(!complete||href||!safeNoteLink(target)||target.length>2048)throw new Error('Lien non sûr ou non pris en charge : HTTP(S) sans identifiants ou mailto simple requis.');
      runs.push(...inline(text.slice(at+1,end),marks,target,depth+1));at=cursor+1;continue;
    }
    if(char==='`'){
      flush();const marker=text.slice(at).match(/^`+/)![0],end=closing(text,marker,at+marker.length);
      if(end<0)throw new Error('Code Markdown non fermé.');
      let value=text.slice(at+marker.length,end);
      if(value.includes('\n'))throw new Error('Code sur plusieurs lignes non pris en charge dans ce mode.');
      if(value.startsWith(' ')&&value.endsWith(' ')&&value.trim())value=value.slice(1,-1);
      append(runs,value,[...marks,'code'],href);at=end+marker.length;continue;
    }
    if(char==='*'||char==='_'){
      flush();const marker=text[at+1]===char?char+char:char,end=closing(text,marker,at+marker.length);
      if(end<0)throw new Error('Gras ou italique Markdown non fermé.');
      const children=inline(text.slice(at+marker.length,end),[...marks,marker.length===2?'bold':'italic'],href,depth+1);
      runs.push(...children);at=end+marker.length;continue;
    }
    plain+=char;at++;
  }
  flush();return runs;
}
type Item={kind:'bullet'|'ordered'|'checklist';indent:number;checked:boolean;text:string;ordinal?:number};
function item(line:string):Item|null{
  const match=line.match(/^( *)(?:- \[([ xX])\] |([-+*]) |(\d+)\. )(.*)$/);
  if(!match)return null;
  if(match[1].length%2||match[1].length>12)throw new Error('Retrait de liste : deux espaces par niveau, six niveaux maximum.');
  return {kind:match[2]!==undefined?'checklist':match[4]?'ordered':'bullet',indent:match[1].length/2,
    checked:match[2]?.toLowerCase()==='x',text:match[5],...(match[4]?{ordinal:Number(match[4])}:{})};
}
export function parseNoteMarkdown(source:string):MarkdownResult<NoteContent>{
  try{
    if(source.length>2_000_000||/[\x00-\x08\x0b-\x1f]/.test(source.replace(/\r\n/g,'\n')))
      throw new Error('Texte Markdown trop volumineux ou caractères de contrôle non autorisés.');
    if(!source)return {ok:true,value:blankNote()};
    const lines=source.replace(/\r\n/g,'\n').split('\n'),blocks:NoteBlock[]=[];
    for(let at=0;at<lines.length;){
      if(!lines[at].trim()){at++;continue;}
      if(/^\s*(?:>|\|)|^\s*```\s*$|^\s*~~~/.test(lines[at]))throw new Error('Citation, tableau ou bloc de code non pris en charge ; utilisez l’éditeur riche.');
      const heading=lines[at].match(/^(#{1,6}) (.*)$/),first=item(lines[at]);
      if(heading){
        if(heading[1].length>3)throw new Error('Titres limités aux niveaux 1 à 3.');
        blocks.push({type:'heading',level:heading[1].length,runs:inline(heading[2])});at++;
      }else if(first){
        const items:Extract<NoteBlock,{type:'list'}>['items']=[];
        while(at<lines.length){const current=item(lines[at]);if(!current||current.kind!==first.kind)break;
          if(current.kind==='ordered'&&current.ordinal!==items.length+1)throw new Error('La liste numérotée doit commencer à 1 et rester consécutive.');
          items.push({runs:inline(current.text),checked:current.checked,indent:current.indent});at++;
          if(items.length>500)throw new Error('Liste limitée à 500 éléments.');
        }
        blocks.push({type:'list',kind:first.kind,items});
      }else{
        const text:string[]=[];
        do{text.push(lines[at++]);}while(at<lines.length&&lines[at].trim()&&!/^(#{1,6}) /.test(lines[at])&&!item(lines[at]));
        blocks.push({type:'paragraph',align:'left',runs:inline(text.join('\n'))});
      }
      if(blocks.length>500)throw new Error('Note limitée à 500 blocs.');
    }
    const content:NoteContent={version:1,blocks};
    if(!validNoteContent(content))throw new Error('La conversion dépasse les limites du schéma de note ; réduisez le contenu.');
    return {ok:true,value:content};
  }catch(error){return failed(error);}
}
function encodedRuns(runs:NoteRun[]){
  return runs.map(run=>{
    if(run.color||run.marks.some(mark=>!['bold','italic','code'].includes(mark)))
      throw new Error('Couleur, souligné ou barré non réversibles dans ce mode ; conservez l’éditeur riche.');
    let text=escape(run.text);
    if(run.marks.includes('code')){
      if(run.text.includes('\n'))throw new Error('Code sur plusieurs lignes non réversible dans ce mode.');
      const count=Math.max(0,...[...run.text.matchAll(/`+/g)].map(match=>match[0].length))+1,marker='`'.repeat(count);
      const pad=run.text.startsWith('`')||run.text.endsWith('`')||(run.text.startsWith(' ')&&run.text.endsWith(' ')&&!!run.text.trim());
      text=marker+(pad?' ':'')+run.text+(pad?' ':'')+marker;
    }
    if(run.marks.includes('bold'))text=`**${text}**`;
    if(run.marks.includes('italic'))text=`_${text}_`;
    if(run.href){if(!safeNoteLink(run.href))throw new Error('Lien non sûr dans la note.');text=`[${text}](${run.href.replace(/[()]/g,'\\$&')})`;}
    return text;
  }).join('');
}
function normalized(content:NoteContent):NoteContent{
  const runs=(values:NoteRun[])=>{const result:NoteRun[]=[];for(const run of values)append(result,run.text,run.marks,run.href,run.color);return result;};
  // JSON property order differs between the backend DTO and this parser.
  // Compare the supported fields in a stable order, preserving their values.
  return {version:1,blocks:content.blocks.map(block=>{
    if(block.type==='paragraph')return {type:'paragraph',runs:runs(block.runs),align:block.align};
    if(block.type==='heading')return {type:'heading',level:block.level,runs:runs(block.runs)};
    if(block.type==='list')return {type:'list',kind:block.kind,
      items:block.items.map(value=>({runs:runs(value.runs),checked:value.checked,indent:value.indent}))};
    return block;
  })};
}
export function noteToMarkdown(content:NoteContent):MarkdownResult<string>{
  try{
    if(!validNoteContent(content))throw new Error('Contenu de note incompatible avec le schéma.');
    const source=normalized(content).blocks.map(block=>{
      if(block.type==='paragraph'){
        if(block.align!=='left')throw new Error('Alignement centré ou à droite non réversible ; conservez l’éditeur riche.');
        return encodedRuns(block.runs);
      }
      if(block.type==='heading')return '#'.repeat(block.level)+' '+encodedRuns(block.runs);
      if(block.type==='list')return block.items.map((value,index)=>'  '.repeat(value.indent)+
        (block.kind==='ordered'?`${index+1}. `:block.kind==='checklist'?`- [${value.checked?'x':' '}] `:'- ')+encodedRuns(value.runs)).join('\n');
      throw new Error('Tableaux et images restent dans l’éditeur riche ; ils ne peuvent pas passer en Markdown sans perte.');
    }).join('\n\n');
    const parsed=parseNoteMarkdown(source);
    if(!parsed.ok||JSON.stringify(normalized(parsed.value))!==JSON.stringify(normalized(content)))
      throw new Error('Cette structure ou ses espaces ne sont pas réversibles en Markdown ; le contenu riche reste intact.');
    return {ok:true,value:source};
  }catch(error){return failed(error);}
}

export type MarkdownDraftState={pending:boolean;valid:boolean};
export type MarkdownDraft={format:1;text:string;base:NoteContent};
export const markdownDraftKey=(draftId:string)=>`agent.notes.markdown.v1.${draftId}`;
export function readMarkdownDraft(draftId:string):MarkdownResult<MarkdownDraft|null>{
  try{
    const raw=localStorage.getItem(markdownDraftKey(draftId));if(raw===null)return {ok:true,value:null};
    const value=JSON.parse(raw);
    if(value?.format!==1||typeof value.text!=='string'||value.text.length>2_000_000||!validNoteContent(value.base))
      throw new Error('Brouillon Markdown illisible conservé sur cet appareil ; exportez-le ou écartez-le explicitement.');
    return {ok:true,value};
  }catch(error){return failed(error);}
}
