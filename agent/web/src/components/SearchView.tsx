import { useEffect, useRef, useState, type FormEvent } from 'react';
import {useQueryObject} from '../hooks/useQueryState';
import { api, type PortfolioRow } from '../lib/api';
import { searchEvidence, type SearchFilters, type EvidencePage } from '../lib/searchApi';
import { SourceInspector } from './SourceInspector';
import { ErrorState } from './Ui';
import '../search.css';

type Project = {id: string; code: string; name: string};
export function SearchView({rows, active, onOpenProject}: {rows: PortfolioRow[]; active: boolean; onOpenProject: (id: string, tab?: string) => void}) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [filters, setFilters] = useQueryObject<SearchFilters>({q: '', project_id: '', source_type: 'all', after: '', before: '', offset: 0}, '/app/search');
  const [page, setPage] = useState<EvidencePage | null>(null);
  const [submitted, setSubmitted] = useState<SearchFilters | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [source, setSource] = useState<{id: string; title: string} | null>(null);
  const controller = useRef<AbortController | null>(null);
  const input = useRef<HTMLInputElement>(null);
  useEffect(() => {
    const abort = new AbortController();
    api.brainProjects().then(result => {if (!abort.signal.aborted) setProjects(result);}).catch(() => {if (!abort.signal.aborted) setError('Impossible de charger les projets.');});
    return () => {abort.abort(); controller.current?.abort();};
  }, []);
  useEffect(() => {if (active) input.current?.focus(); else controller.current?.abort();}, [active]);
  async function run(next: SearchFilters) {
    controller.current?.abort();
    setFilters(next);
    const abort = new AbortController(); controller.current = abort;
    setBusy(true); setError(''); setPage(null); setSubmitted(next);
    try {const result = await searchEvidence(next, abort.signal); if (!abort.signal.aborted) setPage(result);}
    catch (e) {if (!abort.signal.aborted) setError((e as Error).message);}
    finally {if (controller.current === abort) setBusy(false);}
  }
  useEffect(() => {if (active && !submitted && filters.q.trim().length >= 2) void run(filters);}, [active]);
  function submit(event: FormEvent) {event.preventDefault(); if (!busy && filters.q.trim().length >= 2) void run({...filters, q: filters.q.trim(), offset: 0});}
  const changed = submitted && Object.entries(filters).some(([key, value]) => key !== 'offset' && value !== submitted[key as keyof SearchFilters]);
  const field = (key: keyof SearchFilters, value: string) => setFilters(previous => ({...previous, [key]: value, offset: 0}));
  return <section aria-label="Recherche dans Kiara" className="agent-search">
    <div className="workspace-page-header"><div><h1>Recherche</h1><p>Retrouvez un passage, un mail ou une connaissance avec vos mots ou une référence exacte.</p></div></div>
    <form onSubmit={submit}>
      <label className="agent-search-query">Rechercher dans Kiara<input ref={input} className="input" type="search" minLength={2} maxLength={500} required value={filters.q} onChange={e => field('q', e.target.value)} placeholder="Retard de livraison, exigence technique, référence…" /></label>
      <div className="agent-search-filters">
        <label>Projet<select className="input" value={filters.project_id} onChange={e => field('project_id', e.target.value)}><option value="">Tous les projets autorisés</option>{projects.map(p => <option key={p.id} value={p.id}>{p.code} · {p.name}</option>)}</select></label>
        <label>Type<select className="input" value={filters.source_type} onChange={e => field('source_type', e.target.value)}><option value="all">Toutes les sources et connaissances</option><option value="email">Mails</option><option value="document">Documents</option><option value="meeting">Réunions</option><option value="phone">Appels</option><option value="knowledge">Connaissances retenues</option></select></label>
        <label>Depuis le<input className="input" type="date" value={filters.after} max={filters.before || undefined} onChange={e => field('after', e.target.value)} /></label>
        <label>Jusqu’au<input className="input" type="date" value={filters.before} min={filters.after || undefined} onChange={e => field('before', e.target.value)} /></label>
      </div>
      <button className="button primary" type="submit" disabled={busy || filters.q.trim().length < 2}>{busy ? 'Recherche en cours…' : 'Rechercher'}</button>
      {busy && <button className="button secondary" type="button" onClick={() => {controller.current?.abort(); setBusy(false);}}>Annuler</button>}
    </form>
    {busy && <p role="status">Recherche des passages et des références…</p>}
    {error && <div role="alert"><ErrorState message={error} /></div>}
    {changed && page && <p role="status">Les critères ont changé. Lancez la recherche pour actualiser les résultats.</p>}
    {page && <>
      <p role="status">{page.total} résultat(s) · {page.semantic_status === 'ok' ? 'Recherche par le sens EG2 active' : page.semantic_status === 'not_needed' ? 'Recherche dans les connaissances retenues' : 'Recherche textuelle uniquement'} · {page.indexed_sources}/{page.sources} sources indexées dans ce périmètre.</p>
      {page.warnings.map(w => <p className="workspace-notice" key={w}>{w}</p>)}
      {!page.items.length && <p>Aucun résultat pour ces critères. Essayez une référence, d’autres mots ou un périmètre plus large.</p>}
      <div className="agent-search-results">{page.items.map(hit => {
        const project = rows.find(row => row.brain_project_id === hit.project_id);
        return <article key={`${hit.kind}:${hit.id}`}>
          <small>{hit.project_code} · {hit.source_type === 'knowledge' ? 'Connaissance' : hit.source_type === 'email' ? 'Mail' : hit.source_type === 'document' ? 'Document' : 'Réunion / appel'} · {new Date(hit.date).toLocaleDateString('fr-FR')}{hit.author ? ` · ${hit.author}` : ''}</small>
          <h2>{hit.title}</h2><p className="agent-search-excerpt">{hit.excerpt}</p>
          <div className="agent-search-tags">{hit.methods.map(method => <span key={method}>{method === 'exact' ? 'Référence / expression exacte' : method === 'semantic' ? 'Sens proche' : method === 'project' ? 'Code du projet de classement' : 'Mots retrouvés'}</span>)}<span>{hit.level === 'evidence' ? 'Source à interpréter' : hit.level === 'default' ? 'Information retenue par défaut' : 'Connaissance validée'}</span></div>
          <div className="agent-search-actions">{hit.source_id && <button type="button" className="button secondary" onClick={() => setSource({id: hit.source_id!, title: hit.title})}>Consulter la source</button>}{project && <button type="button" className="workspace-text-button" onClick={() => onOpenProject(project.id, 'connaissance')}>Ouvrir le projet</button>}</div>
        </article>;
      })}</div>
      {page.total > page.limit && <nav aria-label="Pages des résultats" className="agent-search-actions"><button type="button" className="button secondary" disabled={busy || page.offset === 0} onClick={() => submitted && void run({...submitted, offset: Math.max(0, page.offset - page.limit)})}>Précédent</button><span>{page.offset + 1}–{page.offset + page.items.length} sur {page.total}</span><button type="button" className="button secondary" disabled={busy || !page.has_next} onClick={() => submitted && void run({...submitted, offset: page.offset + page.limit})}>Suivant</button></nav>}
    </>}
    {source && <SourceInspector sourceId={source.id} title={source.title} onClose={() => setSource(null)} />}
  </section>;
}
