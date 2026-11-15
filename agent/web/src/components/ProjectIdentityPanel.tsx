import { useEffect, useRef, useState, type FormEvent } from "react";
import { identityApi, personName, referenceKinds, type IdentityChange, type IdentityFields, type MemberRole, type Page, type ProjectIdentity, type ProjectMember } from "../lib/projectIdentity";
import { Pagination, PersonPicker, ReferencePicker } from "./IdentityPickers";
import { Badge, ErrorState, LoadingState } from "./Ui";
import "../project-identity.css";

const textFields = [
  ["client_reference","Référence client",120], ["client_site","Site client",255],
  ["client_contact","Contact client",255], ["equipment_number","Numéro d’outillage",120],
] as const;
type TeamDraft={id?:string;person_id:string|null;role:MemberRole;start_date:string;end_date:string};
const emptyMember:TeamDraft={person_id:null,role:"collaborateur_projet",start_date:"",end_date:""};
const actionLabels:Record<string,string>={identity_updated:"Fiche modifiée",member_added:"Affectation créée",member_updated:"Affectation modifiée",member_archived:"Affectation archivée"};
const projectReferences=referenceKinds.map(ref=>({...ref,label:ref.kind==='business_unit'?'Unité d’activité':ref.kind==='typology'?'Type de projet':ref.label}));
const fieldLabels:Record<string,string>={...Object.fromEntries(projectReferences.map(ref=>[ref.field,ref.label])),...Object.fromEntries(textFields.map(([key,label])=>[key,label])),
  responsible_id:"Responsable projet",person_id:"Personne",role:"Rôle métier",description:"Description",quantity:"Quantité",start_date:"Début",planned_end_date:"Fin prévisionnelle",end_date:"Fin",actual_closure_date:"Clôture réelle",standby:"En attente",active:"Affectation active",archived_at:"Archivage"};

