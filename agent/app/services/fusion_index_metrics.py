"""Read derived indexes without creating them, fenced by canonical evidence."""
import sqlite3

from .current_evidence import current_contents
from .settings_service import get_section


def measured_indexes(db, sources):
    from .eg2_memory import EG2MemoryAdapter, evidence_ref
    ids = {source.id for source in sources}
    projects = {source.project_id for source in sources}
    contents = current_contents(db, projects)
    adapter = EG2MemoryAdapter(config=get_section(db, 'memory'))
    text_count = 0
    text_sources = set()
    text_profile = adapter.channel.profile
    if adapter.path.is_file():
        try:
            with sqlite3.connect(adapter.path.resolve().as_uri() + '?mode=ro', uri=True) as index:
                for project, ref, sid, profile, count in index.execute(
                        'SELECT project,ref,source,profile,count(*) FROM passages GROUP BY project,ref,source,profile'):
                    if (sid in ids and project in projects and profile == text_profile
                            and ref == evidence_ref(project, sid, contents.get(sid, ''), profile)):
                        text_count += count
                        text_sources.add(sid)
        except sqlite3.Error:
            text_count = None
    source_count = len(text_sources) if text_count is not None else None
    return {'text_passages': text_count, 'indexed_sources': source_count, 'text_sources': source_count,
            'profiles': [text_profile] if text_profile else [],
            'size_bytes': adapter.path.stat().st_size if adapter.path.is_file() else 0}
