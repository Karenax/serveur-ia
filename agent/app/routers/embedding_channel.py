"""EG2 diagnostic routes using the production memory profile."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..services.embedding_channel import EmbeddingChannel, shared_api_key
from ..services.settings_service import get_section, save_section

router = APIRouter(prefix='/v1/settings/embedding-channel', tags=['embedding-channel'])


class ChannelSettings(BaseModel):
    enabled: bool = False
    endpoint: str = Field(default='', max_length=512)
    model: str = Field(default='text-embedding-embeddinggemma-2', min_length=1, max_length=256)
    timeout_s: int = Field(default=600, ge=1, le=86400)
    batch_size: int = Field(default=8, ge=1, le=32)


class Document(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1, max_length=6000)


class RankRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    documents: list[Document] = Field(min_length=1, max_length=100)
    limit: int = Field(default=5, ge=1, le=20)


def configured_channel(db: Session) -> EmbeddingChannel:
    memory = get_section(db, 'memory')
    cfg = {'enabled': True, 'endpoint': memory['embedding_endpoint'], 'model': memory['embedding_model'],
           'timeout_s': memory['timeout_s'], 'batch_size': memory['batch_size']}
    if not cfg.get('enabled'):
        raise HTTPException(409, "EG2 désactivé")
    endpoint = cfg.get('endpoint') or get_section(db, 'ai').get('base_url', '')
    try:
        return EmbeddingChannel(endpoint, cfg.get('model', 'text-embedding-embeddinggemma-2'),
                                timeout_s=cfg.get('timeout_s', 120), batch_size=cfg.get('batch_size', 8),
                                api_key=shared_api_key(get_section(db, 'ai'), endpoint))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get('')
def configuration(db: Session = Depends(get_db)):
    memory = get_section(db, 'memory')
    cfg = {'enabled': True, 'endpoint': memory['embedding_endpoint'], 'model': memory['embedding_model'],
           'timeout_s': memory['timeout_s'], 'batch_size': memory['batch_size']}
    return {**cfg, 'effective_endpoint': cfg.get('endpoint') or get_section(db, 'ai').get('base_url', ''),
            'experimental': False, 'automatic_ingestion': True}


@router.put('')
def configure(body: ChannelSettings, db: Session = Depends(get_db)):
    if body.endpoint:
        try:
            EmbeddingChannel(body.endpoint)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
    return save_section(db, 'memory', {'embedding_endpoint': body.endpoint or get_section(db, 'memory')['embedding_endpoint'],
                       'embedding_model': body.model, 'timeout_s': body.timeout_s, 'batch_size': body.batch_size})


@router.post('/rank')
async def rank(body: RankRequest, db: Session = Depends(get_db)):
    channel = configured_channel(db)
    try:
        return await channel.rank(body.query, [doc.model_dump() for doc in body.documents], body.limit)
    except Exception as exc:
        # No fallback to a different vector space; no source text or remote response in diagnostics.
        raise HTTPException(502, f"Échec du canal d'embeddings ({type(exc).__name__})") from exc


@router.post('/test')
async def test(db: Session = Depends(get_db)):
    return await rank(RankRequest(query="Quel éclairage pour la maintenance ?", documents=[
        Document(id='light', text="La rampe LED ORION éclaire la zone de maintenance."),
        Document(id='pump', text="La pompe HECTOR transfère de l'eau à 6 bars."),
    ]), db)
