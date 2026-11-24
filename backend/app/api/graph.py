from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import Select, delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.access import EDIT, VIEW, CurrentUser, require_block, require_project
from app.api.paging import PageDep
from app.api.problems import ProblemError, not_found
from app.api.schemas import BlockCreate, BlockOut, BlockUpdate, GraphOut, LinkCreate, LinkOut, LinkUpdate
from app.db import get_session
from app.models import AppUser, Block, BlockKind, BlockLink, MemberRole, Project
from app.services.graph_status import BlockDiagnosis, block_diagnoses
from app.services.status import BlockStatus

NO_CHECKS = BlockDiagnosis(BlockStatus.unknown, "Проверки не настроены", 0, 0)

router = APIRouter(prefix="/api/v1", tags=["graph"])

SessionDep = Annotated[Session, Depends(get_session)]


def load_project(session: Session, project_id: int) -> Project:
    project = session.get(Project, project_id)
    if project is None:
        raise not_found("project", project_id)
    return project


def load_block(session: Session, block_id: int) -> Block:
    block = session.get(Block, block_id)
    if block is None:
        raise not_found("block", block_id)
    return block


def block_out(block: Block, diagnosis: BlockDiagnosis) -> BlockOut:
    return BlockOut(
        id=block.id,
        kind=block.kind,
        name=block.name,
        description=block.description,
        x=block.pos_x,
        y=block.pos_y,
        status=diagnosis.status,
        reason=diagnosis.reason,
        checks_total=diagnosis.checks_total,
        checks_problem=diagnosis.checks_problem,
    )


def link_out(link: BlockLink) -> LinkOut:
    return LinkOut(
        id=link.id,
        source_block_id=link.source_block_id,
        target_block_id=link.target_block_id,
        label=link.label,
    )


def commit_or_conflict(session: Session, detail: str) -> None:
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise ProblemError(409, "conflict", "Conflict", detail) from error


@router.get("/projects/{project_id}/graph", response_model=GraphOut)
def get_graph(project_id: int, session: SessionDep, user: CurrentUser) -> GraphOut:
    project = require_project(session, user, project_id, VIEW)
    now = datetime.now(UTC)
    blocks = session.scalars(select(Block).where(Block.project_id == project_id).order_by(Block.id)).all()
    diagnoses = block_diagnoses(session, [block.id for block in blocks], now)
    links = session.scalars(
        select(BlockLink)
        .join(Block, BlockLink.source_block_id == Block.id)
        .where(Block.project_id == project_id)
        .order_by(BlockLink.id)
    ).all()
    return GraphOut(
        project_id=project_id,
        project_name=project.name,
        generated_at=now,
        blocks=[block_out(block, diagnoses[block.id]) for block in blocks],
        links=[link_out(link) for link in links],
    )


@router.post("/projects/{project_id}/blocks", response_model=BlockOut, status_code=201)
def create_block(project_id: int, payload: BlockCreate, session: SessionDep, user: CurrentUser) -> BlockOut:
    require_project(session, user, project_id, EDIT)
    block = Block(
        project_id=project_id,
        kind=payload.kind,
        name=payload.name,
        description=payload.description,
        pos_x=payload.x,
        pos_y=payload.y,
    )
    session.add(block)
    commit_or_conflict(session, f"block named {payload.name!r} already exists in project {project_id}")
    return block_out(block, NO_CHECKS)


@router.patch("/blocks/{block_id}", response_model=BlockOut)
def update_block(block_id: int, payload: BlockUpdate, session: SessionDep, user: CurrentUser) -> BlockOut:
    block = require_block(session, user, block_id, EDIT)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise ProblemError(422, "validation", "Unprocessable Entity", "nothing to update")
    columns = {"name": "name", "description": "description", "x": "pos_x", "y": "pos_y"}
    for field, value in changes.items():
        setattr(block, columns[field], value)
    commit_or_conflict(session, f"block named {block.name!r} already exists in project {block.project_id}")
    return block_out(block, block_diagnoses(session, [block.id], datetime.now(UTC))[block.id])


@router.delete("/blocks/{block_id}", status_code=204)
def delete_block(block_id: int, session: SessionDep, user: CurrentUser) -> Response:
    require_block(session, user, block_id, EDIT)
    session.execute(delete(Block).where(Block.id == block_id))
    session.commit()
    return Response(status_code=204)


