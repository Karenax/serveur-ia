import { agentFetch } from './agentRoutes';
import { beginActivity, automaticRequestActivity } from './asyncActivity';

export type RequestOptions = RequestInit & { activity?: string | false };
let session: Promise<string> | undefined;
export function invalidateSession() { session=undefined; }

export async function token(): Promise<string> {
  session ??= agentFetch("/api/v1/session", { credentials: "same-origin" })
    .then(async response => {
      if (!response.ok) throw new Error("Session locale indisponible");
      return (await response.json()).token as string;
    }).catch(error => { session = undefined; throw error; });
  return session;
}

export async function request<T>(url: string, init: RequestOptions = {}, timeoutMs = 0): Promise<T> {
  const { activity, ...fetchInit } = init;
  const method = (init.method ?? 'GET').toUpperCase();
  const label=activity??automaticRequestActivity(url,method);
  const finish = label === false ? () => {} : beginActivity(label);
  try {
    const headers = new Headers(init.headers);
    if (!headers.has("Content-Type") && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
    const localStop = method === 'POST' && document.body.dataset.kiaraCapture === 'true'
      && /^\/api\/v1\/meeting-sessions\/[0-9a-f-]{36}\/native-capture\/stop$/.test(url);
    if (!localStop && !["GET", "HEAD"].includes(method)) headers.set("X-Agent-Token", await token());
    const controller = new AbortController();
    const externalSignal = init.signal;
    const externalAbort = () => controller.abort(externalSignal?.reason);
    if (externalSignal?.aborted) externalAbort();
    else externalSignal?.addEventListener("abort", externalAbort, { once: true });
    const timeout = timeoutMs > 0 ? window.setTimeout(() => controller.abort(), timeoutMs) : undefined;
    try {
      const response = await agentFetch(url, { ...fetchInit, headers, signal: controller.signal });
      const data = await response.json();
      if (!response.ok) {
        if (response.status === 403) session = undefined;
        const detail = data.detail;
        throw new Error(typeof detail === "string" ? detail : detail?.message ?? JSON.stringify(detail ?? data));
      }
      return data as T;
    } finally {
      if (timeout !== undefined) window.clearTimeout(timeout);
      externalSignal?.removeEventListener("abort", externalAbort);
    }
  } finally { finish(); }
}
