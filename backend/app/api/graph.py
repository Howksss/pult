from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.problems import ProblemError, not_found
from app.api.schemas import BlockCreate, BlockOut, BlockUpdate, GraphOut, LinkCreate, LinkOut
from app.db import get_session
from app.models import Block, BlockLink, Project
from app.services.graph_status import block_statuses
from app.services.status import BlockStatus

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


def block_out(block: Block, status: BlockStatus) -> BlockOut:
    return BlockOut(
        id=block.id,
        kind=block.kind,
        name=block.name,
        description=block.description,
        x=block.pos_x,
        y=block.pos_y,
        status=status,
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
def get_graph(project_id: int, session: SessionDep) -> GraphOut:
    load_project(session, project_id)
    now = datetime.now(UTC)
    blocks = session.scalars(select(Block).where(Block.project_id == project_id).order_by(Block.id)).all()
    statuses = block_statuses(session, [block.id for block in blocks], now)
    links = session.scalars(
        select(BlockLink)
        .join(Block, BlockLink.source_block_id == Block.id)
        .where(Block.project_id == project_id)
        .order_by(BlockLink.id)
    ).all()
    return GraphOut(
        project_id=project_id,
        generated_at=now,
        blocks=[block_out(block, statuses[block.id]) for block in blocks],
        links=[link_out(link) for link in links],
    )


@router.post("/projects/{project_id}/blocks", response_model=BlockOut, status_code=201)
def create_block(project_id: int, payload: BlockCreate, session: SessionDep) -> BlockOut:
    load_project(session, project_id)
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
    return block_out(block, BlockStatus.unknown)


@router.patch("/blocks/{block_id}", response_model=BlockOut)
def update_block(block_id: int, payload: BlockUpdate, session: SessionDep) -> BlockOut:
    block = load_block(session, block_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise ProblemError(422, "validation", "Unprocessable Entity", "nothing to update")
    columns = {"name": "name", "description": "description", "x": "pos_x", "y": "pos_y"}
    for field, value in changes.items():
        setattr(block, columns[field], value)
    commit_or_conflict(session, f"block named {block.name!r} already exists in project {block.project_id}")
    status = block_statuses(session, [block.id], datetime.now(UTC))[block.id]
    return block_out(block, status)


@router.delete("/blocks/{block_id}", status_code=204)
def delete_block(block_id: int, session: SessionDep) -> Response:
    load_block(session, block_id)
    session.execute(delete(Block).where(Block.id == block_id))
    session.commit()
    return Response(status_code=204)


@router.post("/projects/{project_id}/links", response_model=LinkOut, status_code=201)
def create_link(project_id: int, payload: LinkCreate, session: SessionDep) -> LinkOut:
    load_project(session, project_id)
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
    session.commit()
    return link_out(link)