export function ProjectIdentityPanel({projectId,onSaved}:{projectId:string;onSaved?:()=>void}) {
  return <IdentityEditor key={projectId} projectId={projectId} onSaved={onSaved}/>;
}
function IdentityEditor({projectId,onSaved}:{projectId:string;onSaved?:()=>void}) {
  const [identity,setIdentity]=useState<ProjectIdentity|null>(null);const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");const [notice,setNotice]=useState("");const [busy,setBusy]=useState(false);
  const [draft,setDraft]=useState<Partial<IdentityFields>>({});const [teamDraft,setTeamDraft]=useState<TeamDraft|null>(null);
  const [tab,setTab]=useState("identity");const [archived,setArchived]=useState(false);
  const alive=useRef(true);const readVersion=useRef(0);
  useEffect(()=>{alive.current=true;const controller=new AbortController();const version=++readVersion.current;
    identityApi.read(projectId,controller.signal).then(value=>{if(alive.current&&version===readVersion.current)setIdentity(value);})
      .catch(e=>{if(alive.current&&!controller.signal.aborted)setError(String(e.message||e));})
      .finally(()=>{if(alive.current&&!controller.signal.aborted)setLoading(false);});
    return()=>{alive.current=false;controller.abort();};},[projectId]);
  async function reload() {
    const version=++readVersion.current;setLoading(true);setError("");
    try {const result=await identityApi.read(projectId);if(alive.current&&version===readVersion.current){setIdentity(result);setDraft({});setTeamDraft(null);setNotice("");}}
    catch(e){if(alive.current&&version===readVersion.current)setError(String((e as Error).message||e));}
    finally{if(alive.current&&version===readVersion.current)setLoading(false);}
  }
  async function save(command:()=>Promise<ProjectIdentity>,message:string) {
    if(busy)return;setBusy(true);setError("");setNotice("");
    try {const result=await command();if(alive.current){setIdentity(result);setDraft({});setTeamDraft(null);setNotice(message);onSaved?.();}}
    catch(e){if(alive.current)setError(String((e as Error).message||e));}
    finally{if(alive.current)setBusy(false);}
  }
  if(loading&&!identity)return <LoadingState label="Chargement de la fiche et de l’équipe"/>;
  if(!identity)return <ErrorState message={error||"Fiche indisponible"} retry={()=>void reload()}/>;
  const dirty=Object.keys(draft).length>0||!!teamDraft;
  const readOnly=!identity.can_edit;const disabled=readOnly||busy||loading;
  const field=<K extends keyof IdentityFields>(name:K):IdentityFields[K]=>name in draft?draft[name] as IdentityFields[K]:identity[name];
  const change=<K extends keyof IdentityFields>(name:K,value:IdentityFields[K])=>setDraft(previous=>{const next={...previous};if(value===identity[name])delete next[name];else next[name]=value;return next;});
  const members=identity.members.filter(member=>archived||member.active);
  return <section className="identity-panel" aria-label="Fiche et équipe du projet" data-workspace-dirty={dirty?"true":undefined}>
    <nav className="workspace-tabs" aria-label="Fiche projet">{[["identity","Fiche"],["team",`Équipe · ${identity.members.filter(m=>m.active).length}`],["history","Historique"]].map(([id,label])=>
      <button type="button" key={id} aria-pressed={tab===id} disabled={busy||(dirty&&tab!==id)} onClick={()=>setTab(id)}>{label}</button>)}</nav>
    {readOnly&&<p className="identity-notice" role="status">Consultation seule · les droits sont définis par le serveur.</p>}
    {error&&<div className="identity-error" role="alert"><strong>{error}</strong><p>Votre saisie est conservée. Si une autre personne a modifié la fiche, rechargez avant de reprendre l’édition.</p>
      <button type="button" className="button secondary" disabled={busy||loading} onClick={()=>void reload()}>Recharger et abandonner le brouillon</button></div>}
    {notice&&<p className="identity-notice" role="status">{notice}</p>}
    {tab==="identity"&&<form className="card identity-form" onSubmit={(e:FormEvent)=>{e.preventDefault();if(!disabled&&Object.keys(draft).length)void save(()=>identityApi.patch(projectId,identity.revision,draft),"Fiche enregistrée.");}}>
      <div className="workspace-section-heading"><h2>Fiche du projet</h2>{identity.standby&&<Badge value="En attente"/>}</div>
      <p className="workspace-muted">{identity.code} · {identity.title}</p>
      {identity.legacy_client_name&&<p>Client historique : <strong>{identity.legacy_client_name}</strong></p>}
      <div className="identity-grid">{projectReferences.map(ref=><ReferencePicker key={ref.kind} kind={ref.kind} label={ref.label} value={field(ref.field)} current={identity.references[identity[ref.field]||""]} onChange={id=>change(ref.field,id)} disabled={disabled}/>)}</div>
      <p className="workspace-muted">Les clients, catégories et personnes se gèrent dans Réglages → Clients et équipe.</p>
      <div className="identity-grid"><PersonPicker label="Responsable projet" value={field("responsible_id")} current={identity.responsible} onChange={id=>change("responsible_id",id)} disabled={disabled}/>
        {textFields.map(([key,label,max])=><label key={key}>{label}<input className="input" value={field(key)} maxLength={max} disabled={disabled} onChange={e=>change(key,e.target.value)}/></label>)}
        <label>Quantité<input className="input" type="number" min={1} max={1000000} step={1} value={field("quantity")??""} disabled={disabled} onChange={e=>change("quantity",e.target.value?Number(e.target.value):null)}/></label>
        <label>Début du projet<input className="input" type="date" value={field("start_date")} disabled={disabled} onChange={e=>change("start_date",e.target.value)}/></label>
        <label>Fin prévisionnelle<input className="input" type="date" value={field("planned_end_date")} min={field("start_date")||undefined} disabled={disabled} onChange={e=>change("planned_end_date",e.target.value)}/></label>
      </div>
      <label>Description<textarea className="input" rows={4} value={field("description")} maxLength={20000} disabled={disabled} onChange={e=>change("description",e.target.value)}/></label>
      <label className="identity-checkbox"><input type="checkbox" checked={field("standby")} disabled={disabled} onChange={e=>change("standby",e.target.checked)}/>Projet en attente</label>
      {identity.offer_number&&<p>Numéro d’offre : {identity.offer_number}</p>}{identity.actual_closure_date&&<p>Clôture réelle : {identity.actual_closure_date}</p>}
      {!readOnly&&<div className="identity-actions"><button type="submit" className="button primary" disabled={disabled||!Object.keys(draft).length}>{busy?"Enregistrement…":"Enregistrer la fiche"}</button>
        <button type="button" className="button secondary" disabled={busy||!Object.keys(draft).length} onClick={()=>setDraft({})}>Annuler les modifications</button></div>}
    </form>}
    {tab==="team"&&<section className="card"><div className="workspace-section-heading"><h2>Équipe du projet</h2>{!readOnly&&<button type="button" className="button primary" disabled={disabled||!!teamDraft} onClick={()=>{setTeamDraft({...emptyMember});setError("");setNotice("");}}>Ajouter une affectation</button>}</div>
      <p className="workspace-muted">Les rôles décrivent les responsabilités métier. Ils ne modifient pas les droits d’accès.</p>
      <label className="identity-checkbox"><input type="checkbox" checked={archived} onChange={e=>setArchived(e.target.checked)}/>Afficher les affectations archivées</label>
      {!members.length&&<p>Aucune affectation {archived?"":"active "}dans ce projet.</p>}
      <div className="identity-member-list">{members.map(member=><article key={member.id} className="identity-member"><div><strong>{personName(member.person)}</strong><p>{identity.roles.find(role=>role.code===member.role)?.label||member.role}</p>
        <small>{member.start_date||"Début non renseigné"} → {member.end_date||"Fin non renseignée"}</small>{!member.active&&<Badge value="Affectation archivée"/>}{!member.person.active&&<Badge value="Personne archivée"/>}</div>
        {!readOnly&&member.active&&<div className="identity-actions"><button type="button" className="button secondary sm" disabled={disabled||!!teamDraft} onClick={()=>setTeamDraft({id:member.id,person_id:member.person_id,role:member.role,start_date:member.start_date,end_date:member.end_date})}>Modifier l’affectation</button>
          <button type="button" className="button secondary sm" disabled={disabled||!!teamDraft} onClick={()=>void save(()=>identityApi.archiveMember(projectId,identity.revision,member.id),"Affectation archivée ; son historique est conservé.")}>Archiver l’affectation</button></div>}
      </article>)}</div>
      {teamDraft&&<MemberForm key={teamDraft.id||"new"} draft={teamDraft} identity={identity} disabled={disabled} change={setTeamDraft} cancel={()=>{setTeamDraft(null);setError("");}} submit={()=>{
        if(disabled||!teamDraft.person_id)return;
        const data={person_id:teamDraft.person_id,role:teamDraft.role,start_date:teamDraft.start_date,end_date:teamDraft.end_date};
        void save(()=>teamDraft.id?identityApi.patchMember(projectId,identity.revision,teamDraft.id,data):identityApi.addMember(projectId,identity.revision,data),"Affectation enregistrée.");
      }}/>} </section>}
    {tab==="history"&&<IdentityHistory key={identity.revision} identity={identity}/>}
  </section>;
}
function MemberForm({draft,identity,disabled,change,cancel,submit}:{draft:TeamDraft;identity:ProjectIdentity;disabled:boolean;change:(draft:TeamDraft)=>void;cancel:()=>void;submit:()=>void}) {
  const current:ProjectMember|undefined=identity.members.find(row=>row.id===draft.id);
  return <form className="identity-member-form" onSubmit={e=>{e.preventDefault();submit();}}><h3>{draft.id?"Modifier une affectation":"Nouvelle affectation"}</h3><div className="identity-grid">
    <PersonPicker label="Personne à affecter" value={draft.person_id} current={current?.person} onChange={person_id=>change({...draft,person_id})} disabled={disabled||!!draft.id}/>
    <label>Rôle métier<select className="input" value={draft.role} disabled={disabled} onChange={e=>change({...draft,role:e.target.value as MemberRole})}>{identity.roles.map(role=><option key={role.code} value={role.code}>{role.label}</option>)}</select></label>
    <label>Début de l’affectation<input className="input" type="date" value={draft.start_date} disabled={disabled} onChange={e=>change({...draft,start_date:e.target.value})}/></label>
    <label>Fin de l’affectation<input className="input" type="date" value={draft.end_date} min={draft.start_date||undefined} disabled={disabled} onChange={e=>change({...draft,end_date:e.target.value})}/></label>
  </div><div className="identity-actions"><button className="button primary" type="submit" disabled={disabled||!draft.person_id}>Enregistrer l’affectation</button><button className="button secondary" type="button" disabled={disabled} onClick={cancel}>Annuler l’affectation</button></div></form>;
}
function IdentityHistory({identity}:{identity:ProjectIdentity}) {
  const projectId=identity.project_id;
  const [offset,setOffset]=useState(0);const [page,setPage]=useState<Page<IdentityChange>|null>(null);const [error,setError]=useState("");
  useEffect(()=>{const controller=new AbortController();setPage(null);setError("");identityApi.history(projectId,offset,controller.signal).then(value=>{if(!controller.signal.aborted)setPage(value);}).catch(e=>{if(!controller.signal.aborted)setError(String(e.message||e));});return()=>controller.abort();},[projectId,offset]);
  const format=(key:string,value:unknown)=>{
    if(value===null||value===undefined||value==="")return "—";
    if(typeof value==="boolean")return value?"Oui":"Non";
    if(key==="role")return identity.roles.find(role=>role.code===value)?.label||String(value);
    if(key==="person_id"||key==="responsible_id"){const person=identity.members.find(row=>row.person_id===value)?.person;return person?personName(person):String(value);}
    const ref=identity.references[String(value)];return ref?`${ref.code} · ${ref.label}`:String(value);
  };
  return <section className="card"><h2>Historique de la fiche et de l’équipe</h2>{error&&<p role="alert">{error}</p>}{!page&&!error&&<LoadingState label="Chargement de l’historique"/>}
    {page&&<><Pagination offset={page.offset} total={page.total} limit={page.limit} onChange={setOffset}/>{page.items.map(item=><details className="identity-history" key={item.id}><summary>{actionLabels[item.action]||item.action} · {item.created_at} · {item.actor_id}</summary>
      <table className="data-table"><thead><tr><th>Champ</th><th>Avant</th><th>Après</th></tr></thead><tbody>{Array.from(new Set([...Object.keys(item.previous),...Object.keys(item.value)])).filter(key=>key in fieldLabels&&JSON.stringify(item.previous[key])!==JSON.stringify(item.value[key])).map(key=><tr key={key}><td>{fieldLabels[key]}</td><td>{format(key,item.previous[key])}</td><td>{format(key,item.value[key])}</td></tr>)}</tbody></table>
    </details>)}</>}
  </section>;
}
