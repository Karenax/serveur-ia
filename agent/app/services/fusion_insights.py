"""Measured counts and explicit persisted links in the canonical databases."""
from collections import Counter
from datetime import datetime, timezone
import math

from sqlalchemy import select

from ..meeting_session_models import MeetingSession, MeetingAudioChunk, MeetingSessionEvent
from ..models import Project, Source, SourceArtifact, KnowledgeItem, ProvenanceLink, MemoryProjection
from .current_evidence import is_current_evidence
from .project_access import filter_brain, require_brain


def visible_sources(db, project_id=None):
    if project_id:
        require_brain(project_id)
    query = filter_brain(db.query(Source), Source.project_id)
    if project_id:
        query = query.filter(Source.project_id == project_id)
    return [source for source in query if is_current_evidence(source)]


def visible_sessions(db, project_id=None):
    from .meeting_sessions import get_session
    query = db.query(MeetingSession)
    if project_id:
        require_brain(project_id)
        query = query.filter(MeetingSession.brain_project_id == project_id)
    rows = []
    for row in query:
        try:
            rows.append(get_session(db, row.id))
        except Exception:
            pass
    return rows


def graph(db, project_id=None, limit=300, offset=0):
    all_sources = sorted(visible_sources(db, project_id), key=lambda source: (source.project_id, source.id))
    sources = all_sources[offset:offset+limit]
    ids = {s.id for s in sources}
    nodes = []
    edges = []
    projects = {s.project_id for s in sources}
    for project in db.scalars(select(Project).where(Project.id.in_(projects))):
        nodes.append({'id': 'project:' + project.id, 'label': project.code + ' — ' + project.name,
                      'kind': 'project', 'project_id': project.id})
    for source in sources:
        metadata = source.source_metadata or {}
        nodes.append({'id': 'source:' + source.id, 'source_id': source.id, 'project_id': source.project_id,
                      'kind': 'source', 'label': metadata.get('subject') or metadata.get('filename') or source.source_type})
        edges.append({'id': 'belongs:' + source.id, 'source': 'source:' + source.id,
                      'target': 'project:' + source.project_id, 'kind': 'belongs_to', 'inferred': False})
    provenance = db.query(ProvenanceLink, KnowledgeItem).join(KnowledgeItem,
        KnowledgeItem.id == ProvenanceLink.knowledge_item_id).filter(ProvenanceLink.source_id.in_(ids),
        KnowledgeItem.status == 'validated', KnowledgeItem.project_id.in_(projects)).order_by(ProvenanceLink.id).all()
    known = {n['id'] for n in nodes}
    for link, knowledge in provenance:
        # A persisted cross-project link is never enough to widen visibility.
        source = next(s for s in sources if s.id == link.source_id)
        if source.project_id != knowledge.project_id:
            continue
        node_id = 'knowledge:' + knowledge.id
        if node_id not in known:
            nodes.append({'id': node_id, 'kind': 'knowledge', 'label': knowledge.subject,
                          'project_id': knowledge.project_id})
            known.add(node_id)
        edges.append({'id': link.id, 'source': node_id, 'target': 'source:' + link.source_id,
                      'kind': 'cites', 'inferred': False})
    return {'nodes': nodes, 'edges': edges, 'truncated': offset > 0 or offset+len(sources) < len(all_sources),
            'offset': offset, 'limit': limit, 'total': len(all_sources),
            'has_next': offset+len(sources) < len(all_sources), 'page_provenance_complete': True,
            'semantics': 'Liens de projet et provenance enregistrés ; aucune relation sémantique inférée'}


def percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * fraction) - 1)]


