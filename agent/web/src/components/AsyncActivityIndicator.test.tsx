import { act, cleanup, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { AsyncActivityIndicator } from './AsyncActivityIndicator';
import { beginActivity } from '../lib/asyncActivity';

let finish: (() => void) | undefined;
afterEach(() => { act(() => { finish?.(); }); finish = undefined; cleanup(); vi.useRealTimers(); });

it('annonce uniquement un travail prolongé et se retire après la fin sans bloquer les contrôles', () => {
  vi.useFakeTimers();
  render(<><button>Une autre action</button><AsyncActivityIndicator /></>);
  expect(screen.getByRole('status').textContent).toBe('');
  act(() => { finish = beginActivity('Ajout du CDC au projet'); });
  expect(screen.getByRole('status').textContent).toBe('');
  act(()=>{vi.advanceTimersByTime(1999);});
  expect(screen.getByRole('status').textContent).toBe('');
  act(()=>{vi.advanceTimersByTime(1);});
  expect(screen.getByRole('status').textContent).toContain('Ajout du CDC au projet');
  expect((screen.getByRole('button') as HTMLButtonElement).disabled).toBe(false);
  act(() => { finish?.(); });
  expect(screen.getByRole('status').textContent).toBe('');
});

it('ne fait pas clignoter le popup pour une opération rapide',()=>{
  vi.useFakeTimers();render(<AsyncActivityIndicator/>);
  act(()=>{finish=beginActivity('Préparation du document');});
  act(()=>{vi.advanceTimersByTime(1000);finish?.();});
  act(()=>{vi.advanceTimersByTime(3000);});
  expect(screen.getByRole('status').textContent).toBe('');
  expect(vi.getTimerCount()).toBe(0);
});
