import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { act, cleanup, renderHook } from "@testing-library/react";
import { workspaceApi, type DurableTriageJob } from "../lib/workspaceApi";
import { useDurableMailTriage } from "./useDurableMailTriage";

beforeEach(() => vi.useFakeTimers());
afterEach(() => {cleanup(); vi.useRealTimers(); vi.restoreAllMocks();});
const job: DurableTriageJob = {id: "j1", status: "running", force: false, processed: 8, total: 12, progress: 66.7,
  cancel_requested: false, result: {triaged: 7, divers: 2, errors: [{source_id: "s8", error: "Échec"}]},
  error: null, can_cancel: true, can_retry: false, created_at: "2026-10-02", updated_at: "2026-10-02"};
const options = () => ({onProgress: vi.fn(), onRunning: vi.fn(), onMessage: vi.fn(), onSettled: vi.fn()});
const flush = async () => {await act(async () => {await Promise.resolve();});};
const tick = async () => {await act(async () => {await vi.advanceTimersByTimeAsync(2000);});};

it("ne consulte pas les traitements pour un accès en lecture seule", async () => {
  const latest = vi.spyOn(workspaceApi, 'latestTriage').mockResolvedValue({job:null});
  const callbacks = options();
  const hook = renderHook(({enabled}) => useDurableMailTriage({...callbacks,enabled}), {initialProps:{enabled:false}});
  await tick();
  expect(latest).not.toHaveBeenCalled();
  hook.rerender({enabled:true});
  await flush();
  expect(latest).toHaveBeenCalledTimes(1);
  hook.rerender({enabled:false});
  await tick();
  expect(latest).toHaveBeenCalledTimes(1);
});

it("restaure le compteur du travail serveur après chargement de la page", async () => {
  vi.spyOn(workspaceApi, "latestTriage").mockResolvedValue({job});
  const start = vi.spyOn(workspaceApi, "startTriage");
  const callbacks = options();
  renderHook(() => useDurableMailTriage(callbacks));
  await flush();
  expect(callbacks.onProgress).toHaveBeenLastCalledWith({processed: 8, total: 12, classified: 7, divers: 2, errors: 1, status: "running"});
  expect(callbacks.onRunning).toHaveBeenLastCalledWith(true);
  expect(start).not.toHaveBeenCalled();
  expect(callbacks.onSettled).not.toHaveBeenCalled();
});

it("lance un travail durable et ne l'annule pas à la fermeture du navigateur", async () => {
  vi.spyOn(workspaceApi, "latestTriage").mockResolvedValue({job: null});
  const start = vi.spyOn(workspaceApi, "startTriage").mockResolvedValue({...job, status: "queued", processed: 0, result: {}});
  const cancel = vi.spyOn(workspaceApi, "cancelTriage");
  const callbacks = options();
  const hook = renderHook(() => useDurableMailTriage(callbacks));
  await flush();
  await act(async () => {await hook.result.current.start(true);});
  expect(start).toHaveBeenCalledWith(true);
  expect(callbacks.onProgress).toHaveBeenLastCalledWith(expect.objectContaining({processed: 0, total: 12, status: "running"}));
  expect(callbacks.onMessage).toHaveBeenLastCalledWith("Analyse en attente : 0 / 12 mails traités.");
  hook.unmount();
  expect(cancel).not.toHaveBeenCalled();
});

it("attend la confirmation serveur d'annulation et conserve les compteurs acquis", async () => {
  vi.spyOn(workspaceApi, "latestTriage").mockResolvedValue({job});
  const cancel = vi.spyOn(workspaceApi, "cancelTriage").mockResolvedValue({...job, cancel_requested: true, can_cancel: false});
  const details = vi.spyOn(workspaceApi, "triageJob").mockResolvedValue({...job, status: "cancelled", processed: 10, cancel_requested: true});
  const callbacks = options();
  const hook = renderHook(() => useDurableMailTriage(callbacks));
  await flush();
  await act(async () => {await hook.result.current.cancel();});
  expect(cancel).toHaveBeenCalledWith("j1");
  expect(callbacks.onRunning).toHaveBeenLastCalledWith(true);
  expect(callbacks.onMessage).toHaveBeenLastCalledWith(expect.stringContaining("Annulation demandée : 8 / 12"));
  await tick();
  expect(details).toHaveBeenCalledWith("j1", expect.any(AbortSignal), true);
  expect(callbacks.onProgress).toHaveBeenLastCalledWith(expect.objectContaining({processed: 10, total: 12, status: "interrupted"}));
  expect(callbacks.onRunning).toHaveBeenLastCalledWith(false);
  expect(callbacks.onSettled).toHaveBeenCalledTimes(1);
});

