import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { request } from "../lib/http";
import {MemoryRecovery} from './MemoryRecovery';
import "../progressive-options.css";
export function AiSettingsForm() {
  const [form, setForm] = useState({ provider: "ollama", base_url: "", model: "", api_key: "", enabled: false,
    fallback_enabled: false, fallback_base_url: "http://127.0.0.1:1234", fallback_model: "google/gemma-4-e4b", fallback_autostart: true });
  const [msg, setMsg] = useState("");
  const [ready, setReady] = useState(false);
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    api.brainAiSettings()
      .then((ai: any) => {
        setForm({ provider: ai.provider || "ollama", base_url: ai.base_url || "",
                  model: ai.model || "", api_key: "", enabled: !!ai.enabled,
                  fallback_enabled: !!ai.fallback_enabled, fallback_base_url: ai.fallback_base_url || "http://127.0.0.1:1234",
                  fallback_model: ai.fallback_model || "google/gemma-4-e4b", fallback_autostart: ai.fallback_autostart ?? true });
        setReady(true);
      })
      .catch((e: any) => setMsg(String(e.message || e)));
  }, []);
  const save = async () => {
    if (!ready || saving || testing) return;
    setSaving(true);
    try {
      setMsg("Enregistrement…");
      const body: any = { ...form };
      if (!body.api_key) delete body.api_key;
      await api.saveBrainAiSettings(body);
      setForm({ ...form, api_key: "" });
      setMsg("Enregistré.");
    } catch (e: any) {
      setMsg(String(e.message || e));
    } finally {setSaving(false);}
  };
  const test = async () => {
    if (!ready || testing || saving) return;
    setTesting(true);
    try {
      setMsg("Test en cours…");
      const r: any = await api.brainAiTest();
      setMsg(r.ok ? "Assistant IA accessible." : `Échec : ${r.reason || JSON.stringify(r)}`);
    } catch (e: any) {
      setMsg(String(e.message || e));
    } finally {
      window.dispatchEvent(new Event("agent:connections-refresh"));
      setTesting(false);
    }
  };
  if (!ready && !msg) return <p><small>Chargement du réglage IA…</small></p>;
  return (
    <div className="workspace-settings-form">
      <p className="settings-overview">Choisissez le service qui rédige les réponses et les comptes rendus. Enregistrez les réglages avant de tester la connexion.</p>
      <label><input type="checkbox" checked={form.enabled} disabled={!ready || saving || testing}
        onChange={(e) => setForm({ ...form, enabled: e.target.checked })} /> Activer l’assistant IA</label>
      <label>Service IA{" "}
        <select className="input" value={form.provider} disabled={!ready || saving || testing}
          onChange={(e) => setForm({ ...form, provider: e.target.value })}>
          <option value="none">Désactivé</option>
          <option value="ollama">Ollama sur un ordinateur</option>
          <option value="openai_compatible">LM Studio ou API compatible OpenAI</option>
        </select>
      </label>{" "}
      <label>Modèle{" "}
        <input className="input" value={form.model} placeholder="llama3.1" disabled={!ready || saving || testing}
          onChange={(e) => setForm({ ...form, model: e.target.value })} style={{ width: 200 }} />
      </label>{" "}
      <details className="progressive-options"><summary>Connexion et clé d’accès</summary><div className="progressive-options-grid">
      <label>Adresse du serveur{" "}
        <input className="input" value={form.base_url} placeholder="http://localhost:11434" disabled={!ready || saving || testing}
          onChange={(e) => setForm({ ...form, base_url: e.target.value })} />
      </label>
      <label>Clé d’accès (API){" "}
        <input className="input" type="password" value={form.api_key} placeholder="(inchangée)"
          disabled={!ready || saving || testing}
          onChange={(e) => setForm({ ...form, api_key: e.target.value })} style={{ width: 140 }} />
      </label>{" "}
      <button className="button" disabled={!ready || saving || testing} onClick={async () => {
        setSaving(true);
        try { await api.saveBrainAiSettings({ ...form, clear_api_key: true, api_key: undefined }); setMsg("Clé stockée effacée."); }
        catch (error) { setMsg(String(error)); }
        finally {setSaving(false);}
      }}>Effacer la clé stockée</button>
      </div></details>
      <details className="progressive-options"><summary>Secours local si le serveur ne répond pas</summary><div className="progressive-options-grid">
        <label><input type="checkbox" checked={form.fallback_enabled}
          disabled={!ready || saving || testing}
          onChange={(e) => setForm({ ...form, fallback_enabled: e.target.checked })} /> Utiliser le modèle local si le serveur principal est injoignable</label>
        <label> Adresse de LM Studio sur ce PC <input className="input" value={form.fallback_base_url} disabled={!ready || saving || testing}
          onChange={(e) => setForm({ ...form, fallback_base_url: e.target.value })} /></label>
        <label> Modèle local <input className="input" value={form.fallback_model} disabled={!ready || saving || testing}
          onChange={(e) => setForm({ ...form, fallback_model: e.target.value })} /></label>
        <label><input type="checkbox" checked={form.fallback_autostart}
          disabled={!ready || saving || testing}
          onChange={(e) => setForm({ ...form, fallback_autostart: e.target.checked })} /> Démarrer LM Studio et charger le modèle si nécessaire</label>
        <p><small>Le serveur principal reste prioritaire. Agent vérifie son retour après 30 secondes. Enregistrez avant de tester.</small></p>
        <button className="button" disabled={!ready || saving || testing || !form.fallback_enabled} onClick={async () => {
          setTesting(true); setMsg("Test du secours local en cours…");
          try {
            const result = await request<any>("/v1/settings/ai/fallback/test", {method: "POST"});
            setMsg(result.ok ? `Secours local joignable : ${result.model}. Réponse : ${result.reply}` : `Échec du secours local : ${result.reason}`);
          } catch (error: any) { setMsg(String(error.message || error)); }
          finally { window.dispatchEvent(new Event("agent:connections-refresh")); setTesting(false); }
        }}>Tester le secours local</button>
      </div></details>
      <div className="settings-main-actions"><button className="button primary" disabled={!ready || saving || testing} onClick={save}>{saving ? "Enregistrement…" : "Enregistrer"}</button>
      <button className="button" onClick={test} disabled={!ready || saving || testing}>{testing ? "Test en cours…" : "Tester"}</button></div>
      {msg && <p role="status"><small>{msg}</small></p>}
    </div>
  );
}

