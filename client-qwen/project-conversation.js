/* The project assistant uses the Conversations composer and the existing thread API. */
(() => {
  const threadPath = '/api/v1/workspace/assistant-threads';
  const composer = $('composer'), prompt = $('prompt');
  const personalPlaceholder = prompt.placeholder;
  const workspace = document.querySelector('[data-view="chat"]');
  const controls = wsElement('div', undefined, 'project-conversation-controls');
  const shellToolbar = workspace.querySelector('.conversation-toolbar');
  const region = wsElement('section', undefined, 'project-conversation-messages');
  region.setAttribute('aria-label', 'Conversation de projet');
  region.setAttribute('aria-live', 'polite');
  const toggle = $('project-conversation-toggle') || wsElement('button', 'Assistant de projet', 'secondary');
  const project = wsElement('select'), saved = wsElement('select');
  const temporary = wsElement('input'); temporary.type = 'checkbox'; temporary.checked = true;
  const includeEvidence = wsElement('input'); includeEvidence.type = 'checkbox'; includeEvidence.checked = true;
  const status = wsElement('span'); status.setAttribute('role', 'status');
  const newThread = wsElement('button', 'Nouvel échange', 'secondary');
  const retrySave = wsElement('button', 'Réessayer l’enregistrement', 'secondary');
  const saveCopy = wsElement('button', 'Enregistrer une copie', 'secondary');
  const reopenSaved = wsElement('button', 'Relire la version enregistrée', 'secondary');
  const prepareProject = wsElement('button', 'Relier les sources du projet', 'secondary');
  for (const button of [toggle, newThread, retrySave, saveCopy, reopenSaved, prepareProject]) button.type = 'button';
  function label(text, input) {
    const element = wsElement('label', text); element.append(input); return element;
  }
  const options = wsElement('details', undefined, 'menu project-conversation-options');
  const optionsSummary = wsElement('summary', '···');
  optionsSummary.setAttribute('aria-label', "Options de l'assistant de projet");
  optionsSummary.title = "Options de l'assistant de projet";
  const optionsBody = wsElement('div', undefined, 'menu-body');
  options.append(optionsSummary, optionsBody);
  optionsBody.append(label('Inclure les sources à confirmer ', includeEvidence));
  const recovery = wsElement('div', undefined, 'project-conversation-recovery');
  recovery.append(prepareProject, retrySave, saveCopy, reopenSaved);
  controls.append(label('Projet ', project), newThread, label('Éphémère ', temporary),
    label('Historique de projet ', saved), options, status, recovery);
  if (shellToolbar) {
    shellToolbar.after(controls);
  } else {
    const toolbar = wsElement('div', undefined, 'project-conversation-switch');
    toolbar.append(toggle);
    workspace.prepend(toolbar, controls);
  }
  $('messages').after(region);
  let active = false, opening = false, pending = false, controller = null, thread = null;
  const fresh = ephemeral => ({ephemeral, id:null, revision:0, project:project.value, messages:[], draft:'', unsaved:false});
  const drafts = new Map();
  window.kiaraProjectConversation = {
    get active(){return active;},
    async openWindowsSource(sourceId, excerpt) {
      await api('/client/project-session', {});
      return openSource({source_id:sourceId,excerpt});
    }
  };
  function draftKey(value) {
    return value.id ? 'project-thread:'+value.id : 'project-draft:'+value.project;
  }
  function rememberDraft() {
    if (!active || !thread) return;
    thread.draft = prompt.value;
    if (thread.ephemeral) drafts.set(thread.project, thread.draft);
    else uiComposerRemember(draftKey(thread), thread.draft);
  }
  prompt.addEventListener('input', rememberDraft);

  async function request(path, options = {}) {
    const headers = new Headers(options.headers);
    if (platformCapabilities.platform === 'android') headers.set('Authorization', 'Bearer '+config.key);
    const response = await fetch(path, {credentials:'same-origin', ...options, headers});
    if (!response.ok) {
      const info = await response.json().catch(() => ({}));
      const detail = typeof info.detail === 'string' ? info.detail : info.error?.message;
      throw Object.assign(new Error(detail || 'Le service de projets ne répond pas.'), {status:response.status});
    }
    return response;
  }
  function validSourceId(id) {
    return typeof id === 'string' && /^[A-Za-z0-9_-]{1,128}$/.test(id);
  }
  async function openSource(citation) {
    if (!validSourceId(citation.source_id)) {
      throw new Error('Référence de source invalide.');
    }
    const title = wsElement('h2', 'Source du projet'); title.id = 'fred-source-title';
    const content = wsElement('div');
    const close = wsButton('Fermer', () => wsSourceDialog.close());
    const controller = new AbortController();
    wsSourceDialog.addEventListener('close', () => controller.abort(), {once:true});
    wsSourceDialog.replaceChildren(title, content, close);
    wsSourceDialog.showModal();
    if (citation.excerpt) content.append(wsElement('blockquote', citation.excerpt));
    const state = wsElement('p', 'Chargement de la source…', 'muted');
    state.setAttribute('role', 'status'); content.append(state);
    try {
      const source = await (await request('/v1/sources/'+encodeURIComponent(citation.source_id), {
        signal:controller.signal
      })).json();
      if (controller.signal.aborted) return;
      title.textContent = source.metadata?.subject || source.metadata?.filename || 'Source du projet';
      const extracts = (source.artifacts || []).filter(item => typeof item.text === 'string' && item.text.trim());
      state.textContent = extracts.length ? '' : 'Aucun texte extrait supplémentaire.';
      for (const extract of extracts) content.append(wsElement('pre', extract.text, 'fred-source-passage'));
      const sourceId = encodeURIComponent(citation.source_id);
      const originalPath = source.metadata?.note_version_id
        ? '/api/v1/workspace/sources/'+sourceId+'/original'
        : '/v1/sources/'+sourceId+'/raw';
      const filename = source.metadata?.filename || 'source-'+citation.source_id;
      const download = platformCapabilities.platform === 'android'
        ? wsButton('Télécharger l’original', () => androidRequireBridge().downloadProjectOriginal(originalPath, filename))
        : wsElement('a', 'Télécharger l’original');
      if (download instanceof HTMLAnchorElement) {
        download.href = originalPath;
        download.download = filename;
      }
      content.append(download);
    } catch (failure) {
      if (!controller.signal.aborted) state.textContent = failure.message;
    }
  }
  const json = (method, value, signal) => ({method, signal, headers:{'Content-Type':'application/json'}, body:JSON.stringify(value)});
  let threadListVersion = 0;
  async function refreshThreads() {
    const version = ++threadListVersion;
    const scope = project.value && !project.value.startsWith('erp:') ? '&project_id='+encodeURIComponent(project.value) : '';
    const result = await (await request(threadPath+'?limit=100'+scope)).json();
    if (version !== threadListVersion) return;
    saved.replaceChildren(new Option('Choisir…', ''));
    for (const item of result.items) saved.add(new Option(item.title, item.id));
    saved.value = thread.id || '';
  }
  function render() {
    region.replaceChildren();
    if (!thread.messages.length) region.append(wsElement('p', 'Posez une question sur le projet.', 'muted'));
    for (const message of thread.messages) {
      const {article} = draw({role:message.role,content:message.text},region);
      if (message.citations?.length) {
        const evidence = wsElement('details');
        evidence.append(wsElement('summary', 'Sources'));
        for (const source of message.citations) {
          const item = wsElement('p', source.excerpt || source.project_code || 'Source du projet');
          if (validSourceId(source.source_id)) {
            if (['android','windows'].includes(platformCapabilities.platform)) {
              item.append(' ', wsButton('Voir la source', () => openSource(source)));
            } else {
              const link = wsElement('a', 'Voir la source');
              link.href = (config.web_prefix || '') + '/app/sources?source='+encodeURIComponent(source.source_id);
              link.target = '_blank'; link.rel = 'noopener';
              item.append(' ', link);
            }
          }
          evidence.append(item);
        }
        article.append(evidence);
      }
    }
    if (thread.warnings?.length) {
      const notice = wsElement('details', undefined, 'muted');
      notice.append(wsElement('summary', 'Recherche de sources partielle'));
      const list = wsElement('ul');
      for (const warning of thread.warnings) list.append(wsElement('li', warning));
      notice.append(list); region.append(notice);
    }
    if (thread.partial) {
      const interrupted = draw({role:'assistant',content:thread.partial,interrupted:true},region);
      interrupted.article.setAttribute('aria-label', 'Réponse interrompue');
    }
    region.scrollTop = region.scrollHeight;
  }
  function update() {
    controls.hidden = region.hidden = !active;
    toggle.setAttribute('aria-pressed', String(active));
    toggle.textContent = active ? 'Conversations personnelles' : 'Assistant de projet';
    const draftsPending = window.kiaraComposerDraftsReady?.() === false || !historyReady || historyBlocked;
    toggle.disabled = (!active && !projectAssistantAvailable()) || draftsPending || opening || pending || busy || (active && thread.unsaved);
    if (!active) return;
    project.disabled = saved.disabled = temporary.disabled = includeEvidence.disabled = newThread.disabled = pending || thread.unsaved;
    retrySave.hidden = !thread.unsaved;
    retrySave.disabled = pending;
    saveCopy.hidden = !thread.conflict; saveCopy.disabled = pending;
    reopenSaved.hidden = !thread.conflict || !thread.id; reopenSaved.disabled = pending;
    $('send').hidden = pending;
    prepareProject.hidden = !project.value.startsWith('erp:');
    prepareProject.disabled = pending || thread.unsaved;
    recovery.hidden = prepareProject.hidden && retrySave.hidden && saveCopy.hidden && reopenSaved.hidden;
    $('send').disabled = draftsPending || pending || thread.unsaved || project.selectedIndex < 0 || !prepareProject.hidden;
    $('cancel').hidden = !controller;
    $('cancel').disabled = !controller;
    prompt.readOnly = draftsPending || pending;
  }
  const originalButtons = buttons;
  buttons = function() { originalButtons(); update(); };
  function setThread(value) {
    thread = value; project.value = thread.project; temporary.checked = thread.ephemeral;
    saved.value = [...saved.options].some(option => option.value === thread.id) ? thread.id : '';
    document.body.dataset.projectEphemeral = String(thread.ephemeral);
    prompt.value = thread.draft || (thread.ephemeral ? drafts.get(thread.project) : uiComposerDrafts[draftKey(thread)]) || '';
    status.textContent = thread.project.startsWith('erp:') ? 'Reliez les sources pour interroger ce projet.' :
      thread.ephemeral ? 'Échange conservé en mémoire pour cette session.' :
      thread.id ? 'Conversation enregistrée dans le projet.' : 'L’échange sera enregistré dans le projet.';
    render(); update();
  }
  async function open(erpId) {
    if (active || busy || opening || conversationLocked()) return;
    opening = true; update();
    try {
      await uiPersistPreferences();
      if (!['android','web'].includes(platformCapabilities.platform)) await api('/client/project-session', {});
      const [catalogue, knowledge] = await Promise.all([
        request('/api/v1/project-catalogue').then(response => response.json()),
        request('/api/v1/brain/projects').then(response => response.json()).catch(failure => {
          if (failure.status === 404) return [];
          throw failure;
        })
      ]);
      const targets = new Map(catalogue.map(item => [item.id, item.brain_project_id || 'erp:'+item.id]));
      const target = erpId ? targets.get(erpId) : undefined;
      if (erpId && !target) throw new Error('Ce projet est indisponible. Vérifiez votre accès au projet.');
      project.replaceChildren(new Option('Tous mes projets',''));
      for (const item of catalogue) project.add(new Option(item.title,targets.get(item.id)));
      const represented = new Set(targets.values());
      for (const item of knowledge) if (!represented.has(item.id)) project.add(new Option(item.name,item.id));
      if (target) project.value = target;
      active = true; document.body.dataset.projectConversation = 'true';
      prompt.placeholder = 'Posez une question sur le projet…';
      setThread(thread && (!target || thread.project === target) ? thread : fresh(true));
      showView('chat');
      await refreshThreads();
      prompt.focus();
    } catch (failure) { error(failure); }
    finally { opening = false; update(); }
    return active;
  }
  function leave() {
    if (!active) return true;
    if (pending || thread.unsaved) return false;
    rememberDraft(); active = false; delete document.body.dataset.projectConversation;
    delete document.body.dataset.projectEphemeral;
    prompt.placeholder = personalPlaceholder;
    prompt.value = uiComposerDrafts[currentId] || '';
    uiComposerId = currentId;
    error(''); buttons(); prompt.focus();
    return true;
  }
  toggle.onclick = () => {
    if (active) return leave();
    const linkedProject = projectFromHash();
    if (linkedProject !== undefined) void openLinkedProject(linkedProject);
    else void open();
  };
  const projectChat = $('ws-project-chat');
  const openProjectChat = projectChat.onclick;
  projectChat.onclick = event => {
    if (wsIsAgentProject(ws.project) && projectAssistantAvailable()) {
      return wsTry(async () => { await wsFlush(); await open(ws.project); });
    }
    return openProjectChat.call(projectChat,event);
  };
  onViewChange({before: name => name === 'chat' || leave()});
  for (const selector of ['#new', '#conversation-list', '#conversations', '#client-navigation', '.sidebar-settings']) {
    document.querySelector(selector)?.addEventListener('click', event => {
      if (!leave()) { event.preventDefault(); event.stopImmediatePropagation(); }
    }, true);
  }
  project.onchange = () => {
    const id = project.value;
    rememberDraft(); setThread({...fresh(thread.ephemeral), project:id});
    void refreshThreads().catch(error);
  };
  prepareProject.onclick = async () => {
    const id = project.value.slice(4), option = project.selectedOptions[0];
    pending = true; update(); error('');
    try {
      const link = await (await request('/api/v1/projects/'+encodeURIComponent(id)+'/brain/ensure', json('POST', {}))).json();
      if (!link.linked || !link.brain_project_id) throw new Error('Impossible de relier les sources du projet.');
      const previous = draftKey(thread), projectId = link.brain_project_id, text = prompt.value;
      if (thread.ephemeral) drafts.delete(thread.project);
      else uiComposerRemember(previous, '');
      const duplicate = [...project.options].find(item => item.value === projectId);
      if (duplicate) duplicate.remove();
      option.value = projectId;
      setThread({...fresh(thread.ephemeral), project:projectId, draft:text});
      rememberDraft();
      await refreshThreads();
    } catch (failure) { error(failure); }
    finally { pending = false; update(); prompt.focus(); }
  };
  temporary.onchange = () => { rememberDraft(); setThread(fresh(temporary.checked)); };
  newThread.onclick = () => { rememberDraft(); setThread(fresh(thread.ephemeral)); saved.value = ''; prompt.focus(); };
  async function loadThread(id) {
    rememberDraft(); pending = true; update(); error('');
    try {
      const record = await (await request(threadPath+'/'+encodeURIComponent(id))).json();
      setThread({...fresh(false), id:record.id, project:record.project_id || '', revision:record.revision, messages:record.messages});
    } catch (failure) { error(failure); }
    finally { pending = false; update(); }
  }
  saved.onchange = () => { if (saved.value) void loadThread(saved.value); };
  reopenSaved.onclick = () => {
    if (thread.id && confirm('Relire la version enregistrée et abandonner les réponses en attente d’enregistrement ?')) {
      void loadThread(thread.id);
    }
  };

  async function persist() {
    if (thread.ephemeral) return;
    const previous = draftKey(thread);
    const payload = {title:(thread.messages.find(item => item.role === 'user')?.text || 'Conversation').slice(0,100),
      messages:thread.messages};
    const response = thread.id
      ? await request(threadPath+'/'+encodeURIComponent(thread.id), json('PUT', {...payload, expected_revision:thread.revision}))
      : await request(threadPath, json('POST', {...payload, project_id:thread.project || null}));
    const record = await response.json();
    thread.id = record.id; thread.revision = record.revision; thread.unsaved = false; thread.conflict = false;
    uiComposerRemember(previous, '');
    void refreshThreads().catch(error);
  }
  async function retryPersistence(copy = false) {
    pending = true; update(); error('');
    const original = thread.id;
    if (copy) thread.id = null;
    try { await persist(); }
    catch (failure) { thread.id = original; thread.conflict ||= failure.status === 409; error(failure); }
    finally { pending = false; update(); }
  }
  retrySave.onclick = () => retryPersistence();
  saveCopy.onclick = () => retryPersistence(true);

  async function answer(query, past, signal, updateReply) {
    const history = past.filter(item => item.text).slice(-12)
      .map(item => ({role:item.role,content:item.text.slice(0,4000)}));
    while (history.reduce((sum,item) => sum+item.content.length,0)>12000) history.shift();
    const response = await request('/v1/projects/chat/stream', json('POST', {
      query, project_id:thread.project || null, include_evidence:includeEvidence.checked, history
    },signal));
    if (!response.body) throw new Error('Le flux de réponse est indisponible.');
    const reader = response.body.getReader(), decoder = new TextDecoder();
    let buffer = '', text = '', citations = [], warnings = [], finished = false;
    try {
      for (;;) {
        const {value, done} = await reader.read();
        buffer += done ? decoder.decode() : decoder.decode(value,{stream:true});
        let boundary;
        while ((boundary = buffer.match(/\r?\n\r?\n/))) {
          const lines = buffer.slice(0,boundary.index).split(/\r?\n/);
          buffer = buffer.slice(boundary.index+boundary[0].length);
          const payload = lines.filter(line => line.startsWith('data:')).map(line => line.slice(5).trimStart());
          if (!payload.length) continue;
          const event = lines.find(line => line.startsWith('event:'))?.slice(6).trim();
          const value = JSON.parse(payload.join('\n'));
          if (event === 'error') throw new Error(value.message || 'Réponse interrompue.');
          if (event === 'delta') text += value.text || '';
          if (event === 'metadata' || event === 'done') {
            citations = value.citations || citations;
            if (Array.isArray(value.warnings)) warnings = value.warnings.filter(item => typeof item === 'string' && item);
          }
          if (event === 'done') { finished = true; text = value.answer; }
          updateReply({role:'assistant',text,citations});
        }
        if (done) break;
      }
      if (!finished) throw new Error('La réponse a été interrompue.');
      return warnings;
    } finally { await reader.cancel().catch(() => {}); reader.releaseLock(); }
  }
  composer.addEventListener('submit', async event => {
    if (!active) return;
    event.preventDefault(); event.stopImmediatePropagation();
    const query = prompt.value.trim();
    if (project.selectedIndex < 0 || project.value.startsWith('erp:') || query.length < 2 || pending || thread.unsaved) return;
    const past = thread.messages;
    thread.partial = '';
    pending = true; controller = new AbortController(); error(''); update();
    try {
      thread.warnings = await answer(query,past,controller.signal,reply => {
        thread.messages = [...past,{role:'user',text:query},reply]; render();
      });
      render();
      prompt.value = ''; rememberDraft();
      if (!thread.ephemeral) { thread.unsaved = true; await persist(); }
      status.textContent = thread.ephemeral ? 'Échange conservé en mémoire pour cette session.' : 'Conversation enregistrée dans le projet.';
    } catch (failure) {
      if (!thread.unsaved) {
        thread.partial = thread.messages.length > past.length ? thread.messages.at(-1)?.text : '';
        thread.messages = past; render();
      }
      if (thread.unsaved && failure.status === 409) thread.conflict = true;
      if (failure.name === 'AbortError') status.textContent = 'Réponse arrêtée. Vous pouvez renvoyer la question.';
      else error(failure);
    } finally { pending = false; controller = null; update(); prompt.focus(); }
  }, true);
  composer.addEventListener('paste', event => {
    if (active && [...event.clipboardData?.files || []].length) {
      event.preventDefault(); event.stopImmediatePropagation();
      error('Utilisez les documents du projet comme sources.');
    }
  },true);
  $('cancel').addEventListener('click', event => {
    if (!active) return;
    event.preventDefault(); event.stopImmediatePropagation(); controller?.abort();
  },true);
  const checkPendingEdits = window.uiCheckPendingEdits;
  window.uiCheckPendingEdits = () => {
    checkPendingEdits?.();
    if (pending) throw new Error('Attendez la fin de l’échange de projet.');
    if (thread?.unsaved) throw new Error('Enregistrez l’échange de projet avant de fermer.');
  };
  window.addEventListener('beforeunload', event => {
    if (!pending && !thread?.unsaved && !(active && thread?.ephemeral && prompt.value) && ![...drafts.values()].some(Boolean)) return;
    event.preventDefault(); event.returnValue = '';
  });
  function projectFromHash() {
    const match = /^#projet=(.*)$/.exec(location.hash);
    if (!match) return undefined;
    try { return decodeURIComponent(match[1]); }
    catch { return undefined; }
  }
  let requestedProject = projectFromHash();
  window.addEventListener('hashchange', () => {
    requestedProject = projectFromHash();
    openRequestedProject();
  });
  if (!shellToolbar) toggle.hidden = true;
  function projectAssistantAvailable() {
    return ws.data?.project_catalogue?.state === 'ready';
  }
  const previousDraw = wsDrawProjects;
  wsDrawProjects = function() {
    previousDraw();
    if (!shellToolbar) toggle.hidden = !projectAssistantAvailable();
    update();
    openRequestedProject();
  };
  function openRequestedProject() {
    if (requestedProject !== undefined && !active && !opening && projectAssistantAvailable() && !conversationLocked()) {
      const id = requestedProject;
      requestedProject = undefined;
      void openLinkedProject(id);
    }
  }
  async function openLinkedProject(id) {
    const hash = location.hash;
    if (await open(id) && location.hash === hash) {
      history.replaceState(history.state, '', location.pathname + location.search);
    }
  }
  void clientReady.then(openRequestedProject);
  update();
})();
