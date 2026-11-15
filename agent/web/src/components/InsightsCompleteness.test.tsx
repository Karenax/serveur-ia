import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {SourcesLibrary} from './SourcesLibrary';
import {FusionInsights} from './FusionInsights';
import {fusionSources} from '../lib/fusionSources';
import {fusionInsights,type FusionStats} from '../lib/fusionInsights';

afterEach(()=>{cleanup();vi.restoreAllMocks();});

it('parcourt toutes les pages de relations et revient au début de la liste',async()=>{
  const list=vi.spyOn(fusionSources,'list').mockResolvedValue({items:[],total:0,offset:0,limit:25,has_next:false,labels:[]});
  const graph=vi.spyOn(fusionSources,'graph').mockImplementation(async(_project,_signal,offset=0)=>({
    nodes:[{id:`source-${offset}`,source_id:`source-${offset}`,label:`Source ${offset}`,kind:'source',project_id:'p'}],
    edges:[],truncated:true,offset,limit:200,total:201,has_next:offset===0,page_provenance_complete:true}));
  render(<SourcesLibrary rows={[]} onOpenSource={vi.fn()}/>);
  fireEvent.click(screen.getByRole('tab',{name:'Vue des relations'}));
  await screen.findByRole('button',{name:'Source : Source 0'});
  expect(screen.getByText('1–200 / 201 sources')).toBeTruthy();
  fireEvent.click(screen.getByRole('button',{name:'Relations suivantes'}));
  await screen.findByRole('button',{name:'Source : Source 200'});
  expect(graph).toHaveBeenLastCalledWith(undefined,expect.any(AbortSignal),200);
  expect(screen.getByRole('button',{name:'Relations suivantes'})).toHaveProperty('disabled',true);
  fireEvent.click(screen.getByRole('button',{name:'Relations précédentes'}));
  await screen.findByRole('button',{name:'Source : Source 0'});
  fireEvent.click(screen.getByRole('tab',{name:'Liste des fichiers'}));
  await waitFor(()=>expect(list).toHaveBeenLastCalledWith(expect.objectContaining({offset:0}),expect.any(AbortSignal)));
});

it('distingue la charge de transcription et l’utilité inconnue du nombre de réponses',async()=>{
  const stats:FusionStats={sources:{total:1,current:1,extracted:1,indexed:null,by_type:{document:1}},
    sessions:{total:1,by_state:{completed:1},duration_seconds:10,audio_bytes:39,chunks_by_track:{mic:2,system:1}},
    transcription:{by_status:{pending:1,running:1},pending_chunks:2,pending_audio_seconds:10,oldest_pending_seconds:120},
    assistant:{answers:5,stale:0,enhancements:0,p50_seconds:2.5,p95_seconds:2.5,tokens:null,useful_answers:null},
    engines:{speech:{ready:false},generation:{configured:true,placement:'network'}},
    index:{text_passages:null,profiles:[],size_bytes:0},formulas:{}};
  vi.spyOn(fusionInsights,'stats').mockResolvedValue(stats);
  vi.spyOn(fusionInsights,'settings').mockRejectedValue(new Error('Lecture de préparation indisponible'));
  render(<FusionInsights rows={[]}/>);
  expect(await screen.findByText('Microphone : 2 · Son système : 1')).toBeTruthy();
  expect(screen.getByText('2 fragment(s) · Le plus ancien attend depuis 120 s')).toBeTruthy();
  const useful=screen.getByRole('heading',{name:'Réponses jugées utiles'}).closest('article');
  expect(useful?.textContent).toContain('Indisponible');
  const indexed=screen.getByRole('heading',{name:'Sources indexées'}).closest('article');
  expect(indexed?.textContent).toContain('Indisponible');
  vi.mocked(fusionInsights.stats).mockResolvedValue({...stats,assistant:{...stats.assistant,
    useful_answers:1,evaluated_answers:2,unhelpful_answers:1,tokens:57,
    token_complete_answers:1,token_partial_answers:1,token_unmeasured_answers:3,token_total_answers:5}});
  fireEvent.click(screen.getByRole('button',{name:'Actualiser'}));
  await waitFor(()=>expect(screen.getByRole('heading',{name:'Réponses jugées utiles'}).closest('article')?.textContent)
    .toContain('2 réponse(s) évaluée(s), dont 1 jugée(s) pas utiles'));
  expect(screen.getByRole('heading',{name:'Réponses jugées utiles'}).closest('article')?.textContent)
    .toContain('1');
  const tokens=screen.getByRole('heading',{name:'Tokens mesurés'}).closest('article');
  expect(tokens?.textContent).toContain('57');
  expect(tokens?.textContent).toContain('1 réponse(s) avec mesure complète · 1 partielle(s) · 3 sans mesure');
});
