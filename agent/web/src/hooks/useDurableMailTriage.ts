import { useEffect, useRef } from "react";
import { workspaceApi, type DurableTriageJob } from "../lib/workspaceApi";
import { triageProgressMessage, type TriageProgress } from "../lib/mailTriage";

type Options = {
  enabled?: boolean;
  active?: boolean;
  onProgress: (progress: TriageProgress) => void;
  onRunning: (running: boolean) => void;
  onMessage: (message: string) => void;
  onSettled: () => Promise<void> | void;
};
const active = (job: DurableTriageJob | null) => !!job && ["queued", "running"].includes(job.status);
const messageOf = (error: unknown) => error instanceof Error ? error.message : String(error);

/** A browser observes committed server jobs; closing the page does not cancel them. */
export function useDurableMailTriage(options: Options) {
  const callbacks = useRef(options);
  callbacks.current = options;
  const mounted = useRef(false);
  const generation = useRef(0);
  const commandGeneration = useRef(0);
  const job = useRef<DurableTriageJob | null>(null);
  const signature = useRef("");
  const operation = useRef(false);
  const pollController = useRef<AbortController | null>(null);
  const wakePolling = useRef<(() => void) | null>(null);
  const pendingSettled = useRef(false);

  const notifySettled = () => {
    if (callbacks.current.active === false || document.hidden) {pendingSettled.current = true; return;}
    pendingSettled.current = false;
    void Promise.resolve().then(() => {
      if (!mounted.current) return;
      if (callbacks.current.active === false || document.hidden) {pendingSettled.current = true; return;}
      return callbacks.current.onSettled();
    }).catch(() => undefined);
  };

  const apply = (next: DurableTriageJob, fromStart = false) => {
    if (!mounted.current) return;
    const previous = job.current;
    job.current = next;
    const fingerprint = JSON.stringify(next);
    if (fingerprint === signature.current) return;
    signature.current = fingerprint;
    const status: TriageProgress["status"] = next.status === "queued" ? "running"
      : next.status === "cancelled" ? "interrupted" : next.status;
    const progress: TriageProgress = {processed: next.processed, total: next.total,
      classified: next.result.triaged || 0, divers: next.result.divers || 0,
      ...(next.result.auto_classified ? {autoClassified: next.result.auto_classified} : {}),
      errors: next.result.errors?.length || 0, status};
    callbacks.current.onProgress(progress);
    callbacks.current.onRunning(active(next));
    const message = next.cancel_requested && active(next)
      ? `Annulation demandée : ${next.processed} / ${next.total} mails traités. Le lot en cours se termine avant l’arrêt.`
      : next.status === "queued" ? `Analyse en attente : ${next.processed} / ${next.total} mails traités.`
      : `${triageProgressMessage(progress)}${next.error ? ` ${next.error}` : ""}`;
    callbacks.current.onMessage(message);
    if (!active(next) && (active(previous) || fromStart)) {
      notifySettled();
    }
  };

  useEffect(() => {
    if (options.enabled === false) return;
    mounted.current = true;
    return () => {mounted.current = false; commandGeneration.current++;};
  }, [options.enabled]);

  useEffect(() => {
    if (options.enabled === false || options.active === false) return;
    let timer: number | undefined;
    let live = true;
    let lastConnectionError = "";
    const schedule = () => {
      if (live && !document.hidden && timer === undefined) timer = window.setTimeout(() => void poll(true), 2000);
    };
    const poll = async (quiet=false) => {
      timer = undefined;
      if (!live || document.hidden) return;
      if (operation.current) {schedule(); return;}
      const ticket = ++generation.current;
      const controller = new AbortController();
      pollController.current = controller;
      try {
        const current = job.current;
        const latest = current && active(current) ? await (quiet?workspaceApi.triageJob(current.id,controller.signal,true):workspaceApi.triageJob(current.id, controller.signal))
          : (await (quiet?workspaceApi.latestTriage(controller.signal,true):workspaceApi.latestTriage(controller.signal))).job;
        if (live && !controller.signal.aborted && ticket === generation.current && latest) {
          if (lastConnectionError) signature.current = "";
          apply(latest);
        }
        if (live && !controller.signal.aborted && ticket === generation.current) lastConnectionError = "";
      } catch (error) {
        if (live && ticket === generation.current && !controller.signal.aborted) {
          const message = `Suivi de l’analyse indisponible : ${messageOf(error)}. Nouvelle tentative automatique.`;
          if (message !== lastConnectionError) callbacks.current.onMessage(message);
          lastConnectionError = message;
        }
      } finally {
        if (pollController.current === controller) pollController.current = null;
        if (live && ticket === generation.current) schedule();
      }
    };
    const stop = () => {
      generation.current++;
      if (timer !== undefined) window.clearTimeout(timer);
      timer = undefined;
      pollController.current?.abort();
      pollController.current = null;
    };
    const wake = () => {
      if (!live || document.hidden) return;
      if (pendingSettled.current) notifySettled();
      if (timer !== undefined) window.clearTimeout(timer);
      timer = undefined;
      if (!pollController.current && !operation.current) void poll(true);
      else if (operation.current) schedule();
    };
    const visibility = () => {if (document.hidden) stop(); else wake();};
    wakePolling.current = schedule;
    document.addEventListener('visibilitychange', visibility);
    if (!document.hidden) {
      if (pendingSettled.current) notifySettled();
      void poll();
    }
    return () => {
      live = false;
      document.removeEventListener('visibilitychange', visibility);
      if (wakePolling.current === schedule) wakePolling.current = null;
      stop();
    };
  }, [options.enabled, options.active]);

  const start = async (force: boolean) => {
    if (operation.current || !mounted.current) return;
    operation.current = true;
    const ticket = ++commandGeneration.current;
    generation.current++;
    pollController.current?.abort();
    callbacks.current.onRunning(true);
    callbacks.current.onMessage("Préparation de l’analyse et calcul du nombre de mails à traiter…");
    try {
      const next = await workspaceApi.startTriage(force);
      if (mounted.current && ticket === commandGeneration.current) apply(next, true);
    } catch (error) {
      if (mounted.current && ticket === commandGeneration.current) {
        callbacks.current.onRunning(active(job.current));
        callbacks.current.onMessage(`L’analyse n’a pas pu être lancée : ${messageOf(error)}`);
      }
    } finally {operation.current = false;wakePolling.current?.();}
  };

  const cancel = async () => {
    const current = job.current;
    if (operation.current || !mounted.current || !current || !active(current) || current.cancel_requested) return;
    operation.current = true;
    const ticket = ++commandGeneration.current;
    generation.current++;
    pollController.current?.abort();
    try {
      const next = await workspaceApi.cancelTriage(current.id);
      if (mounted.current && ticket === commandGeneration.current) apply(next);
    } catch (error) {
      if (mounted.current && ticket === commandGeneration.current) callbacks.current.onMessage(`L’annulation n’a pas été confirmée : ${messageOf(error)}`);
    } finally {operation.current = false;wakePolling.current?.();}
  };
  return {start, cancel};
}
