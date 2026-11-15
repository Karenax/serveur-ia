import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,within} from '@testing-library/react';
import {WorkspaceShell} from './WorkspaceShell';
import {fusionSources} from '../lib/fusionSources';
import {workspaceApi} from '../lib/workspaceApi';
import type {PortfolioRow} from '../lib/api';

// Exercise the real SourcesLibrary, shell state and SourceInspector together;
// unrelated modules remain outside this citation contract.
vi.mock('./WorkspaceViews',async importOriginal=>{
  const actual=await importOriginal<typeof import('./WorkspaceViews')>();
  return {...actual,GlobalMeetingsView:()=>null,GlobalJobsView:()=>null,GlobalKnowledgeView:()=>null};
});
vi.mock('./AssistantPanel',()=>({AssistantPanel:()=>null}));
vi.mock('./SettingsForms',()=>({AiSettingsForm:()=>null,MailSettingsForm:()=>null,MemorySettingsForm:()=>null}));
vi.mock('./OperationsPanel',()=>({OperationsPanel:()=>null}));
vi.mock('./ThunderbirdPanel',()=>({ThunderbirdPanel:()=>null}));
vi.mock('./ActionDashboard',()=>({ActionDashboard:()=>null}));
vi.mock('./ConnectionStatus',()=>({ConnectionStatus:()=>null}));
vi.mock('./MailActivity',()=>({MailActivity:()=>null}));
vi.mock('./MeetingStudio',()=>({MeetingStudio:()=>null,MeetingCaptureBar:()=>null}));
vi.mock('./NativeMeetingCapture',()=>({NativeCaptureBar:()=>null}));

beforeEach(()=>{
  localStorage.clear();window.history.replaceState(null,'','/app/sources');
  vi.spyOn(fusionSources,'list').mockResolvedValue({items:[],total:0,offset:0,limit:25,has_next:false,labels:[]});
});
afterEach(()=>{cleanup();vi.restoreAllMocks();});
const rows=[{id:'erp-a',brain_project_id:'brain-a',code:'A-100',title:'Projet fictif'} as PortfolioRow];
it('ouvre un mail dans le lecteur depuis un lien de citation et conserve son HTML',async()=>{
  window.history.replaceState(null,'','/app/sources?source=mail-cite');
  const load=vi.spyOn(workspaceApi,'source').mockResolvedValue({id:'mail-cite',type:'email',status:'resolved',project_id:'brain-a',author:'Recette',
    metadata:{subject:'Mail cité'},body_html:'<table><tr><td>Présentation lisible</td></tr></table>',artifacts:[]});
  render(<WorkspaceShell rows={rows} reload={async()=>undefined} ProjectPanel={()=>null} MailPanel={()=>null} CreatePanel={()=>null} SagePanel={()=>null}/>);
  const dialog=await screen.findByRole('dialog');
  await within(dialog).findByText('Mail cité');
  expect(within(dialog).getByTitle('Contenu du message').getAttribute('srcdoc')).toContain('<table>');
  expect(load).toHaveBeenCalledWith('mail-cite',expect.any(AbortSignal));
});
it.each([
  {modality:'pdf',name:'Page PDF',filename:'plan-version-2.pdf',locator:{physical_page:2,artifact_id:'page-2'},label:'Page physique : 2'},
  {modality:'text',name:'Texte',filename:'devis-version-2.xlsx',locator:{sheet:'Devis',range:'A4:C4',artifact_id:'row-4'},label:'Feuille : Devis · Plage : A4:C4'},
  {modality:'audio',name:'Audio',filename:'reunion-version-2.wav',locator:{start_ms:5000,end_ms:10000,kind:'audio'},label:'Début (ms) : 5000 · Fin (ms) : 10000'},
])('affiche la preuve $name reçue dans l’inspecteur depuis le shell',async({modality,name,filename,locator,label})=>{
  const hit={id:'hit-version-2',source_id:'source-version-2',project_id:'brain-a',modality,text:'Texte complet',excerpt:'Ne pas dépasser 12 Nm.',
    locator,score:.91,source_url:'/v1/sources/source-version-2',profile_key:'profile-qa'};
  vi.spyOn(fusionSources,'search').mockResolvedValue({items:[hit]});
  const load=vi.spyOn(workspaceApi,'source').mockResolvedValue({id:hit.source_id,type:'document',status:'resolved',project_id:hit.project_id,
    author:'Recette fictive',metadata:{filename},artifacts:[{id:'artifact-original',kind:'document_text',text:'Original conservé version 2.'},
      {id:'before-correction',kind:'transcription_snapshot',text:'Ancienne transcription conservée.'}]});
  render(<WorkspaceShell rows={rows} reload={async()=>undefined} ProjectPanel={()=>null} MailPanel={()=>null} CreatePanel={()=>null} SagePanel={()=>null}/>);
  fireEvent.change(screen.getByLabelText('Rechercher une source'),{target:{value:'couple visserie'}});
  fireEvent.click(screen.getByText(/Périmètre et filtres/));
  fireEvent.click(screen.getByRole('button',{name:'Rechercher dans le contenu des sources'}));
  fireEvent.click(await screen.findByRole('button',{name:`Consulter la source · ${name}`}));
  const dialog=await screen.findByRole('dialog');
  await within(dialog).findByText('Original conservé version 2.');
  expect(within(dialog).getByRole('heading',{name:'Transcription avant correction (historique)'})).toBeTruthy();
  const proof=within(dialog).getByRole('region',{name:'Preuve 1'});
  expect(within(proof).getByText(hit.excerpt)).toBeTruthy();
  expect(within(proof).getByText(label)).toBeTruthy();
  expect(within(proof).getByRole('link',{name:'Consulter la source citée'}).getAttribute('href')).toBe('/app/sources?source='+hit.source_id);
  expect(within(proof).queryByText(/Page imprimée|profile-qa|artifact_id/)).toBeNull();
  expect(load).toHaveBeenCalledWith(hit.source_id,expect.any(AbortSignal));
});
