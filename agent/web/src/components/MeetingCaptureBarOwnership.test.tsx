import {afterEach,expect,it,vi} from 'vitest';
import {act,cleanup,fireEvent,render,screen} from '@testing-library/react';
import {MeetingCaptureBar} from './MeetingStudio';
import {meetingCapture,type CaptureSnapshot} from '../lib/meetingCapture';
import type {MeetingSession} from '../lib/meetingSessions';

afterEach(()=>{cleanup();vi.restoreAllMocks();});
it('garde l’annulation globale active pendant la confirmation du partage audio',async()=>{
  let state:CaptureSnapshot={sessionId:'sid',title:'Fictif',phase:'ready',tracks:[],seconds:0,totalBytes:0,savedBytes:0,pending:0,error:''};
  let emit:()=>void=()=>{},resolveStart:(row:MeetingSession)=>void=()=>{};
  vi.spyOn(meetingCapture,'getSnapshot').mockImplementation(()=>state);
  vi.spyOn(meetingCapture,'subscribe').mockImplementation(listener=>{emit=listener;return()=>{};});
  vi.spyOn(meetingCapture,'recover').mockResolvedValue(undefined);
  vi.spyOn(meetingCapture,'activatePrepared').mockImplementation(()=>{
    state={...state,phase:'starting'};emit();
    return new Promise(resolve=>{resolveStart=resolve;});
  });
  const stop=vi.spyOn(meetingCapture,'stop').mockResolvedValue(null);
  render(<MeetingCaptureBar onOpen={vi.fn()}/>);
  fireEvent.click(screen.getByRole('button',{name:'Choisir l’audio du PC et démarrer'}));
  const cancel=screen.getByRole('button',{name:'Annuler le démarrage audio'});
  expect(cancel).toHaveProperty('disabled',false);
  fireEvent.click(cancel);expect(stop).toHaveBeenCalledTimes(1);
  await act(async()=>{resolveStart({id:'sid'} as MeetingSession);});
});
