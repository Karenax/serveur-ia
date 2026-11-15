"""Explicit L1 commands; registered in Agent with trusted operator controls."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..project_identity_schemas import (
    IdentityPatch, MemberCreate, MemberPatch, PersonCreate, PersonPatch,
    ReferenceCreate, ReferenceKind, ReferencePatch, RevisionCommand,
)
from ..services import project_identity as identity

router = APIRouter(prefix="/api/v1", tags=["project-identity"])


def _command(db, action, *args):
    try:
        result = action(db, *args)
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise


@router.get("/project-references")
def references(kind: ReferenceKind | None = None, search: str = Query("", max_length=200),
               include_inactive: bool = False, offset: int = Query(0, ge=0, le=1000000),
               limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    return identity.list_references(db, kind=kind, search=search, include_inactive=include_inactive,
                                    offset=offset, limit=limit)


@router.post("/project-references", status_code=201)
def create_reference(payload: ReferenceCreate, db: Session = Depends(get_db)):
    return _command(db, identity.create_reference, payload)


@router.patch("/project-references/{reference_id}")
def patch_reference(reference_id: str, payload: ReferencePatch, db: Session = Depends(get_db)):
    return _command(db, identity.patch_reference, reference_id, payload)


@router.get("/project-people")
def people(search: str = Query("", max_length=200), include_inactive: bool = False,
           offset: int = Query(0, ge=0, le=1000000), limit: int = Query(50, ge=1, le=200),
           db: Session = Depends(get_db)):
    return identity.list_people(db, search=search, include_inactive=include_inactive, offset=offset, limit=limit)


@router.post("/project-people", status_code=201)
def create_person(payload: PersonCreate, db: Session = Depends(get_db)):
    return _command(db, identity.create_person, payload)


@router.patch("/project-people/{person_id}")
def patch_person(person_id: str, payload: PersonPatch, db: Session = Depends(get_db)):
    return _command(db, identity.patch_person, person_id, payload)


@router.get("/projects/{project_id}/identity")
def project_identity(project_id: str, db: Session = Depends(get_db)):
    return identity.read_identity(db, project_id)


@router.patch("/projects/{project_id}/identity")
def patch_identity(project_id: str, payload: IdentityPatch, db: Session = Depends(get_db)):
    return _command(db, identity.patch_identity, project_id, payload)


@router.get("/projects/{project_id}/identity/history")
def history(project_id: str, offset: int = Query(0, ge=0, le=1000000), limit: int = Query(50, ge=1, le=200),
            db: Session = Depends(get_db)):
    return identity.identity_history(db, project_id, offset=offset, limit=limit)


@router.post("/projects/{project_id}/members", status_code=201)
def add_member(project_id: str, payload: MemberCreate, db: Session = Depends(get_db)):
    return _command(db, identity.add_member, project_id, payload)


@router.patch("/projects/{project_id}/members/{member_id}")
def patch_member(project_id: str, member_id: str, payload: MemberPatch, db: Session = Depends(get_db)):
    return _command(db, identity.patch_member, project_id, member_id, payload)


@router.post("/projects/{project_id}/members/{member_id}/archive")
def archive_member(project_id: str, member_id: str, payload: RevisionCommand, db: Session = Depends(get_db)):
    return _command(db, identity.archive_member, project_id, member_id, payload)