@router.post("/projects/{project_id}/links", response_model=LinkOut, status_code=201)
def create_link(project_id: int, payload: LinkCreate, session: SessionDep, user: CurrentUser) -> LinkOut:
    require_project(session, user, project_id, EDIT)
    if payload.source_block_id == payload.target_block_id:
        raise ProblemError(422, "validation", "Unprocessable Entity", "a block cannot be linked to itself")
    owned = set(
        session.scalars(
            select(Block.id).where(
                Block.project_id == project_id,
                Block.id.in_([payload.source_block_id, payload.target_block_id]),
            )
        )
    )
    foreign = [
        {"block_id": block_id, "message": "block does not belong to the project"}
        for block_id in (payload.source_block_id, payload.target_block_id)
        if block_id not in owned
    ]
    if foreign:
        raise ProblemError(
            422, "validation", "Unprocessable Entity", "link must connect blocks of one project", foreign
        )
    link = BlockLink(
        source_block_id=payload.source_block_id,
        target_block_id=payload.target_block_id,
        label=payload.label,
    )
    session.add(link)
    commit_or_conflict(session, "these blocks are already linked in this direction")
    return link_out(link)


class BlockFilter:
    def __init__(
        self,
        kind: Annotated[BlockKind | None, Query(description="Только блоки этого типа")] = None,
        status: Annotated[BlockStatus | None, Query(description="Только блоки с этим статусом")] = None,
        q: Annotated[str | None, Query(max_length=100, description="Часть имени блока")] = None,
    ) -> None:
        self.kind = kind
        self.status = status
        self.text = q.lower() if q else None

    def apply(self, query: Select[tuple[Block]]) -> Select[tuple[Block]]:
        if self.kind is not None:
            query = query.where(Block.kind == self.kind)
        if self.text:
            query = query.where(func.lower(Block.name).contains(self.text, autoescape=True))
        return query

    def keep(self, items: list[BlockOut]) -> list[BlockOut]:
        return [item for item in items if self.status is None or item.status is self.status]


@router.get("/projects/{project_id}/blocks", response_model=list[BlockOut])
def list_blocks(
    project_id: int,
    session: SessionDep,
    user: CurrentUser,
    page: PageDep,
    filters: Annotated[BlockFilter, Depends()],
) -> list[BlockOut]:
    require_project(session, user, project_id, VIEW)
    blocks = session.scalars(
        filters.apply(select(Block).where(Block.project_id == project_id).order_by(Block.id))
    )
    loaded = list(blocks)
    diagnoses = block_diagnoses(session, [block.id for block in loaded], datetime.now(UTC))
    return page.items(filters.keep([block_out(block, diagnoses[block.id]) for block in loaded]))


@router.get("/blocks/{block_id}", response_model=BlockOut)
def get_block(block_id: int, session: SessionDep, user: CurrentUser) -> BlockOut:
    block = require_block(session, user, block_id, VIEW)
    return block_out(block, block_diagnoses(session, [block.id], datetime.now(UTC))[block.id])


@router.get("/projects/{project_id}/links", response_model=list[LinkOut])
def list_links(
    project_id: int,
    session: SessionDep,
    user: CurrentUser,
    page: PageDep,
    block_id: Annotated[
        int | None, Query(ge=1, description="Только связи, где блок — источник или приёмник")
    ] = None,
) -> list[LinkOut]:
    require_project(session, user, project_id, VIEW)
    query = (
        select(BlockLink)
        .join(Block, BlockLink.source_block_id == Block.id)
        .where(Block.project_id == project_id)
        .order_by(BlockLink.id)
    )
    if block_id is not None:
        query = query.where(or_(BlockLink.source_block_id == block_id, BlockLink.target_block_id == block_id))
    return [link_out(link) for link in session.scalars(page.query(session, query))]


def load_link(session: Session, user: AppUser, link_id: int, roles: frozenset[MemberRole]) -> BlockLink:
    link = session.get(BlockLink, link_id)
    if link is None:
        raise not_found("link", link_id)
    try:
        require_block(session, user, link.source_block_id, roles)
    except ProblemError as error:
        if error.status == 404:
            raise not_found("link", link_id) from error
        raise
    return link


@router.patch("/links/{link_id}", response_model=LinkOut)
def update_link(link_id: int, payload: LinkUpdate, session: SessionDep, user: CurrentUser) -> LinkOut:
    link = load_link(session, user, link_id, EDIT)
    link.label = (payload.label or "").strip() or None
    session.commit()
    return link_out(link)


@router.delete("/links/{link_id}", status_code=204)
def delete_link(link_id: int, session: SessionDep, user: CurrentUser) -> Response:
    session.delete(load_link(session, user, link_id, EDIT))
    session.commit()
    return Response(status_code=204)
