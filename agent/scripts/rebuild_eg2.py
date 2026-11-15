"""Rebuild EG2 projections from canonical sources; back up SQLite before changes."""
from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


async def rebuild(backup: Path, workers: int = 4):
    from app.config import settings
    from app.db import SessionLocal
    from app.models import MemoryDatasetMapping, MemoryProjection, Source
    from app.services.eg2_memory import EG2MemoryAdapter
    from app.services.projections import enqueue, process
    from app.services.settings_service import get_section, save_section
    from sqlalchemy.engine import make_url

    url = make_url(settings.database_url)
    if url.get_backend_name() != "sqlite":
        raise RuntimeError("This migration requires an independently backed-up SQLite database")
    backup.mkdir(parents=True, exist_ok=False)
    with sqlite3.connect(url.database) as src, sqlite3.connect(backup / "brain.db") as dst:
        src.backup(dst)
    with SessionLocal() as db:
        cfg = get_section(db, "memory")
        save_section(db, "memory", {"engine": "eg2", "prefix": cfg.get("prefix", "pb"),
                     "embedding_provider": "openai_compatible",
                     "embedding_model": cfg.get("embedding_model") if "embeddinggemma" in cfg.get("embedding_model", "").lower() else "text-embedding-embeddinggemma-2",
                     "embedding_endpoint": cfg.get("embedding_endpoint") or get_section(db, "ai").get("base_url") or "http://192.9.110.115:1234",
                     "index_path": cfg.get("index_path", ""), "timeout_s": cfg.get("timeout_s", 120), "batch_size": cfg.get("batch_size", 8)})
        # Remove retired engine settings rather than merging unknown historical keys.
        from app.models import AppSetting
        row = db.get(AppSetting, "memory")
        row.value = {k: row.value[k] for k in ("engine", "prefix", "embedding_provider", "embedding_model",
                                             "embedding_endpoint", "index_path", "timeout_s", "batch_size")}
        diagnostic = db.get(AppSetting, "embedding_channel")
        if diagnostic is not None:
            db.delete(diagnostic)
        for mapping in db.query(MemoryDatasetMapping):
            mapping.engine, mapping.engine_version = "eg2", "eg2-v1"
        for projection in db.query(MemoryProjection):
            projection.external_ref = None
            projection.last_error = None
            projection.status = "forgotten" if projection.status in {"obsolete", "forgotten"} else "pending"
        db.flush()
        sources = db.query(Source).filter_by(status="resolved").all()
        for source in sources:
            enqueue(db, source.project_id, "evidence", source_id=source.id)
        db.commit()
        ids = [p.id for p in db.query(MemoryProjection).filter_by(status="pending").order_by(MemoryProjection.id)]
    adapter = EG2MemoryAdapter(SessionLocal)
    probe = await adapter.probe()
    if probe["status"] != "ok":
        raise RuntimeError("Remote EG2 probe failed")
    totals = {"indexed": 0, "failed": 0, "forgotten": 0}
    started = datetime.now(timezone.utc).isoformat()
    queue = asyncio.Queue()
    for pid in ids:
        queue.put_nowait(pid)
    processed = 0

    async def worker():
        nonlocal processed
        while not queue.empty():
            pid = queue.get_nowait()
            with SessionLocal() as db:
                result = await process(db, adapter, projection_ids=[pid], limit=1)
            for key in totals:
                totals[key] += result[key]
            processed += 1
            state = {"started": started, "total": len(ids), "processed": processed, **totals}
            (backup / "progress.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
            if processed % 20 == 0 or processed == len(ids):
                print(json.dumps(state), flush=True)

    await asyncio.gather(*(worker() for _ in range(workers)))
    from app.services.memory_recovery import reconcile
    with SessionLocal() as db:
        reconcile(db)
    print(json.dumps({"health": await adapter.health(), "probe": probe}), flush=True)
    return 1 if totals["failed"] else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup", type=Path, required=True)
    parser.add_argument("--workers", type=int, choices=range(1, 5), default=4)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(rebuild(args.backup, args.workers)))
