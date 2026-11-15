"""Source-backed project information is retained by default, with reversible demotion."""
from datetime import datetime, timezone

from fastapi import HTTPException

from ..models import KnowledgeItem, Proposal, ProvenanceLink, Source, ValidationDecision, MemoryProjection


def accept_by_default(db, proposal):
    from ..routers.core import _canonical_validation_lock, _project_truth
    if proposal.status != 'pending' or proposal.kind == 'project_attach' or not proposal.project_id:
        return False
    source = db.get(Source, proposal.source_id) if proposal.source_id else None
    if not source or source.status != 'resolved' or source.project_id != proposal.project_id:
        return False
    if not proposal.value.strip():
        return False
    with _canonical_validation_lock:
        # Short SQLite write claim; default acceptance and provenance share the transaction.
        changed = db.query(Proposal).filter_by(id=proposal.id, status='pending').update(
            {Proposal.status: 'pending'}, synchronize_session=False)
        if not changed:
            return False
        db.refresh(source)
        if source.status != 'resolved' or source.project_id != proposal.project_id:
            return False
        if db.query(KnowledgeItem).filter_by(project_id=proposal.project_id, kind=proposal.kind,
                                            subject=proposal.subject, value=proposal.value, status='invalidated').first():
            proposal.reason = 'Information déclassée précédemment ; rétablissement humain nécessaire'
            return False
        item = _project_truth(db, proposal.project_id, proposal.kind, proposal.subject, proposal.value,
                              'auto-default', source.id, proposal.confidence, default_accept=True)
        proposal.status = 'accepted'
        db.add(ValidationDecision(proposal_id=proposal.id, decision='accept', actor='auto-default',
                                  comment='Information retenue par défaut ; déclassable', resulting_knowledge_id=item.id))
        db.flush()
    return True


def promote_pending(db, limit=None):
    query = db.query(Proposal).join(Source, Proposal.source_id == Source.id).filter(
        Proposal.status == 'pending', Proposal.kind != 'project_attach',
        Source.status == 'resolved', Source.project_id == Proposal.project_id).order_by(Proposal.created_at, Proposal.id)
    if limit is not None:
        query = query.limit(limit)
    rows = query.all()
    result = {'retained': 0, 'skipped': 0}
    for proposal in rows:
        result['retained' if accept_by_default(db, proposal) else 'skipped'] += 1
    db.commit()
    return result


def change_status(db, project_id, knowledge_id, action, actor, comment=None):
    from ..routers.core import _canonical_validation_lock, _audit
    if action == 'confirm':
        from .knowledge_context import contexts
        from backend.app.services.project_operator import current_operator
        from .project_access import require_brain
        require_brain(project_id)
        operator = current_operator()
        if operator.role == 'reader':
            raise HTTPException(403, 'Opérateur en lecture seule')
        with _canonical_validation_lock:
            item = db.get(KnowledgeItem, knowledge_id)
            if not item or item.project_id != project_id:
                raise HTTPException(404, 'Information inconnue dans ce projet')
            if item.status != 'validated':
                raise HTTPException(409, 'Rétablir puis examiner cette information avant confirmation')
            if item.validated_by != 'auto-default':
                return {'id': item.id, 'status': item.status, 'validation_mode': 'human'}
            context = contexts(db, [item])[item.id]
            if not context['can_confirm']:
                raise HTTPException(409, 'Vérifier les preuves et résoudre les valeurs concurrentes avant confirmation')
            changed = db.query(KnowledgeItem).filter_by(id=item.id, status='validated',
                validated_by='auto-default', version=item.version).update({
                    KnowledgeItem.validated_by: operator.id,
                    KnowledgeItem.validated_at: datetime.now(timezone.utc)}, synchronize_session=False)
            if changed != 1:
                raise HTTPException(409, 'Information modifiée : actualisez la liste')
            _audit(db, 'knowledge.confirmed.v1', project_id, operator.id,
                   {'knowledge_id': item.id, 'comment': comment, 'declared_actor': actor})
            db.commit()
        return {'id': knowledge_id, 'status': 'validated', 'validation_mode': 'human'}
    if action not in {'invalidate', 'restore'}:
        raise HTTPException(404, 'Action de connaissance inconnue')
    target = 'invalidated' if action == 'invalidate' else 'validated'
    with _canonical_validation_lock:
        item = db.get(KnowledgeItem, knowledge_id)
        if not item or item.project_id != project_id:
            raise HTTPException(404, 'Information inconnue dans ce projet')
        if item.status == target:
            return {'id': item.id, 'status': item.status}
        if item.status not in {'validated', 'invalidated'}:
            raise HTTPException(409, 'Cette version a été remplacée')
        links = db.query(ProvenanceLink).filter_by(knowledge_item_id=item.id).all()
        if action == 'restore' and links:
            sources = [db.get(Source, link.source_id) for link in links]
            if not any(s and s.status == 'resolved' and s.project_id == project_id for s in sources):
                raise HTTPException(409, 'La source ne relève plus de ce projet')
        changed = db.query(KnowledgeItem).filter_by(id=item.id, status=item.status, version=item.version).update(
            {KnowledgeItem.status: target}, synchronize_session=False)
        if not changed:
            raise HTTPException(409, 'Information modifiée entre-temps ; actualisez la vue')
        db.refresh(item)
        if action == 'invalidate':
            item.valid_to = datetime.now(timezone.utc)
            for projection in db.query(MemoryProjection).filter_by(knowledge_item_id=item.id):
                projection.status = 'obsolete'
        else:
            item.valid_to = None
        decisions = db.query(ValidationDecision).filter_by(resulting_knowledge_id=item.id).all()
        ids = {decision.proposal_id for decision in decisions}
        for proposal in db.query(Proposal).filter(Proposal.id.in_(ids)):
            source = db.get(Source, proposal.source_id) if proposal.source_id else None
            if action == 'restore' and (not source or source.status != 'resolved' or source.project_id != project_id):
                continue
            proposal.status = 'rejected' if action == 'invalidate' else 'accepted'
            db.add(ValidationDecision(proposal_id=proposal.id, resulting_knowledge_id=item.id,
                                      decision='reject' if action == 'invalidate' else 'accept', actor=actor, comment=comment))
        _audit(db, 'knowledge.' + ('demoted' if action == 'invalidate' else 'restored') + '.v1',
               project_id, actor, {'knowledge_id': item.id, 'comment': comment})
        db.commit()
    return {'id': item.id, 'status': item.status}
