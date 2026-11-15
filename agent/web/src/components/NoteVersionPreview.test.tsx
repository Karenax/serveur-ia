import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import {NoteVersionPreview} from './NoteVersionPreview';
import {notesApi,type NoteContent,type NoteVersion} from '../lib/projectNotes';
import {meetingSessions,type SessionNoteVersion} from '../lib/meetingSessions';

const url='/api/v1/projects/erp/notes/note/versions/v2';
const content:NoteContent={version:1,blocks:[{type:'paragraph',align:'left',runs:[{text:'Devis 250 W non validé.',marks:[],href:null,color:null}]}]};
const version:NoteVersion={id:'v2',project_id:'erp',note_id:'note',revision:2,title:'Note exacte',created_at:'2026-10-11T15:30:00Z',actor_id:'human',operation:'save',
  value:{title:'Note exacte',content},attachment_bindings:{}};
afterEach(()=>{cleanup();vi.restoreAllMocks();});

it('charge seulement la version exacte demandée et affiche son titre, date et contenu readonly',async()=>{
  let finish!:(value:NoteVersion)=>void;
  const load=vi.spyOn(notesApi,'version').mockReturnValue(new Promise(resolve=>{finish=resolve;})),head=vi.spyOn(notesApi,'read');
  render(<NoteVersionPreview citation={{source_url:url,locator:{note_version_id:'v2',block_index:0}}}/>);
  expect(load).not.toHaveBeenCalled();fireEvent.click(screen.getByRole('button',{name:'Lire la version citée'}));
  await screen.findByText('Chargement de la version citée…');expect(load).toHaveBeenCalledWith('erp','note','v2',expect.any(AbortSignal));
  finish(version);const preview=await screen.findByRole('region',{name:'Aperçu de la version citée'});
  await within(preview).findByText('Note exacte · version 2');expect(within(preview).getByText('Devis 250 W non validé.')).toBeTruthy();
  expect(preview.querySelector('time')?.getAttribute('datetime')).toBe(version.created_at);
  expect(within(preview).queryByRole('textbox')).toBeNull();expect(head).not.toHaveBeenCalled();
  expect(within(preview).getByRole('link',{name:'Télécharger cette version de note'}).getAttribute('href')).toBe(url);
});

it('télécharge la version citée sous le préfixe du web Kiara', async () => {
  const previous = window.location.href;
  window.history.replaceState(null, '', '/agent/app/sources');
  try {
    vi.spyOn(notesApi, 'version').mockResolvedValue(version);
    render(<NoteVersionPreview citation={{source_url:url}}/>);
    fireEvent.click(screen.getByRole('button', {name:'Lire la version citée'}));
    const download = await screen.findByRole('link', {name:'Télécharger cette version de note'});
    expect(download.getAttribute('href')).toBe(`/agent${url}`);
  } finally {
    window.history.replaceState(null, '', previous);
  }
});

it.each([{id:'wrong-version'},{project_id:'other-project'},{note_id:'other-note'}])('refuse une version incohérente sans afficher son contenu : %j',async mismatch=>{
  vi.spyOn(notesApi,'version').mockResolvedValue({...version,...mismatch});
  render(<NoteVersionPreview citation={{source_url:url}}/>);fireEvent.click(screen.getByRole('button',{name:'Lire la version citée'}));
  await screen.findByText('La version reçue ne correspond pas à la note citée.');expect(screen.queryByText('Devis 250 W non validé.')).toBeNull();
});

it('refuse une forme de note incompatible avec son schéma',async()=>{
  vi.spyOn(notesApi,'version').mockResolvedValue({...version,value:{title:'Note exacte',content:{version:1,blocks:[{type:'script'}]} as unknown as NoteContent}});
  render(<NoteVersionPreview citation={{source_url:url}}/>);fireEvent.click(screen.getByRole('button',{name:'Lire la version citée'}));
  await screen.findByText('Le contenu de cette version de note est incompatible avec l’aperçu.');expect(screen.queryByText('Note exacte · version 2')).toBeNull();
});

it('expose le refus de droits et permet une reprise explicite du même snapshot',async()=>{
  const load=vi.spyOn(notesApi,'version').mockRejectedValueOnce(new Error('Accès interdit (403)')).mockResolvedValueOnce(version);
  render(<NoteVersionPreview citation={{source_url:url}}/>);fireEvent.click(screen.getByRole('button',{name:'Lire la version citée'}));
  await screen.findByText('Accès interdit (403)');expect(screen.queryByText('Devis 250 W non validé.')).toBeNull();
  fireEvent.click(screen.getByRole('button',{name:'Relire cette version'}));await screen.findByText('Devis 250 W non validé.');
  expect(load.mock.calls.map(call=>call.slice(0,3))).toEqual([['erp','note','v2'],['erp','note','v2']]);
});

