import { afterEach, expect, it, vi } from 'vitest';
import { act, cleanup, render, screen } from '@testing-library/react';
import { request } from '../lib/http';
import { ProjectIndexing } from './ProjectIndexing';

vi.mock('../lib/http',()=>({request:vi.fn()}));
const originalHidden=Object.getOwnPropertyDescriptor(document,'hidden');
afterEach(()=>{cleanup();vi.useRealTimers();vi.resetAllMocks();if(originalHidden)Object.defineProperty(document,'hidden',originalHidden);else Reflect.deleteProperty(document,'hidden');});

it('interrompt le suivi masqué, reprend au retour et ignore une réponse devenue ancienne',async()=>{
  vi.useFakeTimers();Object.defineProperty(document,'hidden',{configurable:true,value:true});
  let finishOld!:(value:unknown)=>void;
  const value={engine:'eg2',model:'fictif',server:'fictif',compute:'network',automatic:true,sources:2,indexed:2,passages:3,error:null,projects:[]};
  vi.mocked(request).mockReturnValueOnce(new Promise(resolve=>{finishOld=resolve;})).mockResolvedValue(value);
  render(<ProjectIndexing active projectId="p1"/>);await act(async()=>{});
  expect(request).not.toHaveBeenCalled();
  Object.defineProperty(document,'hidden',{configurable:true,value:false});await act(async()=>{document.dispatchEvent(new Event('visibilitychange'));});
  expect(request).toHaveBeenCalledTimes(1);const first=vi.mocked(request).mock.calls[0][1]!.signal as AbortSignal;
  Object.defineProperty(document,'hidden',{configurable:true,value:true});await act(async()=>{document.dispatchEvent(new Event('visibilitychange'));});
  expect(first.aborted).toBe(true);
  await act(async()=>{await vi.advanceTimersByTimeAsync(45000);});expect(request).toHaveBeenCalledTimes(1);
  Object.defineProperty(document,'hidden',{configurable:true,value:false});await act(async()=>{document.dispatchEvent(new Event('visibilitychange'));});
  expect(request).toHaveBeenCalledTimes(2);expect(screen.getByText(/2 \/ 2 sources indexées/)).toBeTruthy();
  await act(async()=>{finishOld({...value,indexed:0});});expect(screen.getByText(/2 \/ 2 sources indexées/)).toBeTruthy();
});

it('conserve le dernier état en quittant Sources puis le réactualise au retour',async()=>{
  vi.useFakeTimers();
  const value={engine:'eg2',model:'fictif',server:'fictif',compute:'network',automatic:true,sources:2,indexed:2,passages:3,error:null,projects:[]};
  vi.mocked(request).mockResolvedValue(value);
  const view=render(<ProjectIndexing active projectId="p1"/>);await act(async()=>{});
  expect(screen.getByText(/2 \/ 2 sources indexées/)).toBeTruthy();
  view.rerender(<ProjectIndexing active={false} projectId="p1"/>);
  await act(async()=>{await vi.advanceTimersByTimeAsync(45000);});expect(request).toHaveBeenCalledTimes(1);
  expect(screen.getByText(/2 \/ 2 sources indexées/)).toBeTruthy();
  view.rerender(<ProjectIndexing active projectId="p1"/>);await act(async()=>{});
  expect(request).toHaveBeenCalledTimes(2);expect(screen.getByText(/2 \/ 2 sources indexées/)).toBeTruthy();
});
