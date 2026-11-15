import { useState } from "react";
import { afterEach, expect, it, vi } from "vitest";
import { act, cleanup, renderHook } from "@testing-library/react";
import { request } from "../lib/http";
import { useAssistantHistory, type AssistantMessage } from "./useAssistantHistory";

vi.mock("../lib/http", () => ({request: vi.fn()}));
afterEach(() => {cleanup(); vi.mocked(request).mockReset();});
const endpoint = "/api/v1/workspace/assistant-threads";
type SavedThread = {id: string; title: string; project_id: string | null; revision: number; messages: AssistantMessage[]};
const initial: AssistantMessage[] = [{role: "user", text: "Date de la revue ?"}];
function useHarness(messagesAtStart: AssistantMessage[] = initial, pausedAtStart = false) {
  const [messages, setMessages] = useState(messagesAtStart);
  const [project, setProject] = useState("brain-a");
  const [paused, setPaused] = useState(pausedAtStart);
  const history = useAssistantHistory(true, messages, project, (restored, scope) => {setMessages(restored); setProject(scope);}, paused);
  return {history, messages, project, setMessages, setPaused};
}
const flush = async () => {await act(async () => {await Promise.resolve();});};
const mutations = () => vi.mocked(request).mock.calls.filter(([, init]) => ["POST", "PUT"].includes(init?.method || ""));
function saved(id: string, revision: number, messages: AssistantMessage[]): SavedThread {
  return {id, revision, messages, title: messages[0]?.text || "Conversation", project_id: "brain-a"};
}

it("sérialise les révisions même quand une réponse arrive pendant l'enregistrement", async () => {
  let resolveCreate: (value: SavedThread) => void = () => {};
  vi.mocked(request).mockImplementation((url, init) => {
    if (!init?.method) return Promise.resolve({items: []});
    const body = JSON.parse(String(init.body));
    if (init.method === "POST") return new Promise(resolve => {resolveCreate = resolve;});
    return Promise.resolve(saved("thread-a", body.expected_revision + 1, body.messages));
  });
  const hook = renderHook(() => useHarness());
  await flush();
  expect(mutations()).toHaveLength(1);
  const withAnswer: AssistantMessage[] = [...initial, {role: "assistant", text: "Revue prévue le 9 octobre."}];
  act(() => hook.result.current.setMessages(withAnswer));
  await flush();
  expect(mutations()).toHaveLength(1);
  await act(async () => {resolveCreate(saved("thread-a", 1, initial));});
  await flush();
  expect(mutations()).toHaveLength(2);
  expect(JSON.parse(String(mutations()[1][1]?.body))).toMatchObject({expected_revision: 1, messages: withAnswer});
  act(() => hook.result.current.setMessages([...withAnswer, {role: "user", text: "Qui participe ?"}]));
  await flush();
  expect(JSON.parse(String(mutations()[2][1]?.body))).toMatchObject({expected_revision: 2});
  expect(hook.result.current.history.status).toBe("Enregistrée localement");
});

it("n'enregistre pas en boucle après la mise à jour de l'état et de la liste", async () => {
  vi.mocked(request).mockImplementation((_url, init) => !init?.method ? Promise.resolve({items: []})
    : Promise.resolve(saved("thread-a", 1, JSON.parse(String(init.body)).messages)));
  const hook = renderHook(() => useHarness());
  await flush();
  expect(hook.result.current.history.threadId).toBe("thread-a");
  hook.rerender();
  await flush();
  hook.rerender();
  await flush();
  expect(mutations()).toHaveLength(1);
  expect(vi.mocked(request).mock.calls.filter(([url]) => url === endpoint + "?limit=100")).toHaveLength(2);
});

it("conserve le brouillon après conflit et crée une copie explicite sans écraser l'original", async () => {
  let created = 0;
  vi.mocked(request).mockImplementation((_url, init) => {
    if (!init?.method) return Promise.resolve({items: []});
    if (init.method === "PUT") return Promise.reject(new Error("Conflit de révision : conversation modifiée ailleurs"));
    created++;
    return Promise.resolve(saved(created === 1 ? "original" : "copie", 1, JSON.parse(String(init.body)).messages));
  });
  const hook = renderHook(() => useHarness());
  await flush();
  const draft: AssistantMessage[] = [...initial, {role: "assistant", text: "Compte rendu à vérifier."}];
  act(() => hook.result.current.setMessages(draft));
  await flush();
  expect(hook.result.current.history.error).toContain("Conflit de révision");
  expect(hook.result.current.history.threadId).toBe("original");
  expect(hook.result.current.messages).toEqual(draft);
  const newerDraft: AssistantMessage[] = [...draft, {role: "user", text: "Conserver ma correction."}];
  act(() => hook.result.current.setMessages(newerDraft));
  await flush();
  expect(mutations().filter(([, init]) => init?.method === "PUT")).toHaveLength(1);
  act(() => hook.result.current.history.fork());
  await flush();
  expect(hook.result.current.history.threadId).toBe("copie");
  const posts = mutations().filter(([, init]) => init?.method === "POST");
  expect(posts).toHaveLength(2);
  expect(JSON.parse(String(posts[1][1]?.body)).messages).toEqual(newerDraft);
  expect(mutations().filter(([, init]) => init?.method === "PUT")).toHaveLength(1);
});

it("ignore une ancienne conversation chargée après la conversation nouvellement sélectionnée", async () => {
  let resolveOld: (value: SavedThread) => void = () => {};
  vi.mocked(request).mockImplementation(url => {
    if (url === endpoint + "/ancienne") return new Promise(resolve => {resolveOld = resolve;});
    if (url === endpoint + "/nouvelle") return Promise.resolve(saved("nouvelle", 4, [{role: "user", text: "Sujet actuel"}]));
    return Promise.resolve({items: []});
  });
  const hook = renderHook(() => useHarness([]));
  await flush();
  let oldSelection: Promise<void> = Promise.resolve();
  act(() => {oldSelection = hook.result.current.history.select("ancienne");});
  await flush();
  await act(async () => {await hook.result.current.history.select("nouvelle");});
  await act(async () => {resolveOld(saved("ancienne", 2, [{role: "user", text: "Sujet périmé"}])); await oldSelection;});
  expect(hook.result.current.history.threadId).toBe("nouvelle");
  expect(hook.result.current.messages).toEqual([{role: "user", text: "Sujet actuel"}]);
  expect(hook.result.current.history.loading).toBe(false);
  expect(mutations()).toHaveLength(0);
});

it("attend la fin du rendu progressif avant d'enregistrer la réponse complète", async () => {
  vi.mocked(request).mockImplementation((_url, init) => !init?.method ? Promise.resolve({items: []})
    : Promise.resolve(saved("thread-a", 1, JSON.parse(String(init.body)).messages)));
  const hook = renderHook(() => useHarness(initial, true));
  await flush();
  act(() => hook.result.current.setMessages([...initial, {role: "assistant", text: "Réponse partielle"}]));
  await flush();
  expect(mutations()).toHaveLength(0);
  const completed: AssistantMessage[] = [...initial, {role: "assistant", text: "Réponse complète avec sa source."}];
  act(() => {hook.result.current.setMessages(completed); hook.result.current.setPaused(false);});
  await flush();
  expect(mutations()).toHaveLength(1);
  expect(JSON.parse(String(mutations()[0][1]?.body)).messages).toEqual(completed);
});