it("ignore un ancien résultat de polling après une commande d'annulation", async () => {
  vi.spyOn(workspaceApi, "latestTriage").mockResolvedValue({job});
  let oldResponse: (value: DurableTriageJob) => void = () => {};
  vi.spyOn(workspaceApi, "triageJob").mockImplementation(() => new Promise(resolve => {oldResponse = resolve;}));
  vi.spyOn(workspaceApi, "cancelTriage").mockResolvedValue({...job, cancel_requested: true, can_cancel: false});
  const callbacks = options();
  const hook = renderHook(() => useDurableMailTriage(callbacks));
  await flush();
  await tick();
  await act(async () => {await hook.result.current.cancel();});
  await act(async () => {oldResponse({...job, processed: 9});});
  expect(callbacks.onProgress).toHaveBeenLastCalledWith(expect.objectContaining({processed: 8, total: 12}));
  expect(callbacks.onMessage).toHaveBeenLastCalledWith(expect.stringContaining("Annulation demandée"));
});

it("conserve le compteur lors d'une coupure de suivi et restaure le message après reconnexion", async () => {
  vi.spyOn(workspaceApi, "latestTriage").mockResolvedValue({job});
  vi.spyOn(workspaceApi, "triageJob").mockRejectedValueOnce(new Error("Connexion coupée")).mockResolvedValue(job);
  const callbacks = options();
  renderHook(() => useDurableMailTriage(callbacks));
  await flush();
  await tick();
  expect(callbacks.onMessage).toHaveBeenLastCalledWith(expect.stringContaining("Suivi de l’analyse indisponible"));
  expect(callbacks.onProgress).toHaveBeenLastCalledWith(expect.objectContaining({processed: 8, total: 12}));
  expect(callbacks.onRunning).toHaveBeenLastCalledWith(true);
  await tick();
  expect(callbacks.onMessage).toHaveBeenLastCalledWith(expect.stringContaining("Analyse en cours : 8 / 12"));
});

it("restaure une analyse terminée sans écraser ensuite les messages de classement manuel", async () => {
  vi.spyOn(workspaceApi, "latestTriage").mockResolvedValue({job: {...job, status: "completed", processed: 12}});
  const callbacks = options();
  renderHook(() => useDurableMailTriage(callbacks));
  await flush();
  expect(callbacks.onMessage).toHaveBeenLastCalledWith(expect.stringContaining("Analyse terminée : 12 / 12"));
  const calls = callbacks.onMessage.mock.calls.length;
  await tick();
  expect(callbacks.onMessage.mock.calls.length).toBe(calls);
  expect(callbacks.onSettled).not.toHaveBeenCalled();
});

it("utilise le callback courant à la fin du traitement après un changement de recherche", async () => {
  vi.spyOn(workspaceApi, "latestTriage").mockResolvedValue({job});
  vi.spyOn(workspaceApi, "triageJob").mockResolvedValue({...job, status: "completed", processed: 12});
  const initial = options(), updated = options();
  const hook = renderHook(({callbacks}) => useDurableMailTriage(callbacks), {initialProps: {callbacks: initial}});
  await flush();
  hook.rerender({callbacks: updated});
  await tick();
  expect(initial.onSettled).not.toHaveBeenCalled();
  expect(updated.onSettled).toHaveBeenCalledTimes(1);
});

