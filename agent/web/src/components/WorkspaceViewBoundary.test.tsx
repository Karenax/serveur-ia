import {Suspense} from 'react';
import {cleanup, fireEvent, render, screen} from '@testing-library/react';
import {afterEach, expect, it, vi} from 'vitest';
import {retryableLazy} from '../lib/retryableLazy';
import {WorkspaceViewBoundary} from './WorkspaceViewBoundary';

afterEach(() => {cleanup(); vi.restoreAllMocks();});

it('relance un chargement échoué sans remonter un autre brouillon', async () => {
  vi.spyOn(console, 'error').mockImplementation(() => {});
  const load = vi.fn().mockRejectedValue(new Error('Connexion interrompue'));
  const retry = vi.fn().mockResolvedValue({default: () => <p>Rubrique disponible</p>});
  const Deferred = retryableLazy(load, retry);
  render(<>
    <WorkspaceViewBoundary><Suspense fallback={<p>Chargement…</p>}><Deferred /></Suspense></WorkspaceViewBoundary>
    <WorkspaceViewBoundary><label>Brouillon voisin<input defaultValue="Texte conservé" /></label></WorkspaceViewBoundary>
  </>);
  expect(await screen.findByText(/Le chargement de cette rubrique a échoué/)).toBeTruthy();
  fireEvent.change(screen.getByLabelText('Brouillon voisin'), {target:{value:'Saisie à conserver'}});
  fireEvent.click(screen.getByRole('button', {name:'Réessayer'}));
  expect(await screen.findByText('Rubrique disponible')).toBeTruthy();
  expect(load).toHaveBeenCalledTimes(1);expect(retry).toHaveBeenCalledTimes(1);
  expect((screen.getByLabelText('Brouillon voisin') as HTMLInputElement).value).toBe('Saisie à conserver');
});

it('ne prétend pas relancer une feuille de style échouée et prévient avant un rechargement', async () => {
  vi.spyOn(console, 'error').mockImplementation(() => {});
  const load = vi.fn().mockRejectedValue(new Error('Unable to preload CSS for /assets/mail.css'));
  const Deferred = retryableLazy(load, load);
  render(<WorkspaceViewBoundary><Suspense fallback={<p>Chargement…</p>}><Deferred /></Suspense></WorkspaceViewBoundary>);
  expect(await screen.findByText(/enregistrez vos autres brouillons avant de recharger Kiara/)).toBeTruthy();
  expect(screen.queryByRole('button', {name:'Réessayer'})).toBeNull();
  expect(load).toHaveBeenCalledTimes(1);
});

it('invite à préserver les brouillons si la seconde adresse échoue aussi', async () => {
  vi.spyOn(console, 'error').mockImplementation(() => {});
  const load = vi.fn().mockRejectedValue(new Error('Réseau indisponible'));
  const retry = vi.fn().mockRejectedValue(new Error('Toujours indisponible'));
  const Deferred = retryableLazy(load, retry);
  render(<WorkspaceViewBoundary><Suspense fallback={<p>Chargement…</p>}><Deferred /></Suspense></WorkspaceViewBoundary>);
  expect(await screen.findByRole('button', {name:'Réessayer'})).toBeTruthy();
  fireEvent.click(screen.getByRole('button', {name:'Réessayer'}));
  expect(await screen.findByText(/enregistrez vos autres brouillons avant de recharger Kiara/)).toBeTruthy();
  expect(screen.queryByRole('button', {name:'Réessayer'})).toBeNull();
  expect(load).toHaveBeenCalledTimes(1);expect(retry).toHaveBeenCalledTimes(1);
});

it('garde le formulaire parent monté quand un panneau interne ne se charge pas', async () => {
  vi.spyOn(console, 'error').mockImplementation(() => {});
  const load = vi.fn().mockRejectedValue(new Error('Connexion interrompue'));
  const retry = vi.fn().mockResolvedValue({default: () => <p>Panneau retrouvé</p>});
  const Deferred = retryableLazy(load, retry), leave = vi.fn();
  render(<WorkspaceViewBoundary>
    <label>Correction de la fiche<input defaultValue="À conserver" /></label>
    <WorkspaceViewBoundary onLeave={leave} leaveLabel="Retour aux réunions">
      <Suspense fallback={<p>Chargement…</p>}><Deferred /></Suspense>
    </WorkspaceViewBoundary>
  </WorkspaceViewBoundary>);
  expect(await screen.findByRole('button', {name:'Retour aux réunions'})).toBeTruthy();
  fireEvent.change(screen.getByLabelText('Correction de la fiche'), {target:{value:'Texte non enregistré'}});
  fireEvent.click(screen.getByRole('button', {name:'Réessayer'}));
  expect(await screen.findByText('Panneau retrouvé')).toBeTruthy();
  expect((screen.getByLabelText('Correction de la fiche') as HTMLInputElement).value).toBe('Texte non enregistré');
  expect(leave).not.toHaveBeenCalled();
});
