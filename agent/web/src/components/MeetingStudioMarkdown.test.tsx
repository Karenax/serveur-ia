import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {MeetingStudio} from './MeetingStudio';
import {meetingSessions,type MeetingSession,type SessionCapabilities} from '../lib/meetingSessions';
import {markdownDraftKey} from '../lib/noteMarkdown';
import type {NoteContent} from '../lib/projectNotes';

vi.mock('./AssistantPanel',()=>({AssistantPanel:()=>null}));
vi.mock('./MeetingAudioPanel',()=>({MeetingAudioPanel:()=>null}));
const note=(text:string):NoteContent=>({version:1,blocks:[{type:'paragraph',align:'left',runs:[{text,marks:[],href:null,color:null}]}]});
const a:MeetingSession={id:'markdown-a',title:'Séance A',kind:'note',project_id:'erp',brain_project_id:'brain',state:'created',revision:3,
  date:'2026-10-11',recording_id:null,note_id:'note-a',note_revision:4,note_version_id:'v4',
  note:{id:'note-a',project_id:'erp',title:'Note A',content:note('Puissance non validée.'),revision:4,version_id:'v4',attachment_ids:[],
    read_only:false,source_kind:null,updated_at:'2026-10-11',actor_id:'local'},tracks:[],total_bytes:0,duration_seconds:0,issues:[],created_at:'2026-10-11',updated_at:'2026-10-11'};
const b:MeetingSession={...a,id:'markdown-b',title:'Séance B',note_id:'note-b',note:{...a.note!,id:'note-b',title:'Note B',content:note('Cote B à confirmer.')}};
const capabilities:SessionCapabilities={enabled:true,capture:{durable:true,max_upload_mb:50,max_duration_minutes:120,tracks:['mic','system'],browser_permission_required:true},
  transcription:{batch_ready:false,live_ready:false,detail:'Essai fictif sans audio'},notes:{staging:true,erp_projection:true},assistant:{ready:true}};
beforeEach(()=>{localStorage.clear();vi.spyOn(meetingSessions,'watchEvents').mockResolvedValue(undefined);vi.spyOn(meetingSessions,'get').mockImplementation(async id=>id===a.id?a:b);
  vi.spyOn(meetingSessions,'askHistory').mockResolvedValue({items:[]});vi.spyOn(meetingSessions,'enhancements').mockResolvedValue({items:[]});vi.spyOn(meetingSessions,'liveAnswers').mockResolvedValue({items:[]});});
afterEach(()=>{cleanup();vi.restoreAllMocks();});

it('conserve le vrai brouillon Markdown invalide par séance puis convertit explicitement avant sauvegarde canonique',async()=>{
  const converted=note('Puissance 250 W non validée.');
  const save=vi.spyOn(meetingSessions,'saveNote').mockResolvedValue({...a,revision:4,note_revision:5,note_version_id:'v5',note:{...a.note!,revision:5,version_id:'v5',content:converted}});
  const props={rows:[],capabilities,onClose:vi.fn(),onOpenProject:vi.fn()};
  const view=render(<MeetingStudio key={a.id} sessionId={a.id} {...props}/>);
  await screen.findByRole('textbox',{name:'Texte du bloc 1'});fireEvent.click(screen.getByRole('button',{name:'Éditer en Markdown'}));
  fireEvent.change(screen.getByLabelText('Texte Markdown'),{target:{value:'**Puissance 250 W non validée.'}});
  await screen.findByText('Brouillon Markdown invalide : corrigez-le et appliquez-le avant d’enregistrer, d’améliorer ou de publier la note.');
  expect(screen.getByRole('button',{name:'Valider et revenir à l’éditeur riche'})).toHaveProperty('disabled',true);
  expect(screen.getByRole('button',{name:'Enregistrer la note'})).toHaveProperty('disabled',true);
  fireEvent.click(screen.getByRole('button',{name:'Notes enrichies'}));
  expect(screen.getByRole('button',{name:'Améliorer les notes'})).toHaveProperty('disabled',true);
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer la note'}));expect(save).not.toHaveBeenCalled();
  view.rerender(<MeetingStudio key={b.id} sessionId={b.id} {...props}/>);await screen.findByRole('textbox',{name:'Texte du bloc 1'});
  expect(screen.getByRole('textbox',{name:'Texte du bloc 1'}).textContent).toBe('Cote B à confirmer.');
  view.rerender(<MeetingStudio key={a.id} sessionId={a.id} {...props}/>);
  await screen.findByDisplayValue('**Puissance 250 W non validée.');
  expect(JSON.parse(localStorage.getItem(markdownDraftKey(a.id))!).text).toBe('**Puissance 250 W non validée.');
  fireEvent.change(screen.getByLabelText('Texte Markdown'),{target:{value:'Puissance 250 W non validée.'}});
  expect(screen.getByRole('button',{name:'Enregistrer la note'})).toHaveProperty('disabled',true);
  fireEvent.click(screen.getByRole('button',{name:'Valider et revenir à l’éditeur riche'}));
  expect(screen.getByRole('textbox',{name:'Texte du bloc 1'}).textContent).toBe('Puissance 250 W non validée.');
  expect(localStorage.getItem(markdownDraftKey(a.id))).toBeNull();
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer la note'}));
  await waitFor(()=>expect(save).toHaveBeenCalledWith(a.id,expect.objectContaining({content:converted,expected_note_revision:4,expected_note_version_id:'v4'})));
  await screen.findByText('Note enregistrée · version 5');
  expect(localStorage.getItem('agent.meeting-note.v1.'+a.id)).toBeNull();
});
