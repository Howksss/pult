from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.access import EDIT, VIEW, CurrentUser, require_block
from app.api.graph import commit_or_conflict
from app.api.problems import ProblemError, not_found
from app.api.schemas import ScopeCreate, ScopeOut, ScopeUpdate
from app.db import get_session
from app.models import AppUser, BlockScope

router = APIRouter(prefix="/api/v1", tags=["scopes"])

SessionDep = Annotated[Session, Depends(get_session)]


def scope_out(scope: BlockScope) -> ScopeOut:
    return ScopeOut(id=scope.id, path_glob=scope.path_glob, access=scope.access)


def load_scope(session: Session, user: AppUser, scope_id: int) -> BlockScope:
    scope = session.get(BlockScope, scope_id)
    if scope is None:
        raise not_found("scope", scope_id)
    try:
        require_block(session, user, scope.block_id, EDIT)
    except ProblemError as error:
        if error.status == 404:
            raise not_found("scope", scope_id) from error
        raise
    return scope


@router.get("/blocks/{block_id}/scopes", response_model=list[ScopeOut])
def list_scopes(block_id: int, session: SessionDep, user: CurrentUser) -> list[ScopeOut]:
    require_block(session, user, block_id, VIEW)
    scopes = session.scalars(
        select(BlockScope).where(BlockScope.block_id == block_id).order_by(BlockScope.path_glob)
    ).all()
    return [scope_out(scope) for scope in scopes]


@router.post("/blocks/{block_id}/scopes", response_model=ScopeOut, status_code=201)
def create_scope(block_id: int, payload: ScopeCreate, session: SessionDep, user: CurrentUser) -> ScopeOut:
    require_block(session, user, block_id, EDIT)
    scope = BlockScope(block_id=block_id, path_glob=payload.path_glob, access=payload.access)
    session.add(scope)
    commit_or_conflict(session, f"path {payload.path_glob} is already in the block scope")
    return scope_out(scope)


@router.patch("/scopes/{scope_id}", response_model=ScopeOut)
def update_scope(scope_id: int, payload: ScopeUpdate, session: SessionDep, user: CurrentUser) -> ScopeOut:
    scope = load_scope(session, user, scope_id)
    scope.access = payload.access
    session.commit()
    return scope_out(scope)


@router.delete("/scopes/{scope_id}", status_code=204)
def delete_scope(scope_id: int, session: SessionDep, user: CurrentUser) -> Response:
    session.delete(load_scope(session, user, scope_id))
    session.commit()
    return Response(status_code=204)
