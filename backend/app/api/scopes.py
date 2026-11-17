from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.graph import commit_or_conflict, load_block
from app.api.problems import not_found
from app.api.schemas import ScopeCreate, ScopeOut, ScopeUpdate
from app.db import get_session
from app.models import BlockScope

router = APIRouter(prefix="/api/v1", tags=["scopes"])

SessionDep = Annotated[Session, Depends(get_session)]


def scope_out(scope: BlockScope) -> ScopeOut:
    return ScopeOut(id=scope.id, path_glob=scope.path_glob, access=scope.access)


def load_scope(session: Session, scope_id: int) -> BlockScope:
    scope = session.get(BlockScope, scope_id)
    if scope is None:
        raise not_found("scope", scope_id)
    return scope


@router.get("/blocks/{block_id}/scopes", response_model=list[ScopeOut])
def list_scopes(block_id: int, session: SessionDep) -> list[ScopeOut]:
    load_block(session, block_id)
    scopes = session.scalars(
        select(BlockScope).where(BlockScope.block_id == block_id).order_by(BlockScope.path_glob)
    ).all()
    return [scope_out(scope) for scope in scopes]


@router.post("/blocks/{block_id}/scopes", response_model=ScopeOut, status_code=201)
def create_scope(block_id: int, payload: ScopeCreate, session: SessionDep) -> ScopeOut:
    load_block(session, block_id)
    scope = BlockScope(block_id=block_id, path_glob=payload.path_glob, access=payload.access)
    session.add(scope)
    commit_or_conflict(session, f"path {payload.path_glob} is already in the block scope")
    return scope_out(scope)


@router.patch("/scopes/{scope_id}", response_model=ScopeOut)
def update_scope(scope_id: int, payload: ScopeUpdate, session: SessionDep) -> ScopeOut:
    scope = load_scope(session, scope_id)
    scope.access = payload.access
    session.commit()
    return scope_out(scope)


@router.delete("/scopes/{scope_id}", status_code=204)
def delete_scope(scope_id: int, session: SessionDep) -> Response:
    session.delete(load_scope(session, scope_id))
    session.commit()
    return Response(status_code=204)
