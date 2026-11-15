/* Browser transport for the shared Conversations view. The session cookie
   authenticates server requests. Browser preferences are scoped to the account. */
window.kiaraPlatform = Object.freeze({
  platform:'web', local_api:false, settings:['access'], send_with_modifier:false
});
const browserFetch = window.fetch.bind(window);
let browserHistoryMarker;
function browserReply(value) {
  return new Response(JSON.stringify(value), {headers:{'Content-Type':'application/json'}});
}
const fetch = async (path, options = {}) => {
  const prefix = config.web_prefix;
  const method = options.method || 'GET';
  const values = () => JSON.parse(options.body || '{}');
  const key = 'kiara-web-'+config.storage;
  const preferences = () => JSON.parse(localStorage.getItem(key+'-preferences') || '{}');
  const request = (url, opts = options) => {
    const headers = new Headers(opts.headers);
    headers.delete('Authorization');
    return browserFetch(prefix+url,{...opts,headers});
  };
  async function history() {
    const response = await request('/v1/history',{signal:options.signal});
    if (!response.ok) return response;
    const value = await response.json();
    browserHistoryMarker = {reset_id:value.reset_id,generation:value.generation};
    if (!value.history) {
      const emptyHistory = {conversations:library,currentId};
      const saved = await request('/v1/history',{method:'POST',signal:options.signal,
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({history:emptyHistory,revision:value.revision,...browserHistoryMarker})});
      if (saved.status === 409) {
        const latest = await request('/v1/history',{signal:options.signal});
        if (!latest.ok) return latest;
        const replacement = await latest.json();
        if (!replacement.history) return saved;
        browserHistoryMarker = {reset_id:replacement.reset_id,generation:replacement.generation};
        return browserReply({...replacement,message:'Historique du serveur'});
      }
      if (!saved.ok) return saved;
      value.revision = (await saved.json()).revision;
      value.history = emptyHistory;
    }
    return browserReply({...value,history:value.history,server_synced:true,pending:false,message:'Historique du serveur'});
  }
  if (path === '/client/state') return browserReply({preferences:preferences()});
  if (path === '/client/preferences') {
    const current = preferences(), changes = values();
    const drafts = {...current.conversation_drafts};
    for (const [id,text] of Object.entries(changes.conversation_drafts || {})) {
      if (text) drafts[id] = text; else delete drafts[id];
    }
    localStorage.setItem(key+'-preferences',JSON.stringify({...current,...changes,conversation_drafts:drafts}));
    return browserReply({saved:true});
  }
  if (path === '/client/draft') {
    if (method === 'POST') localStorage.setItem(key+'-document',JSON.stringify(values().draft));
    return browserReply({draft:JSON.parse(localStorage.getItem(key+'-document') || 'null')});
  }
  if (path === '/client/history' && method === 'POST') {
    if (!browserHistoryMarker) return new Response('{}',{status:409});
    const response = await request('/v1/history',{...options,body:JSON.stringify({...values(),...browserHistoryMarker})});
    if (!response.ok) return response;
    return browserReply({...await response.json(),message:'Historique enregistré sur le serveur'});
  }
  if (path === '/client/history' || path === '/client/history/sync') return history();
  if (path === '/client/history/flush') return browserReply({saved:true});
  if (path.startsWith('/client/')) return new Response('{}',{status:404});
  return request(path);
};
