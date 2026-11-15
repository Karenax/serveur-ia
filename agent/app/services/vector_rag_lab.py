"""Isolated persistent vector retrieval prototype. No EG2 dependency."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .embedding_channel import EmbeddingChannel, rank_vectors


class VectorRagLab:
    def __init__(self, path: Path, channel: EmbeddingChannel):
        self.path, self.channel = path, channel
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS passages (project TEXT, id TEXT, source TEXT, text TEXT, vector TEXT, profile TEXT, PRIMARY KEY(project,id))')

    async def index(self, project: str, passages: list[dict]):
        vectors = await self.channel.embed([p['text'] for p in passages])
        with sqlite3.connect(self.path) as db:
            db.executemany('INSERT OR REPLACE INTO passages VALUES (?,?,?,?,?,?)',
                           [(project, p['id'], p['doc_id'], p['text'], json.dumps(v), self.channel.profile)
                            for p, v in zip(passages, vectors, strict=True)])

    async def recall(self, project: str, query: str, limit: int = 8):
        with sqlite3.connect(self.path) as db:
            rows = db.execute('SELECT id,source,text,vector,profile FROM passages WHERE project=?', (project,)).fetchall()
        if not rows:
            return []
        if any(row[4] != self.channel.profile for row in rows):
            raise ValueError('Profil incompatible : réindexation nécessaire')
        query_vector = (await self.channel.embed([query], query=True))[0]
        docs = [{'id': row[0], 'text': row[2]} for row in rows]
        sources = {row[0]: row[1] for row in rows}
        return [{**hit, 'source_id': sources[hit['id']], 'project_code': project, 'level': 'proposed'}
                for hit in rank_vectors(query_vector, docs, [json.loads(row[3]) for row in rows], limit)]
