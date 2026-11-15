"""Back up Brain/EG2, extract existing resolved mail attachments and queue their embeddings."""
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


async def run(backup, *, project_id=None, retry=False, workers=3):
    from sqlalchemy.engine import make_url
    from app.config import settings
    from app.db import SessionLocal
    from app.db_support import backup_sqlite
    from app.models import Source, SourceArtifact
    from app.services.eg2_memory import index_path
    from app.services.mail_attachments import prepare
    from app.services.projections import enqueue
    from app.services.settings_service import get_section

    backup.mkdir(parents=True, exist_ok=False)
    url = make_url(settings.database_url)
    if url.get_backend_name() != 'sqlite':
        raise ValueError('Une sauvegarde SQLite est requise pour cette reprise')
    backup_sqlite(Path(url.database), backup / 'brain.db')
    with SessionLocal() as db:
        path = index_path(get_section(db, 'memory'))
        if path.is_file():
            backup_sqlite(path, backup / 'eg2.db')
        query = db.query(Source).filter_by(source_type='email', status='resolved')
        if project_id:
            query = query.filter_by(project_id=project_id)
        ids = [row.id for row in query.order_by(Source.received_at, Source.id)]
    state = {'started_at': datetime.now(timezone.utc).isoformat(), 'running': True,
             'total': len(ids), 'processed': 0, 'queued': 0, 'failed': 0, 'parts': 0, 'states': {}}
    errors = []
    slots = asyncio.Semaphore(workers)

    async def one(source_id):
        async with slots:
            try:
                with SessionLocal() as db:
                    source = db.get(Source, source_id)
                    changed = await prepare(db, source, retry=retry)
                    db.expire_all()
                    source = db.get(Source, source_id)
                    if source and source.status == 'resolved' and source.project_id:
                        projection = enqueue(db, source.project_id, 'evidence', source_id=source_id)
                        content = '\n'.join(a.content_text or '' for a in db.query(SourceArtifact).filter_by(source_id=source_id)
                            if a.kind not in {'audio_pending', 'attachment_status'} and not (a.content_json or {}).get('superseded'))
                        stale = projection.status == 'indexed' and projection.content_hash != hashlib.sha256(content.encode()).hexdigest()
                        if changed or stale:
                            projection.status, projection.last_error = 'pending', None
                            state['queued'] += 1
                        db.commit()
                    summary = (source.source_metadata or {}).get('attachment_extraction', {}) if source else {}
                    state['parts'] += len(summary.get('parts', []))
                    for status, count in summary.get('states', {}).items():
                        state['states'][status] = state['states'].get(status, 0) + count
            except Exception as exc:
                state['failed'] += 1
                errors.append({'source_id': source_id, 'type': type(exc).__name__})
            state['processed'] += 1
            (backup / 'progress.json').write_text(json.dumps(state, indent=2), encoding='utf-8')
            if state['processed'] % 10 == 0:
                print(json.dumps(state), flush=True)

    await asyncio.gather(*(one(source_id) for source_id in ids))
    state['running'] = False
    state['finished_at'] = datetime.now(timezone.utc).isoformat()
    (backup / 'progress.json').write_text(json.dumps(state, indent=2), encoding='utf-8')
    (backup / 'errors.json').write_text(json.dumps(errors, indent=2), encoding='utf-8')
    print(json.dumps(state), flush=True)
    return 1 if state['failed'] else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backup', type=Path, required=True)
    parser.add_argument('--project-id')
    parser.add_argument('--retry', action='store_true', help='Recheck extraction receipts, including incomplete files')
    parser.add_argument('--workers', type=int, choices=range(1, 5), default=3)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.backup, project_id=args.project_id, retry=args.retry, workers=args.workers)))
