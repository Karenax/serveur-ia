import {afterEach, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, within, waitFor} from '@testing-library/react';
import {MeetingStudio} from './MeetingStudio';
import {meetingSessions, type MeetingSession, type SessionCapabilities} from '../lib/meetingSessions';
import {meetingAudio, type MeetingRecording} from '../lib/meetingAudio';
import {meetingCapture} from '../lib/meetingCapture';

// Keep the real Studio and audio/review panel together; no hardware or transport.
vi.mock('./NoteRichEditor', () => ({NoteRichEditor: () => null, NoteContentView: () => null}));
vi.mock('./MeetingCalendarContext', () => ({MeetingCalendarContext: () => null}));
afterEach(() => {cleanup(); localStorage.clear(); vi.restoreAllMocks();});

const session: MeetingSession = {
  id:'review-session', title:'Réunion relue', kind:'meeting', project_id:'erp', brain_project_id:'brain',
  state:'completed', revision:4, date:'2026-10-16', recording_id:'recording', note_id:null,
  tracks:[], chunks:[], total_bytes:0, duration_seconds:20, issues:[],
  created_at:'2026-10-16', updated_at:'2026-10-16', transcript_provisional:true,
  segments:[{id:'live-old', track:'mic', start_ms:0, end_ms:5000, speaker:'Voix 1',
    text:'Provisoire : 2250 watts.', revision:1, finalized:false}],
};
const record: MeetingRecording = {
  id:'recording', source_id:'source', title:'Réunion relue', date:'2026-10-16', filename:'fictitious.wav',
  num_speakers:1, segments:[{id:'complete-1', start:0, end:5, speaker:'SPEAKER_01', text:'Puissance relue : 1250 watts.'}],
  speaker_names:{SPEAKER_01:'Marie'}, revision:2, reviewed_revision:2, summary_revision:2,
  summary:{overview:'Brouillon privé du CR.', decisions:[], actions:[], open_points:[]},
  summary_model:'réseau', published_meeting_id:null, job_kind:'synthesis', job_status:'completed', stage:'synthesized',
  progress:100, processed_seconds:20, duration_seconds:20, cancel_requested:false, error:null,
  created_at:'2026-10-16', updated_at:'2026-10-16',
};
const capabilities: SessionCapabilities = {
  enabled:true, capture:{durable:true, max_upload_mb:50, max_duration_minutes:120,
    tracks:['mic','system'], browser_permission_required:true},
  transcription:{enabled:false, batch_ready:true, live_ready:false, detail:''},
  notes:{staging:true, erp_projection:true},
};

it('présente la transcription relue avant le direct archivé, unifie les onglets et conserve les deux brouillons', async () => {
  localStorage.setItem('agent-meeting-layout-v2','complete');
  vi.spyOn(meetingSessions,'get').mockResolvedValue(session);
  vi.spyOn(meetingSessions,'watchEvents').mockResolvedValue(undefined);
  vi.spyOn(meetingSessions,'askHistory').mockResolvedValue({items:[]});
  vi.spyOn(meetingSessions,'enhancements').mockResolvedValue({items:[]});
  vi.spyOn(meetingSessions,'liveAnswers').mockResolvedValue({items:[]});
  vi.spyOn(meetingAudio,'list').mockResolvedValue([record]);
  vi.spyOn(meetingAudio,'get').mockResolvedValue(record);
  vi.spyOn(meetingAudio,'status').mockResolvedValue({ready:true, model:'medium', device:'cpu',
    detail:'Prêt', max_upload_mb:50, max_duration_minutes:120});
  const transcribe=vi.spyOn(meetingAudio,'transcribe'), synthesize=vi.spyOn(meetingAudio,'synthesize');
  const publish=vi.spyOn(meetingAudio,'publish'), capture=vi.spyOn(meetingCapture,'start');
  const transport=vi.spyOn(globalThis,'fetch').mockRejectedValue(new Error('Transport non autorisé dans cette fixture'));
  render(<MeetingStudio sessionId={session.id} rows={[]} capabilities={capabilities} onClose={vi.fn()} onOpenProject={vi.fn()}/>);
  fireEvent.click(await screen.findByRole('tab',{name:'Transcription'}));
  const corrected=await screen.findByRole('textbox',{name:'Texte complete-1'});
  expect(corrected).toHaveProperty('value','Puissance relue : 1250 watts.');
  expect(screen.getAllByRole('tab',{name:'Transcription'})).toHaveLength(1);
  const history=screen.getByText('Historique du direct (texte provisoire)').closest('details')!;
  expect(history.open).toBe(false);
  expect(corrected.compareDocumentPosition(history) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  fireEvent.click(screen.getByRole('tab',{name:'Compte rendu'}));
  const summary=await screen.findByRole('textbox',{name:'Résumé de la réunion'});
  fireEvent.change(summary,{target:{value:'CR humain non publié.'}});
  fireEvent.click(screen.getByRole('tab',{name:'Transcription'}));
  fireEvent.click(screen.getByRole('tab',{name:'Compte rendu'}));
  expect(screen.getByRole('textbox',{name:'Résumé de la réunion'})).toHaveProperty('value','CR humain non publié.');
  fireEvent.click(screen.getByRole('tab',{name:'Transcription'}));
  fireEvent.change(screen.getByRole('textbox',{name:'Texte complete-1'}),{target:{value:'Correction en cours : 1500 watts.'}});
  fireEvent.click(screen.getByRole('tab',{name:'Compte rendu'}));
  // A stale human draft stays visible for recovery, with publication disabled.
  expect(screen.getByText('La transcription a changé. Refaites le compte rendu après validation.')).toBeTruthy();
  expect(screen.getByRole('textbox',{name:'Résumé de la réunion'})).toHaveProperty('value','CR humain non publié.');
  expect(screen.getByRole('button',{name:'Valider et enregistrer le compte rendu'})).toHaveProperty('disabled',true);
  fireEvent.click(screen.getByRole('tab',{name:'Transcription'}));
  expect(screen.getByRole('textbox',{name:'Texte complete-1'})).toHaveProperty('value','Correction en cours : 1500 watts.');
  fireEvent.click(within(history).getByText('Historique du direct (texte provisoire)'));
  expect(within(history).getByText('Provisoire : 2250 watts.')).toBeTruthy();
  const review=vi.spyOn(meetingAudio,'review').mockResolvedValue({...record, revision:3, reviewed_revision:3,
    segments:[{...record.segments[0], text:'Correction en cours : 1500 watts.'}]});
  fireEvent.click(screen.getByRole('button',{name:'Valider la transcription'}));
  await waitFor(()=>expect(review).toHaveBeenCalledOnce());
  await waitFor(()=>expect(screen.getByRole('tab',{name:'Compte rendu'})).toHaveProperty('ariaSelected','true'));
  expect(screen.getByRole('textbox',{name:'Résumé de la réunion'})).toHaveProperty('value','CR humain non publié.');
  expect(screen.getByRole('button',{name:'Valider et enregistrer le compte rendu'})).toHaveProperty('disabled',true);
  expect(transcribe).not.toHaveBeenCalled(); expect(synthesize).not.toHaveBeenCalled();
  expect(publish).not.toHaveBeenCalled(); expect(capture).not.toHaveBeenCalled(); expect(transport).not.toHaveBeenCalled();
});
