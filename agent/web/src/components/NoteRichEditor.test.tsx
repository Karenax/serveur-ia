import {useState} from 'react';
import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen} from '@testing-library/react';
import {NoteRichEditor} from './NoteRichEditor';
import {validNoteContent,type NoteContent,type NoteRun} from '../lib/projectNotes';

const run=(text:string,marks:NoteRun['marks']=[]):NoteRun=>({text,marks,href:null,color:null});
const paragraph=(text:string):NoteContent['blocks'][number]=>({type:'paragraph',align:'left',runs:[run(text)]});
function Editor({initial,disabled=false}:{initial:NoteContent;disabled?:boolean}){
  const [content,setContent]=useState(initial);
  return <><NoteRichEditor content={content} onChange={setContent} projectId="p" noteId="n" disabled={disabled}/><output data-testid="content">{JSON.stringify(content)}</output></>;
}
const value=():NoteContent=>JSON.parse(screen.getByTestId('content').textContent!);
function caret(element:HTMLElement,offset=0){
  element.focus();const walker=document.createTreeWalker(element,NodeFilter.SHOW_TEXT);let node=walker.nextNode(),left=offset;
  while(node&&left>node.textContent!.length){left-=node.textContent!.length;node=walker.nextNode();}
  const range=document.createRange();if(node)range.setStart(node,left);else{range.selectNodeContents(element);range.collapse(false);}
  range.collapse(true);window.getSelection()!.removeAllRanges();window.getSelection()!.addRange(range);
}
afterEach(()=>{cleanup();localStorage.clear();vi.restoreAllMocks();});

it('splits a formatted paragraph with Enter and merges it back without losing marks',()=>{
  render(<Editor initial={{version:1,blocks:[{type:'paragraph',align:'center',runs:[run('Réserve '),run('12 Nm',['bold'])]}]}}/>);
  const first=screen.getByRole('textbox',{name:'Texte du bloc 1'});caret(first,8);fireEvent.keyDown(first,{key:'Enter'});
  expect(value().blocks).toEqual([{type:'paragraph',align:'center',runs:[run('Réserve ')]},{type:'paragraph',align:'left',runs:[run('12 Nm',['bold'])]}]);
  const second=screen.getByRole('textbox',{name:'Texte du bloc 2'});caret(second);fireEvent.keyDown(second,{key:'Backspace'});
  expect(value().blocks).toEqual([{type:'paragraph',align:'center',runs:[run('Réserve '),run('12 Nm',['bold'])]}]);
  expect(validNoteContent(value())).toBe(true);
  fireEvent.click(screen.getByRole('button',{name:'Annuler'}));expect(value().blocks).toHaveLength(2);
  fireEvent.click(screen.getByRole('button',{name:'Rétablir'}));expect(value().blocks).toHaveLength(1);
});

it('writes checklists with Enter and Tab, then leaves the empty item with Enter',()=>{
  render(<Editor initial={{version:1,blocks:[{type:'list',kind:'checklist',items:[{runs:[run('Vérifier le plan')],checked:true,indent:0}]}]}}/>);
  const first=screen.getByRole('textbox',{name:'Élément 1 du bloc 1'});caret(first,16);fireEvent.keyDown(first,{key:'Enter'});
  expect(value().blocks[0]).toMatchObject({items:[{checked:true},{checked:false,runs:[]}]});
  const second=screen.getByRole('textbox',{name:'Élément 2 du bloc 1'});caret(second);fireEvent.keyDown(second,{key:'Tab'});
  expect(value().blocks[0]).toMatchObject({items:[{}, {indent:1}]});
  fireEvent.keyDown(second,{key:'Enter'});
  expect(value().blocks).toEqual([{type:'list',kind:'checklist',items:[{runs:[run('Vérifier le plan')],checked:true,indent:0}]},{type:'paragraph',align:'left',runs:[]}]);
  expect(screen.queryByRole('button',{name:'Ajouter un élément'})).toBeNull();
  expect(validNoteContent(value())).toBe(true);
});

it('changes list style in place and exposes secondary actions without controls beside each block',()=>{
  render(<Editor initial={{version:1,blocks:[paragraph('Action à confirmer'),paragraph('Compte rendu') ]}}/>);
  caret(screen.getByRole('textbox',{name:'Texte du bloc 1'}),5);
  fireEvent.click(screen.getByRole('button',{name:'Liste à puces'}));
  expect(value().blocks[0]).toEqual({type:'list',kind:'bullet',items:[{runs:[run('Action à confirmer')],checked:false,indent:0}]});
  expect(document.querySelector('.note-block-actions')).toBeNull();
  expect(document.querySelector('details.note-format-menu')?.hasAttribute('open')).toBe(false);
  expect(document.querySelector('.note-block button')).toBeNull();
  fireEvent.click(screen.getByText(/Insérer \/ format/));
  expect(screen.getByRole('button',{name:'Ajouter un élément'})).toBeTruthy();
  fireEvent.click(screen.getByRole('button',{name:'Ajouter un élément'}));
  expect(value().blocks[0]).toMatchObject({items:[{}, {runs:[],checked:false,indent:0}]});
});