def stats(db, project_id=None):
    from .live_speech import runtime_status
    sources = visible_sources(db, project_id)
    source_ids = {s.id for s in sources}
    artifacts = list(db.scalars(select(SourceArtifact).where(SourceArtifact.source_id.in_(source_ids))))
    projections = list(db.scalars(select(MemoryProjection).where(MemoryProjection.source_id.in_(source_ids))))
    rows = visible_sessions(db, project_id)
    session_ids = {s.id for s in rows}
    chunks = list(db.scalars(select(MeetingAudioChunk).where(MeetingAudioChunk.session_id.in_(session_ids))))
    events = list(db.scalars(select(MeetingSessionEvent).where(MeetingSessionEvent.session_id.in_(session_ids))))
    answers = [e.data for e in events if e.kind in {'assistant.answer', 'assistant.live-answer'}]
    from .scoped_assistant import context_current
    by_id = {s.id: s for s in rows}
    stale = sum(not context_current(db, by_id[e.session_id], e.data) for e in events
                if e.kind in {'assistant.answer', 'assistant.live-answer'})
    durations = [a['elapsed_seconds'] for a in answers if type(a.get('elapsed_seconds')) in (int, float)
                 and math.isfinite(a['elapsed_seconds']) and a['elapsed_seconds'] >= 0]
    from .fusion_index_metrics import measured_indexes
    index = measured_indexes(db, sources)
    from .speech_admission import eligible_direct
    queued = [chunk for chunk in chunks if chunk.speech_status in {'pending', 'running'}
              and eligible_direct(chunk) and by_id[chunk.session_id].state != 'cancelled']
    current_time = datetime.now(timezone.utc)
    pending_ages = [max(0, (current_time-(chunk.created_at.replace(tzinfo=timezone.utc)
                    if chunk.created_at.tzinfo is None else chunk.created_at)).total_seconds()) for chunk in queued]
    from .fusion_readiness import generation_snapshot
    from .assistant_feedback import summary
    from .scoped_assistant import answer_visible
    allowed_answers = {(e.session_id, e.kind, e.data['id']) for e in events
                       if e.kind in {'assistant.answer', 'assistant.live-answer'}
                       and e.data.get('id') and answer_visible(db, e.data)}
    from .llm_usage import aggregate
    tokens = aggregate([a for a in answers if answer_visible(db, a)])
    return {'sources': {'total': len(sources), 'current': len(sources), 'by_type': dict(Counter(s.source_type for s in sources)),
                'extracted': len({a.source_id for a in artifacts if a.content_text and not (a.content_json or {}).get('superseded')}),
                'indexed': index['indexed_sources'],
                'projection_receipts_indexed': len({p.source_id for p in projections if p.purpose == 'evidence' and p.status == 'indexed'})},
        'sessions': {'total': len(rows), 'by_state': dict(Counter(r.state for r in rows)), 'audio_bytes': sum(c.size_bytes for c in chunks),
                     'duration_seconds': sum(max((c.start_ms + c.duration_ms for c in chunks if c.session_id == row.id), default=0) / 1000 for row in rows),
                     'chunks_by_track': dict(Counter(c.track for c in chunks))},
        'transcription': {'by_status': dict(Counter(c.speech_status for c in chunks)),
                          'pending_chunks': len(queued), 'pending_audio_seconds': sum(c.duration_ms for c in queued)/1000,
                          'oldest_pending_seconds': max(pending_ages) if pending_ages else None},
        'assistant': {'answers': len(answers), 'stale': stale, 'enhancements': sum(e.kind == 'enhancement.proposed' for e in events),
                      'p50_seconds': percentile(durations, .5), 'p95_seconds': percentile(durations, .95),
                      'measured_latency_samples': len(durations), **summary(events, allowed_answers), **tokens},
        'engines': {'speech': runtime_status(),
                    'generation': generation_snapshot(db)},
        'index': index,
        'formulas': {'duration_seconds': 'Somme, par séance visible, du plus grand (start_ms + duration_ms) / 1000 ; deux pistes ne doublent pas la durée',
                     'audio_bytes': 'Somme des tailles des chunks conservés dans les séances visibles',
                     'latency': 'Percentile rang le plus proche des temps de réponses réellement enregistrés',
                     'tokens': 'Somme des tokens renvoyés par le moteur pour les tentatives instrumentées des réponses accessibles ; couverture complète/partielle/absente indiquée ; total fourni ou somme des deux composantes fournies ; aucune estimation du texte ni économie calculée',
                     'graph': 'Provenance et appartenance enregistrées, sans relations inventées',
                     'indexed_sources': 'Union des sources avec passages texte ou multimodaux actuels et de profil compatible ; null si une couverture est illisible',
                     'projection_receipts_indexed': 'Reçus historiques de projection ; ne prouvent pas seuls la présence actuelle de vecteurs',
                     'chunks_by_track': 'Nombre de fragments conservés par piste, pas une durée cumulée de séance',
                     'pending_audio_seconds': 'Somme des durées des fragments mic/system directs pending/running des séances visibles non annulées ; deux pistes représentent deux traitements',
                     'oldest_pending_seconds': 'Âge depuis la conservation du plus ancien fragment direct en attente ; ce n’est pas une latence d’affichage',
                     'useful_answers': 'Nombre de réponses accessibles dont le dernier avis humain explicite est Utile ; un avis retiré ne compte plus ; aucune utilité inférée du nombre de réponses',
                     'evaluated_answers': 'Nombre de réponses accessibles avec un dernier avis Utile ou Pas utile ; chaque réponse de discussion ou du direct compte une fois, indépendamment du nombre de changements d’avis',
                     'unhelpful_answers': 'Nombre de réponses accessibles dont le dernier avis humain explicite est Pas utile ; l’historique des avis reste conservé',
                     'text_passages': 'Passages EG2 des seules sources visibles, avec référence de contenu et profil actuels ; null si index illisible',
                     'size_bytes': 'Taille physique du fichier index EG2, hors WAL ; aucun volume de source estimé'}}
