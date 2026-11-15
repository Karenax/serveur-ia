import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { ProjectKnowledgePanel } from './ProjectKnowledgePanel';
import { projectKnowledgeApi, type KnowledgeAnalysis } from '../lib/projectKnowledge';

const result:KnowledgeAnalysis={enabled:true,status:'waiting_idle',error:null,cursor:2,total_batches:10,next_due:null,retry_after:null,interval_hours:48,stale:false,
  activity:{active_calls:1,waiting_calls:0,background_active:false},report:{},items:[],total:0,offset:0,limit:20};
beforeEach(()=>vi.spyOn(projectKnowledgeApi,'read').mockResolvedValue(result));
afterEach(()=>{cleanup();vi.restoreAllMocks();});

it('affiche immédiatement l’attente du modèle et la progression',async()=>{
  render(<ProjectKnowledgePanel projectId="p1"/>);
  expect(await screen.findByText('En attente de disponibilité du modèle',{selector:'summary span'})).toBeTruthy();
  expect(screen.getByText('Informations à vérifier').closest('details')?.open).toBe(false);
  fireEvent.click(screen.getByText('Informations à vérifier'));
  expect(screen.getByText(/2\/10 lots traités/)).toBeTruthy();
  expect(screen.getByText(/toutes les 48 h/)).toBeTruthy();
});

it('distingue le bilan périmé, les propositions et les preuves accessibles',async()=>{
  vi.mocked(projectKnowledgeApi.read).mockResolvedValue({...result,status:'completed',stale:true,total:21,report:{completed_at:'2026-10-10T12:00:00Z',knowledge_count:45,counts:{satisfied:1,unknown:20}},
    items:[{id:'c1',human_id:'FC-01',kind:'constraint',title:'Tenue thermique',state:'satisfied',reason:'PV thermique disponible',proofs:[{knowledge_id:'k1',quote:'Essai conforme à 50 °C.',sources:['s1']}]}]});
  render(<ProjectKnowledgePanel projectId="p1"/>);
  fireEvent.click(screen.getByText('Informations à vérifier'));
  expect(await screen.findByText(/Une nouvelle analyse est nécessaire/)).toBeTruthy();
  expect(screen.getByText(/Ces évaluations IA sont à confirmer/)).toBeTruthy();
  expect(screen.getByText('Essai conforme à 50 °C.')).toBeTruthy();
  fireEvent.click(screen.getByRole('button',{name:'Suivant'}));
  await waitFor(()=>expect(projectKnowledgeApi.read).toHaveBeenLastCalledWith('p1',20,expect.any(AbortSignal)));
});

it('n’interroge pas un panneau inactif et annule ses lectures au changement de projet',async()=>{
  const view=render(<ProjectKnowledgePanel projectId="p1" active={false}/>);
  expect(projectKnowledgeApi.read).not.toHaveBeenCalled();
  view.rerender(<ProjectKnowledgePanel projectId="p1" active/>);
  await waitFor(()=>expect(projectKnowledgeApi.read).toHaveBeenCalledTimes(1));
  const signal=vi.mocked(projectKnowledgeApi.read).mock.calls[0][2]!;
  view.rerender(<ProjectKnowledgePanel projectId="p2" active/>);
  await waitFor(()=>expect(projectKnowledgeApi.read).toHaveBeenLastCalledWith('p2',0,expect.any(AbortSignal)));
  expect(signal.aborted).toBe(true);
});
