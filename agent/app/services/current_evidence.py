"""Read canonical versions before using derived evidence; failures close the scope."""


def is_current_evidence(source, *, erp_factory=None):
    if source is None or source.status != "resolved" or not source.project_id:
        return False
    metadata = source.source_metadata or {}
    if metadata.get("superseded"):
        return False
    if metadata.get("origin_kind") == "erp_note":
        from .note_evidence_bridge import current_source_version
        return current_source_version(metadata, erp_factory=erp_factory)["eligible"]
    return True


def current_contents(db, project_ids):
    from ..models import Source, SourceArtifact
    sources = {s.id: s for s in db.query(Source).filter(
        Source.project_id.in_(project_ids), Source.status == "resolved")
        if is_current_evidence(s)}
    contents = {}
    for artifact in db.query(SourceArtifact).filter(SourceArtifact.source_id.in_(sources)):
        if artifact.kind not in {"audio_pending", "attachment_status"} and not (artifact.content_json or {}).get("superseded"):
            contents.setdefault(artifact.source_id, []).append(artifact.content_text or "")
    return {sid: "\n".join(parts) for sid, parts in contents.items()}
