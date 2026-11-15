"""Read-only view of actual EG2 coverage, scoped to canonical current sources."""
import sqlite3
from collections import defaultdict
from urllib.parse import urlsplit

from .current_evidence import current_contents
from .eg2_memory import EG2MemoryAdapter, evidence_ref
from .fusion_insights import visible_sources
from .settings_service import get_section


def snapshot(db, project_id=None):
    from ..models import Project, MemoryProjection, MemoryDatasetMapping
    sources = visible_sources(db, project_id)
    ids = {source.id for source in sources}
    projects = {source.project_id for source in sources}
    contents = current_contents(db, projects)
    config = get_section(db, 'memory')
    adapter = EG2MemoryAdapter(config=config)
    profile = adapter.channel.profile
    indexed, passage_counts, error = set(), defaultdict(int), None
    if adapter.path.is_file():
        try:
            with sqlite3.connect(adapter.path.resolve().as_uri() + '?mode=ro', uri=True) as index:
                for project, ref, sid, saved_profile, count in index.execute(
                        'SELECT project,ref,source,profile,count(*) FROM passages GROUP BY project,ref,source,profile'):
                    if (sid in ids and saved_profile == profile and project in projects
                            and ref == evidence_ref(project, sid, contents.get(sid, ''), profile)):
                        indexed.add(sid)
                        passage_counts[project] += count
        except sqlite3.Error:
            error = 'Index EG2 illisible ; couverture non vérifiée'
    elif sources:
        error = 'Index EG2 absent ; couverture non vérifiée'
    states = defaultdict(set)
    for projection in db.query(MemoryProjection).join(MemoryDatasetMapping,
            MemoryDatasetMapping.id == MemoryProjection.dataset_mapping_id).filter(
            MemoryProjection.source_id.in_(ids), MemoryProjection.purpose == 'evidence',
            MemoryDatasetMapping.engine == config.get('engine', 'eg2')):
        states[projection.source_id].add(projection.status)
    grouped = defaultdict(list)
    for source in sources:
        grouped[source.project_id].append(source.id)
    result = []
    for project in db.query(Project).filter(Project.id.in_(projects)).order_by(Project.code):
        selected = grouped[project.id]
        missing = [sid for sid in selected if sid not in indexed and contents.get(sid, '').strip()]
        result.append({'project_id': project.id, 'code': project.code, 'sources': len(selected),
                       'indexed': sum(sid in indexed for sid in selected) if error is None else None,
                       'passages': passage_counts[project.id] if error is None else None,
                       'pending': sum('pending' in states[sid] for sid in missing),
                       'failed': sum('failed' in states[sid] for sid in missing),
                       'missing': len(missing), 'without_text': sum(not contents.get(sid, '').strip() for sid in selected)})
    host = urlsplit(adapter.channel.endpoint).hostname
    return {'engine': config.get('engine', 'eg2'), 'model': adapter.channel.model,
            'server': adapter.channel.endpoint, 'compute': 'local' if host in {'localhost','127.0.0.1','::1'} else 'network',
            'automatic': True, 'projects': result, 'error': error,
            'sources': len(sources), 'indexed': len(indexed) if error is None else None,
            'passages': sum(passage_counts.values()) if error is None else None}