it("suspend le suivi en quittant Mails et reprend sans appliquer une réponse ancienne", async () => {
  vi.spyOn(workspaceApi, "latestTriage").mockResolvedValue({job});
  let resolveOld: (value: DurableTriageJob) => void = () => {};
  let oldSignal: AbortSignal | undefined;
  const details = vi.spyOn(workspaceApi, "triageJob").mockImplementationOnce((_id, signal) => {
    oldSignal = signal;
    return new Promise(resolve => {resolveOld = resolve;});
  }).mockResolvedValue({...job, status:"completed", processed:12});
  const cancel = vi.spyOn(workspaceApi, "cancelTriage");
  const callbacks = options();
  const hook = renderHook(({active}) => useDurableMailTriage({...callbacks,active}), {initialProps:{active:true}});
  await flush();await tick();
  hook.rerender({active:false});
  expect(oldSignal?.aborted).toBe(true);
  await act(async () => {resolveOld({...job, processed:9});await vi.advanceTimersByTimeAsync(10000);});
  expect(details).toHaveBeenCalledTimes(1);
  expect(callbacks.onProgress).toHaveBeenLastCalledWith(expect.objectContaining({processed:8}));
  expect(cancel).not.toHaveBeenCalled();
  hook.rerender({active:true});await flush();
  expect(details).toHaveBeenCalledTimes(2);
  expect(callbacks.onProgress).toHaveBeenLastCalledWith(expect.objectContaining({processed:12,status:"completed"}));
  expect(callbacks.onSettled).toHaveBeenCalledTimes(1);
});

it("suspend le suivi quand la fenêtre est masquée et le reprend immédiatement", async () => {
  const hidden = vi.spyOn(document, 'hidden', 'get').mockReturnValue(false);
  vi.spyOn(workspaceApi, "latestTriage").mockResolvedValue({job});
  let oldSignal: AbortSignal | undefined;
  const details = vi.spyOn(workspaceApi, "triageJob").mockImplementationOnce((_id, signal) => {
    oldSignal = signal;return new Promise(() => {});
  }).mockResolvedValue({...job, processed:10});
  const callbacks = options();
  renderHook(() => useDurableMailTriage(callbacks));
  await flush();await tick();
  hidden.mockReturnValue(true);
  act(() => document.dispatchEvent(new Event('visibilitychange')));
  expect(oldSignal?.aborted).toBe(true);
  await act(async () => {await vi.advanceTimersByTimeAsync(10000);});
  expect(details).toHaveBeenCalledTimes(1);
  hidden.mockReturnValue(false);
  act(() => document.dispatchEvent(new Event('visibilitychange')));
  await flush();
  expect(details).toHaveBeenCalledTimes(2);
  expect(callbacks.onProgress).toHaveBeenLastCalledWith(expect.objectContaining({processed:10}));
});

it("conserve une commande en cours pendant la navigation et actualise au retour", async () => {
  const latest = vi.spyOn(workspaceApi, "latestTriage").mockResolvedValue({job:null});
  let resolveStart: (value: DurableTriageJob) => void = () => {};
  vi.spyOn(workspaceApi, "startTriage").mockImplementation(() => new Promise(resolve => {resolveStart = resolve;}));
  const cancel = vi.spyOn(workspaceApi, "cancelTriage");
  const callbacks = options();
  const hook = renderHook(({active}) => useDurableMailTriage({...callbacks,active}), {initialProps:{active:true}});
  await flush();
  let started: Promise<void> | undefined;
  act(() => {started=hook.result.current.start(false);});
  hook.rerender({active:false});
  const completed={...job,status:"completed" as const,processed:12};
  await act(async () => {resolveStart(completed);await started;});
  expect(callbacks.onProgress).toHaveBeenLastCalledWith(expect.objectContaining({processed:12,status:"completed"}));
  expect(callbacks.onSettled).not.toHaveBeenCalled();
  expect(cancel).not.toHaveBeenCalled();
  latest.mockResolvedValue({job:completed});
  hook.rerender({active:true});await flush();
  expect(callbacks.onSettled).toHaveBeenCalledTimes(1);
});
