import { useEffect, useRef, useState } from 'react';
import { blockerLabel, discoveryBoundLabel, documentApi, originLabel, warningLabel, type DocumentChoice, type DocumentDiscovery, type DocumentId, type DocumentLink,
  type DocumentFolderDiscovery, type DocumentPreview, type DocumentWorkspace } from '../lib/projectDocuments';
import { Pagination } from './IdentityPickers';
import { useAlive, message } from './PlanningTasksPanel';
import './project-documents.css';
import { DocumentFormPersistence } from './DocumentFormPersistence';
import { DocumentBatchPanel } from './DocumentBatchPanel';
import { DocumentFolderResults } from './DocumentFolderResults';

export function ProjectDocumentsPanel(props:{projectId:string;active?:boolean}) {return <DocumentsView key={props.projectId} {...props}/>;}
function DocumentsView({projectId,active=true}:{projectId:string;active?:boolean}) {
  const [workspace,setWorkspace]=useState<DocumentWorkspace|null>(null),[offset,setOffset]=useState(0),[tick,setTick]=useState(0);
  const [documentId,setDocumentId]=useState<DocumentId|null>(null),[link,setLink]=useState<DocumentLink|null>(null),[path,setPath]=useState('');
  const [overrides,setOverrides]=useState<Record<string,string>>({}),[preview,setPreview]=useState<DocumentPreview|null>(null);
  const [confirmed,setConfirmed]=useState(false),[loading,setLoading]=useState(false),[busy,setBusy]=useState<'preview'|'copy'|'discovery'|'folder'|null>(null);
  const [discovery,setDiscovery]=useState<DocumentDiscovery|null>(null);
  const [folderResult,setFolderResult]=useState<{result:DocumentFolderDiscovery;link:DocumentLink}|null>(null);
  const [error,setError]=useState(''),[loadError,setLoadError]=useState(''),[notice,setNotice]=useState('');
  const [formBusy,setFormBusy]=useState(false),[formDirty,setFormDirty]=useState(false);
  const [batchBusy,setBatchBusy]=useState(false);
  const [download,setDownload]=useState<{url:string;name:string;sha256:string}|null>(null);
  const action=useRef<AbortController|null>(null),alive=useAlive();
  const scanSelection=useRef<DocumentId|null>(null),sourceForm=useRef<HTMLFormElement>(null);
  const invalid=()=>{setPreview(null);setConfirmed(false);setDownload(null);setNotice('');setError('');};
  useEffect(()=>{if(!active)return;const controller=new AbortController();setLoading(true);setLoadError('');
    setPreview(null);setConfirmed(false);setDownload(null);setDiscovery(null);setFolderResult(null);
    documentApi.workspace(projectId,offset,controller.signal).then(value=>{if(!controller.signal.aborted){setWorkspace(value);setDocumentId(previous=>previous||value.templates[0]?.id||null);}})
      .catch(e=>{if(!controller.signal.aborted)setLoadError(message(e));}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    return()=>controller.abort();},[projectId,active,offset,tick]);
  useEffect(()=>()=>action.current?.abort(),[]);
  useEffect(()=>{if(!active){action.current?.abort();setBusy(null);}},[active]);
  useEffect(()=>()=>{if(download)URL.revokeObjectURL(download.url);},[download]);
  const template=workspace?.templates.find(row=>row.id===documentId);
  const mapped=[...new Set([...(template?.cells||[]),...(template?.bookmarks||[])].map(([,field])=>field))];
  const disabled=!active||loading||!!busy||!!loadError||formBusy||batchBusy;
  const rootLink=workspace?.links.items.find(row=>row.path&&row.code.toLowerCase()==='projet')||
    workspace?.links.items.find(row=>row.path&&row.code.toLowerCase()==='affaire')||
    workspace?.links.items.find(row=>row.path&&row.code==='dossier_client_kiara');
  const folderLink=link?.path&&!link.missing?link:rootLink;
  const ready=!!workspace&&workspace.file_access.status==='configured'&&!!documentId&&!!link&&!link.missing&&!disabled;
  const choice=():DocumentChoice=>({document_id:documentId!,link_id:link!.id,relative_path:path.trim()==='.'?'':path.trim().split('\\').join('/'),overrides});
  async function discover(){if(!ready)return;const controller=new AbortController();action.current=controller;invalid();setDiscovery(null);setBusy('discovery');
    try{const value=await documentApi.discover(projectId,documentId!,link!.id,controller.signal);
      if(alive.current&&!controller.signal.aborted){if(value.project_id!==projectId||value.document_id!==documentId||value.link_id!==link!.id)
        throw new Error('Résultats reçus différents du projet, du lien ou de la trame sélectionnés');setDiscovery(value);}}
    catch(e){if(alive.current&&!controller.signal.aborted)setError(message(e));}
    finally{if(alive.current&&action.current===controller){setBusy(null);action.current=null;}}}
  async function discoverFolder(){
    if(disabled||!folderLink||workspace?.file_access.status!=='configured')return;
    const controller=new AbortController();action.current=controller;setError('');setNotice('');setFolderResult(null);setBusy('folder');
    try{
      const result=await documentApi.discoverFolder(projectId,folderLink.id,controller.signal);
      if(alive.current&&!controller.signal.aborted){
        if(result.project_id!==projectId||result.link_id!==folderLink.id)throw new Error('La recherche a renvoyé un autre dossier. Relancez-la.');
        setFolderResult({result,link:folderLink});
      }
    }catch(e){if(alive.current&&!controller.signal.aborted)setError(message(e));}
    finally{if(alive.current&&action.current===controller){setBusy(null);action.current=null;}}
  }
  function chooseFound(id:DocumentId,relativePath:string,existing:boolean){
    if(!folderResult||disabled)return;
    if(id!==documentId){
      if(formDirty&&!window.confirm('Changer de trame sans enregistrer les choix modifiés ?'))return;
      scanSelection.current=id;
      setDocumentId(id);setOverrides({});setFormDirty(false);
    }
    invalid();setDiscovery(null);setLink(folderResult.link);setPath(relativePath);
    setNotice(existing?'Fichier existant sélectionné. Vérifiez les changements dans l’aperçu.':'Trame sélectionnée. Affichez l’aperçu pour vérifier son contenu.');
    sourceForm.current?.focus();
  }
  async function inspect(){if(!ready)return;const controller=new AbortController();action.current=controller;invalid();setBusy('preview');
    try{const value=await documentApi.preview(projectId,choice(),controller.signal);
      if(alive.current&&!controller.signal.aborted){if(value.source.project_id!==projectId||value.document_id!==documentId||value.source.link_id!==link!.id)
        throw new Error('Aperçu reçu différent du projet ou de la trame sélectionnés');setPreview(value);}}
    catch(e){if(alive.current&&!controller.signal.aborted)setError(message(e));}
    finally{if(alive.current&&action.current===controller){setBusy(null);action.current=null;}}}
  async function prepare(){if(!ready||!confirmed||!preview?.can_prepare||!preview.can_prepare_copy)return;
    const controller=new AbortController();action.current=controller;setBusy('copy');setError('');setDownload(null);setNotice('');
    try{const result=await documentApi.copy(projectId,choice(),preview,controller.signal);
      if(alive.current&&!controller.signal.aborted){setDownload({url:URL.createObjectURL(result.blob),name:result.filename,sha256:result.sha256});
        setNotice('Copie prête et vérifiée. Utilisez le lien pour l’enregistrer.');}}
    catch(e){if(alive.current&&!controller.signal.aborted){setError(message(e));setPreview(null);setConfirmed(false);}}
    finally{if(alive.current&&action.current===controller){setBusy(null);action.current=null;}}}
  const sourceValues=preview?.field_values||workspace;
  return <section className="project-documents" aria-label="Préparation des documents projet" data-workspace-dirty={formDirty||(!workspace?.search_preferences?.available&&Object.keys(overrides).length)?'true':undefined}>
    <header className="planning-heading"><div><h3>Préparer un document</h3><p>Choisissez une trame, vérifiez les informations puis téléchargez la copie.</p></div>
      <button className="button secondary sm" type="button" disabled={disabled} onClick={()=>{invalid();setTick(value=>value+1);}}>Actualiser les informations</button></header>
    {loadError&&<div role="alert" className="state-panel error"><p>{loadError}</p><button type="button" className="button secondary" onClick={()=>setTick(value=>value+1)}>Réessayer</button></div>}
    {loading&&<p role="status">Lecture des liens et des informations projet…</p>}
    {workspace&&<><ol className="document-steps" aria-label="Étapes de préparation"><li className={!preview?'current':''}>1 · Trame et informations</li>
      <li className={preview&&!download?'current':''}>2 · Aperçu et vérification</li><li className={download?'current':''}>3 · Copie à enregistrer</li></ol>
      {workspace.file_access.status!=='configured'&&<p role="status" className="document-warning">{workspace.file_access.detail}. Contactez l’administrateur pour activer l’accès aux trames.</p>}
      {!workspace.can_prepare_copy&&<p className="document-warning">Lecture seule : vous pouvez consulter l’aperçu. La préparation est réservée aux personnes autorisées à modifier le projet.</p>}
      <div className="document-actions"><button className="button secondary" type="button"
        disabled={disabled||!folderLink||workspace.file_access.status!=='configured'} onClick={()=>void discoverFolder()}>
        Rechercher les documents</button>
        {folderLink&&<p className="document-path">{folderLink.path}</p>}
      </div>
      {folderResult&&<DocumentFolderResults result={folderResult.result} workspace={workspace} disabled={disabled} onChoose={chooseFound}/>}
      {documentId&&<DocumentFormPersistence projectId={projectId} documentId={documentId} active={active}
        installed={!!workspace.search_preferences?.available} canEdit={workspace.can_prepare_copy} disabled={loading||!!busy||!!loadError||batchBusy}
        choice={{link_id:link?.id||null,relative_path:path,overrides}} onBusy={setFormBusy} onDirty={setFormDirty}
        fieldLabels={Object.fromEntries(Object.entries(workspace.fields).map(([key,value])=>[key,value.label]))}
        onApply={(saved,initial)=>{if(initial&&scanSelection.current===documentId){
          scanSelection.current=null;setOverrides({...saved.overrides});return;
        }
          invalid();setDiscovery(null);setLink(saved.selected_link||(saved.link_id?{id:saved.link_id,code:'Lien absent',label:'Lien absent',path:'',order:0,missing:true}:null));
          setPath(saved.relative_path);setOverrides({...saved.overrides});}}/>}
      <form ref={sourceForm} tabIndex={-1} onSubmit={e=>{e.preventDefault();void inspect();}} aria-label="Choix de la trame documentaire">
        <fieldset disabled={disabled}><legend>1 · Trame et fichier source</legend>
          <div className="document-template-grid">{workspace.templates.map(row=><label className={`document-template ${documentId===row.id?'selected':''}`} key={row.id}>
            <input type="radio" name="document-template" checked={documentId===row.id} onChange={()=>{if(formDirty&&!window.confirm('Changer de trame sans enregistrer les choix modifiés ?'))return;
              scanSelection.current=null;invalid();setDiscovery(null);setDocumentId(row.id);setOverrides({});setFormDirty(false);}}/>
            <span><strong>{row.label}</strong><small>{row.format}</small></span></label>)}</div>
          <label className="document-source">Dossier ou fichier du projet<select className="input" value={link?.id||''} onChange={e=>{invalid();setDiscovery(null);setPath('');setLink(workspace.links.items.find(row=>row.id===e.target.value)||null);}}>
            <option value="">Choisir un dossier ou un fichier lié au projet</option>
            {link&&!workspace.links.items.some(row=>row.id===link.id)&&<option value={link.id}>{link.label||link.code} · sélection conservée</option>}
            {workspace.links.items.map(row=><option key={row.id} value={row.id}>{row.label||row.code} · {row.path||'Chemin à renseigner'}</option>)}</select></label>
          {link&&<p className="document-path">{link.path}</p>}
          <Pagination {...workspace.links} onChange={setOffset} disabled={disabled}/>
          {!workspace.links.total&&<p>Aucun dossier ou fichier renseigné. Ajoutez-le dans « Fichiers et dossiers ».</p>}
          <details className="document-source-options"><summary>Choisir un fichier précis</summary>
          <label className="document-source">Fichier de la trame dans ce lien<input className="input" value={path} maxLength={2048}
            placeholder={`Ex. Trames/Demande.${template?.format.toLowerCase()||'docx'} — vide si le lien désigne le fichier`} onChange={e=>{invalid();setPath(e.target.value);}}/></label>
          <p className="document-help">Indiquez le fichier à l’intérieur du dossier sélectionné. Laissez ce champ vide si le fichier est déjà sélectionné.</p></details>
          <button className="button secondary" type="button" disabled={!ready||template?.search_active===false} onClick={()=>void discover()}>Rechercher les trames dans ce lien</button>
          {template?.search_active===false&&<p className="document-help">La recherche est désactivée pour cette trame dans les réglages documentaires. La sélection manuelle reste disponible.</p>}
          {discovery&&<section className="document-discovery" aria-label="Trames trouvées dans le lien projet"><h4>Résultats de la recherche</h4>
            <p role="status">{discovery.candidates.length} candidat(s) · {discovery.examined.files} fichier(s) observé(s) · {discovery.examined.directories} dossier(s) parcouru(s).</p>
            {discovery.status!=='completed'&&<p className="document-warning">Recherche partielle{discovery.bounds.length?` : limite de ${discovery.bounds.map(discoveryBoundLabel).join(', ')} atteinte`: ' : annulée'}.
              Les résultats ne couvrent pas tout le dossier. Précisez le lien ou saisissez le fichier directement.</p>}
            {discovery.ambiguous&&discovery.candidates.length>1&&<p className="document-warning">Plusieurs correspondances possibles. Vérifiez le nom et l’indice avant de choisir.</p>}
            {!discovery.candidates.length&&<p>Aucune trame correspondante. Vous pouvez saisir le chemin relatif du fichier ci-dessus.</p>}
            <details><summary>Critères de recherche</summary><p>Dossiers : {discovery.rule.relative_paths.join(' ou ')}.</p>
              <p>Mots du nom : {discovery.rule.filename_patterns.join(' ou ')}. Les mots d’un motif sont tous requis.</p>
              {!!discovery.rule.excluded_tokens.length&&<p>Exclusions : {discovery.rule.excluded_tokens.join(', ')}.</p>}
              {discovery.rule.preferred_version!==null&&<p>Indice préféré : {discovery.rule.preferred_version}.</p>}</details>
            <ul className="document-candidates">{discovery.candidates.map(candidate=><li key={candidate.relative_path}>
              <div><strong>{candidate.filename}</strong><p className="document-path">{candidate.relative_path||'Fichier désigné par le lien'}</p>
                <small>{(candidate.size_bytes/1024).toLocaleString('fr-FR',{maximumFractionDigits:1})} Ko · {candidate.version===null?'Indice non détecté':`Indice ${candidate.version} ${candidate.version_origin==='explicit'?'indiqué dans le nom':'déduit des nombres du nom'}`}
                  {discovery.recommended_path===candidate.relative_path&&' · Meilleure correspondance observée'}</small>
                <small>Dossier : {candidate.direct_file_link?'lien direct':candidate.matched_paths.join(' ou ')} · Nom : {candidate.matched_patterns.join(' ou ')}</small></div>
              <button className="button secondary sm" type="button" onClick={()=>{invalid();setPath(candidate.relative_path);setNotice('Trame sélectionnée. Affichez l’aperçu pour vérifier son contenu.');}}
                aria-label={`Choisir la trame ${candidate.relative_path||candidate.filename}`}>Choisir cette trame</button></li>)}</ul>
            <p className="document-help">La recherche observe les noms et emplacements. L’aperçu vérifiera le fichier choisi et ses cellules ou signets.</p>
          </section>}
        </fieldset>
        {template&&<fieldset disabled={disabled}><legend>Informations de cette copie</legend><p className="document-help">Les corrections ci-dessous s’appliquent à ce document. Pour actualiser les données communes, utilisez la fiche projet ou les référentiels.</p>
          <div className="document-field-grid">{mapped.map(key=>{const field=workspace.fields[key],corrected=Object.prototype.hasOwnProperty.call(overrides,key);
            return <div className="document-field" key={key}><label>{field?.label||key}<textarea className="input" rows={key==='description'?3:1}
              value={corrected?overrides[key]:workspace.values[key]||''} readOnly={field?.edit_scope===null} maxLength={10_000}
              onChange={e=>{invalid();setOverrides(value=>({...value,[key]:e.target.value}));}}/></label>
              <small>{corrected?'Correction de cette copie':originLabel(workspace.origins[key])}</small>
              {corrected&&<button className="button secondary sm" type="button" onClick={()=>{invalid();setOverrides(value=>{const next={...value};delete next[key];return next;});}}>Revenir à la donnée projet · {field?.label||key}</button>}
            </div>;})}</div>
          {sourceValues?.warnings.map(code=><p key={code} className="document-warning">{warningLabel(code)}</p>)}
        </fieldset>}
        <div className="document-actions"><button className="button primary" type="submit" disabled={!ready}>{busy==='preview'?'Lecture de la trame…':'Afficher l’aperçu'}</button>
          {busy&&<button className="button secondary" type="button" onClick={()=>{action.current?.abort();setBusy(null);setNotice('Opération annulée.');}}>Annuler l’opération</button>}</div>
      </form>
      {error&&<p role="alert" className="document-warning">{error}</p>}
      {busy&&<p role="status" className={busy==='discovery'||busy==='folder'?'document-searching':undefined}>{busy==='folder'?'Recherche des documents dans le dossier…':busy==='discovery'?'Recherche des trames dans le lien sélectionné… Le nombre total de fichiers est encore inconnu.':busy==='preview'?'Analyse des emplacements de la trame…':'Préparation et vérification de la copie…'}</p>}
      {preview&&<section className="document-preview" aria-label="Aperçu des informations à remplir"><h4>2 · Vérifier la copie</h4>
        <p><strong>{preview.source.filename}</strong> · {(preview.size_bytes/1024).toLocaleString('fr-FR',{maximumFractionDigits:1})} Ko{preview.sheet&&` · Feuille « ${preview.sheet} »`}</p>
        {preview.output_filename&&<p>Nom de la copie : <strong>{preview.output_filename}</strong></p>}
        {preview.missing_fields.length>0&&<p className="document-warning">À compléter : {preview.missing_fields.map(key=>workspace.fields[key]?.label||key).join(', ')}.</p>}
        {preview.blockers.map(code=><p className="document-warning" key={code}>{blockerLabel(code)}{code.startsWith('target_unavailable:')&&` · ${workspace.fields[code.split(':')[1]]?.label||code.split(':')[1]}`}</p>)}
        <div className="document-table-scroll"><table className="data-table"><thead><tr><th>Emplacement</th><th>Champ et origine</th><th>Texte actuel</th><th>Texte proposé</th><th>État</th></tr></thead>
          <tbody>{preview.targets.map((target,index)=><tr key={`${target.target}-${index}`}><td>{target.kind==='cell'?'Cellule':'Signet'} {target.target}</td>
            <td>{workspace.fields[target.field]?.label||target.field}<small>{originLabel(preview.field_values.origins[target.field])}</small></td>
            <td>{target.existing_value||'—'}</td><td>{target.proposed_value||'À renseigner'}</td><td>{target.available?(target.replaces_placeholder?'Formule de préremplissage remplacée':'Disponible'):target.blockers.map(blockerLabel).join(' ')}</td></tr>)}</tbody></table></div>
        {!!preview.unmapped_fields.length&&<p className="document-help">Champs sans emplacement dans cette trame : {preview.unmapped_fields.map(key=>workspace.fields[key]?.label||key).join(', ')}.</p>}
        {!!Object.keys(preview.macro_parts).length&&<p className="document-help">Les macros existantes sont conservées dans la copie. Elles ne sont pas exécutées pendant la préparation.</p>}
        <label className="document-confirm"><input type="checkbox" disabled={disabled||!preview.can_prepare||!preview.can_prepare_copy} checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/>J’ai vérifié les informations proposées pour cette copie.</label>
        <button className="button primary" type="button" disabled={disabled||!confirmed||!preview.can_prepare||!preview.can_prepare_copy} onClick={()=>void prepare()}>Préparer la copie</button>
        <p className="document-help">La trame source reste intacte. L’enregistrement sur le réseau se fera ensuite depuis votre téléchargement.</p>
      </section>}
      {notice&&<p role="status">{notice}</p>}
      {download&&<section className="document-download" aria-label="Copie prête à enregistrer"><h4>3 · Enregistrer la copie</h4>
        <a className="button primary" href={download.url} download={download.name}>Télécharger {download.name}</a>
        <details><summary>Vérification de la copie</summary><p className="document-path">SHA-256 : {download.sha256}</p></details></section>}
      {workspace.batch_available&&<DocumentBatchPanel projectId={projectId} active={active} canEdit={workspace.can_prepare_copy}
        disabled={loading||!!busy||!!loadError||formBusy} choice={link&&documentId?choice():null} preview={preview} reviewed={confirmed}
        templates={workspace.templates} onBusy={setBatchBusy}/>}
    </>}
  </section>;
}
