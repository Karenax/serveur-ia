import { useEffect, useRef, useState } from 'react';
import { planningApi, type PlanningInfo, type PlanningTemplate, type TemplateDefinition, type TemplateDetail, type TemplateVersionDetail, type TemplateVersion } from '../lib/projectPlanning';
import type { Page } from '../lib/projectIdentity';
import { Pagination, ReferencePicker } from './IdentityPickers';
import { PlanningDefinitionEditor, definitionIssues } from './PlanningDefinitionEditor';
import { PlanningTemplateApplication } from './PlanningTemplateApplication';
import { PlanningValue } from './PlanningChanges';
import { changedFields, focusPlanning, message, useAlive, useEditorFocus } from './PlanningTasksPanel';
import { ErrorState, LoadingState } from './Ui';
import '../project-planning.css';

export function PlanningTemplatesPanel(props:{projectId:string;active?:boolean;onSaved:()=>void}) {return <TemplatesView key={props.projectId} {...props}/>;}
function TemplatesView({projectId,active=true,onSaved}:{projectId:string;active?:boolean;onSaved:()=>void}) {
  const [search,setSearch]=useState('');const [offset,setOffset]=useState(0);const [archived,setArchived]=useState(false);const [tick,setTick]=useState(0);
  const [page,setPage]=useState<(Page<PlanningTemplate>&{can_manage:boolean})|null>(null);const [info,setInfo]=useState<PlanningInfo|null>(null);
  const [selected,setSelected]=useState<TemplateDetail|null>(null);const [creating,setCreating]=useState<TemplateDefinition|null>(null);
  const [error,setError]=useState('');const [notice,setNotice]=useState('');const [loading,setLoading]=useState(true);const [opening,setOpening]=useState(false);const alive=useAlive();const generation=useRef(0);
  useEffect(()=>{if(!active)return;const controller=new AbortController();setLoading(true);setError('');const timer=window.setTimeout(()=>Promise.all([
    planningApi.templates({search,offset,include_inactive:archived,signal:controller.signal}),planningApi.info(projectId,controller.signal)])
    .then(([values,state])=>{if(!controller.signal.aborted){setPage(values);setInfo(state);}}).catch(e=>{if(!controller.signal.aborted)setError(message(e));}).finally(()=>{if(!controller.signal.aborted)setLoading(false);}),150);
    return()=>{controller.abort();window.clearTimeout(timer);};},[projectId,active,search,offset,archived,tick]);
  async function open(row?:PlanningTemplate){if(opening)return;setOpening(true);setError('');setNotice('');const request=++generation.current;try{
    if(row){const result=await planningApi.template(row.id);if(alive.current&&request===generation.current){setSelected(result);setCreating(null);}}
    else {const result=await planningApi.standard();if(alive.current&&request===generation.current){setCreating(result);setSelected(null);}}
  }catch(e){if(alive.current&&request===generation.current)setError(message(e));}finally{if(alive.current&&request===generation.current)setOpening(false);}}
  function saved(text:string){if(!alive.current)return;setSelected(null);setCreating(null);setNotice(text);setTick(value=>value+1);onSaved();}
  return <section className="planning-panel" aria-label="Modèles de planning"><header className="planning-heading"><div><h3>Modèles de planning</h3><p>Des versions conservées, un calendrier explicite et une application vérifiée projet par projet.</p></div>
    {page?.can_manage&&<button type="button" className="button primary" disabled={loading||opening||!!selected||!!creating} onClick={()=>void open()}>Créer un modèle</button>}</header>
    <div className="planning-toolbar"><label>Rechercher un modèle<input className="input" type="search" maxLength={200} value={search} onChange={e=>{setSearch(e.target.value);setOffset(0);}}/></label>
      <label className="identity-checkbox"><input type="checkbox" checked={archived} onChange={e=>{setArchived(e.target.checked);setOffset(0);}}/>Inclure les modèles archivés</label>
      <button type="button" className="button secondary sm" disabled={loading||opening} onClick={()=>setTick(value=>value+1)}>Recharger le catalogue</button></div>
    {notice&&<p role="status" className="planning-notice">{notice}</p>}{error&&<ErrorState message={error} retry={()=>setTick(value=>value+1)}/>}{loading&&<LoadingState label="Chargement des modèles"/>}
    {opening&&<p role="status">Chargement de la version ou du modèle…</p>}
    {creating&&<VersionEditor key="new" initial={creating} onCancel={()=>setCreating(null)} onSaved={()=>saved('Modèle créé et première version publiée. Aucun projet n’a été modifié.')}/>}
    {selected&&info&&<TemplateView key={selected.id} projectId={projectId} initial={selected} onClose={()=>setSelected(null)} onSaved={saved}/>}
    {page&&<><Pagination offset={page.offset} total={page.total} limit={page.limit} onChange={setOffset} disabled={loading||opening}/>
      {!page.items.length&&!loading&&<p>Aucun modèle dans cette recherche. Les projets conservent leur planning actuel.</p>}
      <div className="planning-table-scroll"><table className="data-table planning-template-table"><thead><tr><th>Modèle</th><th>Version publiée</th><th>État</th><th>Action</th></tr></thead><tbody>{page.items.map(row=><tr key={row.id}><td><strong>{row.name}</strong><small>{row.code} · {row.typology_id?'Typologie spécifique':'Toutes typologies'}</small></td><td>{row.latest_version?`Version ${row.latest_version.number}`:'Aucune version'}</td><td>{row.active?'Actif':'Archivé'}</td><td><button type="button" className="button secondary sm" aria-label={`Ouvrir le modèle · ${row.name}`} disabled={loading||opening||!!selected||!!creating} onClick={()=>void open(row)}>Versions et application</button></td></tr>)}</tbody></table></div></>}
  </section>;
}
function TemplateView({projectId,initial,onClose,onSaved}:{projectId:string;initial:TemplateDetail;onClose:()=>void;onSaved:(text:string)=>void}) {
  const [template,setTemplate]=useState(initial);const [page,setPage]=useState<Page<TemplateVersion>|null>(null);const [offset,setOffset]=useState(0);const [selected,setSelected]=useState<TemplateVersionDetail|null>(null);
  const [editor,setEditor]=useState<'publish'|'metadata'|null>(null);const [application,setApplication]=useState<PlanningInfo|null>(null);const [busy,setBusy]=useState(false);const [loading,setLoading]=useState(true);const [error,setError]=useState('');const alive=useAlive();const focus=useRef<HTMLElement>(null);
  useEffect(()=>{focusPlanning(focus.current);const controller=new AbortController();setLoading(true);planningApi.versions(template.id,offset,controller.signal).then(value=>{if(!controller.signal.aborted)setPage(value);}).catch(e=>{if(!controller.signal.aborted)setError(message(e));}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});return()=>controller.abort();},[template.id,offset]);
  async function view(id:string){if(busy)return;setBusy(true);setError('');try{const value=await planningApi.version(template.id,id);if(alive.current){setSelected(value);setApplication(null);setEditor(null);}}catch(e){if(alive.current)setError(message(e));}finally{if(alive.current)setBusy(false);}}
  async function prepare(kind:'publish'|'metadata'|'apply'){if(busy)return;setBusy(true);setError('');try{const detail=await planningApi.template(template.id);if(!alive.current)return;setTemplate(detail);
    if(kind==='apply'){const info=await planningApi.info(projectId);if(alive.current)setApplication(info);}else setEditor(kind);
  }catch(e){if(alive.current)setError(message(e));}finally{if(alive.current)setBusy(false);}}
  return <section ref={focus} tabIndex={-1} className="card planning-template-detail" aria-label={`Versions du modèle · ${template.name}`}>
    <div className="planning-heading"><div><h3>{template.name} · {template.code}</h3><p>Modèle {template.active?'actif':'archivé'} · révision {template.revision}</p></div><button type="button" className="button secondary sm" disabled={busy||!!editor||!!application} onClick={onClose}>Fermer le modèle</button></div>
    <p>Publier une version ne change aucun projet. Une version existante reste consultable et ne peut pas être réécrite.</p>
    {error&&<p role="alert" className="planning-error">{error}</p>}
    {template.can_manage&&!editor&&!application&&<button type="button" className="button secondary sm" disabled={busy} onClick={()=>void prepare('metadata')}>Modifier les métadonnées du modèle</button>}
    {editor==='metadata'&&<TemplateMetadataEditor initial={template} onCancel={()=>setEditor(null)} onSaved={()=>onSaved('Métadonnées du modèle enregistrées. Les versions et projets sont conservés.')}/>}
    {editor==='publish'&&selected&&<VersionEditor key={`publish-${selected.id}`} template={template} source={selected} initial={selected.definition} onCancel={()=>setEditor(null)} onSaved={()=>onSaved('Nouvelle version publiée. Les projets existants restent inchangés.')}/>}
    {application&&selected&&<PlanningTemplateApplication key={`${template.id}-${selected.id}`} projectId={projectId} template={template} version={selected} initial={application} onCancel={()=>setApplication(null)} onSaved={()=>onSaved('Aperçu appliqué au projet ; planning et historique actualisés.')}/>}
    {selected&&!editor&&!application&&<section className="planning-version" aria-label={`Version publiée ${selected.number}`}><div className="planning-heading"><h4>Version {selected.number} · {selected.definition.name}</h4><button type="button" className="button secondary sm" onClick={()=>setSelected(null)}>Fermer la version</button></div>
      <details><summary>Intégrité de la version publiée</summary><code>{selected.sha256}</code></details>
      <div className="planning-actions">{template.can_manage&&template.active&&<button type="button" className="button secondary" disabled={busy} onClick={()=>void prepare('publish')}>Créer une nouvelle version depuis v{selected.number}</button>}
        {template.active&&<button type="button" className="button primary" disabled={busy} onClick={()=>void prepare('apply')}>Préparer l’application de v{selected.number}</button>}</div>
      <PlanningDefinitionEditor value={selected.definition} onChange={()=>{}} readOnly/></section>}
    <section aria-label="Liste des versions"><h4>Versions publiées</h4>{loading&&<LoadingState label="Chargement des versions"/>}{page&&<><Pagination offset={page.offset} total={page.total} limit={page.limit} onChange={setOffset} disabled={busy||loading||!!editor||!!application}/>
      <div className="planning-table-scroll"><table className="data-table planning-version-table"><thead><tr><th>Version</th><th>Publication / opérateur</th><th>Action</th></tr></thead><tbody>{page.items.map(row=><tr key={row.id}><td>Version {row.number}</td><td>{row.created_at?new Date(row.created_at).toLocaleString('fr-FR'):'Date non renseignée'}<small>{row.actor_id||'Opérateur non renseigné'}</small></td><td><button type="button" className="button secondary sm" disabled={busy||!!editor||!!application} onClick={()=>void view(row.id)} aria-label={`Consulter la version ${row.number}`}>Consulter</button></td></tr>)}</tbody></table></div></>}</section>
  </section>;
}
function VersionEditor({template,source,initial,onCancel,onSaved}:{template?:TemplateDetail;source?:TemplateVersionDetail;initial:TemplateDefinition;onCancel:()=>void;onSaved:()=>void}) {
  const [base,setBase]=useState(template);const [latest,setLatest]=useState<TemplateDetail|null>(null);const [draft,setDraft]=useState<TemplateDefinition>(()=>structuredClone(initial));
  const [code,setCode]=useState('');const [name,setName]=useState('');const [typology,setTypology]=useState<string|null>(null);const [error,setError]=useState('');const [busy,setBusy]=useState(false);const alive=useAlive();const focus=useEditorFocus();
  const creating=!base;const issues=definitionIssues(draft);const allowed=creating||!!base?.can_manage&&base.active;
  async function save(){if(busy||latest||!allowed)return;if(issues.length){setError(issues.join(' '));return;}setBusy(true);setError('');try{if(base)await planningApi.publish(base,draft);else await planningApi.createTemplate({code,name,typology_id:typology,definition:draft});if(alive.current)onSaved();}catch(e){if(alive.current)setError(message(e));}finally{if(alive.current)setBusy(false);}}
  async function reload(){if(!base||busy)return;setBusy(true);try{const row=await planningApi.template(base.id);if(alive.current)setLatest(row);}catch(e){if(alive.current)setError(message(e));}finally{if(alive.current)setBusy(false);}}
  return <form ref={focus} tabIndex={-1} className="card planning-editor" aria-label={creating?'Création du modèle':'Publication d’une nouvelle version'} data-workspace-dirty="true" onSubmit={e=>{e.preventDefault();void save();}}>
    <div className="planning-heading"><h3>{creating?'Créer un modèle depuis le cycle standard':`Nouvelle version depuis v${source?.number}`}</h3>{base&&<span>Révision du modèle {base.revision}</span>}</div>
    {error&&<p role="alert" className="planning-error">{error} Le brouillon est conservé.</p>}
    {latest&&<section className="planning-conflict" aria-label="Révision actuelle du modèle"><h4>{latest.name} · révision {latest.revision} · dernière version {latest.latest_version?.number}</h4><p>Votre brouillon reste basé sur la version {source?.number}. Relire les publications avant de créer une version supplémentaire.</p><button type="button" className="button secondary" disabled={busy||!latest.can_manage||!latest.active} onClick={()=>{setBase(latest);setLatest(null);setError('');}}>Préparer la publication sur cette révision</button></section>}
    {creating&&<div className="planning-form-grid"><label>Code du modèle<input className="input" required maxLength={64} value={code} disabled={busy} onChange={e=>setCode(e.target.value)}/></label><label>Nom du modèle<input className="input" required maxLength={255} value={name} disabled={busy} onChange={e=>setName(e.target.value)}/></label><ReferencePicker kind="typology" label="Typologie du modèle" value={typology} onChange={setTypology} disabled={busy}/></div>}
    <PlanningDefinitionEditor value={draft} onChange={setDraft} readOnly={busy||!allowed||!!latest}/>
    {issues.length>0&&<div className="planning-note" role="status"><strong>À compléter avant publication</strong><ul>{issues.slice(0,10).map((value,index)=><li key={index}>{value}</li>)}</ul>{issues.length>10&&<p>{issues.length-10} autre(s) point(s) à compléter.</p>}</div>}
    <div className="planning-actions"><button className="button primary" type="submit" disabled={busy||!!latest||!allowed||issues.length>0||creating&&(!code.trim()||!name.trim())}>{creating?'Créer et publier la première version':'Publier cette nouvelle version'}</button>
      {error&&base&&<button type="button" className="button secondary" disabled={busy} onClick={()=>void reload()}>Relire le modèle sans perdre le brouillon</button>}
      <button type="button" className="button secondary" disabled={busy} onClick={onCancel}>Annuler le brouillon de version</button></div>
  </form>;
}
type Metadata={name:string;typology_id:string|null;active:boolean};
const metadata=(row:PlanningTemplate):Metadata=>({name:row.name,typology_id:row.typology_id,active:row.active});
function TemplateMetadataEditor({initial,onCancel,onSaved}:{initial:TemplateDetail;onCancel:()=>void;onSaved:()=>void}) {
  const [base,setBase]=useState(initial);const [draft,setDraft]=useState(()=>metadata(initial));const [latest,setLatest]=useState<TemplateDetail|null>(null);const [error,setError]=useState('');const [busy,setBusy]=useState(false);const alive=useAlive();const focus=useEditorFocus();const patches=changedFields(metadata(base),draft);
  function change(patch:Partial<Metadata>){setDraft(value=>({...value,...patch}));setLatest(null);}
  async function save(){if(busy||latest||!base.can_manage)return;setBusy(true);setError('');try{await planningApi.patchTemplate(base,patches);if(alive.current)onSaved();}catch(e){if(alive.current)setError(message(e));}finally{if(alive.current)setBusy(false);}}
  async function reload(){if(busy)return;setBusy(true);try{const row=await planningApi.template(base.id);if(alive.current)setLatest(row);}catch(e){if(alive.current)setError(message(e));}finally{if(alive.current)setBusy(false);}}
  return <form ref={focus} tabIndex={-1} className="card planning-editor" aria-label="Métadonnées du modèle" data-workspace-dirty={Object.keys(patches).length?'true':undefined} onSubmit={e=>{e.preventDefault();void save();}}><h3>Métadonnées du modèle · révision {base.revision}</h3>
    <p className="planning-note">Archiver conserve toutes les versions et tous les projets ; le modèle ne pourra plus être publié ni appliqué jusqu’à sa réactivation.</p>
    {error&&<p role="alert" className="planning-error">{error} Votre saisie est conservée.</p>}
    {latest&&<section className="planning-conflict" aria-label="Comparaison des métadonnées du modèle"><h4>Modèle actuel · révision {latest.revision}</h4><div className="planning-table-scroll"><table className="data-table"><thead><tr><th>Champ</th><th>Au début</th><th>Actuellement</th><th>Votre saisie</th></tr></thead><tbody>{Object.entries(patches).map(([key,value])=><tr key={key}><td>{key==='name'?'Nom':key==='active'?'Actif':'Typologie'}</td><td><PlanningValue value={metadata(base)[key as keyof Metadata]}/></td><td><PlanningValue value={metadata(latest)[key as keyof Metadata]}/></td><td><PlanningValue value={value}/></td></tr>)}</tbody></table></div><button type="button" className="button secondary" disabled={busy||!latest.can_manage} onClick={()=>{setDraft({...metadata(latest),...patches});setBase(latest);setLatest(null);setError('');}}>Préparer mes métadonnées sur cette révision</button></section>}
    <div className="planning-form-grid"><label>Nom du modèle<input className="input" required maxLength={255} value={draft.name} disabled={busy||!base.can_manage} onChange={e=>change({name:e.target.value})}/></label><ReferencePicker kind="typology" label="Typologie du modèle" value={draft.typology_id} onChange={id=>change({typology_id:id})} disabled={busy||!base.can_manage}/></div>
    <label className="identity-checkbox"><input type="checkbox" checked={draft.active} disabled={busy||!base.can_manage} onChange={e=>change({active:e.target.checked})}/>Modèle actif</label>
    <div className="planning-actions"><button className="button primary" type="submit" disabled={busy||!!latest||!base.can_manage||!draft.name.trim()||!Object.keys(patches).length}>Enregistrer les métadonnées du modèle</button>{error&&<button type="button" className="button secondary" disabled={busy} onClick={()=>void reload()}>Relire et comparer le modèle</button>}<button type="button" className="button secondary" disabled={busy} onClick={onCancel}>Annuler les métadonnées</button></div>
  </form>;
}
