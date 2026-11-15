"""Freeze actual references, then flag changes during ordinary assistant output."""
import hashlib
import json

from ..models import KnowledgeItem, Source, SourceArtifact, ProvenanceLink


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def freeze(db, metadata):
    from .scoped_assistant import source_stamp
    versions = {}
    for citation in metadata.get('citations', []):
        source_id = citation.get('source_id')
        if source_id:
            source = db.get(Source, source_id)
            if source:
                from fastapi import HTTPException
                from .project_access import require_brain
                try:
                    require_brain(source.project_id)
                except HTTPException:
                    citation.update(source_id=None, provenance_unavailable=True)
                    metadata.setdefault('warnings', []).append('Une provenance est hors du périmètre autorisé')
                    source = None
            if source:
                versions['source:' + source_id] = source_stamp(db, source_id)
                if versions['source:' + source_id] is None:
                    citation['historical_or_unavailable'] = True
                    metadata['context_incomplete'] = True
                    metadata.setdefault('warnings', []).append(
                        'Une preuve est historique ou indisponible : vérifier la version applicable.')
                data = source.source_metadata or {}
                citation['title'] = data.get('subject') or data.get('filename') or source.source_type
                citation['source_url'] = f'/v1/sources/{source_id}'
                if data.get('note_id') and data.get('note_version_id'):
                    citation['locator'] = {key: data[key] for key in ('note_id', 'note_version_id', 'note_revision', 'erp_project_id') if key in data}
                    citation['source_url'] = f"/api/v1/projects/{data['erp_project_id']}/notes/{data['note_id']}/versions/{data['note_version_id']}"
                else:
                    from .unified_search import lexical
                    artifacts = [a for a in db.query(SourceArtifact).filter_by(source_id=source_id)
                                 if a.content_text and not (a.content_json or {}).get('superseded')]
                    if artifacts:
                        artifact = max(artifacts, key=lambda a: lexical(citation.get('excerpt', ''), a.content_text)[0])
                        locator = dict(artifact.content_json or {})
                        for key in ('content', 'source_metadata', 'provenance'):
                            locator.pop(key, None)
                        citation['locator'] = {**locator, 'artifact_id': artifact.id}
        knowledge_id = citation.get('knowledge_id')
        knowledge = db.get(KnowledgeItem, knowledge_id) if knowledge_id else None
        if knowledge:
            versions['knowledge:' + knowledge.id] = _hash([knowledge.status, knowledge.version, knowledge.value])
            # Retained facts can legitimately cite a historical immutable note
            # version. The Source head must never silently rewrite that pointer.
            link = db.query(ProvenanceLink).filter_by(knowledge_item_id=knowledge.id,
                                                     source_id=citation.get('source_id')).first()
            if link and link.locator:
                citation['locator'] = dict(link.locator)
                locator = citation['locator']
                if all(locator.get(key) for key in ('erp_project_id', 'note_id', 'note_version_id')):
                    citation['source_url'] = f"/api/v1/projects/{locator['erp_project_id']}/notes/{locator['note_id']}/versions/{locator['note_version_id']}"
    metadata['context_versions'] = versions
    return metadata


def finalize(db, metadata):
    from .scoped_assistant import source_stamp
    db.expire_all()
    changed = False
    for identity, stamp in metadata.get('context_versions', {}).items():
        kind, identifier = identity.split(':', 1)
        if kind == 'source':
            current = source_stamp(db, identifier)
        else:
            knowledge = db.get(KnowledgeItem, identifier)
            current = _hash([knowledge.status, knowledge.version, knowledge.value]) if knowledge else None
        changed |= current != stamp
    result = {**metadata, 'stale': bool(metadata.get('context_incomplete')) or changed}
    if changed:
        result['warnings'] = [*result.get('warnings', []), 'Une source ou information a changé pendant la réponse ; interroger à nouveau le contexte actuel.']
    return result
