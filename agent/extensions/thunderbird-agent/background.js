/* API Thunderbird officielle ; aucune lecture de MBOX ni envoi automatique. */
let base = "http://127.0.0.1:8001/v1/thunderbird";
let token = "";
let active = false;
let syncRequested = false;
let syncInfo = { imported: 0, duplicates: 0, errors: 0, running: false };
let mailControl = { source: "thunderbird", auto_scan: true, folder_ids: null, interval_minutes: 5 };
let alarmInterval = 5;
async function configureFromAgent(result) {
  if (!result.mail_config) return;
  mailControl = result.mail_config;
  if (Array.isArray(mailControl.folder_ids)) await messenger.storage.local.set({ folders: mailControl.folder_ids });
  const interval = Math.max(1, Number(mailControl.interval_minutes) || 5);
  if (interval !== alarmInterval) {
    await messenger.alarms.create("agent-sync", { periodInMinutes: interval });
    alarmInterval = interval;
  }
}
const api = async (path, body) => {
  const headers = { "X-Agent-Thunderbird-Token": token };
  if (body && !(body instanceof FormData)) headers["Content-Type"] = "application/json";
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 60000);
  try {
    const response = await fetch(base + "/bridge" + path, { method: "POST", headers, redirect: "error",
      body: body instanceof FormData ? body : JSON.stringify(body || {}), signal: controller.signal });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || `Agent : HTTP ${response.status}`);
    return result;
  } finally { clearTimeout(timer); }
};

async function catalog() {
  const accounts = await messenger.accounts.list(true);
  const folders = [];
  const visit = (account, folder) => {
    if (!AgentThunderbird.allowedFolder(folder)) return;
    if (folder.id && !folder.isRoot) folders.push({ id: folder.id, account_id: account.id, name: folder.name,
      path: folder.path, type: folder.type, specialUse: folder.specialUse || [] });
    for (const child of folder.subFolders || []) visit(account, child);
  };
  for (const account of accounts) {
    if (!["imap", "pop3", "none"].includes(account.type)) continue;
    if (account.rootFolder) {
      const children = await messenger.folders.getSubFolders(account.rootFolder.id, true);
      for (const folder of children) visit(account, folder);
    } else for (const folder of account.folders || []) visit(account, folder);
  }
  return { accounts: accounts.map(a => ({ id: a.id, name: a.name, type: a.type,
    identities: (a.identities || []).map(i => ({ id: i.id, email: i.email, name: i.name })) })), folders };
}

async function sync(folderIds) {
  if (mailControl.source !== "thunderbird") return { paused: true };
  const state = await messenger.storage.local.get(["folders", "transferred"]);
  const selected = Array.isArray(folderIds) ? folderIds : state.folders || [];
  if (Array.isArray(folderIds)) await messenger.storage.local.set({ folders: folderIds });
  const known = state.transferred || {};
  const data = await catalog();
  syncInfo = { imported: 0, duplicates: 0, errors: 0, running: true, folder_ids: selected, processed: 0, total: 0 };
  let scanned = 0;
  const candidates = [];
  for (const folder of data.folders.filter(f => selected.includes(f.id))) {
    let page = await messenger.messages.list(folder.id);
    while (page) {
      for (const message of page.messages) {
        if (!AgentThunderbird.eligible(message)) continue;
        const key = AgentThunderbird.messageKey(folder.account_id, folder.id, message);
        if (known[key]) continue;
        candidates.push({ folder, message, key });
      }
      page = page.id ? await messenger.messages.continueList(page.id) : null;
    }
  }
  syncInfo.total = candidates.length;
  await configureFromAgent(await api("/heartbeat", { version: messenger.runtime.getManifest().version, ...data, sync: syncInfo }));
  for (const { folder, message, key } of candidates) {
        if (mailControl.source !== "thunderbird") break;
        if (Array.isArray(mailControl.folder_ids) && !mailControl.folder_ids.includes(folder.id)) continue;
        try {
          const file = await messenger.messages.getRaw(message.id, { data_format: "File", decrypt: false });
          const form = new FormData();
          form.append("file", file, "thunderbird.eml"); form.append("account_id", folder.account_id); form.append("folder_id", folder.id);
          const result = await api("/import", form);
          if (result.status === "duplicate") syncInfo.duplicates++; else syncInfo.imported++;
          known[key] = result.source_id;
          syncInfo.processed++;
          await messenger.storage.local.set({ transferred: known });
        } catch (error) {
          syncInfo.errors++; syncInfo.last_error = String(error.message || error);
          // Une coupure Agent ne déclenche pas des milliers de tentatives.
          await messenger.storage.local.set({ sync: syncInfo });
          throw error;
        }
        scanned++;
        if (scanned % 10 === 0) await configureFromAgent(await api("/heartbeat", { version: messenger.runtime.getManifest().version, ...data, sync: syncInfo }));
        if (scanned >= 100) {
          syncInfo.running = false; syncInfo.more_pending = scanned < candidates.length;
          await messenger.storage.local.set({ sync: syncInfo });
          return syncInfo;
        }
  }
  syncInfo.running = false; syncInfo.more_pending = false;
  await messenger.storage.local.set({ sync: syncInfo });
  return syncInfo;
}

