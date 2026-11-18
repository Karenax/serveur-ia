import {useEffect, useState} from "react";
import {agentPath} from '../lib/agentRoutes';
import {workspaceApi, type WorkspaceCitation, type WorkspaceSource} from '../lib/workspaceApi';
import {citationSourceUrl, citationReaderUrl, citationAudioUrl, citationLocatorText, isNoteVersionUrl} from '../lib/citationLinks';
import {Glyph, P} from '../os/icons';
import {AsyncDownloadLink} from './AsyncDownloadLink';
import {MessageContent} from './MessageContent';
import {NoteVersionPreview} from './NoteVersionPreview';
import {Modal} from './WorkspaceModal';
import {dateLabel, errorMessage} from './workspaceViewUtils';
import '../workspace-views.css';

export function SourceInspector({sourceId, evidence = [], title = "Source et preuve", onClose}: {
  sourceId: string; evidence?: WorkspaceCitation[]; title?: string; onClose: () => void;
}) {
  const [source, setSource] = useState<WorkspaceSource | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    let live = true;
    setSource(null); setError(""); setLoading(true);
    void workspaceApi.source(sourceId, controller.signal).then(value => {if (live) setSource(value);}).catch(cause => {
      if (live && !controller.signal.aborted) setError(errorMessage(cause));
    }).finally(() => {if (live) setLoading(false);});
    return () => {live = false; controller.abort();};
  }, [sourceId, retry]);
  const citations = evidence.filter(item => item.source_id === sourceId);
  return <Modal title={title} onClose={onClose}>
    <div className="workspace-source-content">
      {citations.map((citation, index) => <section className="workspace-proof" key={index} aria-label={`Preuve ${index + 1}`}>
        <strong>{citation.title || "Extrait cité"}</strong>
        {citation.excerpt && <blockquote>{citation.excerpt}</blockquote>}
        {citationSourceUrl(citation)&&<a href={agentPath(citationReaderUrl(citation)!)} target="_blank" rel="noreferrer">{isNoteVersionUrl(citationSourceUrl(citation))?'Ouvrir la version citée':'Consulter la source citée'}</a>}
        <NoteVersionPreview citation={citation}/>
        {citation.locator && <p className="workspace-meta">{citationLocatorText(citation.locator,' : ')}</p>}
        {citationAudioUrl(citation) && <audio controls preload="metadata" src={agentPath(citationAudioUrl(citation)!)}>Lecture audio indisponible.</audio>}
      </section>)}
      {loading && <p role="status">Chargement de la source…</p>}
      {error && <div role="alert"><p>{error}</p><button type="button" onClick={() => setRetry(value => value + 1)}>Réessayer</button></div>}
      {source && <>
        <div className="workspace-source-heading"><h3>{source.metadata.subject || source.metadata.filename || "Source originale"}</h3>
          <p className="workspace-meta">{source.author || "Auteur non précisé"} · {dateLabel(source.received_at)} · {source.type}</p>
          <AsyncDownloadLink href={source.metadata.note_version_id?`/api/v1/workspace/sources/${encodeURIComponent(source.id)}/original`:`/v1/sources/${encodeURIComponent(source.id)}/raw`} target="_blank" rel="noreferrer">{source.metadata.note_version_id?'Télécharger la version actuelle de note':'Télécharger l’original'} <Glyph d={P.download} size={16} /></AsyncDownloadLink>
        </div>
        {(source.body_html || source.artifacts.length) ? (source.body_html ? [{id:"original-mail",kind:"body_text",text:source.body_html}] : source.artifacts).map(artifact => <section key={artifact.id} className="workspace-source-text">
          <h4>{({body_text: "Texte du message", transcription: "Transcription", transcription_snapshot: "Transcription avant correction (historique)", ocr: "Texte du document", document_page: "Texte du document", sheet_row: "Ligne du tableur", document_text: "Texte du document", web_page: "Texte de la page web", media: "Fichier image ou audio"} as Record<string, string>)[artifact.kind] || "Contenu extrait"}</h4>
          {source.type === "email" || artifact.kind === "body_text" ? <MessageContent text={artifact.text || "Aucun texte disponible pour cette version."} inlineImages={source.inline_images}/> : <pre>{artifact.text || "Aucun texte disponible pour cette version."}</pre>}
        </section>) : <p>Cette source ne contient pas de texte extrait. Consultez le fichier original.</p>}
      </>}
    </div>
  </Modal>;
}
