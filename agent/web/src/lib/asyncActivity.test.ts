import { afterEach, describe, expect, it, vi } from 'vitest';
import { automaticRequestActivity, beginActivity, getActivitySnapshot, requestActivityLabel, subscribeActivity, withActivity } from './asyncActivity';

const finishes: Array<() => void> = [];
afterEach(() => { finishes.splice(0).forEach(finish => finish()); vi.useRealTimers(); });

describe('Travail en cours', () => {
  it('réserve le suivi automatique aux traitements longs explicitement reconnus',()=>{
    for(const path of ['/api/v1/portfolio','/v1/status','/api/v1/projects/x/cdc/sources','/v1/search?q=analyse','/v1/settings'])
      expect(automaticRequestActivity(path,'GET')).toBe(false);
    expect(automaticRequestActivity('/v1/settings/ai','PUT')).toBe(false);
    expect(automaticRequestActivity('/api/v1/projects','POST')).toBe(false);
    expect(automaticRequestActivity('/api/v1/projects/x/cdc/analyze','POST')).toBe('Mise à jour du CDC…');
    expect(automaticRequestActivity('/api/v1/projects/x/import','POST')).toBe('Import en cours…');
    expect(automaticRequestActivity('/v1/sources/x/ocr','POST')).not.toBe(false);
  });
  it('reste visible jusqu’à la dernière opération concurrente et supporte une clôture répétée', () => {
    const first = beginActivity('Ajout du CDC');
    const second = beginActivity('Recherche en cours');
    finishes.push(first, second);
    expect(getActivitySnapshot()?.labels).toEqual(['Ajout du CDC', 'Recherche en cours']);
    first(); first();
    expect(getActivitySnapshot()?.label).toBe('Recherche en cours');
    second();
    expect(getActivitySnapshot()).toBeNull();
  });

  it('masque les lectures rapides et retire leur délai sans notification', async () => {
    vi.useFakeTimers();
    const listener = vi.fn();
    const unsubscribe = subscribeActivity(listener);
    const finish = beginActivity('Chargement', { delayMs: 800 });
    finishes.push(finish, unsubscribe);
    await vi.advanceTimersByTimeAsync(799);
    expect(getActivitySnapshot()).toBeNull();
    finish();
    await vi.advanceTimersByTimeAsync(1000);
    expect(getActivitySnapshot()).toBeNull();
    expect(listener).not.toHaveBeenCalled();
    expect(vi.getTimerCount()).toBe(0);
  });

  it('signale une lecture lente après le délai et ne répète pas le même libellé', async () => {
    vi.useFakeTimers();
    const one = beginActivity('Chargement des documents…', { delayMs: 800 });
    const two = beginActivity('Chargement des documents…', { delayMs: 800 });
    finishes.push(one, two);
    await vi.advanceTimersByTimeAsync(800);
    expect(getActivitySnapshot()?.labels).toEqual(['Chargement des documents…']);
    one();
    expect(getActivitySnapshot()?.label).toBe('Chargement des documents…');
    two();
    expect(getActivitySnapshot()).toBeNull();
  });

  it('englobe toutes les étapes, sans disparition entre import et actualisation', async () => {
    let next!: () => void;
    const delayed = new Promise<void>(resolve => { next = resolve; });
    const pending = withActivity('Import et actualisation', async () => { await delayed; return 42; });
    expect(getActivitySnapshot()?.label).toBe('Import et actualisation');
    next();
    await expect(pending).resolves.toBe(42);
    expect(getActivitySnapshot()).toBeNull();
  });

  it('termine aussi après erreur sans changer cette erreur', async () => {
    const failure = new Error('Import refusé');
    await expect(withActivity('Import', async () => { throw failure; })).rejects.toBe(failure);
    expect(getActivitySnapshot()).toBeNull();
  });

  it('ne révèle ni paramètres ni identifiants dans le message commun', () => {
    expect(requestActivityLabel('/api/v1/projects/private-id/cdc/sources/upload?filename=secret.pdf', 'POST')).toBe('Mise à jour du CDC…');
    expect(requestActivityLabel('/v1/search?q=donnee-confidentielle')).toBe('Recherche en cours…');
  });
});
