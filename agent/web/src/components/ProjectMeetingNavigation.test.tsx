import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {cleanup,render,screen} from '@testing-library/react';
import {ProjectWindow} from '../App';
import {api,type Meeting,type PortfolioRow,type ProjectDetail} from '../lib/api';

vi.mock('./ProjectFolder',()=>({ProjectFolder:()=>null}));
vi.mock('./MeetingAudioPanel',()=>({MeetingAudioPanel:()=>null}));
vi.mock('./ProjectReviewsPanel',()=>({ProjectReviewsPanel:()=> <section aria-label="Revue de lancement héritée"/>}));
const row={id:'p1',code:'QA-01',title:'Projet de recette',status:'active',client_name:'Fictif'} as PortfolioRow;
const detail={id:'p1',tasks:[],milestones:[],deliverables:[],planning_revision:1} as unknown as ProjectDetail;
const meetings:Meeting[]=[
  {id:'old-report',date:'2026-10-10',title:'Ancien compte rendu',participants:'',decisions:'Ancienne synthèse fermée',actions:[],open_actions:0},
  {id:'published-report',date:'2026-10-11',title:'Compte rendu publié',participants:'Paul',decisions:'Synthèse exacte du compte rendu ciblé',
    actions:[{id:'action',title:'Vérifier le matériel',owner:'Paul',due_date:'2026-10-16',task_id:null}],open_actions:1},
];
const props={projectId:'p1',row,initialTab:'reviews' as const,reloadRows:vi.fn(async()=>{}),back:vi.fn()};
beforeEach(()=>{
  window.history.replaceState(null,'','/app/projects/p1/reviews');
  vi.spyOn(api,'detail').mockResolvedValue(detail);vi.spyOn(api,'cdcItems').mockResolvedValue([]);
  vi.spyOn(api,'cdcSources').mockResolvedValue([]);vi.spyOn(api,'meetings').mockResolvedValue(meetings);
  vi.spyOn(api,'cdcJobs').mockResolvedValue([]);vi.spyOn(api,'aiStatus').mockResolvedValue({reachable:false,detail:'Test'});
});
afterEach(()=>{cleanup();vi.restoreAllMocks();window.history.replaceState(null,'','/app/');});

it('ouvre directement la réunion publiée et ses actions en conservant la cible URL',async()=>{
  window.history.replaceState(null,'','/app/projects/p1/reviews?meeting=published-report');
  render(<ProjectWindow {...props}/>);
  await screen.findByText('Synthèse exacte du compte rendu ciblé');
  expect(screen.getByRole('tab',{name:'Comptes rendus et audio'}).getAttribute('aria-selected')).toBe('true');
  expect(screen.getByRole('tab',{name:'Revue de lancement'}).getAttribute('aria-selected')).toBe('false');
  expect(screen.getByText('Vérifier le matériel')).toBeTruthy();expect(screen.getByText('2026-10-16')).toBeTruthy();
  expect(screen.queryByText('Ancienne synthèse fermée')).toBeNull();
  expect(window.location.search).toBe('?meeting=published-report');
  expect(api.meetings).toHaveBeenCalledWith('p1');
});

it('expose le même Studio depuis le projet sans modifier la revue héritée',async()=>{
  render(<ProjectWindow {...props}/>);
  const link=await screen.findByRole('link',{name:'Ouvrir les séances du projet'});
  expect(link.getAttribute('href')).toBe('/app/meetings?project=p1');
  expect(screen.getByRole('tab',{name:'Revue de lancement'}).getAttribute('aria-selected')).toBe('true');
  expect(screen.getByLabelText('Revue de lancement héritée')).toBeTruthy();
});

it.each(['','?meeting=missing-report','?meeting=other-project-report'])('conserve la revue de lancement sans cible présente dans le projet : %s',async query=>{
  window.history.replaceState(null,'','/app/projects/p1/reviews'+query);
  render(<ProjectWindow {...props}/>);
  expect((await screen.findByRole('tab',{name:'Revue de lancement'})).getAttribute('aria-selected')).toBe('true');
  expect(screen.getByRole('tab',{name:'Comptes rendus et audio'}).getAttribute('aria-selected')).toBe('false');
  expect(screen.queryByText('Synthèse exacte du compte rendu ciblé')).toBeNull();
  expect(api.meetings).toHaveBeenCalledWith('p1');
  expect(api.meetings).not.toHaveBeenCalledWith('other-project');
});

it('ignore la cible d’une URL appartenant à un autre projet même si son ID ressemble à une réunion présente',async()=>{
  window.history.replaceState(null,'','/app/projects/other-project/reviews?meeting=published-report');
  render(<ProjectWindow {...props}/>);
  expect((await screen.findByRole('tab',{name:'Revue de lancement'})).getAttribute('aria-selected')).toBe('true');
  expect(screen.queryByText('Synthèse exacte du compte rendu ciblé')).toBeNull();
  expect(api.meetings).toHaveBeenCalledWith('p1');
});
