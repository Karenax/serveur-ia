import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { DocumentSettings } from './DocumentSettings';
import { documentApi, type DocumentId, type DocumentPreferences } from '../lib/projectDocuments';

const ids:DocumentId[]=['offer_lt_simple','tdao','tdsp','manufacturing_specification','user_manual','ce_request','customer_satisfaction_product','customer_satisfaction_fixed_price'];
const state:DocumentPreferences={available:true,revision:2,version_id:'s2',items:ids.map((id,index)=>({document_id:id,label:`Trame ${index+1}`,format:'DOCX',
  relative_paths:['.'],filename_patterns:['Trame'],excluded_tokens:[],preferred_version:null,active:true,order:index}))};
beforeEach(()=>{vi.spyOn(documentApi,'preferences').mockResolvedValue(structuredClone(state));
  vi.spyOn(documentApi,'savePreferences').mockImplementation(async(_revision,items)=>({...state,revision:3,items}));
  vi.spyOn(documentApi,'restorePreferences').mockResolvedValue({...state,revision:3});
  vi.spyOn(documentApi,'preferencesHistory').mockResolvedValue({items:[{id:'s1',revision:1,created_at:'2026-10-07T00:00:00+00:00',sha256:'a'.repeat(64),value:{actor_id:'local',items:state.items}}],total:1,offset:0,limit:20});});
afterEach(()=>{cleanup();vi.restoreAllMocks();});
async function ready(){await screen.findByLabelText('Modifier les recherches des trames');await waitFor(()=>expect((screen.getAllByLabelText('Libellé')[0] as HTMLInputElement).disabled).toBe(false));}

it('enregistre les huit règles explicitement avec des listes normalisées et une révision',async()=>{
  render(<DocumentSettings active onBusy={vi.fn()}/>);await ready();expect(screen.getAllByLabelText('Libellé')).toHaveLength(8);
  fireEvent.change(screen.getAllByLabelText('Libellé')[0],{target:{value:'Ma trame'}});
  fireEvent.change(screen.getAllByLabelText('Dossiers relatifs')[0],{target:{value:'Etudes\n\nTrames\n'}});
  expect(documentApi.savePreferences).not.toHaveBeenCalled();fireEvent.click(screen.getByRole('button',{name:'Enregistrer les réglages'}));await screen.findByText('Réglages enregistrés · version 3.');
  expect(vi.mocked(documentApi.savePreferences).mock.calls[0][0]).toBe(2);
  expect(vi.mocked(documentApi.savePreferences).mock.calls[0][1][0].relative_paths).toEqual(['Etudes','Trames']);
  expect(document.querySelector('[data-workspace-dirty="true"]')).toBeNull();
});

it('préserve les réglages sur conflit et exige un chargement explicite du serveur',async()=>{
  vi.mocked(documentApi.savePreferences).mockRejectedValue(new Error('Révision modifiée'));
  vi.mocked(documentApi.preferences).mockResolvedValueOnce(state).mockResolvedValue({...state,revision:4,items:state.items.map(item=>({...item,label:'Serveur'}))});
  render(<DocumentSettings active onBusy={vi.fn()}/>);await ready();fireEvent.change(screen.getAllByLabelText('Libellé')[0],{target:{value:'Local'}});
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer les réglages'}));await screen.findByRole('alert');expect((screen.getAllByLabelText('Libellé')[0] as HTMLInputElement).value).toBe('Local');
  fireEvent.click(screen.getByRole('button',{name:'Comparer avec les réglages enregistrés'}));await screen.findByRole('region',{name:'Réglages enregistrés à comparer'});
  expect((screen.getAllByLabelText('Libellé')[0] as HTMLInputElement).value).toBe('Local');fireEvent.click(screen.getByRole('button',{name:'Charger cette version et remplacer mes réglages'}));
  expect((screen.getAllByLabelText('Libellé')[0] as HTMLInputElement).value).toBe('Serveur');expect(document.querySelector('[data-workspace-dirty="true"]')).toBeNull();
});

it('conserve le brouillon après changement de vue et restaure une révision explicitement',async()=>{
  const view=render(<DocumentSettings active onBusy={vi.fn()}/>);await ready();fireEvent.change(screen.getAllByLabelText('Libellé')[0],{target:{value:'Local'}});
  view.rerender(<DocumentSettings active={false} onBusy={vi.fn()}/>);view.rerender(<DocumentSettings active onBusy={vi.fn()}/>);
  expect((screen.getAllByLabelText('Libellé')[0] as HTMLInputElement).value).toBe('Local');expect(documentApi.preferences).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole('button',{name:'Historique des réglages'}));await screen.findByText('Version 1');
  vi.spyOn(window,'confirm').mockReturnValueOnce(false).mockReturnValueOnce(true);
  fireEvent.click(screen.getByRole('button',{name:'Restaurer la version 1'}));expect(documentApi.restorePreferences).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button',{name:'Restaurer la version 1'}));await screen.findByText('Réglages enregistrés · version 3.');
  expect(documentApi.restorePreferences).toHaveBeenCalledWith(2,'s1',expect.any(AbortSignal));
});

it('explique les droits insuffisants et ne montre pas un formulaire administrable',async()=>{
  vi.mocked(documentApi.preferences).mockRejectedValue(new Error('Administration réservée au propriétaire'));
  render(<DocumentSettings active onBusy={vi.fn()}/>);expect(await screen.findByRole('alert')).toHaveProperty('textContent','Administration réservée au propriétaire');
  expect(screen.queryByRole('button',{name:'Enregistrer les réglages'})).toBeNull();
});
