"""Read-only qualification of retained facts; never rewrite human decisions."""
from collections import defaultdict
import unicodedata

from sqlalchemy import func

from ..models import KnowledgeItem, ProvenanceLink, Source
from .current_evidence import is_current_evidence

REVIEW_LABELS = {
    'historical_source': 'La source a été remplacée : vérifier la version applicable.',
    'unavailable_source': 'La preuve actuelle est indisponible : vérifier la source.',
    'conflicting_values': 'Plusieurs valeurs sont retenues pour ce sujet : choisir la valeur applicable.',
    'critical_default': 'Information engageante retenue par défaut : confirmer avant engagement.',
}


def critical_information(kind, subject):
    text = unicodedata.normalize('NFKD', f'{kind} {subject}'.casefold())
    text = ''.join(char for char in text if not unicodedata.combining(char))
    return kind in {'requirement', 'constraint', 'risk', 'milestone'} or any(
        word in text for word in ('contract', 'securite', 'pression', 'tension', 'responsabilite', 'echeance'))


def contexts(db, items):
    """Batch provenance and competing values, scoped to the supplied projects."""
    if not items:
        return {}
    from backend.app.services.project_operator import current_operator
    writable = current_operator().role != 'reader'
    ids = [item.id for item in items]
    projects = {item.project_id for item in items}
    links = defaultdict(list)
    # Stay below SQLite's parameter budget for a full review list.
    for start in range(0, len(ids), 400):
        for link, source in db.query(ProvenanceLink, Source).outerjoin(
                Source, Source.id == ProvenanceLink.source_id).filter(
                ProvenanceLink.knowledge_item_id.in_(ids[start:start + 400])):
            links[link.knowledge_item_id].append(source)
    conflicts = set(db.query(KnowledgeItem.project_id, KnowledgeItem.kind, KnowledgeItem.subject).filter(
        KnowledgeItem.project_id.in_(projects), KnowledgeItem.status == 'validated').group_by(
        KnowledgeItem.project_id, KnowledgeItem.kind, KnowledgeItem.subject).having(
        func.count(func.distinct(KnowledgeItem.value)) > 1).all())
    current_cache = {}
    result = {}
    for item in items:
        bound = links[item.id]
        visible = [source for source in bound if source and source.project_id == item.project_id]
        active = []
        for source in visible:
            if source.id not in current_cache:
                current_cache[source.id] = is_current_evidence(source)
            if current_cache[source.id]:
                active.append(source)
        source_state = ('current' if active else 'historical' if visible and all(
            (source.source_metadata or {}).get('superseded') for source in visible)
            else 'unavailable' if bound else 'unproven')
        reasons = []
        if source_state == 'historical':
            reasons.append('historical_source')
        elif source_state == 'unavailable':
            reasons.append('unavailable_source')
        if (item.project_id, item.kind, item.subject) in conflicts:
            reasons.append('conflicting_values')
        if item.validated_by == 'auto-default' and critical_information(item.kind, item.subject):
            reasons.append('critical_default')
        result[item.id] = {'source_state': source_state, 'needs_review': bool(reasons),
            'review_reasons': reasons, 'review_messages': [REVIEW_LABELS[reason] for reason in reasons],
            'source_id': (active or visible)[0].id if active or visible else None,
            'can_confirm': writable and item.status == 'validated' and item.validated_by == 'auto-default'
                and source_state == 'current' and 'conflicting_values' not in reasons}
    return result


def usable_as_current(item, context):
    # A historical human decision remains available with an explicit reserve.
    # An auto-retained fact must not silently claim an obsolete source is current.
    return item.validated_by != 'auto-default' or context['source_state'] not in {'historical', 'unavailable'}