it('tabs across a table and adds a row while preserving headers, links and images',()=>{
  const image={type:'image' as const,attachment_id:'12345678-1234-1234-1234-123456789012',caption:'Plan de référence'};
  const link={...run('Plan',['italic']),href:'https://example.com/plan'};
  const initial:NoteContent={version:1,blocks:[{type:'table',header:true,rows:[[[run('Sujet',['bold'])],[run('Décision')]],[[link],[run('À vérifier')]]]},image]};
  render(<Editor initial={initial}/>);
  const cell=screen.getByRole('textbox',{name:'Ligne 2, colonne 2 du bloc 1'});caret(cell);fireEvent.keyDown(cell,{key:'Tab'});
  expect(value().blocks).toEqual([{...initial.blocks[0],rows:[[[run('Sujet',['bold'])],[run('Décision')]],[[link],[run('À vérifier')]],[[],[]]]},image]);
  expect(screen.getByRole('textbox',{name:'Ligne 3, colonne 1 du bloc 1'})).toBe(document.activeElement);
  expect(document.querySelectorAll('th')).toHaveLength(2);expect(validNoteContent(value())).toBe(true);
});

it('keeps read-only note content unchanged when editing keys are sent',()=>{
  const initial:NoteContent={version:1,blocks:[paragraph('Décision validée')]};render(<Editor initial={initial} disabled/>);
  const text=screen.getByRole('textbox',{name:'Texte du bloc 1'});caret(text,8);fireEvent.keyDown(text,{key:'Enter'});fireEvent.keyDown(text,{key:'Backspace'});
  expect(value()).toEqual(initial);expect(text.getAttribute('contenteditable')).toBe('false');expect(screen.queryByRole('toolbar')).toBeNull();
});

it('restores the cursor after undoing or redoing a paragraph split',()=>{
  render(<Editor initial={{version:1,blocks:[paragraph('Plan à revoir')]}}/>);
  const first=screen.getByRole('textbox',{name:'Texte du bloc 1'});caret(first,5);fireEvent.keyDown(first,{key:'Enter'});
  expect(screen.getByRole('textbox',{name:'Texte du bloc 2'})).toBe(document.activeElement);
  fireEvent.click(screen.getByRole('button',{name:'Annuler'}));
  expect(value().blocks).toEqual([paragraph('Plan à revoir')]);
  expect(screen.getByRole('textbox',{name:'Texte du bloc 1'})).toBe(document.activeElement);
  expect(window.getSelection()!.getRangeAt(0).startOffset).toBe(5);
  fireEvent.click(screen.getByRole('button',{name:'Rétablir'}));
  expect(value().blocks).toHaveLength(2);expect(screen.getByRole('textbox',{name:'Texte du bloc 2'})).toBe(document.activeElement);
  expect(window.getSelection()!.getRangeAt(0).startOffset).toBe(0);
});

it('formats a selection across paragraphs as one reversible change and keeps intervening images',()=>{
  const image={type:'image' as const,attachment_id:'12345678-1234-1234-1234-123456789012',caption:'Plan conservé'};
  const initial:NoteContent={version:1,blocks:[paragraph('Alpha'),image,paragraph('Bêta')]};render(<Editor initial={initial}/>);
  const first=screen.getByRole('textbox',{name:'Texte du bloc 1'}),last=screen.getByRole('textbox',{name:'Texte du bloc 3'});
  first.focus();const range=document.createRange();range.setStart(first.firstChild!,2);range.setEnd(last.firstChild!,2);
  window.getSelection()!.removeAllRanges();window.getSelection()!.addRange(range);
  fireEvent.click(screen.getByText(/Insérer \/ format/));fireEvent.click(screen.getByRole('button',{name:'Code'}));
  expect(value().blocks).toEqual([{type:'paragraph',align:'left',runs:[run('Al'),run('pha',['code'])]},image,{type:'paragraph',align:'left',runs:[run('Bê',['code']),run('ta')]}]);
  expect(document.querySelectorAll('.note-document-page>.note-block')).toHaveLength(3);
  expect(screen.getByRole('img',{name:'Plan conservé'})).toBeTruthy();expect(validNoteContent(value())).toBe(true);
  fireEvent.click(screen.getByRole('button',{name:'Annuler'}));expect(value()).toEqual(initial);
  expect(screen.getByRole('button',{name:'Annuler'})).toHaveProperty('disabled',true);
  fireEvent.click(screen.getByRole('button',{name:'Rétablir'}));expect(value().blocks[1]).toEqual(image);
});
