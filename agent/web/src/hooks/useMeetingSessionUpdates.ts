import {useEffect, useState, type RefObject} from 'react';
import {meetingSessions, type MeetingSession} from '../lib/meetingSessions';

/** Keep a visible session current without replacing the canonical snapshot or local draft. */
export function useMeetingSessionUpdates({sessionId, active, rowRef, reload}: {
  sessionId: string;
  active: boolean;
  rowRef: RefObject<MeetingSession | null>;
  reload: (signal?: AbortSignal, quiet?: boolean) => Promise<MeetingSession>;
}) {
  const [eventReadError, setEventReadError] = useState('');

  useEffect(() => {
    if (!active) return;
    let disposed = false, timer: ReturnType<typeof setInterval> | undefined;
    const controllers = new Set<AbortController>();
    const refresh = () => {
      if (disposed || document.hidden || controllers.size >= 2) return;
      const current = new AbortController(); controllers.add(current);
      void reload(current.signal, true).catch(() => undefined).finally(() => {controllers.delete(current);});
    };
    const visibility = () => {
      if (document.hidden) {
        for (const current of controllers) current.abort(); controllers.clear();
        if (timer !== undefined) clearInterval(timer); timer = undefined;
      } else if (timer === undefined) {
        refresh(); timer = setInterval(refresh, 5000);
      }
    };
    if (!document.hidden) timer = setInterval(refresh, 5000);
    document.addEventListener('visibilitychange', visibility);
    return () => {disposed = true; for (const current of controllers) current.abort(); controllers.clear(); if (timer !== undefined) clearInterval(timer); document.removeEventListener('visibilitychange', visibility);};
  }, [reload, active]);

  useEffect(() => {
    if (!active || typeof meetingSessions.watchEvents !== 'function') return;
    let disposed = false, controller: AbortController | null = null, reading: AbortController | null = null, queued = false, cursor = 0;
    let retry: ReturnType<typeof setTimeout> | undefined;
    const refresh = async () => {
      if (disposed || document.hidden || !controller || controller.signal.aborted || (reading && !reading.signal.aborted)) return;
      const current = controller;
      reading = current;
      try {
        while (queued && !disposed && !document.hidden && !current.signal.aborted) {
          queued = false;
          const row = await reload(current.signal, true);
          if (disposed || current.signal.aborted || controller !== current) return;
          if ((row.event_cursor ?? 0) < cursor) {queued = true; break;}
        }
      } catch {/* The canonical polling fallback remains available; retain this wake-up. */
        if (!disposed && controller === current && !current.signal.aborted) queued = true;
      }
      finally {
        if (reading === current) reading = null;
        if (queued && !disposed && !document.hidden && controller === current && !current.signal.aborted) {
          retry = setTimeout(() => {retry = undefined; void refresh();}, 500);
        }
      }
    };
    const requestRefresh = () => {queued = true; if (retry) clearTimeout(retry); retry = undefined; void refresh();};
    const visible = () => {
      if (disposed) return;
      controller?.abort(); controller = null;
      if (retry) clearTimeout(retry); retry = undefined;
      if (document.hidden) return;
      const current = new AbortController(); controller = current;
      cursor = Math.max(cursor, rowRef.current?.id === sessionId ? rowRef.current.event_cursor ?? 0 : 0);
      void meetingSessions.watchEvents(sessionId, {
        after: cursor, signal: current.signal,
        onConnected: () => {if (!disposed && controller === current && !current.signal.aborted) {setEventReadError(''); requestRefresh();}},
        onEvent: event => {
          if (disposed || controller !== current || current.signal.aborted || event.id <= cursor) return;
          cursor = event.id;
          const known = rowRef.current?.id === sessionId ? rowRef.current.event_cursor ?? 0 : 0;
          if (event.id > known) requestRefresh();
        },
        onError: failure => {
          if (!disposed && controller === current && !current.signal.aborted && !failure.retryable) {
            setEventReadError(failure.message); current.abort();
          }
        },
      }).catch(() => {/* The five-second snapshot fallback also supports older servers. */});
    };
    visible();
    document.addEventListener('visibilitychange', visible);
    return () => {disposed = true; controller?.abort(); if (retry) clearTimeout(retry); document.removeEventListener('visibilitychange', visible);};
  }, [active, sessionId, reload, rowRef]);

  return eventReadError;
}