export function MailSettingsForm() {
  const [form,setForm]=useState({source:"thunderbird",folder:"",auto_scan:true,scan_interval_minutes:5,auto_classification_threshold:.75,thunderbird_folder_ids:[] as string[]});
  const [status,setStatus]=useState<any>(null);
  const [msg,setMsg]=useState("");
  const [error,setError]=useState("");
  const [ready,setReady]=useState(false);
  const [busy,setBusy]=useState(false);
  const [search,setSearch]=useState("");
  const [account,setAccount]=useState("");
  const [scanFolder,setScanFolder]=useState("");
  useEffect(()=>{
    let live=true;
    Promise.all([api.brainMailSettings(),request<any>("/v1/thunderbird/status")]).then(([m,value]:any[])=>{
      if(!live)return;
      setForm({source:m.source||"thunderbird",folder:m.folder||"",auto_scan:m.auto_scan!==false,
        scan_interval_minutes:Number(m.scan_interval_minutes)||5,
        auto_classification_threshold:m.auto_classification_threshold??.75,
        thunderbird_folder_ids:m.thunderbird_folder_ids??value.sync?.folder_ids??(value.folders||[]).filter((f:any)=>/(?:^|\/)INBOX$/i.test(f.path)).map((f:any)=>f.id)});
      setStatus(value);setReady(true);
    }).catch(e=>{if(live)setError(String(e.message||e));});
    const timer=window.setInterval(()=>{if(!document.hidden)void request<any>("/v1/thunderbird/status",{activity:false},20000).then(value=>{if(live)setStatus(value);}).catch(e=>{if(live)setError(String(e.message||e));});},30000);
    return()=>{live=false;window.clearInterval(timer);};
  },[]);
  const save=async()=>{
    if(!ready||busy)return;
    setBusy(true);setError("");setMsg("");
    try {await api.saveBrainMailSettings(form);setMsg("Réglages enregistrés. La liaison adopte ce choix au prochain échange.");}
    catch(e:any){setError(String(e.message||e));}finally{setBusy(false);}
  };
  const synchronize=async()=>{
    if(!ready||busy)return;
    setBusy(true);setError("");setMsg("");
    try {
      await api.saveBrainMailSettings(form);
      if(form.source==="thunderbird"){
        await request("/v1/thunderbird/sync",{method:"POST",body:JSON.stringify({folder_ids:form.thunderbird_folder_ids})});
        setMsg(status?.connected?"Synchronisation demandée dans Thunderbird.":"Demande enregistrée. Ouvrez Thunderbird pour lancer la synchronisation.");
      }else{
        const r:any=await api.brainScanGlobal();setMsg(`Scan : ${r.scanned||0} mail(s), ${r.imported||0} importé(s), ${r.duplicates||0} doublon(s).`);
      }
    }catch(e:any){setError(String(e.message||e));}finally{setBusy(false);}
  };
  const scanOnce=async(useDefault:boolean)=>{
    if(!ready||busy)return;
    setBusy(true);setError("");setMsg("");
    try{
      if(useDefault){
        const {folder}=await request<{folder:string}>("/v1/ingest/default-folder");
        setScanFolder(folder);
      }else{
        const result=await request<{scanned:number;imported?:number;duplicates?:number;error?:string}>(
          "/v1/ingest/scan",{method:"POST",body:JSON.stringify({folder:scanFolder.trim()}),activity:"Analyse du dossier EML"},0);
        if(result.error)throw new Error(result.error);
        setMsg(`${result.scanned} mail(s) parcouru(s), ${result.imported??0} importé(s), ${result.duplicates??0} doublon(s).`);
      }
    }catch(e){setError(e instanceof Error?e.message:String(e));}finally{setBusy(false);}
  };
  const selected=new Set(form.thunderbird_folder_ids);
  const validThreshold=Number.isFinite(form.auto_classification_threshold) && form.auto_classification_threshold>=.01 && form.auto_classification_threshold<=1;
  const folders=(status?.folders||[]).filter((f:any)=>(!account||f.account_id===account)&&`${f.path} ${f.name}`.toLocaleLowerCase().includes(search.toLocaleLowerCase()));
  const sync=status?.sync;
  return <div className="workspace-settings-form mail-settings-form">
    <label>Source des mails<select className="input" value={form.source} disabled={!ready||busy} onChange={e=>setForm({...form,source:e.target.value})}>
      <option value="thunderbird">Thunderbird</option><option value="folder">Dossier de fichiers EML</option>
    </select></label>
    {form.source==="folder"?<label>Dossier des e-mails (côté serveur)<input className="input" value={form.folder} disabled={busy} placeholder="C:\\...\\Mails" onChange={e=>setForm({...form,folder:e.target.value})}/></label>:
      <section className="mail-source-folders mail-settings-source" aria-label="Dossiers Thunderbird">
        <p role="status"><strong>{status?.connected?"Thunderbird connecté":"Thunderbird fermé ou liaison indisponible"}</strong>
          {status?.last_seen&&` · Dernier contact : ${new Date(status.last_seen).toLocaleString("fr-FR")}`}</p>
        <p>Thunderbird doit être ouvert pour synchroniser. Les mails déjà importés restent disponibles dans Kiara.</p>
        {status?.version&&status.version!=="0.2.0"&&<p>La sélection est protégée par Kiara. Installez la liaison 0.2.0 pour appliquer aussi les réglages à la synchronisation automatique de Thunderbird.</p>}
        <details className="progressive-options"><summary>Choisir les dossiers · {selected.size} sélectionné(s)</summary><div className="progressive-options-grid">
        <label>Compte Thunderbird<select className="input" value={account} onChange={e=>setAccount(e.target.value)}><option value="">Tous les comptes</option>{(status?.accounts||[]).map((a:any)=><option key={a.id} value={a.id}>{a.name}</option>)}</select></label>
        <label>Rechercher un dossier<input className="input" type="search" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Réception, envoyés, projet…"/></label>
        <p>{selected.size} dossier(s) sélectionné(s) · {folders.length} affiché(s)</p>
        <div className="mail-source-folder-list">{folders.map((f:any)=><label key={f.id} style={{paddingInlineStart:Math.min(5,(f.path||"").split("/").length-1)*12+10}}><input type="checkbox" disabled={busy||!ready} checked={selected.has(f.id)} onChange={()=>setForm(previous=>({...previous,thunderbird_folder_ids:selected.has(f.id)?previous.thunderbird_folder_ids.filter(id=>id!==f.id):[...previous.thunderbird_folder_ids,f.id]}))}/><span>{status.accounts?.find((a:any)=>a.id===f.account_id)?.name} · {f.path||f.name}</span></label>)}</div>
        {!folders.length&&<p>Aucun dossier disponible avec ces filtres. Ouvrez Thunderbird et vérifiez sa liaison.</p>}
        <small>Indésirables, corbeille et brouillons exclus. Réception et Envoyés peuvent être sélectionnés ensemble.</small>
        </div></details>
        {(sync?.running||sync?.total>0)&&<p role="status">{sync.total!=null?`${sync.processed||0} / ${sync.total} mails transférés` : "Import en cours…"}</p>}
        {sync?.total>0&&<progress aria-label="Transfert des mails Thunderbird" value={sync.processed||0} max={sync.total}/>}
        {sync&&<p>Dernier lot : {sync.imported||0} nouveaux · {sync.duplicates||0} doublons · {sync.errors||0} erreurs{sync.more_pending?" · suite au prochain passage":""}</p>}
        {sync?.last_error&&<p role="alert">{sync.last_error}</p>}
      </section>}
    <label><input type="checkbox" checked={form.auto_scan} disabled={!ready||busy} onChange={e=>setForm({...form,auto_scan:e.target.checked})}/> Synchronisation automatique</label>
    <details className="progressive-options"><summary>Options de synchronisation et de classement</summary><div className="progressive-options-grid">
    <label>Intervalle de synchronisation (minutes)<input className="input" type="number" min={1} max={1440} value={form.scan_interval_minutes} disabled={!ready||busy} onChange={e=>setForm({...form,scan_interval_minutes:Number(e.target.value)||5})}/></label>
    <label>Seuil de classement automatique (%)<input className="input" type="number" min={1} max={100} step={0.1} value={Number((form.auto_classification_threshold*100).toFixed(2))} disabled={!ready||busy} aria-invalid={!validThreshold} onChange={e=>setForm({...form,auto_classification_threshold:Number(e.target.value)/100})}/></label>
    <small>À partir de ce score, les mails sont classés dans le projet suggéré. En dessous, validation manuelle.</small>
    </div></details>
    <div className="mail-settings-actions settings-main-actions">
      <button className="button primary" disabled={!ready||busy||!validThreshold} onClick={()=>void save()}>Enregistrer</button>
      <button className="button" disabled={!ready||busy||!validThreshold||(form.source==="thunderbird"&&!selected.size)} onClick={()=>void synchronize()}>{busy?"Traitement…":"Synchroniser maintenant"}</button>
    </div>
    <details className="progressive-options"><summary>Analyser un dossier EML ponctuellement</summary>
      <form onSubmit={event=>{event.preventDefault();if(scanFolder.trim())void scanOnce(false);}}>
        <label>Dossier EML sur le serveur<input className="input" value={scanFolder} disabled={!ready||busy}
          onChange={event=>setScanFolder(event.target.value)}/></label>
        <button type="button" className="button" disabled={!ready||busy} onClick={()=>void scanOnce(true)}>Utiliser le dossier par défaut</button>
        <button type="submit" className="button" disabled={!ready||busy||!scanFolder.trim()}>Analyser le dossier</button>
      </form>
    </details>
    {error&&<p role="alert">{error}</p>}{msg&&<p role="status">{msg}</p>}
  </div>;
}

