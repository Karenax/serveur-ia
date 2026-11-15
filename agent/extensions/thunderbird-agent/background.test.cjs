const { test } = require("node:test");
const assert = require("node:assert/strict");
const vm = require("node:vm");
const fs = require("node:fs");
const path = require("node:path");
const { setImmediate } = require("node:timers/promises");

async function harness(job, initial = {}, configuration, pairing = { token: "secret" }, configureError) {
  const state = { ...initial }, calls = [], saved = [], lists = [], alarms = [];
  const noop = { addListener() {} };
  const accounts = [{ id: "account1", type: "imap", name: "Mail", rootFolder: { id: "root" },
    identities: [{ id: "identity1", email: "moi@example.com", name: "Moi" }] }];
  const messenger = {
    accounts: { list: async () => accounts },
    folders: { getSubFolders: async () => [{ id: "inbox", type: "inbox", name: "INBOX", path: "/INBOX", specialUse: ["inbox"] }] },
    messages: { onNewMailReceived: noop, list: async (id) => {lists.push(id);return { messages: [], id: null };},
      saveMessage: async (details, options) => { saved.push({ details, options }); return { messages: [{ id: 42 }] }; } },
    compose: {}, tabs: {},
    storage: { local: {
      get: async keys => Object.fromEntries((Array.isArray(keys) ? keys : [keys]).filter(k => k in state).map(k => [k, state[k]])),
      set: async value => Object.assign(state, value), remove: async key => { delete state[key]; },
    } },
    runtime: { getURL: value => "extension://" + value, getManifest: () => ({ version: "0.1.0" }), onMessage: noop },
    alarms: { onAlarm: noop, create: async (name, options) => { alarms.push({name,options}); } },
    browserAction: { onClicked: noop, setBadgeText: async () => {} },
  };
  const context = vm.createContext({ messenger, File, FormData, Uint8Array, AbortController, atob,
    setTimeout: () => 1, clearTimeout: () => {}, console,
    fetch: async (url, init) => {
      if (url.startsWith("extension://")) return { json: async () => pairing };
      const payload = JSON.parse(init.body); calls.push({ url, payload, redirect: init.redirect });
      assert.equal(init.headers["X-Agent-Thunderbird-Token"], "secret");
      if (url.endsWith("/configure") && configureError) {
        return { ok: false, status: 403, json: async () => ({ detail: configureError }) };
      }
      const result = url.endsWith("/jobs/claim") ? { job } : { status: "ok", mail_config: configuration };
      if (url.endsWith("/jobs/claim")) job = null;
      return { ok: true, json: async () => result };
    },
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, "core.js"), "utf8"), context);
  vm.runInContext(fs.readFileSync(path.join(__dirname, "background.js"), "utf8"), context);
  for (let i = 0; i < 10; i++) await setImmediate();
  return { state, calls, saved, context, lists, alarms };
}

test("le paquet Kiara utilise le relais local sans suivre les redirections", async () => {
  const result = await harness(null, {}, undefined, { token: "secret", kiara: true });
  assert.ok(result.calls.length > 0);
  assert.ok(result.calls.every(call => call.url.startsWith("http://127.0.0.1:17841/v1/thunderbird/bridge/")));
  assert.ok(result.calls.every(call => call.redirect === "error"));
});

test("le client annonce les dossiers et crée un vrai brouillon API, jamais un envoi", async () => {
  const result = await harness({ id: "job1", kind: "draft", payload: { identity_id: "identity1",
    to: ["client@example.com"], cc: [], subject: "Devis", body: "Bonjour", attachments: [], open_window: false } });
  assert.equal(result.saved.length, 1);
  assert.equal(result.saved[0].options.mode, "draft");
  assert.equal(result.saved[0].details.identityId, "identity1");
  assert.ok(result.calls.some(c => c.url.endsWith("/jobs/job1/result") && c.payload.status === "done"));
  assert.equal(result.state.connection.connected, true);
  assert.equal(result.state.jobJournal, undefined);
  await vm.runInContext("tick()", result.context);
  assert.equal(result.saved.length, 1);
});

test("un journal interrompu est signalé incertain sans rejouer la création", async () => {
  const result = await harness(null, { jobJournal: { id: "interrupted" } });
  assert.ok(result.calls.some(c => c.url.endsWith("/jobs/interrupted/result") && c.payload.status === "uncertain"));
  assert.equal(result.saved.length, 0);
});

test("le choix dossier EML suspend les listes Thunderbird",async()=>{
  const result=await harness(null,{}, {source:"folder",auto_scan:true,folder_ids:["inbox"],interval_minutes:12});
  assert.equal(result.lists.length,0);
  assert.ok(result.alarms.some(a=>a.name==="agent-sync"&&a.options.periodInMinutes===12));
});

test("auto désactivé conserve la synchronisation manuelle durable",async()=>{
  const control={source:"thunderbird",auto_scan:false,folder_ids:["inbox"],interval_minutes:7};
  const idle=await harness(null,{},control);
  assert.equal(idle.lists.length,0);
  const manual=await harness({id:"manual",kind:"sync",payload:{folder_ids:["inbox"]}}, {},control);
  assert.deepEqual(manual.lists,["inbox"]);
  assert.ok(manual.calls.some(c=>c.url.endsWith("/jobs/manual/result")&&c.payload.status==="done"));
});

test("Agent impose sa sélection sans effacer le catalogue de comptes",async()=>{
  const result=await harness(null,{folders:["old"]},{source:"thunderbird",auto_scan:true,folder_ids:["inbox"],interval_minutes:5});
  assert.equal(JSON.stringify(result.state.folders),'["inbox"]');
  assert.deepEqual(result.lists,["inbox"]);
  const reports=result.calls.filter(c=>c.url.endsWith("/heartbeat"));
  assert.equal(reports.at(-1).payload.sync.total,0);
  assert.equal(reports.at(-1).payload.sync.processed,0);
});

test("la synchronisation manuelle rapporte le refus de Kiara", async () => {
  const detail = "Appareil Thunderbird non autorisé.";
  const denied = await harness(null, {}, undefined, { token: "secret", kiara: true }, detail);
  const result = await vm.runInContext('requestManualSync(["inbox"])', denied.context);
  assert.equal(result.accepted, false);
  assert.equal(result.detail, detail);
  assert.equal(denied.state.connection.connected, false);

  const allowed = await harness(null);
  assert.equal((await vm.runInContext('requestManualSync(["inbox"])', allowed.context)).accepted, true);
});
