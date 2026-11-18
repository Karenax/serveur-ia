import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.resetModules(); });

function abortableFetch() {
  return vi.fn((_url: string, init?: RequestInit) => new Promise<Response>((_resolve, reject) => {
    const signal = init?.signal;
    if (signal?.aborted) reject(signal.reason);
    else signal?.addEventListener("abort", () => reject(signal.reason), { once: true });
  }));
}

describe("Transport local", () => {
  it("distingue une réponse HTTP refusée d’une erreur réseau", async () => {
    vi.stubGlobal('fetch',vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({detail:'Révision différente'}),{status:409}))
      .mockRejectedValueOnce(new TypeError('Connexion interrompue')));
    const {request}=await import('./http');
    const {HttpError}=await import('./httpError');
    await expect(request('/v1/test',{activity:false})).rejects.toMatchObject({name:'HttpError',status:409,message:'Révision différente'});
    try {await request('/v1/test',{activity:false});throw new Error('La lecture aurait dû échouer');}
    catch (error) {expect(error).toBeInstanceOf(TypeError);expect(error).not.toBeInstanceOf(HttpError);}
  });
  it("borne une lecture de session quand son appelant demande un délai", async () => {
    vi.useFakeTimers();const fetch=abortableFetch();vi.stubGlobal('fetch',fetch);
    const {api}=await import('./api');
    const pending=api.session(undefined,20000);
    const rejected=expect(pending).rejects.toMatchObject({name:'AbortError'});
    await vi.advanceTimersByTimeAsync(19999);
    expect(fetch.mock.calls[0][1]?.signal?.aborted).toBe(false);
    await vi.advanceTimersByTimeAsync(1);await rejected;
    expect(fetch.mock.calls[0][1]?.signal?.aborted).toBe(true);
  });
  it("libère les lectures de réunions et traitements bloquées après leur délai", async () => {
    vi.useFakeTimers();
    const fetch=abortableFetch();vi.stubGlobal("fetch",fetch);
    const {workspaceApi}=await import("./workspaceApi");
    const {api}=await import("./api");
    const pending=[workspaceApi.jobs({},undefined,true),workspaceApi.meetings({},undefined,true),
      workspaceApi.latestTriage(undefined,true),workspaceApi.triageJob('fictif',undefined,true),
      api.classifiedMailPage(),api.rejectedMailPage()];
    const outcomes=Promise.all(pending.map(value=>value.then(()=>"success",error=>error.name)));
    await vi.advanceTimersByTimeAsync(29_999);
    expect(fetch.mock.calls.every(([,init])=>!init?.signal?.aborted)).toBe(true);
    await vi.advanceTimersByTimeAsync(1);
    expect(await outcomes).toEqual(["AbortError","AbortError","AbortError","AbortError","AbortError","AbortError"]);
    expect(fetch.mock.calls.every(([,init])=>init?.signal?.aborted)).toBe(true);
  });
  it("ne coupe pas une opération longue au bout de six minutes par défaut", async () => {
    vi.useFakeTimers();vi.stubGlobal("fetch", abortableFetch());
    const external = new AbortController();
    const { request } = await import("./http");
    const pending = request("/api/v1/projects/test/cdc/analyze", {activity:false,signal:external.signal});
    const rejected = expect(pending).rejects.toMatchObject({name:"AbortError"});
    await vi.advanceTimersByTimeAsync(3_600_000);
    expect(vi.getTimerCount()).toBe(0);
    external.abort();await rejected;
  });
  it("laisse un traitement OCR sans plafond de durée tout en respectant son annulation", async () => {
    vi.useFakeTimers();vi.stubGlobal("fetch", abortableFetch());
    const external = new AbortController();
    const { request } = await import("./http");
    const pending = request("/api/v1/workspace/sources/test/ocr", {activity:false,signal:external.signal}, 0);
    const rejected = expect(pending).rejects.toMatchObject({name:"AbortError"});
    await vi.advanceTimersByTimeAsync(3_600_000);
    expect(vi.getTimerCount()).toBe(0);
    external.abort();await rejected;
  });
  it("garde une lecture ordinaire silencieuse même si son décodage est lent", async () => {
    vi.useFakeTimers();
    let resolve!: (value: object) => void;
    const decoded = new Promise<object>(done => { resolve = done; });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: () => decoded }));
    const { request } = await import("./http");
    const { getActivitySnapshot } = await import("./asyncActivity");
    const pending = request("/api/v1/projects/test/cdc/sources");
    expect(getActivitySnapshot()).toBeNull();
    await vi.advanceTimersByTimeAsync(10_000);
    expect(getActivitySnapshot()).toBeNull();
    resolve({ sources: [] });
    await pending;
    expect(getActivitySnapshot()).toBeNull();
    expect(vi.getTimerCount()).toBe(0);
  });

  it("signale l’attente du jeton et termine aussi si l’ouverture de session échoue", async () => {
    let reject!: (failure: Error) => void;
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => new Promise((_resolve, fail) => { reject = fail; })));
    const { request } = await import("./http");
    const { getActivitySnapshot } = await import("./asyncActivity");
    const pending = request("/api/v1/projects/test/cdc/sources/upload", { method: "POST" });
    const failure = new Error("Session refusée");
    const rejected = expect(pending).rejects.toBe(failure);
    expect(getActivitySnapshot()?.label).toBe("Mise à jour du CDC…");
    reject(failure);
    await rejected;
    expect(getActivitySnapshot()).toBeNull();
  });

  it("garde le polling silencieux sans transmettre l’option UI au serveur", async () => {
    vi.useFakeTimers();
    const fetch = abortableFetch();
    vi.stubGlobal("fetch", fetch);
    const { request } = await import("./http");
    const { getActivitySnapshot } = await import("./asyncActivity");
    const cancel = new AbortController();
    const pending = request("/v1/status", { activity: false, signal: cancel.signal });
    const rejected = expect(pending).rejects.toMatchObject({ name: "AbortError" });
    await vi.advanceTimersByTimeAsync(2000);
    expect(getActivitySnapshot()).toBeNull();
    expect(fetch.mock.calls[0][1]).not.toHaveProperty("activity");
    cancel.abort(); await rejected;
    expect(vi.getTimerCount()).toBe(0);
  });
  it("partage le jeton de session pour les écritures et respecte FormData", async () => {
    const fetch = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ token: "test-session" })))
      .mockImplementation(async () => new Response(JSON.stringify({ ok: true })));
    vi.stubGlobal("fetch", fetch);
    const { request } = await import("./http");
    await request("/v1/projects", { method: "POST", body: JSON.stringify({}) });
    await request("/v1/sources", { method: "POST", body: new FormData() });
    expect(fetch).toHaveBeenCalledTimes(3);
    const headers = fetch.mock.calls[2][1].headers as Headers;
    expect(headers.get("X-Agent-Token")).toBe("test-session");
    expect(headers.has("Content-Type")).toBe(false);
  });
  it("affiche le message des contrôles bloquants", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ detail: { message: "Revue incomplète", blockers: 2 } }), { status: 409 })));
    const { request } = await import("./http");
    await expect(request("/api/v1/offer")).rejects.toThrow("Revue incomplète");
  });

  it("interrompt une requête arrivée au délai même avec un signal externe actif", async () => {
    vi.useFakeTimers();
    const fetch = abortableFetch();
    vi.stubGlobal("fetch", fetch);
    const external = new AbortController();
    const { request } = await import("./http");
    const pending = request("/api/v1/workspace/sources", { signal: external.signal }, 30);
    const rejected = expect(pending).rejects.toMatchObject({ name: "AbortError" });
    await vi.advanceTimersByTimeAsync(29);
    expect(fetch.mock.calls[0][1]?.signal?.aborted).toBe(false);
    await vi.advanceTimersByTimeAsync(1);
    await rejected;
    expect(fetch.mock.calls[0][1]?.signal?.aborted).toBe(true);
    expect(external.signal.aborted).toBe(false);
    expect(vi.getTimerCount()).toBe(0);
  });

  it("transmet une annulation externe et sa raison avant le délai", async () => {
    vi.useFakeTimers();
    const fetch = abortableFetch();
    vi.stubGlobal("fetch", fetch);
    const external = new AbortController();
    const reason = new DOMException("Écran fermé", "AbortError");
    const { request } = await import("./http");
    const pending = request("/api/v1/workspace/sources", { signal: external.signal }, 30000);
    const rejected = expect(pending).rejects.toBe(reason);
    external.abort(reason);
    await rejected;
    expect(fetch.mock.calls[0][1]?.signal?.reason).toBe(reason);
    expect(vi.getTimerCount()).toBe(0);
  });

  it("respecte un signal déjà annulé sans laisser un délai actif", async () => {
    vi.useFakeTimers();
    vi.stubGlobal("fetch", abortableFetch());
    const external = new AbortController();
    const reason = new DOMException("Navigation précédente", "AbortError");
    external.abort(reason);
    const { request } = await import("./http");
    await expect(request("/api/v1/workspace/sources", { signal: external.signal }, 30000)).rejects.toBe(reason);
    expect(vi.getTimerCount()).toBe(0);
  });

  it("retire le délai et le relais externe après une réponse réussie", async () => {
    vi.useFakeTimers();
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ total: 42 })));
    vi.stubGlobal("fetch", fetch);
    const external = new AbortController();
    const remove = vi.spyOn(external.signal, "removeEventListener");
    const { request } = await import("./http");
    await expect(request("/api/v1/workspace/sources", { signal: external.signal }, 30000)).resolves.toEqual({ total: 42 });
    const signal = fetch.mock.calls[0][1].signal as AbortSignal;
    expect(remove).toHaveBeenCalledWith("abort", expect.any(Function));
    expect(vi.getTimerCount()).toBe(0);
    external.abort();
    await vi.advanceTimersByTimeAsync(30000);
    expect(signal.aborted).toBe(false);
  });
});
