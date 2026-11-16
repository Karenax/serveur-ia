const portalPrefix = (path: string): string => /^\/(kiara|agent)(?=\/)/.exec(path)?.[0] ?? '';

export function agentPath(path: string): string {
  return /^\/(?:app|api\/v1|v1|assets)(?:[/?#]|$)/.test(path)
    ? portalPrefix(window.location.pathname) + path : path;
}

export function agentLocation(path: string): string {
  return path.slice(portalPrefix(path).length);
}

export function agentFetch(path: string, init?: RequestInit): Promise<Response> {
  return fetch(agentPath(path), init);
}

export function conversationsHref(): string | null {
  if (document.body.dataset.kiaraWebConversations === 'true') return agentPath('/app/conversations');
  if (document.body.dataset.kiaraDesktop === 'true') return '/chat';
  return null;
}

export function projectConversationHref(projectId = ''): string | null {
  if (document.body.dataset.kiaraWebConversations !== 'true'
      && document.body.dataset.kiaraProjectConversation !== 'true') return null;
  const path = conversationsHref();
  return path ? path + '#projet=' + encodeURIComponent(projectId) : null;
}
