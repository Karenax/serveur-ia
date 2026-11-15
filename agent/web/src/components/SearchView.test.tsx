import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { SearchView } from './SearchView';
import { searchEvidence, type EvidencePage } from '../lib/searchApi';
import { api } from '../lib/api';

vi.mock('../lib/searchApi', () => ({searchEvidence: vi.fn()}));
vi.mock('../lib/api', () => ({api: {brainProjects: vi.fn()}}));
vi.mock('./WorkspaceViews', () => ({SourceInspector: ({sourceId, onClose}: {sourceId: string; onClose: () => void}) => <section aria-label="Source consultée">{sourceId}<button onClick={onClose}>Fermer la source</button></section>}));
beforeEach(() => {window.history.replaceState({},'', '/app/search');vi.mocked(api.brainProjects).mockResolvedValue([{id: 'p1', code: 'PROJET', name: 'Projet test'}]);});
afterEach(() => {cleanup(); vi.clearAllMocks();window.history.replaceState({},'', '/');});
const page: EvidencePage = {items: [{id: 's1', kind: 'source', source_id: 's1', source_type: 'email',
  project_id: 'p1', project_code: 'PROJET', title: 'Retard fournisseur', author: 'Fournisseur', date: '2026-10-11',
  excerpt: 'La livraison est décalée.', methods: ['semantic'], level: 'evidence', semantic_score: .6}],
  total: 26, offset: 0, limit: 25, has_next: true, semantic_status: 'ok', warnings: [], sources: 10, indexed_sources: 10};

function setup() {render(<SearchView rows={[]} active onOpenProject={vi.fn()} />);}
function submit(q = 'retard livraison') {
  fireEvent.change(screen.getByRole('searchbox', {name: 'Rechercher dans Agent'}), {target: {value: q}});
  fireEvent.click(screen.getByRole('button', {name: 'Rechercher'}));
}
it('affiche la progression, évite les doubles clics et ouvre la source', async () => {
  let done!: (value: EvidencePage) => void;
  vi.mocked(searchEvidence).mockImplementation(() => new Promise(resolve => {done = resolve;}));
  setup(); submit();
  expect(screen.getByRole('button', {name: 'Recherche en cours…'}).hasAttribute('disabled')).toBe(true);
  fireEvent.click(screen.getByRole('button', {name: 'Recherche en cours…'}));
  expect(searchEvidence).toHaveBeenCalledTimes(1);
  done(page);
  await screen.findByText('Retard fournisseur');
  expect(screen.getByText(/Recherche par le sens EG2 active/)).toBeTruthy();
  fireEvent.click(screen.getByRole('button', {name: 'Consulter la source'}));
  expect(screen.getByRole('region', {name: 'Source consultée'}).textContent).toContain('s1');
});
it('affiche une panne EG2 et conserve la portée recherchée lors de la pagination', async () => {
  vi.mocked(searchEvidence).mockResolvedValue({...page, semantic_status: 'unavailable', warnings: ['EG2 indisponible : mots exacts uniquement.']});
  setup();
  await screen.findByRole('option', {name: 'PROJET · Projet test'});
  fireEvent.change(screen.getByLabelText('Projet'), {target: {value: 'p1'}});
  submit('AIRB25LTH0806-A');
  await screen.findByText('EG2 indisponible : mots exacts uniquement.');
  expect(screen.getByText(/Recherche textuelle uniquement/)).toBeTruthy();
  fireEvent.change(screen.getByRole('searchbox'), {target: {value: 'nouvelle requête'}});
  expect(screen.getByText(/Les critères ont changé/)).toBeTruthy();
  fireEvent.click(screen.getByRole('button', {name: 'Suivant'}));
  await waitFor(() => expect(searchEvidence).toHaveBeenLastCalledWith(expect.objectContaining({q: 'AIRB25LTH0806-A', project_id: 'p1', offset: 25}), expect.any(AbortSignal)));
  expect(new URLSearchParams(window.location.search).get('offset')).toBe('25');
  expect(new URLSearchParams(window.location.search).get('q')).toBe('AIRB25LTH0806-A');
});
it('reprend la page et les critères exacts après rechargement',async()=>{
  window.history.replaceState({},'', '/app/search?q=capteur&project_id=p1&offset=25');
  vi.mocked(searchEvidence).mockResolvedValue({...page,offset:25});
  setup();
  await waitFor(()=>expect(searchEvidence).toHaveBeenLastCalledWith(expect.objectContaining({q:'capteur',project_id:'p1',offset:25}),expect.any(AbortSignal)));
  expect(screen.getByRole('searchbox',{name:'Rechercher dans Agent'})).toHaveProperty('value','capteur');
});
it('annule la requête et ignore sa réponse tardive', async () => {
  let done!: (value: EvidencePage) => void;
  vi.mocked(searchEvidence).mockImplementation(() => new Promise(resolve => {done = resolve;}));
  setup(); submit();
  const signal = vi.mocked(searchEvidence).mock.calls[0][1]!;
  fireEvent.click(screen.getByRole('button', {name: 'Annuler'}));
  expect(signal.aborted).toBe(true);
  done(page);
  await waitFor(() => expect(screen.queryByText('Retard fournisseur')).toBeNull());
});
it('affiche les erreurs HTTP sans inventer de résultats', async () => {
  vi.mocked(searchEvidence).mockRejectedValue(new Error('Projet introuvable'));
  setup(); submit();
  await screen.findByRole('alert');
  expect(screen.getByText('Projet introuvable')).toBeTruthy();
  expect(screen.queryByText('Retard fournisseur')).toBeNull();
});
