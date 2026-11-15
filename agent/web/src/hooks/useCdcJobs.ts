import { useEffect, useRef, useState } from "react";
import { api, type CdcJob } from "../lib/api";

export function useCdcJobs(projectId: string, onUpdated: () => void) {
  const [jobs, setJobs] = useState<CdcJob[]>([]);
  const [error, setError] = useState("");
  const update = useRef(onUpdated);
  update.current = onUpdated;
  useEffect(() => {
    let disposed = false;
    let loading = false;
    const previous = new Map<string, string>();
    setJobs([]); setError("");
    const load = async (quiet=false) => {
      if (loading) return;
      loading = true;
      try {
        const rows = await (quiet?api.cdcJobs(projectId,true):api.cdcJobs(projectId));
        if (disposed) return;
        if (rows.some(j => previous.has(j.id) && previous.get(j.id) !== j.status && ["completed", "failed", "cancelled"].includes(j.status))) update.current();
        rows.forEach(j => previous.set(j.id, j.status));
        setJobs(rows); setError("");
      } catch (e) { if (!disposed) setError(e instanceof Error ? e.message : String(e)); }
      finally { loading = false; }
    };
    void load();
    const timer = window.setInterval(() => void load(true), 2000);
    return () => { disposed = true; window.clearInterval(timer); };
  }, [projectId]);
  const action = async (run: () => Promise<CdcJob>) => {
    try {
      const job = await run();
      setJobs(rows => [job, ...rows.filter(j => j.id !== job.id)]); setError("");
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
  };
  return { jobs, error, running: jobs.some(j => ["queued", "running"].includes(j.status)),
    enqueue: (source: string) => action(() => api.analyzeCdc(projectId, source)),
    cancel: (job: string) => action(() => api.cancelCdcJob(projectId, job)),
    retry: (job: string) => action(() => api.retryCdcJob(projectId, job)) };
}
