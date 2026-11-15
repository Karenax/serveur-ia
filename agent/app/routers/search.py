"""Scoped read-only EG2 search."""
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..services.unified_search import search

router = APIRouter(prefix="/v1/search", tags=["search"])


@router.get("")
async def unified_search(q: str = Query(min_length=2, max_length=500), project_id: str | None = None,
                         source_type: Literal["all", "email", "document", "meeting", "phone", "knowledge"] = "all",
                         after: date | None = None, before: date | None = None,
                         offset: int = Query(default=0, ge=0), limit: int = Query(default=25, ge=1, le=100),
                         db: Session = Depends(get_db)):
    if len(q.strip()) < 2:
        raise HTTPException(422, "Saisir au moins deux caractères")
    if after and before and after > before:
        raise HTTPException(422, "La date de début doit précéder la date de fin")
    return await search(db, query=q.strip(), project_id=project_id, source_type=source_type,
                        after=after, before=before, offset=offset, limit=limit)
