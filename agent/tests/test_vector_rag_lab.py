"""Safety properties of the persistent candidate, independent of remote models."""
import asyncio

import pytest

from app.services.vector_rag_lab import VectorRagLab


class Channel:
    profile = 'profile-one'

    async def embed(self, texts, *, query=False):
        return [[1.0, 0.0] for _ in texts]


def test_reload_and_project_isolation(tmp_path):
    path = tmp_path / 'index.db'
    lab = VectorRagLab(path, Channel())
    asyncio.run(lab.index('A', [{'id': 'p1', 'doc_id': 'd1', 'text': 'preuve du projet A'}]))
    reopened = VectorRagLab(path, Channel())
    assert asyncio.run(reopened.recall('B', 'preuve')) == []
    hit = asyncio.run(reopened.recall('A', 'preuve'))[0]
    assert hit['source_id'] == 'd1' and hit['text'] == 'preuve du projet A'


def test_incompatible_embedding_profile_fails_closed(tmp_path):
    channel = Channel()
    lab = VectorRagLab(tmp_path / 'index.db', channel)
    asyncio.run(lab.index('A', [{'id': 'p1', 'doc_id': 'd1', 'text': 'preuve'}]))
    channel.profile = 'different-model'
    with pytest.raises(ValueError, match='Profil incompatible'):
        asyncio.run(lab.recall('A', 'preuve'))
