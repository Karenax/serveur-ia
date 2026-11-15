"""Search the existing EG2 corpus from the source library."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Source
from ..services.current_evidence import is_current_evidence
from ..services.project_access import brain_ids, require_brain
from ..services.unified_search import search as text_search

router = APIRouter(prefix='/api/v1/workspace', tags=['source-search'])


def scope(db, project_id, source_ids):
    allowed = brain_ids()
    if project_id:
        require_brain(project_id)
        allowed = {project_id}
    for source_id in source_ids:
        source = db.get(Source, source_id)
        if not source or not is_current_evidence(source):
            raise HTTPException(404, 'Source actuelle introuvable')
        require_brain(source.project_id)
        if allowed is not None and source.project_id not in allowed:
            raise HTTPException(404, 'Source hors du périmètre sélectionné')


@router.get('/sources/search')
async def search(query: str = Query(..., min_length=2, max_length=2000), project_id: str | None = None,
                 source_ids: str = Query('', max_length=19000), limit: int = Query(10, ge=1, le=50),
                 modality: Literal['all', 'text', 'image', 'audio'] = Query('all'), db: Session = Depends(get_db)):
    if modality in {'image', 'audio'}:
        raise HTTPException(410, 'La recherche multimodale locale est obsolète. Rechercher le texte extrait.')
    chosen = set(filter(None, source_ids.split(',')))
    scope(db, project_id, chosen)
    result = await text_search(db, query=query, project_id=project_id, source_ids=chosen or None, limit=limit)
    return {**result, 'engine': 'eg2', 'items': [
        {**item, 'modality': 'text', 'text': item['excerpt'], 'source_url': f"/v1/sources/{item['source_id']}"}
        for item in result['items'] if item.get('source_id')
    ]}
