import {afterEach, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, waitFor} from '@testing-library/react';
import {GlobalKnowledgeView} from './WorkspaceViews';
import {SourcesLibrary} from './SourcesLibrary';
import {workspaceApi, type WorkspaceKnowledge} from '../lib/workspaceApi';
import {fusionSources, type LibrarySource} from '../lib/fusionSources';

afterEach(() => {cleanup(); vi.restoreAllMocks(); window.history.replaceState({}, '', '/');});
const fact:WorkspaceKnowledge = {id:'fact',project_id:'brain',brain_project_id:'brain',project_code:'FICTIF',project_name:'Fictif',
  erp_projects:[],kind:'requirement',subject:'Pression maximale',value:'6 bars',status:'validated',citations:[],validation_mode:'default',
  context:{source_state:'current',needs_review:true,review_reasons:['critical_default'],
    review_messages:['Information engageante retenue par défaut : confirmer avant engagement.'],can_confirm:true}};

it('filtre les informations à réexaminer avec pagination cohérente sans déclasser de donnée', async () => {
  window.history.replaceState({}, '', '/app/knowledge?offset=25');
  const load=vi.spyOn(workspaceApi,'knowledge').mockResolvedValue({items:[fact],total:60});
  const change=vi.spyOn(workspaceApi,'changeKnowledge');
  render(<GlobalKnowledgeView rows={[]} onOpenProject={vi.fn()}/>);
  await screen.findByText('Pression maximale');
  fireEvent.click(screen.getByLabelText('À réexaminer seulement'));
  await waitFor(() => expect(load).toHaveBeenLastCalledWith(expect.objectContaining({review_only:true,offset:0}), expect.any(AbortSignal)));
  expect(change).not.toHaveBeenCalled();
  expect(screen.getByText('6 bars')).toBeTruthy();
});

it('confirme seulement après relecture explicitement acceptée et conserve le texte métier', async () => {
  vi.spyOn(workspaceApi,'knowledge').mockResolvedValue({items:[fact],total:1});
  const change=vi.spyOn(workspaceApi,'changeKnowledge').mockResolvedValue({id:'fact',status:'validated'});
  const confirm=vi.spyOn(window,'confirm').mockReturnValue(false);
  render(<GlobalKnowledgeView rows={[]} onOpenProject={vi.fn()}/>);
  fireEvent.click(await screen.findByRole('button',{name:'Confirmer après relecture'}));
  expect(change).not.toHaveBeenCalled();
  confirm.mockReturnValue(true);
  fireEvent.click(screen.getByRole('button',{name:'Confirmer après relecture'}));
  await waitFor(() => expect(change).toHaveBeenCalledWith('brain','fact','confirm'));
  expect(screen.getByText('6 bars')).toBeTruthy();
});

it('ne propose pas une confirmation simple pour une information contradictoire', async () => {
  vi.spyOn(workspaceApi,'knowledge').mockResolvedValue({items:[{...fact,context:{...fact.context!,can_confirm:false,
    review_reasons:['conflicting_values'],review_messages:['Plusieurs valeurs sont retenues pour ce sujet.']}}],total:1});
  render(<GlobalKnowledgeView rows={[]} onOpenProject={vi.fn()}/>);
  await screen.findByText('Pression maximale');
  expect(screen.queryByRole('button',{name:'Confirmer après relecture'})).toBeNull();
  expect(screen.getByRole('button',{name:'Déclasser'})).toBeTruthy();
});

it('annule une reconnaissance longue sans annoncer une extraction réussie ni perdre le lien original', async () => {
  const scan:LibrarySource={id:'scan',source_id:'scan',version_id:'v1',kind:'document',title:'Plan fictif.pdf',project_id:'brain',
    file_format:'pdf',labels:[],status:'resolved',current:true,date:'2026-10-22',extraction_status:'ocr_required',index_status:'not_indexed'};
  vi.spyOn(fusionSources,'list').mockResolvedValue({items:[scan],total:1,offset:0,limit:25,has_next:false,labels:[]});
  let reject!:(reason:Error)=>void;
  vi.spyOn(fusionSources,'ocr').mockReturnValue(new Promise((_resolve,fail)=>{reject=fail;}));
  const cancel=vi.spyOn(fusionSources,'cancelOcr').mockResolvedValue({cancel_requested:true});
  render(<SourcesLibrary rows={[]} onOpenSource={vi.fn()}/>);
  await screen.findByRole('button',{name:scan.title});
  fireEvent.click(screen.getByLabelText('Détails de '+scan.title));
  fireEvent.click(screen.getByRole('button',{name:'Reconnaître le texte du scan'}));
  fireEvent.click(await screen.findByRole('button',{name:'Annuler la reconnaissance'}));
  await waitFor(() => expect(cancel).toHaveBeenCalledWith('scan'));
  reject(new Error('Reconnaissance annulée ; original conservé'));
  await screen.findByRole('alert');
  expect(screen.getByRole('link',{name:'Ouvrir l’original : '+scan.title})).toBeTruthy();
  expect(screen.queryByText(/page\(s\) reconnue\(s\)/)).toBeNull();
});
