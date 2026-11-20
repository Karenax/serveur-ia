import { discoveryBoundLabel, type DocumentFolderDiscovery, type DocumentId, type DocumentWorkspace } from '../lib/projectDocuments';

type Props = {
  result: DocumentFolderDiscovery;
  workspace: DocumentWorkspace;
  disabled: boolean;
  onChoose: (documentId: DocumentId, path: string, existing: boolean) => void;
};

export function DocumentFolderResults({result, workspace, disabled, onChoose}: Props) {
  return <section className="document-discovery" aria-label="Documents trouvés dans le dossier">
    <p role="status">{result.examined.directories} dossier(s) parcouru(s).</p>
    {result.status!=='completed'&&<p className="document-warning">
      Recherche partielle. {result.bounds.length ? 'Limite atteinte : '+result.bounds.map(discoveryBoundLabel).join(', ')+'. ' : ''}
      Précisez le dossier ou choisissez un fichier.
    </p>}
    <ul className="document-candidates">
      {result.items.map(item=>{
        const label=workspace.templates.find(row=>row.id===item.document_id)?.label;
        const recommended=item.candidates.find(row=>row.relative_path===item.recommended_path);
        return <li key={item.document_id}>
          <div><strong>{label}</strong>
            {item.missing_fields.length>0&&<small>Données projet manquantes : {item.missing_fields.map(key=>workspace.fields[key]?.label||key).join(', ')}.</small>}
            {item.existing_files.map(file=><div className="document-actions" key={file.relative_path}>
              <button className="button secondary sm" type="button" disabled={disabled}
                onClick={()=>onChoose(item.document_id,file.relative_path,true)}>Partir du fichier existant · {file.filename}</button>
              <small className="document-path">{file.relative_path}</small>
            </div>)}
            {recommended&&<p className="document-path">{recommended.relative_path||recommended.filename}</p>}
            {item.candidates.length===0&&<small>Aucune trame trouvée.</small>}
            {item.candidates.length>0&&(!recommended||item.candidates.length>1)&&<details>
              <summary>{recommended?'Autres trames':'Choisir parmi les trames trouvées'} ({item.candidates.length-(recommended?1:0)})</summary>
              {item.candidates.filter(candidate=>candidate!==recommended).map(candidate=>
                <p key={candidate.relative_path}><button className="button secondary sm" type="button" disabled={disabled}
                  onClick={()=>onChoose(item.document_id,candidate.relative_path,false)}>
                  Choisir {candidate.relative_path||candidate.filename}
                </button></p>)}
            </details>}
          </div>
          {recommended&&<button className="button secondary sm" type="button" disabled={disabled}
            onClick={()=>onChoose(item.document_id,recommended.relative_path,false)} aria-label={'Choisir la trame · '+label}>Choisir la trame</button>}
        </li>;
      })}
    </ul>
  </section>;
}
