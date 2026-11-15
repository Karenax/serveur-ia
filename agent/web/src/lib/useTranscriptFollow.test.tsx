import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen} from '@testing-library/react';
import {useTranscriptFollow} from './useTranscriptFollow';

afterEach(()=>{cleanup();vi.restoreAllMocks();});
function Harness({id='s1',state='recording',visible=true,rows=1,editing=false}:{id?:string;state?:string;visible?:boolean;rows?:number;editing?:boolean}){
  const live=['recording','paused'].includes(state);
  const follow=useTranscriptFollow({sessionId:id,live,visible,update:String(rows)});
  return <><textarea aria-label="Notes"/><div ref={node=>{
    follow.panelRef.current=node;
    if(node){Object.defineProperty(node,'clientHeight',{configurable:true,value:100});
      node.getBoundingClientRect=()=>({bottom:100} as DOMRect);}
  }} data-testid="pane" hidden={!visible} onScroll={follow.onScroll} onWheel={follow.onWheel}
    onKeyDown={follow.onKeyDown} onFocusCapture={follow.onFocusCapture}>
    {live&&<>{follow.following?<span>Suivi du direct</span>:<button onClick={follow.returnToLive}>Revenir au direct</button>}</>}
    <ol ref={node=>{
      follow.listRef.current=node;
      if(node){const last=node.lastElementChild as HTMLElement;
        last.getBoundingClientRect=()=>({bottom:rows*200-(follow.panelRef.current?.scrollTop||0)} as DOMRect);}
    }}><li>Dernier passage{editing&&<div className="meeting-transcript-edit"><textarea aria-label="Correction" defaultValue="Brouillon"/></div>}</li></ol>
  </div></>;
}

it('suit les nouveaux passages dans le panneau pendant enregistrement et pause, en conservant le focus des notes',()=>{
  const scrollPage=vi.spyOn(window,'scrollTo').mockImplementation(()=>{});
  const view=render(<Harness/>),pane=screen.getByTestId('pane');
  expect(pane.scrollTop).toBe(112);
  const notes=screen.getByLabelText('Notes');notes.focus();
  view.rerender(<Harness rows={2}/>);expect(pane.scrollTop).toBe(312);
  view.rerender(<Harness state="paused" rows={3}/>);expect(pane.scrollTop).toBe(512);
  expect(document.activeElement).toBe(notes);expect(scrollPage).not.toHaveBeenCalled();
});

it('conserve la lecture manuelle et reprend seulement sur Revenir au direct',()=>{
  const view=render(<Harness/>),pane=screen.getByTestId('pane');
  pane.scrollTop=20;fireEvent.scroll(pane);
  view.rerender(<Harness rows={2}/>);expect(pane.scrollTop).toBe(20);
  fireEvent.click(screen.getByRole('button',{name:'Revenir au direct'}));expect(pane.scrollTop).toBe(312);
  view.rerender(<Harness rows={3}/>);expect(pane.scrollTop).toBe(512);
});

it('ne déplace aucun autre onglet et conserve le choix de lecture en quittant la transcription',()=>{
  const view=render(<Harness/>),pane=screen.getByTestId('pane');
  view.rerender(<Harness visible={false} rows={2}/>);expect(pane.scrollTop).toBe(112);
  view.rerender(<Harness rows={2}/>);expect(pane.scrollTop).toBe(312);
  fireEvent.wheel(pane,{deltaY:-10});pane.scrollTop=25;fireEvent.scroll(pane);
  view.rerender(<Harness visible={false} rows={3}/>);
  view.rerender(<Harness rows={3}/>);expect(pane.scrollTop).toBe(25);
  expect(screen.getByRole('button',{name:'Revenir au direct'})).toBeTruthy();
});

it('laisse une séance terminée en lecture sans suivi automatique',()=>{
  const view=render(<Harness state="completed"/>),pane=screen.getByTestId('pane');
  view.rerender(<Harness state="completed" rows={2}/>);expect(pane.scrollTop).toBe(0);
  expect(screen.queryByText('Suivi du direct')).toBeNull();expect(screen.queryByRole('button',{name:'Revenir au direct'})).toBeNull();
});

it('protège la correction et son focus quand un nouveau passage arrive',()=>{
  const view=render(<Harness/>),pane=screen.getByTestId('pane');
  view.rerender(<Harness editing/>);
  const input=screen.getByLabelText('Correction');input.focus();fireEvent.change(input,{target:{value:'Correction en cours'}});
  view.rerender(<Harness editing rows={2}/>);
  expect(pane.scrollTop).toBe(112);expect(document.activeElement).toBe(input);
  expect(screen.getByDisplayValue('Correction en cours')).toBe(input);
  expect(screen.getByRole('button',{name:'Revenir au direct'})).toBeTruthy();
});

it('ouvre une autre séance avec le suivi actif sans transférer son choix de lecture',()=>{
  const view=render(<Harness/>),pane=screen.getByTestId('pane');
  fireEvent.keyDown(pane,{key:'PageUp'});pane.scrollTop=10;fireEvent.scroll(pane);
  view.rerender(<Harness id="s2" rows={2}/>);expect(pane.scrollTop).toBe(312);
  expect(screen.getByText('Suivi du direct')).toBeTruthy();
});
