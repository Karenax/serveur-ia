import {expect,it} from 'vitest';
import {citationSourceUrl,citationReaderUrl,citationAudioUrl,citationLocatorText,isNoteVersionUrl} from './citationLinks';

it('ouvre un lecteur lisible sans changer les versions exactes ni les téléchargements',()=>{
  expect(citationReaderUrl({source_id:'mail-1'})).toBe('/app/sources?source=mail-1');
  expect(citationReaderUrl({source_url:'/v1/sources/mail-1'})).toBe('/app/sources?source=mail-1');
  expect(citationReaderUrl({source_id:'mail-1',source_url:'/v1/sources/other'})).toBeNull();
  expect(citationReaderUrl({source_url:'/v1/sources/mail-1/raw'})).toBe('/v1/sources/mail-1/raw');
  expect(citationReaderUrl({source_url:'/api/v1/projects/erp/notes/note/versions/v2'})).toBe('/api/v1/projects/erp/notes/note/versions/v2');
});

it('conserve une version ancienne et refuse une incohérence avec ses identifiants',()=>{
  const source_url='/api/v1/projects/erp/notes/note/versions/v2';
  expect(citationSourceUrl({source_id:'head',source_url,locator:{note_version_id:'v2'}})).toBe(source_url);
  expect(citationSourceUrl({source_url,locator:{note_version_id:'v3'}})).toBeNull();
  expect(citationSourceUrl({source_url:'/v1/sources/head',source_id:'head',locator:{erp_project_id:'erp',note_id:'note',note_version_id:'v2'}})).toBe(source_url);
});
it('refuse une autre source, une autre séance et les liens externes sans preuve locale',()=>{
  expect(citationSourceUrl({source_url:'/v1/sources/other',source_id:'expected'})).toBeNull();
  expect(citationSourceUrl({source_url:'/api/v1/meeting-sessions/other/segments',locator:{session_id:'expected'}})).toBeNull();
  for(const source_url of ['https://external.invalid/secret','//external.invalid','javascript:alert(1)','/api/v1/projects/p/notes/n/versions/%2e%2e'])
    expect(citationSourceUrl({source_url})).toBeNull();
});
it('conserve la piste et le timecode audio et refuse une piste ou séance incohérente',()=>{
  const audio_url='/api/v1/meeting-sessions/sid/audio?track=system#t=3.5';
  expect(citationAudioUrl({audio_url,locator:{session_id:'sid',track:'system'}})).toBe(audio_url);
  expect(citationAudioUrl({audio_url,locator:{session_id:'other'}})).toBeNull();
  expect(citationAudioUrl({audio_url,locator:{track:'mic'}})).toBeNull();
  expect(citationAudioUrl({audio_url:'https://external.invalid/audio'})).toBeNull();
  expect(citationAudioUrl({audio_url:'/api/v1/projects/erp/recordings/audio/audio#t=3'})).toBe('/api/v1/projects/erp/recordings/audio/audio#t=3');
});
it('affiche les repères physiques sans inventer de page et masque les chemins internes',()=>{
  expect(citationLocatorText({physical_page:7,printed_page:'B-3',ordinal:1,path:'private',profile_key:'private'})).toBe('Page physique: 7 · Page imprimée: B-3');
  expect(citationLocatorText({sheet:'Chiffrage',range:'A4:C4',block:0,note_revision:2})).toBe('Feuille: Chiffrage · Plage: A4:C4 · Bloc: 1 · Version de note: 2');
});
it('conserve les snapshots staging exacts et adapte une citation historique de séance sans changer de version',()=>{
  const source_url='/api/v1/meeting-sessions/sid/note-versions/v1';
  expect(citationSourceUrl({source_url,locator:{session_id:'sid',staged_note_version_id:'v1',note_version_id:'v1'}})).toBe(source_url);
  expect(isNoteVersionUrl(source_url)).toBe(true);
  expect(citationSourceUrl({source_url:'/api/v1/meeting-sessions/sid',locator:{staged_note_version_id:'v1',note_version_id:'v1'}})).toBe(source_url);
  expect(citationSourceUrl({source_url,locator:{session_id:'other'}})).toBeNull();
  expect(citationSourceUrl({source_url,locator:{staged_note_version_id:'v2'}})).toBeNull();
  expect(citationSourceUrl({source_url:'/api/v1/meeting-sessions/sid',locator:{staged_note_version_id:'v1',note_version_id:'v2'}})).toBeNull();
});
