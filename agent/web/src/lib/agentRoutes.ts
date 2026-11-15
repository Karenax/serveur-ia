export function agentPath(path: string): string {
  return window.location.pathname.startsWith('/agent/') && /^\/(?:app|api\/v1|v1|assets)(?:[/?#]|$)/.test(path)
    ? `/agent${path}` : path;
}

export function agentLocation(path: string): string {
  return path.startsWith('/agent/') ? path.slice('/agent'.length) : path;
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
