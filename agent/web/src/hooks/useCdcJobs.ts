import { useEffect, useRef, useState } from "react";
import { api, type CdcJob } from "../lib/api";

export function useCdcJobs(projectId: string, onUpdated: () => void, active = true) {
  const [jobs, setJobs] = useState<CdcJob[]>([]);
  const [error, setError] = useState("");
  const update = useRef(onUpdated);
  update.current = onUpdated;
  const previous = useRef(new Map<string, string>());
  const wake = useRef<() => void>(() => {});
  useEffect(() => {
    previous.current.clear();
    setJobs([]); setError("");
  }, [projectId]);
  useEffect(() => {
    if (!active) return;
    let disposed = false;
    let loading = false;
    let refreshRequested = false;
    let timer: number | undefined;
    const schedule = (delay: number) => {
      window.clearTimeout(timer);
      if (!disposed && !document.hidden) timer = window.setTimeout(() => void load(true), delay);
    };
    const load = async (quiet = false) => {
      if (loading || document.hidden || disposed) return;
      loading = true;
      try {
        const rows = await (quiet ? api.cdcJobs(projectId, true) : api.cdcJobs(projectId));
        if (disposed || document.hidden) return;
        if (rows.some(j => previous.current.has(j.id) && previous.current.get(j.id) !== j.status && ["completed", "failed", "cancelled"].includes(j.status))) update.current();
        rows.forEach(j => previous.current.set(j.id, j.status));
        setJobs(rows); setError("");
        schedule(rows.some(j => ["queued", "running"].includes(j.status)) ? 2000 : 30000);
      } catch (e) {
        if (!disposed) { setError(e instanceof Error ? e.message : String(e)); schedule(30000); }
      } finally {
        loading = false;
        if (refreshRequested && !disposed && !document.hidden) {
          refreshRequested = false;
          schedule(0);
        }
      }
    };
    const visibility = () => {
      window.clearTimeout(timer);
      if (!document.hidden) { if (loading) refreshRequested = true; else void load(true); }
    };
    wake.current = () => { if (loading) refreshRequested = true; else schedule(2000); };
    document.addEventListener("visibilitychange", visibility);
    void load();
    return () => { disposed = true; wake.current = () => {}; window.clearTimeout(timer); document.removeEventListener("visibilitychange", visibility); };
  }, [projectId, active]);
  const action = async (run: () => Promise<CdcJob>) => {
    try {
      const job = await run();
      previous.current.set(job.id, job.status);
      setJobs(rows => [job, ...rows.filter(j => j.id !== job.id)]); setError(""); wake.current();
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
  };
  return { jobs, error, running: jobs.some(j => ["queued", "running"].includes(j.status)),
    enqueue: (source: string) => action(() => api.analyzeCdc(projectId, source)),
    cancel: (job: string) => action(() => api.cancelCdcJob(projectId, job)),
    retry: (job: string) => action(() => api.retryCdcJob(projectId, job)) };
}
