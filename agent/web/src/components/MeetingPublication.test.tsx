import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {MeetingNotePublication} from './MeetingNotePublication';
import {MeetingTranscriptEdit} from './MeetingTranscriptEdit';
import {meetingSessions,type MeetingSession} from '../lib/meetingSessions';
import {notesApi,type NoteVersion} from '../lib/projectNotes';
const session:MeetingSession={id:'sid',title:'Revue',kind:'note',project_id:'erp',brain_project_id:'brain',state:'completed',revision:4,date:'2026-10-11',recording_id:null,note_id:'note',
  note_revision:2,note_version_id:'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',note:{id:'note',project_id:'erp',title:'Note',revision:2,version_id:'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
    content:{version:1,blocks:[{type:'paragraph',align:'left',runs:[{text:'Attendre le contrôle avant fabrication.',marks:[],href:null,color:null}]}]},
    attachment_ids:[],read_only:false,source_kind:null,updated_at:'2026-10-11',actor_id:'owner'},tracks:[],total_bytes:0,duration_seconds:0,issues:[],created_at:'2026-10-11',updated_at:'2026-10-11'};
beforeEach(()=>{localStorage.clear();});afterEach(()=>{cleanup();vi.restoreAllMocks();});
it('lie le compte rendu publié au projet et à son identifiant dans une URL rechargeable',()=>{
  render(<MeetingNotePublication session={{...session,published_meeting_id:'report'}} dirty={false} unfinished={false} onPublished={vi.fn()} onOpenProject={vi.fn()}/>);
  expect(screen.getByRole('link',{name:'Ouvrir le compte rendu'}).getAttribute('href')).toBe('/app/projects/erp/reviews?meeting=report');
});
it('garde la version des notes publiée même si la note courante a changé',async()=>{
  const load=vi.spyOn(notesApi,'version').mockResolvedValue({id:'published-version',project_id:'erp',note_id:'note',revision:2,title:'Notes publiées',actor_id:'human',created_at:'2026-10-11T15:30:00Z',operation:'save',
    value:{title:'Notes publiées',content:session.note!.content},attachment_bindings:{}} as NoteVersion);
  render(<MeetingNotePublication session={{...session,note_version_id:'new-version',published_meeting_id:'report',published_note_version_id:'published-version'}} dirty={false} unfinished={false} onPublished={vi.fn()} onOpenProject={vi.fn()}/>);
  expect(screen.getByRole('link',{name:'Ouvrir la version des notes publiée'}).getAttribute('href')).toBe('/api/v1/projects/erp/notes/note/versions/published-version');
  fireEvent.click(screen.getByRole('button',{name:'Lire les notes publiées'}));await screen.findByText('Notes publiées · version 2');
  expect(load).toHaveBeenCalledWith('erp','note','published-version',expect.any(AbortSignal));
});
it('permet de relire la version ancienne du brouillon lorsque la note a changé',()=>{
  localStorage.setItem('agent.meeting-publication.v1.sid',JSON.stringify({version:'old-version',pending:null,
    summary:{overview:'Réserve relue',decisions:[{text:'Attendre',block_index:0,quote:'Attendre'}],actions:[],open_points:[]}}));
  render(<MeetingNotePublication session={session} dirty={false} unfinished={false} onPublished={vi.fn()} onOpenProject={vi.fn()}/>);
  expect(screen.getByRole('link',{name:'Ouvrir la version citée des notes'}).getAttribute('href')).toBe('/api/v1/projects/erp/notes/note/versions/old-version');
  expect(screen.getByText('Bloc 1 de la version citée')).toBeTruthy();
});
it('publie seulement après relecture avec citations de la version ERP et rejoue sa commande exacte après perte réseau',async()=>{
  const publish=vi.spyOn(meetingSessions,'publishNotes').mockRejectedValueOnce(new Error('Réseau interrompu')).mockResolvedValueOnce({session:{...session,published_meeting_id:'cr'},meeting_id:'cr',published_note_version_id:session.note_version_id!,action_ids:[],replayed:true});
  const changed=vi.fn();render(<MeetingNotePublication session={session} dirty={false} unfinished={false} onPublished={changed} onOpenProject={vi.fn()}/>);
  const button=screen.getByRole('button',{name:'Publier le compte rendu relu'});expect(button).toHaveProperty('disabled',true);
  fireEvent.change(screen.getByLabelText('Synthèse relue'),{target:{value:'Fabrication suspendue au contrôle.'}});
  fireEvent.change(screen.getByLabelText('Formulation'),{target:{value:'Attendre le contrôle'}});
  fireEvent.change(screen.getByLabelText('Bloc cité'),{target:{value:'0'}});
  fireEvent.click(screen.getByRole('button',{name:'Ajouter au compte rendu'}));
  fireEvent.click(screen.getByLabelText(/J’ai relu la synthèse/));fireEvent.click(button);
  await screen.findByText('Réseau interrompu');
  const original=publish.mock.calls[0][1];expect(original).toMatchObject({expected_revision:4,expected_note_revision:2,expected_note_version_id:session.note_version_id,
    summary:{decisions:[{text:'Attendre le contrôle',block_index:0,quote:'Attendre le contrôle avant fabrication.'}],actions:[]}});
  fireEvent.click(screen.getByRole('button',{name:'Reprendre la publication conservée'}));
  await waitFor(()=>expect(changed).toHaveBeenCalled());expect(publish.mock.calls[1][1]).toEqual(original);
});
it('interdit une citation qui ne figure pas exactement dans les notes',()=>{
  render(<MeetingNotePublication session={session} dirty={false} unfinished={false} onPublished={vi.fn()} onOpenProject={vi.fn()}/>);
  fireEvent.change(screen.getByLabelText('Formulation'),{target:{value:'Fabriquer immédiatement'}});
  fireEvent.change(screen.getByLabelText('Bloc cité'),{target:{value:'0'}});
  fireEvent.change(screen.getByLabelText('Extrait exact de la note'),{target:{value:'Fabriquer immédiatement'}});
  expect(screen.getByRole('button',{name:'Ajouter au compte rendu'})).toHaveProperty('disabled',true);
});
it.each([{unfinished:true,dirty:false},{unfinished:false,dirty:true}])('distingue séance non terminée et corrections réelles : %j',({unfinished,dirty})=>{
  const publish=vi.spyOn(meetingSessions,'publishNotes');
  const props={session,dirty:false,unfinished:false,onPublished:vi.fn(),onOpenProject:vi.fn()};
  const view=render(<MeetingNotePublication {...props}/>);
  fireEvent.change(screen.getByLabelText('Synthèse relue'),{target:{value:'Attendre le contrôle.'}});
  fireEvent.click(screen.getByLabelText(/J’ai relu la synthèse/));
  expect(screen.getByRole('button',{name:'Publier le compte rendu relu'})).toHaveProperty('disabled',false);
  view.rerender(<MeetingNotePublication {...props} session={{...session,state:unfinished?'created':'completed'}} dirty={dirty} unfinished={unfinished}/>);
  expect(!!screen.queryByText(/Terminez la prise de notes avant de publier/)).toBe(unfinished);
  expect(!!screen.queryByText(/corrections à enregistrer/)).toBe(dirty);
  expect(screen.getByLabelText(/J’ai relu la synthèse/).matches(':disabled')).toBe(true);
  fireEvent.click(screen.getByRole('button',{name:'Publier le compte rendu relu'}));
  expect(publish).not.toHaveBeenCalled();
  view.rerender(<MeetingNotePublication {...props}/>);
  expect(screen.getByRole('button',{name:'Publier le compte rendu relu'})).toHaveProperty('disabled',false);
});
it('retrouve tous les champs non ajoutés après remontage sans les publier ni les approuver',()=>{
  const publish=vi.spyOn(meetingSessions,'publishNotes');
  const props={session,dirty:false,unfinished:false,onPublished:vi.fn(),onOpenProject:vi.fn()};
  const view=render(<MeetingNotePublication {...props}/>);
  fireEvent.change(screen.getByLabelText('Élément du compte rendu'),{target:{value:'actions'}});
  fireEvent.change(screen.getByLabelText('Formulation'),{target:{value:'Vérifier le matériel'}});
  fireEvent.change(screen.getByLabelText('Bloc cité'),{target:{value:'0'}});
  fireEvent.change(screen.getByLabelText('Extrait exact de la note'),{target:{value:'Attendre le contrôle'}});
  fireEvent.change(screen.getByLabelText('Responsable'),{target:{value:'Paul'}});
  fireEvent.change(screen.getByLabelText('Échéance'),{target:{value:'2026-10-23'}});
  view.unmount();render(<MeetingNotePublication {...props}/>);
  expect(screen.getByLabelText('Élément du compte rendu')).toHaveProperty('value','actions');
  expect(screen.getByLabelText('Formulation')).toHaveProperty('value','Vérifier le matériel');
  expect(screen.getByLabelText('Bloc cité')).toHaveProperty('value','0');
  expect(screen.getByLabelText('Extrait exact de la note')).toHaveProperty('value','Attendre le contrôle');
  expect(screen.getByLabelText('Responsable')).toHaveProperty('value','Paul');
  expect(screen.getByLabelText('Échéance')).toHaveProperty('value','2026-10-23');
  expect(screen.getByLabelText(/J’ai relu la synthèse/)).toHaveProperty('checked',false);
  expect(screen.getByRole('button',{name:'Publier le compte rendu relu'})).toHaveProperty('disabled',true);
  expect(publish).not.toHaveBeenCalled();
});
it('garde la version préparée et les champs non ajoutés quand une autre version de note arrive',()=>{
  const props={session,dirty:false,unfinished:false,onPublished:vi.fn(),onOpenProject:vi.fn()};
  const view=render(<MeetingNotePublication {...props}/>);
  fireEvent.change(screen.getByLabelText('Formulation'),{target:{value:'Contrôler avant fabrication'}});
  fireEvent.change(screen.getByLabelText('Bloc cité'),{target:{value:'0'}});
  const changed={...session,note_revision:3,note_version_id:'new-version',note:{...session.note!,revision:3,version_id:'new-version'}};
  view.rerender(<MeetingNotePublication {...props} session={changed}/>);
  expect(screen.getByText(/La note a changé depuis la préparation/)).toBeTruthy();
  expect(screen.getByLabelText('Formulation')).toHaveProperty('value','Contrôler avant fabrication');
  expect(screen.getByLabelText('Bloc cité')).toHaveProperty('value','0');
  expect(JSON.parse(localStorage.getItem('agent.meeting-publication.v1.sid')!)).toMatchObject({version:session.note_version_id});
  expect(screen.getByRole('button',{name:'Publier le compte rendu relu'})).toHaveProperty('disabled',true);
});
it('préserve le texte corrigé face à un conflit de révision live',async()=>{
  const segment={id:'segment',track:'mic' as const,start_ms:1000,end_ms:2500,speaker:'Voix 1',text:'Ne pas fabriquer.',revision:1,finalized:false};
  vi.spyOn(meetingSessions,'editSegment').mockRejectedValue(new Error('Le segment a changé'));
  vi.spyOn(meetingSessions,'get').mockResolvedValue({...session,revision:5,segments:[{...segment,text:'Ne pas fabriquer avant contrôle.',revision:2}]});
  render(<MeetingTranscriptEdit session={session} segment={segment} onChanged={vi.fn()}/>);
  fireEvent.click(screen.getByRole('button',{name:'Corriger ce passage'}));
  fireEvent.change(screen.getByLabelText('Texte corrigé'),{target:{value:'Ne pas fabriquer avant validation client.'}});
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer cette correction'}));
  await screen.findByText('Ce passage ou la séance a changé. Votre correction reste conservée.');
  expect(screen.getByLabelText('Texte corrigé')).toHaveProperty('value','Ne pas fabriquer avant validation client.');
  expect(screen.getByRole('button',{name:'Reprendre la correction'})).toHaveProperty('disabled',true);
});
