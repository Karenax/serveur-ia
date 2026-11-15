import {afterEach,expect,it,vi} from 'vitest';
import {act,cleanup,fireEvent,render,screen} from '@testing-library/react';
import {MeetingTranscriptEdit} from './MeetingTranscriptEdit';
import {meetingSessions,type LiveTranscriptSegment,type MeetingSession} from '../lib/meetingSessions';

const segment:LiveTranscriptSegment={id:'segment-fictif',track:'mic',start_ms:0,end_ms:1000,
  speaker:'Voix fictive',text:'Puissance non validée.',revision:1,finalized:false};
const row:MeetingSession={id:'session-fictive',title:'Recette fictive',kind:'note',project_id:null,
  brain_project_id:null,state:'completed',revision:1,date:'2026-10-12',recording_id:null,note_id:null,
  tracks:[],total_bytes:0,duration_seconds:0,issues:[],created_at:'2026-10-12',updated_at:'2026-10-12',segments:[segment]};
afterEach(()=>{cleanup();vi.restoreAllMocks();});
const reloadIsBlocked=()=>{
  const event=new Event('beforeunload',{cancelable:true});window.dispatchEvent(event);return event.defaultPrevented;
};
const open=()=>{render(<MeetingTranscriptEdit session={row} segment={segment} onChanged={vi.fn()}/>);
  fireEvent.click(screen.getByRole('button',{name:'Corriger ce passage'}));};

it('protège une correction seule à actualisation, puis retire la garde après fermeture explicite',()=>{
  open();expect(reloadIsBlocked()).toBe(false);
  fireEvent.change(screen.getByLabelText('Texte corrigé'),{target:{value:'Puissance de 250 W à confirmer.'}});
  expect(reloadIsBlocked()).toBe(true);
  fireEvent.click(screen.getByRole('button',{name:'Fermer la correction'}));
  expect(reloadIsBlocked()).toBe(false);
});

it('protège aussi un changement d’intervenant sans modification du texte',()=>{
  open();fireEvent.change(screen.getByLabelText('Intervenant'),{target:{value:'Intervenant fictif 2'}});
  expect(reloadIsBlocked()).toBe(true);
});

it('protège une commande incertaine sans changement texte, puis libère après accusé de sauvegarde',async()=>{
  let resolve!:(value:MeetingSession)=>void;
  vi.spyOn(meetingSessions,'editSegment').mockReturnValue(new Promise(finish=>{resolve=finish;}));
  open();fireEvent.click(screen.getByRole('button',{name:'Enregistrer cette correction'}));
  expect(reloadIsBlocked()).toBe(true);
  expect(screen.getByLabelText('Texte corrigé').closest('[data-workspace-dirty="true"]')).toBeTruthy();
  await act(async()=>{resolve({...row,revision:2});});
  expect(reloadIsBlocked()).toBe(false);
});

it('conserve garde et payload de reprise après échec réseau malgré un texte inchangé',async()=>{
  vi.spyOn(meetingSessions,'editSegment').mockRejectedValue(new Error('Panne réseau fictive'));
  vi.spyOn(meetingSessions,'get').mockResolvedValue(row);
  open();fireEvent.click(screen.getByRole('button',{name:'Enregistrer cette correction'}));
  await screen.findByText('Panne réseau fictive');
  expect(reloadIsBlocked()).toBe(true);
  expect(screen.getByRole('button',{name:'Reprendre la correction'})).toBeTruthy();
});
