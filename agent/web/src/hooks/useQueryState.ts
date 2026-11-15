import {useCallback, useEffect, useRef, useState, type SetStateAction} from 'react';

type Value = string | number | boolean;
const changed = 'agent:querychange';
function read<T extends Record<string, Value>>(defaults: T): T {
  const params = new URLSearchParams(window.location.search);
  return Object.fromEntries(Object.entries(defaults).map(([key, fallback]) => {
    const raw = params.get(key);
    const value = raw === null ? fallback : typeof fallback === 'boolean' ? raw === 'true'
      : typeof fallback === 'number' ? (/^\d+$/.test(raw) && Number.isSafeInteger(Number(raw)) ? Number(raw) : fallback) : raw;
    return [key, value];
  })) as T;
}

/** Each cached view owns only its query keys and never writes another view's URL. */
export function useQueryObject<T extends Record<string, Value>>(defaults: T, path?: string) {
  const config = useRef({defaults, path: path ?? window.location.pathname});
  const [value, setValue] = useState<T>(() => window.location.pathname === config.current.path ? read(defaults) : defaults);
  const current = useRef(value);
  current.current = value;
  useEffect(() => {
    const restore = () => {
      if (window.location.pathname !== config.current.path) return;
      const next = read(config.current.defaults);
      current.current = next; setValue(next);
    };
    window.addEventListener('popstate', restore);
    window.addEventListener(changed, restore);
    return () => {window.removeEventListener('popstate', restore); window.removeEventListener(changed, restore);};
  }, []);
  const update = useCallback((action: SetStateAction<T>) => {
    const next = typeof action === 'function' ? action(current.current) : action;
    current.current = next; setValue(next);
    if (window.location.pathname !== config.current.path) return;
    const url = new URL(window.location.href);
    Object.entries(next).forEach(([key, item]) => {
      if (item === config.current.defaults[key]) url.searchParams.delete(key);
      else url.searchParams.set(key, String(item));
    });
    window.history.replaceState(window.history.state, '', url.pathname + url.search + url.hash);
    // Notify the other query-key owners outside the updater/render stack.
    queueMicrotask(() => window.dispatchEvent(new Event(changed)));
  }, []);
  return [value, update] as const;
}

export function useQueryState<T extends Value>(key: string, fallback: T, path?: string) {
  const [state, setState] = useQueryObject({[key]: fallback}, path);
  const update = useCallback((action: SetStateAction<T>) => {
    setState(previous => ({[key]: typeof action === 'function' ? action(previous[key]) : action}));
  }, [key, setState]);
  return [state[key], update] as const;
}