export function MemorySettingsForm() {
  const [form, setForm] = useState({engine: "eg2", prefix: "pb", embedding_provider: "openai_compatible",
    embedding_model: "text-embedding-embeddinggemma-2", embedding_endpoint: "http://192.9.110.115:1234",
    index_path: "", timeout_s: 120, batch_size: 8});
  const [state, setState] = useState<any>(null), [msg, setMsg] = useState(""), [busy, setBusy] = useState(false);
  useEffect(() => {api.brainMemorySettings().then((m: any) => {setForm(f => ({...f, ...m.configured}));setState(m);})
    .catch((e: any) => setMsg(String(e.message || e)));}, []);
  const save = async () => {try {setBusy(true);await api.saveBrainMemorySettings(form);
    setState(await api.brainMemorySettings());setMsg("Réglages de recherche enregistrés. Si le modèle ou le serveur change, reconstruisez les index des projets.");}
    catch (e: any) {setMsg(String(e.message || e));} finally {setBusy(false);}};
  const probe = async () => {try {setBusy(true);setMsg("Test de la recherche : indexation, recherche et nettoyage…");
    const r: any = await api.brainMemoryTest();setMsg(r.status === "ok" ? `Recherche vérifiée : ${r.recall_hits} résultat(s), indexation ${r.remember_s}s, recherche ${r.recall_s}s.` : `Échec : ${r.error || r.status}`);}
    catch (e: any) {setMsg(String(e.message || e));} finally {setBusy(false);}};
  return <div className="workspace-settings-form">
    <h3>Recherche dans les documents</h3>
    <p className="settings-overview">La recherche retrouve les passages utiles des sources du projet. L’assistant IA peut ensuite rédiger une réponse avec ses citations.</p>
    <p>{state?.active?.health?.passages!=null ? `${state.active.health.passages} passages disponibles pour la recherche` : "Nombre de passages non vérifié"}</p>
    {state?.active?.health?.status&&state.active.health.status!=="ok"&&<p role="alert">Recherche à vérifier · {state.active.health.status}</p>}
    <details className="progressive-options"><summary>Connexion au service de recherche</summary><div className="progressive-options-grid">
    <label>Adresse du serveur de recherche <input className="input" value={form.embedding_endpoint} disabled={busy || !state} onChange={e => setForm(f => ({...f, embedding_endpoint: e.target.value}))}/></label>{" "}
    <label>Modèle <input className="input" value={form.embedding_model} disabled={busy || !state} onChange={e => setForm(f => ({...f, embedding_model: e.target.value}))}/></label>{" "}
    </div></details>
    <div className="settings-main-actions"><button className="button primary" disabled={busy || !state} onClick={save}>Enregistrer</button>
    <button className="button" disabled={busy || !state} onClick={probe}>{busy ? "En cours…" : "Tester la recherche"}</button></div>
    <details className="progressive-options"><summary>Réglages avancés et diagnostic</summary><div className="progressive-options-grid">
      <p>Moteur EG2 · Modèle de recherche : {form.embedding_model}</p>
      <p>Index : {state?.active?.health?.data_dir || "chargement…"} · État : {state?.active?.health?.status || "non vérifié"}</p>
      <label>Chemin de l’index (SQLite) <input className="input" value={form.index_path} disabled={busy || !state} placeholder="stockage EG2 par défaut" onChange={e => setForm(f => ({...f, index_path: e.target.value}))}/></label>
      <p>Un changement de profil exige une reconstruction. Les sources et les validations sont conservées.</p>
    </div></details>
    <div className="settings-maintenance"><MemoryRecovery/></div>
    {msg && <p role="status">{msg}</p>}
  </div>;
}
