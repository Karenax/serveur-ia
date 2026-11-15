import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen} from '@testing-library/react';
import {NoteRichEditor} from './NoteRichEditor';
import {markdownDraftKey} from '../lib/noteMarkdown';
import type {NoteContent} from '../lib/projectNotes';
const run=(text:string)=>({text,marks:[] as [],href:null,color:null});
const original:NoteContent={version:1,blocks:[{type:'paragraph',align:'left',runs:[run('Ne pas valider : 12 Nm provisoires.')]}]};
const props={content:original,projectId:'erp-a',noteId:'note-a',draftId:'session-a'};
afterEach(()=>{cleanup();vi.restoreAllMocks();localStorage.clear();});
const enter=()=>fireEvent.click(screen.getByRole('button',{name:'Éditer en Markdown'}));
const apply=()=>screen.getByRole('button',{name:'Valider et revenir à l’éditeur riche'});
it('ne transmet que la conversion validée et garde le journal avant application',()=>{
  const change=vi.fn(),state=vi.fn();render(<NoteRichEditor {...props} onChange={change} onMarkdownDraftState={state}/>);enter();
  fireEvent.change(screen.getByLabelText('Texte Markdown'),{target:{value:'# Revue\n\nNe **pas** valider : 12 Nm.'}});
  expect(change).not.toHaveBeenCalled();expect(state).toHaveBeenLastCalledWith({pending:true,valid:true});
  expect(JSON.parse(localStorage.getItem(markdownDraftKey('session-a'))!).base).toEqual(original);
  fireEvent.click(apply());expect(change).toHaveBeenCalledExactlyOnceWith({version:1,blocks:[
    {type:'heading',level:1,runs:[run('Revue')]},
    {type:'paragraph',align:'left',runs:[run('Ne '),{...run('pas'),marks:['bold']},run(' valider : 12 Nm.')]},
  ]});
  expect(state).toHaveBeenLastCalledWith({pending:false,valid:true});
  expect(localStorage.getItem(markdownDraftKey('session-a'))).toBeNull();
});
it('garde la saisie invalide et son journal au départ A→B→A, sans appel onChange',()=>{
  const change=vi.fn(),state=vi.fn();const view=render(<NoteRichEditor {...props} onChange={change} onMarkdownDraftState={state}/>);enter();
  fireEvent.change(screen.getByLabelText('Texte Markdown'),{target:{value:'**Réserve non fermée'}});
  expect(apply()).toHaveProperty('disabled',true);expect(state).toHaveBeenLastCalledWith({pending:true,valid:false});
  expect(document.querySelector('[data-workspace-dirty="true"]')).toBeTruthy();
  view.rerender(<NoteRichEditor {...props} draftId="session-b" projectId="erp-b" onChange={change}/>);
  expect(screen.queryByLabelText('Texte Markdown')).toBeNull();
  view.rerender(<NoteRichEditor {...props} onChange={change} onMarkdownDraftState={state}/>);
  expect(screen.getByLabelText('Texte Markdown')).toHaveProperty('value','**Réserve non fermée');expect(change).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button',{name:'Écarter ce brouillon Markdown'}));
  expect(localStorage.getItem(markdownDraftKey('session-a'))).toBeNull();expect(change).not.toHaveBeenCalled();
});
it('signale un changement riche externe et exige une reprise explicite du buffer',()=>{
  const change=vi.fn(),view=render(<NoteRichEditor {...props} onChange={change}/>);enter();
  fireEvent.change(screen.getByLabelText('Texte Markdown'),{target:{value:'Ne pas publier IP65.'}});
  const external:NoteContent={version:1,blocks:[{type:'paragraph',align:'left',runs:[run('Version reçue : IP67 à vérifier.')]}]};
  view.rerender(<NoteRichEditor {...props} content={external} onChange={change}/>);
  expect(apply()).toHaveProperty('disabled',true);expect(screen.getByText(/La note riche a changé depuis ce brouillon/)).toBeTruthy();
  expect(JSON.parse(localStorage.getItem(markdownDraftKey('session-a'))!).base).toEqual(original);
  fireEvent.click(screen.getByRole('button',{name:'Reprendre ce Markdown sur la note affichée'}));
  expect(apply()).toHaveProperty('disabled',false);expect(change).not.toHaveBeenCalled();fireEvent.click(apply());
  expect(change).toHaveBeenCalledWith(expect.objectContaining({blocks:[expect.objectContaining({runs:[run('Ne pas publier IP65.')]})]}));
  expect(external.blocks[0]).toHaveProperty('runs',[run('Version reçue : IP67 à vérifier.')]);
});
it('refuse les tableaux sans aplatir la note riche ni démarrer un brouillon',()=>{
  const content:NoteContent={version:1,blocks:[{type:'table',header:true,rows:[[[run('Article')],[run('Tube 316L')]]]}]},change=vi.fn();
  render(<NoteRichEditor {...props} content={content} onChange={change}/>);enter();
  expect(screen.queryByLabelText('Texte Markdown')).toBeNull();expect(screen.getByText(/Tableaux et images restent/)).toBeTruthy();
  expect(screen.getByRole('textbox',{name:'Ligne 1, colonne 2 du bloc 1'}).textContent).toBe('Tube 316L');expect(change).not.toHaveBeenCalled();
});
it('conserve la saisie lorsque le stockage Markdown est plein et autorise une reprise explicite',()=>{
  const change=vi.fn(),state=vi.fn();render(<NoteRichEditor {...props} onChange={change} onMarkdownDraftState={state}/>);enter();
  const store=vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw new DOMException('Quota','QuotaExceededError');});
  fireEvent.change(screen.getByLabelText('Texte Markdown'),{target:{value:'IP65 non confirmé.'}});
  expect(screen.getByLabelText('Texte Markdown')).toHaveProperty('value','IP65 non confirmé.');expect(apply()).toHaveProperty('disabled',true);
  expect(state).toHaveBeenLastCalledWith({pending:true,valid:false});expect(change).not.toHaveBeenCalled();
  store.mockRestore();fireEvent.click(screen.getByRole('button',{name:'Réessayer la conservation Markdown'}));
  expect(apply()).toHaveProperty('disabled',false);fireEvent.click(apply());expect(change).toHaveBeenCalledTimes(1);
});
it('ne clôture pas un buffer si le parent refuse sa conservation et ne partage pas une clé vide',()=>{
  const change=vi.fn().mockReturnValue(false);render(<NoteRichEditor {...props} onChange={change}/>);enter();
  fireEvent.change(screen.getByLabelText('Texte Markdown'),{target:{value:'12 Nm non approuvé.'}});fireEvent.click(apply());
  expect(screen.getByLabelText('Texte Markdown')).toHaveProperty('value','12 Nm non approuvé.');
  expect(localStorage.getItem(markdownDraftKey('session-a'))).not.toBeNull();
  cleanup();render(<NoteRichEditor content={original} projectId="" noteId="" onChange={vi.fn()}/>);enter();
  expect(screen.queryByLabelText('Texte Markdown')).toBeNull();expect(screen.getByText(/Identité de note requise/)).toBeTruthy();
});
