from typing import Annotated

from fastapi import APIRouter, Query, Response
from sqlalchemy import delete, func, select

from app.api.access import EDIT, VIEW, CurrentUser, SessionDep, member_role, require_project
from app.api.paging import PageDep
from app.api.problems import ProblemError, not_found
from app.api.schemas import (
    MemberAdd,
    MemberOut,
    MemberProject,
    MemberUpdate,
    ProjectCreate,
    ProjectCreated,
    ProjectOut,
    ProjectUpdate,
)
from app.models import AppUser, MemberRole, Project, ProjectMember
from app.services.auth import new_token, token_hash

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


def conflict(detail: str) -> ProblemError:
    return ProblemError(409, "conflict", "Conflict", detail)


RoleFilter = Annotated[MemberRole | None, Query(description="Только проекты или участники с этой ролью")]


@router.get("", response_model=list[MemberProject])
def list_projects(
    session: SessionDep, user: CurrentUser, page: PageDep, role: RoleFilter = None
) -> list[MemberProject]:
    query = (
        select(Project.id, Project.name, ProjectMember.role)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(ProjectMember.user_id == user.id)
        .order_by(Project.id)
    )
    if role is not None:
        query = query.where(ProjectMember.role == role)
    rows = session.execute(page.query(session, query)).all()
    return [MemberProject(id=row.id, name=row.name, role=row.role) for row in rows]


@router.post("", response_model=ProjectCreated, status_code=201)
def create_project(payload: ProjectCreate, session: SessionDep, user: CurrentUser) -> ProjectCreated:
    existing = session.scalar(
        select(Project.id)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(ProjectMember.user_id == user.id, Project.repo_full_name == payload.repo_full_name)
    )
    if existing is not None:
        raise conflict(f"you already have project {existing} for {payload.repo_full_name}")
    token = new_token()
    project = Project(
        name=payload.name.strip(), repo_full_name=payload.repo_full_name, probe_token_hash=token_hash(token)
    )
    session.add(project)
    session.flush()
    session.add(ProjectMember(project_id=project.id, user_id=user.id, role=MemberRole.owner))
    session.commit()
    return ProjectCreated(id=project.id, name=project.name, role=MemberRole.owner, probe_token=token)


def members(session: SessionDep, project_id: int) -> list[MemberOut]:
    rows = session.execute(
        select(AppUser.id, AppUser.email, AppUser.full_name, ProjectMember.role)
        .join(ProjectMember, ProjectMember.user_id == AppUser.id)
        .where(ProjectMember.project_id == project_id)
        .order_by(AppUser.full_name)
    ).all()
    return [
        MemberOut(user_id=row.id, email=row.email, full_name=row.full_name, role=row.role) for row in rows
    ]


def load_member(session: SessionDep, project_id: int, user_id: int) -> ProjectMember:
    member = session.get(ProjectMember, (project_id, user_id))
    if member is None:
        raise not_found("member", user_id)
    return member


def ensure_owner_remains(session: SessionDep, member: ProjectMember) -> None:
    owners = session.scalar(
        select(func.count())
        .select_from(ProjectMember)
        .where(ProjectMember.project_id == member.project_id, ProjectMember.role == MemberRole.owner)
    )
    if member.role is MemberRole.owner and owners == 1:
        raise conflict("the project must keep at least one owner")


def project_out(session: SessionDep, user: CurrentUser, project: Project) -> ProjectOut:
    role = member_role(session, user, project.id)
    if role is None:
        raise not_found("project", project.id)
    return ProjectOut(
        id=project.id,
        name=project.name,
        role=role,
        description=project.description,
        repo_full_name=project.repo_full_name,
        default_branch=project.default_branch,
        created_at=project.created_at,
    )


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, session: SessionDep, user: CurrentUser) -> ProjectOut:
    return project_out(session, user, require_project(session, user, project_id, VIEW))


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int, payload: ProjectUpdate, session: SessionDep, user: CurrentUser
) -> ProjectOut:
    project = require_project(session, user, project_id, EDIT)
    changes = payload.model_dump(exclude_unset=True)
    for field in ("name", "default_branch"):
        if changes.get(field) is not None:
            changes[field] = changes[field].strip()
        elif field in changes:
            del changes[field]
    for field, value in changes.items():
        setattr(project, field, value)
    session.commit()
    return project_out(session, user, project)


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, session: SessionDep, user: CurrentUser) -> Response:
    require_project(session, user, project_id, EDIT)
    session.execute(delete(Project).where(Project.id == project_id))
    session.commit()
    return Response(status_code=204)


@router.get("/{project_id}/members", response_model=list[MemberOut])
def list_members(
    project_id: int,
    session: SessionDep,
    user: CurrentUser,
    page: PageDep,
    role: RoleFilter = None,
) -> list[MemberOut]:
    require_project(session, user, project_id, VIEW)
    items = [item for item in members(session, project_id) if role is None or item.role is role]
    return page.items(items)


@router.post("/{project_id}/members", response_model=MemberOut, status_code=201)
def add_member(project_id: int, payload: MemberAdd, session: SessionDep, user: CurrentUser) -> MemberOut:
    require_project(session, user, project_id, EDIT)
    invited = session.scalar(select(AppUser).where(AppUser.email == payload.email))
    if invited is None:
        raise ProblemError(
            404, "not-found", "Not Found", "no user with this email: ask them to register first"
        )
    if session.get(ProjectMember, (project_id, invited.id)) is not None:
        raise conflict("already a member of the project")
    session.add(ProjectMember(project_id=project_id, user_id=invited.id, role=payload.role))
    session.commit()
    return MemberOut(user_id=invited.id, email=invited.email, full_name=invited.full_name, role=payload.role)


@router.patch("/{project_id}/members/{user_id}", response_model=MemberOut)
def update_member(
    project_id: int, user_id: int, payload: MemberUpdate, session: SessionDep, user: CurrentUser
) -> MemberOut:
    require_project(session, user, project_id, EDIT)
    member = load_member(session, project_id, user_id)
    if payload.role is not MemberRole.owner:
        ensure_owner_remains(session, member)
    member.role = payload.role
    session.commit()
    return next(item for item in members(session, project_id) if item.user_id == user_id)


@router.delete("/{project_id}/members/{user_id}", status_code=204)
def remove_member(project_id: int, user_id: int, session: SessionDep, user: CurrentUser) -> Response:
    require_project(session, user, project_id, EDIT)
    member = load_member(session, project_id, user_id)
    ensure_owner_remains(session, member)
    session.delete(member)
    session.commit()
    return Response(status_code=204)
