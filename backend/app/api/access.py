from typing import Annotated

from fastapi import Cookie, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.problems import ProblemError, not_found
from app.db import get_session
from app.models import AppUser, Block, MemberRole, Project, ProjectMember
from app.services.auth import user_by_token

SessionDep = Annotated[Session, Depends(get_session)]

VIEW = frozenset(MemberRole)
EDIT = frozenset({MemberRole.owner})
OPERATE = frozenset({MemberRole.owner, MemberRole.developer})


def unauthenticated() -> ProblemError:
    return ProblemError(401, "unauthenticated", "Unauthorized", "sign in first")


def current_user(session: SessionDep, pult_session: Annotated[str | None, Cookie()] = None) -> AppUser:
    user = user_by_token(session, pult_session)
    if user is None:
        raise unauthenticated()
    return user


CurrentUser = Annotated[AppUser, Depends(current_user)]


def member_role(session: Session, user: AppUser, project_id: int) -> MemberRole | None:
    return session.scalar(
        select(ProjectMember.role).where(
            ProjectMember.project_id == project_id, ProjectMember.user_id == user.id
        )
    )


def require_project(
    session: Session, user: AppUser, project_id: int, roles: frozenset[MemberRole]
) -> Project:
    project = session.get(Project, project_id)
    role = member_role(session, user, project_id) if project else None
    if project is None or role is None:
        raise not_found("project", project_id)
    if role not in roles:
        raise ProblemError(403, "forbidden", "Forbidden", f"role {role.value} cannot do this")
    return project


def require_block(session: Session, user: AppUser, block_id: int, roles: frozenset[MemberRole]) -> Block:
    block = session.get(Block, block_id)
    if block is None or member_role(session, user, block.project_id) is None:
        raise not_found("block", block_id)
    require_project(session, user, block.project_id, roles)
    return block