it('annule la lecture à la fermeture et ignore la réponse tardive avant une autre citation',async()=>{
  let finish!:(value:NoteVersion)=>void;
  const load=vi.spyOn(notesApi,'version').mockReturnValueOnce(new Promise(resolve=>{finish=resolve;})).mockResolvedValueOnce({...version,id:'v3',revision:3,value:{...version.value,title:'Autre version'}});
  const view=render(<NoteVersionPreview citation={{source_url:url}}/>);fireEvent.click(screen.getByRole('button',{name:'Lire la version citée'}));
  await waitFor(()=>expect(load).toHaveBeenCalledOnce());const signal=load.mock.calls[0][3]!;
  fireEvent.click(screen.getByRole('button',{name:'Fermer l’aperçu de version'}));expect(signal.aborted).toBe(true);
  view.rerender(<NoteVersionPreview citation={{source_url:'/api/v1/projects/erp/notes/note/versions/v3'}}/>);
  finish(version);fireEvent.click(screen.getByRole('button',{name:'Lire la version citée'}));await screen.findByText('Autre version · version 3');
  expect(screen.queryByText('Note exacte · version 2')).toBeNull();view.unmount();expect(load.mock.calls[1][3]?.aborted).toBe(true);
});

it('affiche la pièce historique liée au snapshot sans substituer une pièce de la tête actuelle',async()=>{
  const old='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',bound='bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
  const original:NoteVersion={...version,value:{title:'Image conservée',content:{version:1,blocks:[{type:'image',attachment_id:old,caption:'Schéma avant modification'}]}},attachment_bindings:{[old]:bound}};
  const load=vi.spyOn(notesApi,'version').mockResolvedValue(original),head=vi.spyOn(notesApi,'read');
  render(<NoteVersionPreview citation={{source_url:url}}/>);fireEvent.click(screen.getByRole('button',{name:'Lire la version citée'}));
  const image=await screen.findByRole('img',{name:'Schéma avant modification'});
  expect(image.getAttribute('src')).toBe(`/api/v1/projects/erp/notes/note/attachments/${bound}/image`);
  expect(original.value.content.blocks[0]).toMatchObject({attachment_id:old});expect(head).not.toHaveBeenCalled();expect(load).toHaveBeenCalledOnce();
});

it('refuse une image historique dépourvue de liaison plutôt que de charger l’identifiant périmé',async()=>{
  vi.spyOn(notesApi,'version').mockResolvedValue({...version,value:{title:'Image',content:{version:1,blocks:[{type:'image',attachment_id:'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',caption:'Ancienne image'}]}}});
  render(<NoteVersionPreview citation={{source_url:url}}/>);fireEvent.click(screen.getByRole('button',{name:'Lire la version citée'}));
  await screen.findByText('Image historique sans liaison actuelle');expect(screen.queryByRole('img')).toBeNull();
});

it('ne propose aucun chargement depuis une adresse extérieure ou une identité de locator discordante',()=>{
  const load=vi.spyOn(notesApi,'version');const view=render(<NoteVersionPreview citation={{source_url:'https://outside.example/version'}}/>);
  expect(screen.queryByRole('button')).toBeNull();view.rerender(<NoteVersionPreview citation={{source_url:url,locator:{note_version_id:'other'}}}/>);
  expect(screen.queryByRole('button')).toBeNull();expect(load).not.toHaveBeenCalled();
});

it('lit le snapshot historique exact d’une note sans projet et n’interroge pas la tête de séance',async()=>{
  const snapshot:SessionNoteVersion={id:'stage-v1',session_id:'sid',revision:1,title:'Brouillon historique sans projet',content,plain_text:'Devis 250 W non validé.',
    sha256:'a'.repeat(64),created_at:'2026-10-11T15:30:00Z'};
  const load=vi.spyOn(meetingSessions,'noteVersion').mockResolvedValue(snapshot),head=vi.spyOn(meetingSessions,'get');
  render(<NoteVersionPreview citation={{source_url:'/api/v1/meeting-sessions/sid',locator:{staged_note_version_id:'stage-v1',note_version_id:'stage-v1',session_id:'sid'}}}/>);
  fireEvent.click(screen.getByRole('button',{name:'Lire la version citée'}));await screen.findByText('Brouillon historique sans projet · version 1');
  expect(load).toHaveBeenCalledWith('sid','stage-v1',expect.any(AbortSignal));expect(head).not.toHaveBeenCalled();
  expect(screen.getByRole('link',{name:'Télécharger cette version de note'}).getAttribute('href')).toBe('/api/v1/meeting-sessions/sid/note-versions/stage-v1');
});

it.each([{id:'foreign-version',session_id:'sid'},{id:'stage-v1',session_id:'foreign-session'}])('refuse un snapshot staging étranger : %j',async identity=>{
  vi.spyOn(meetingSessions,'noteVersion').mockResolvedValue({...identity,revision:1,title:'Ne pas afficher',content,plain_text:'',sha256:'a'.repeat(64),created_at:'2026-10-11T15:30:00Z'});
  render(<NoteVersionPreview citation={{source_url:'/api/v1/meeting-sessions/sid/note-versions/stage-v1'}}/>);
  fireEvent.click(screen.getByRole('button',{name:'Lire la version citée'}));await screen.findByText('La version reçue ne correspond pas au brouillon de séance cité.');
  expect(screen.queryByText('Devis 250 W non validé.')).toBeNull();
});
