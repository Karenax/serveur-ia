import {installPublicationLocksForTest} from '../test/publicationLocks';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {act,cleanup,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import {MeetingNotePublication} from './MeetingNotePublication';
import {MeetingTranscriptEdit} from './MeetingTranscriptEdit';
import {meetingSessions,type MeetingSession} from '../lib/meetingSessions';
import {notesApi,type NoteVersion} from '../lib/projectNotes';
const session:MeetingSession={id:'sid',title:'Revue',kind:'note',project_id:'erp',brain_project_id:'brain',state:'completed',revision:4,date:'2026-10-11',recording_id:null,note_id:'note',
  note_revision:2,note_version_id:'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',note:{id:'note',project_id:'erp',title:'Note',revision:2,version_id:'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
    content:{version:1,blocks:[{type:'paragraph',align:'left',runs:[{text:'Attendre le contrôle avant fabrication.',marks:[],href:null,color:null}]}]},
    attachment_ids:[],read_only:false,source_kind:null,updated_at:'2026-10-11',actor_id:'owner'},tracks:[],total_bytes:0,duration_seconds:0,issues:[],created_at:'2026-10-11',updated_at:'2026-10-11'};
beforeEach(()=>{installPublicationLocksForTest();localStorage.clear();});afterEach(()=>{cleanup();vi.restoreAllMocks();});
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
it('ne publie qu’une commande lors de deux activations simultanées et la reprend après interruption',async()=>{
  let reject!:(reason:Error)=>void;
  const publish=vi.spyOn(meetingSessions,'publishNotes')
    .mockReturnValueOnce(new Promise((_resolve,fail)=>{reject=fail;}))
    .mockResolvedValueOnce({session:{...session,published_meeting_id:'cr'},meeting_id:'cr',published_note_version_id:session.note_version_id!,action_ids:[],replayed:true});
  const changed=vi.fn();render(<MeetingNotePublication session={session} dirty={false} unfinished={false} onPublished={changed} onOpenProject={vi.fn()}/>);
  fireEvent.change(screen.getByLabelText('Synthèse relue'),{target:{value:'Fabrication suspendue au contrôle.'}});
  fireEvent.click(screen.getByLabelText(/J’ai relu la synthèse/));
  const button=screen.getByRole('button',{name:'Publier le compte rendu relu'});
  act(()=>{fireEvent.click(button);fireEvent.click(button);});
  expect(publish).toHaveBeenCalledTimes(1);
  const original=publish.mock.calls[0][1];
  expect(JSON.parse(localStorage.getItem('agent.meeting-publication.v1.sid')!).pending).toEqual(original);
  await act(async()=>reject(new Error('Réseau interrompu')));
  await screen.findByText('Réseau interrompu');
  expect(screen.getByLabelText('Synthèse relue')).toHaveProperty('value','Fabrication suspendue au contrôle.');
  fireEvent.click(screen.getByRole('button',{name:'Reprendre la publication conservée'}));
  await waitFor(()=>expect(changed).toHaveBeenCalledTimes(1));
  expect(publish).toHaveBeenCalledTimes(2);
  expect(publish.mock.calls[1][1]).toEqual(original);
});
it('garde la synthèse et permet de réessayer si le stockage local refuse la commande',async()=>{
  const publish=vi.spyOn(meetingSessions,'publishNotes').mockResolvedValue({session:{...session,published_meeting_id:'cr'},meeting_id:'cr',
    published_note_version_id:session.note_version_id!,action_ids:[],replayed:false});
  render(<MeetingNotePublication session={session} dirty={false} unfinished={false} onPublished={vi.fn()} onOpenProject={vi.fn()}/>);
  fireEvent.change(screen.getByLabelText('Synthèse relue'),{target:{value:'Décision à conserver.'}});
  fireEvent.click(screen.getByLabelText(/J’ai relu la synthèse/));
  const storage=vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw new Error('stockage indisponible');});
  fireEvent.click(screen.getByRole('button',{name:'Publier le compte rendu relu'}));
  await screen.findByText(/Le brouillon de publication ne peut pas être conservé/);
  expect(publish).not.toHaveBeenCalled();
  expect(screen.getByLabelText('Synthèse relue')).toHaveProperty('value','Décision à conserver.');
  storage.mockRestore();
  fireEvent.click(screen.getByRole('button',{name:'Publier le compte rendu relu'}));
  await waitFor(()=>expect(publish).toHaveBeenCalledTimes(1));
});
it('conserve et rend accessibles les champs non ajoutés après publication et réouverture',async()=>{
  const published={...session,published_meeting_id:'cr'};
  vi.spyOn(meetingSessions,'publishNotes').mockResolvedValue({session:published,meeting_id:'cr',
    published_note_version_id:session.note_version_id!,action_ids:[],replayed:false});
  const changed=vi.fn();const props={session,dirty:false,unfinished:false,onPublished:changed,onOpenProject:vi.fn()};
  const view=render(<MeetingNotePublication {...props}/>);
  fireEvent.change(screen.getByLabelText('Synthèse relue'),{target:{value:'Synthèse à publier.'}});
  fireEvent.change(screen.getByLabelText('Élément du compte rendu'),{target:{value:'actions'}});
  fireEvent.change(screen.getByLabelText('Formulation'),{target:{value:'Vérifier le montage'}});
  fireEvent.change(screen.getByLabelText('Bloc cité'),{target:{value:'0'}});
  fireEvent.change(screen.getByLabelText('Responsable'),{target:{value:'Camille'}});
  fireEvent.change(screen.getByLabelText('Échéance'),{target:{value:'2026-10-23'}});
  fireEvent.click(screen.getByLabelText(/J’ai relu la synthèse/));
  fireEvent.click(screen.getByRole('button',{name:'Publier le compte rendu relu'}));
  await waitFor(()=>expect(changed).toHaveBeenCalledTimes(1));
  expect(JSON.parse(localStorage.getItem('agent.meeting-publication.v1.sid')!).fields).toMatchObject({
    kind:'actions',text:'Vérifier le montage',blockIndex:'0',owner:'Camille',due:'2026-10-23'});
  view.unmount();render(<MeetingNotePublication {...props} session={published}/>);
  expect(screen.getByText('Brouillon conservé sur cet appareil')).toBeTruthy();
  expect(screen.getByText('Vérifier le montage')).toBeTruthy();
  expect(screen.getByText('Camille')).toBeTruthy();
  expect(screen.getByText('2026-10-23')).toBeTruthy();
});
it('reprend une ancienne publication en gardant les champs non ajoutés',async()=>{
  const summary={overview:'Synthèse relue.',decisions:[],actions:[],open_points:[]};
  const command={command_id:'commande-fictive',expected_revision:4,expected_note_revision:2,
    expected_note_version_id:session.note_version_id!,summary};
  const fields={kind:'actions',text:'Vérifier le montage',blockIndex:'0',quote:'Attendre le contrôle',owner:'Camille',due:'2026-10-23'};
  localStorage.setItem('agent.meeting-publication.v1.sid',JSON.stringify({version:session.note_version_id,pending:command,summary,fields}));
  const published={...session,published_meeting_id:'cr'};
  const publish=vi.spyOn(meetingSessions,'publishNotes').mockResolvedValue({session:published,meeting_id:'cr',
    published_note_version_id:session.note_version_id!,action_ids:[],replayed:true});
  const changed=vi.fn();const props={session,dirty:false,unfinished:false,onPublished:changed,onOpenProject:vi.fn()};
  const view=render(<MeetingNotePublication {...props}/>);
  fireEvent.click(screen.getByRole('button',{name:'Reprendre la publication conservée'}));
  await waitFor(()=>expect(changed).toHaveBeenCalledTimes(1));
  expect(publish).toHaveBeenCalledWith(session.id,command);
  expect(JSON.parse(localStorage.getItem('agent.meeting-publication.v1.sid')!).fields).toEqual(fields);
  view.rerender(<MeetingNotePublication {...props} session={published}/>);
  expect(screen.getByText('Vérifier le montage')).toBeTruthy();
});
it('retire le brouillon après publication lorsqu’aucun élément ne reste en préparation',async()=>{
  const published={...session,published_meeting_id:'cr'};
  vi.spyOn(meetingSessions,'publishNotes').mockResolvedValue({session:published,meeting_id:'cr',
    published_note_version_id:session.note_version_id!,action_ids:[],replayed:false});
  const changed=vi.fn();const props={session,dirty:false,unfinished:false,onPublished:changed,onOpenProject:vi.fn()};
  const view=render(<MeetingNotePublication {...props}/>);
  fireEvent.change(screen.getByLabelText('Synthèse relue'),{target:{value:'Synthèse complète.'}});
  fireEvent.click(screen.getByLabelText(/J’ai relu la synthèse/));
  fireEvent.click(screen.getByRole('button',{name:'Publier le compte rendu relu'}));
  await waitFor(()=>expect(changed).toHaveBeenCalledTimes(1));
  expect(localStorage.getItem('agent.meeting-publication.v1.sid')).toBeNull();
  view.rerender(<MeetingNotePublication {...props} session={published}/>);
  expect(screen.queryByText('Brouillon conservé sur cet appareil')).toBeNull();
});
it('ne supprime pas un brouillon remplacé depuis un autre onglet pendant la publication',async()=>{
  let resolve!:(value:Awaited<ReturnType<typeof meetingSessions.publishNotes>>)=>void;
  vi.spyOn(meetingSessions,'publishNotes').mockReturnValue(new Promise(done=>{resolve=done;}));
  const published={...session,published_meeting_id:'cr'};
  const changed=vi.fn();const props={session,dirty:false,unfinished:false,onPublished:changed,onOpenProject:vi.fn()};
  const view=render(<MeetingNotePublication {...props}/>);
  fireEvent.change(screen.getByLabelText('Synthèse relue'),{target:{value:'Première synthèse.'}});
  fireEvent.click(screen.getByLabelText(/J’ai relu la synthèse/));
  fireEvent.click(screen.getByRole('button',{name:'Publier le compte rendu relu'}));
  const other={version:session.note_version_id,pending:null,
    summary:{overview:'Synthèse d’un autre onglet.',decisions:[],actions:[],open_points:[]},
    fields:{kind:'decisions',text:'Autre décision à conserver',blockIndex:'0',quote:'Attendre le contrôle',owner:'',due:''}};
  localStorage.setItem('agent.meeting-publication.v1.sid',JSON.stringify(other));
  await act(async()=>resolve({session:published,meeting_id:'cr',published_note_version_id:session.note_version_id!,action_ids:[],replayed:false}));
  expect(JSON.parse(localStorage.getItem('agent.meeting-publication.v1.sid')!)).toEqual(other);
  view.rerender(<MeetingNotePublication {...props} session={published}/>);
  expect(screen.getByText('Synthèse d’un autre onglet.')).toBeTruthy();
  expect(screen.getByText('Autre décision à conserver')).toBeTruthy();
});
it('rend un brouillon local accessible si une autre personne a déjà publié',()=>{
  localStorage.setItem('agent.meeting-publication.v1.sid',JSON.stringify({version:session.note_version_id,pending:null,
    summary:{overview:'Synthèse locale à comparer.',decisions:[{text:'Décision locale',block_index:0,quote:'Attendre le contrôle'}],actions:[],open_points:[]},
    fields:{kind:'decisions',text:'Autre idée locale',blockIndex:'0',quote:'Attendre le contrôle',owner:'',due:''}}));
  render(<MeetingNotePublication session={{...session,published_meeting_id:'cr'}} dirty={false} unfinished={false} onPublished={vi.fn()} onOpenProject={vi.fn()}/>);
  expect(screen.getByText('Brouillon conservé sur cet appareil')).toBeTruthy();
  expect(screen.getByText('Synthèse locale à comparer.')).toBeTruthy();
  expect(screen.getByText('Décision locale')).toBeTruthy();
  expect(screen.getByText('Autre idée locale')).toBeTruthy();
  expect(localStorage.getItem('agent.meeting-publication.v1.sid')).not.toBeNull();
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
it('garde le brouillon visible si une publication distante arrive pendant la saisie',()=>{
  const props={session,dirty:false,unfinished:false,onPublished:vi.fn(),onOpenProject:vi.fn()};
  const view=render(<MeetingNotePublication {...props}/>);
  fireEvent.change(screen.getByLabelText('Synthèse relue'),{target:{value:'Texte local en cours.'}});
  fireEvent.change(screen.getByLabelText('Formulation'),{target:{value:'Élément non ajouté.'}});
  view.rerender(<MeetingNotePublication {...props} session={{...session,published_meeting_id:'cr'}}/>);
  expect(screen.getByText('Brouillon conservé sur cet appareil')).toBeTruthy();
  expect(screen.getByText('Texte local en cours.')).toBeTruthy();
  expect(screen.getByText('Élément non ajouté.')).toBeTruthy();
});
it('réserve l’édition à une fenêtre et recharge le dernier brouillon lorsque la seconde reprend',async()=>{
  const held=new Set<string>();
  Object.defineProperty(navigator,'locks',{configurable:true,value:{request:(name:string,_options:unknown,callback:(lock:Lock|null)=>Promise<void>)=>{
    if(held.has(name))return callback(null);
    held.add(name);return callback({name,mode:'exclusive'} as Lock).finally(()=>held.delete(name));
  }}});
  const props={session,dirty:false,unfinished:false,onPublished:vi.fn(),onOpenProject:vi.fn()};
  const first=render(<MeetingNotePublication {...props}/>);
  const second=render(<MeetingNotePublication {...props}/>);
  const a=within(first.container),b=within(second.container);
  await waitFor(()=>expect(a.getByLabelText('Formulation').matches(':disabled')).toBe(false));
  await waitFor(()=>expect(b.getByLabelText('Formulation').matches(':disabled')).toBe(true));
  expect(b.getByText(/Ce compte rendu est ouvert dans une autre fenêtre/)).toBeTruthy();
  fireEvent.change(a.getByLabelText('Formulation'),{target:{value:'Brouillon de la première fenêtre'}});
  expect(JSON.parse(localStorage.getItem('agent.meeting-publication.v1.sid')!).fields.text).toBe('Brouillon de la première fenêtre');
  first.unmount();await waitFor(()=>expect(held.size).toBe(0));
  fireEvent.click(b.getByRole('button',{name:'réessayez'}));
  await waitFor(()=>expect(b.getByLabelText('Formulation').matches(':disabled')).toBe(false));
  expect(b.getByLabelText('Formulation')).toHaveProperty('value','Brouillon de la première fenêtre');
});
it('reprend un ancien brouillon dont certains champs facultatifs sont absents',()=>{
  localStorage.setItem('agent.meeting-publication.v1.sid',JSON.stringify({version:session.note_version_id,pending:null,
    summary:{overview:'Synthèse ancienne.',decisions:[],actions:[],open_points:[]},fields:{kind:'actions',text:'Action ancienne'}}));
  render(<MeetingNotePublication session={session} dirty={false} unfinished={false} onPublished={vi.fn()} onOpenProject={vi.fn()}/>);
  expect(screen.queryByText(/Le brouillon local ne peut pas être relu/)).toBeNull();
  expect(screen.getByLabelText('Formulation')).toHaveProperty('value','Action ancienne');
  expect(screen.getByLabelText('Formulation').matches(':disabled')).toBe(false);
  expect(screen.getByLabelText('Responsable')).toHaveProperty('value','');
});
it('conserve le brouillon et interdit l’édition si la protection du navigateur est absente',()=>{
  const original=JSON.stringify({version:session.note_version_id,pending:null,
    summary:{overview:'Synthèse conservée.',decisions:[],actions:[],open_points:[]},
    fields:{kind:'decisions',text:'Brouillon conservé',blockIndex:'',quote:'',owner:'',due:''}});
  localStorage.setItem('agent.meeting-publication.v1.sid',original);
  Object.defineProperty(navigator,'locks',{configurable:true,value:undefined});
  render(<MeetingNotePublication session={session} dirty={false} unfinished={false} onPublished={vi.fn()} onOpenProject={vi.fn()}/>);
  expect(screen.getByText(/Impossible de protéger ce brouillon entre fenêtres/)).toBeTruthy();
  expect(screen.getByLabelText('Formulation').matches(':disabled')).toBe(true);
  expect(screen.getByLabelText('Formulation')).toHaveProperty('value','Brouillon conservé');
  expect(localStorage.getItem('agent.meeting-publication.v1.sid')).toBe(original);
});
it('n’envoie qu’une correction de transcription simultanée et reprend la même commande après coupure',async()=>{
  const segment={id:'segment',track:'mic' as const,start_ms:1000,end_ms:2500,speaker:'Voix 1',text:'Ne pas fabriquer.',revision:1,finalized:false};
  let reject!:(reason:Error)=>void;
  const save=vi.spyOn(meetingSessions,'editSegment')
    .mockReturnValueOnce(new Promise((_resolve,fail)=>{reject=fail;}))
    .mockResolvedValueOnce({...session,revision:5});
  vi.spyOn(meetingSessions,'get').mockResolvedValue({...session,segments:[segment]});
  const changed=vi.fn();render(<MeetingTranscriptEdit session={session} segment={segment} onChanged={changed}/>);
  fireEvent.click(screen.getByRole('button',{name:'Corriger ce passage'}));
  fireEvent.change(screen.getByLabelText('Texte corrigé'),{target:{value:'Ne pas fabriquer avant validation.'}});
  const button=screen.getByRole('button',{name:'Enregistrer cette correction'});
  act(()=>{fireEvent.click(button);fireEvent.click(button);});
  expect(save).toHaveBeenCalledTimes(1);
  const original=save.mock.calls[0][2];
  await act(async()=>reject(new Error('Réseau interrompu')));
  await screen.findByText('Réseau interrompu');
  expect(screen.getByLabelText('Texte corrigé')).toHaveProperty('value','Ne pas fabriquer avant validation.');
  fireEvent.click(screen.getByRole('button',{name:'Reprendre la correction'}));
  await waitFor(()=>expect(save).toHaveBeenCalledTimes(2));
  expect(save.mock.calls[1][2]).toEqual(original);
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