async function createDraft(payload) {
  const data = await catalog();
  const account = data.accounts.find(a => a.identities.some(i => i.id === payload.identity_id));
  if (!account) throw new Error("Identité d’expédition introuvable dans Thunderbird");
  const attachments = (payload.attachments || []).map(a => {
    const bytes = Uint8Array.from(atob(a.content_base64), c => c.charCodeAt(0));
    return { file: new File([bytes], a.name, { type: a.content_type }), name: a.name };
  });
  const details = { identityId: payload.identity_id, to: payload.to, cc: payload.cc,
    subject: payload.subject, plainTextBody: payload.body, isPlainText: true, attachments };
  if (payload.reply_message_id) {
    let list = await messenger.messages.query({ accountId: account.id, headerMessageId: payload.reply_message_id });
    let original;
    while (list) {
      original ||= list.messages[0];
      if (original) { if (list.id) await messenger.messages.abortList(list.id); break; }
      list = list.id ? await messenger.messages.continueList(list.id) : null;
    }
    if (!original) throw new Error("Mail d’origine non retrouvé dans Thunderbird ; aucun brouillon créé");
    const tab = await messenger.compose.beginReply(original.id, "replyToSender", details);
    if (payload.open_window) return { opened: true, tab_id: tab.id };
    const result = await messenger.compose.saveMessage(tab.id, { mode: "draft" });
    await messenger.tabs.remove(tab.id);
    return { draft_ids: result.messages.map(m => m.id) };
  }
  if (payload.open_window) {
    const tab = await messenger.compose.beginNew(details);
    return { opened: true, tab_id: tab.id };
  }
  const result = await messenger.messages.saveMessage(details, { mode: "draft" });
  return { draft_ids: result.messages.map(m => m.id) };
}

async function tick() {
  if (active || !token) return;
  active = true;
  try {
    const journal = (await messenger.storage.local.get("jobJournal")).jobJournal;
    if (journal) {
      await api(`/jobs/${journal.id}/result`, journal.result || { status: "uncertain", result: { error: "Thunderbird a été interrompu pendant cette commande ; vérifier les brouillons avant de recommencer." } });
      await messenger.storage.local.remove("jobJournal");
    }
    const data = await catalog();
    const selected = (await messenger.storage.local.get("folders")).folders || [];
    await configureFromAgent(await api("/heartbeat", { version: messenger.runtime.getManifest().version, ...data, sync: { ...syncInfo, folder_ids: selected } }));
    const { job } = await api("/jobs/claim");
    if (job) {
      await messenger.storage.local.set({ jobJournal: { id: job.id } });
      let result;
      try {
        result = { status: "done", result: job.kind === "draft" ? await createDraft(job.payload) : await sync(job.payload.folder_ids) };
      } catch (error) { result = { status: "failed", result: { error: String(error.message || error) } }; }
      await messenger.storage.local.set({ jobJournal: { id: job.id, result } });
      await api(`/jobs/${job.id}/result`, result);
      await messenger.storage.local.remove("jobJournal");
    } else if (syncRequested) { syncRequested = false; if (mailControl.source === "thunderbird" && mailControl.auto_scan) await sync(); }
    await configureFromAgent(await api("/heartbeat", { version: messenger.runtime.getManifest().version, ...data, sync: { ...syncInfo, folder_ids: (await messenger.storage.local.get("folders")).folders || [] } }));
    await messenger.storage.local.set({ connection: { connected: true, last_seen: new Date().toISOString() } });
    await messenger.browserAction.setBadgeText({ text: "" });
  } catch (error) {
    syncInfo.running = false;
    await messenger.storage.local.set({ connection: { connected: false, error: String(error.message || error) } });
    await messenger.browserAction.setBadgeText({ text: "!" });
  } finally { active = false; }
}

messenger.alarms.onAlarm.addListener(alarm => {
  if (alarm.name === "agent-sync") syncRequested = true;
  void tick();
});
messenger.messages.onNewMailReceived.addListener(() => { syncRequested = true; void tick(); }, true);
async function requestManualSync(folders) {
  try {
    const selected = folders || (await messenger.storage.local.get("folders")).folders || [];
    await api("/configure", { folder_ids: selected });
    await tick();
    return { accepted: true };
  } catch (error) {
    const detail = String(error.message || error);
    await messenger.storage.local.set({ connection: { connected: false, error: detail } });
    await messenger.browserAction.setBadgeText({ text: "!" });
    return { accepted: false, detail };
  }
}
messenger.browserAction.onClicked.addListener(() => { void requestManualSync(); });
messenger.runtime.onMessage.addListener(async message => {
  if (message.action === "sync") return requestManualSync();
  if (message.action === "configure") {
    return requestManualSync(message.folders || []);
  }
});
(async () => {
  const config = await (await fetch(messenger.runtime.getURL("pairing.json"))).json();
  if (config.kiara === true) base = "http://127.0.0.1:17841/v1/thunderbird";
  token = config.token;
  const state = await messenger.storage.local.get("folders");
  if (!state.folders) {
    const data = await catalog();
    const inboxes = data.folders.filter(f => f.type === "inbox" || f.specialUse.includes("inbox")).map(f => f.id);
    await messenger.storage.local.set({ folders: inboxes });
  }
  syncRequested = true;
  await messenger.alarms.create("agent-sync", { periodInMinutes: 5 });
  await messenger.alarms.create("agent-heartbeat", { periodInMinutes: .5 });
  await tick();
})();
