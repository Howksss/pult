from typing import Annotated

from fastapi import APIRouter, Cookie, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.access import CurrentUser, SessionDep
from app.api.problems import ProblemError
from app.api.schemas import Credentials, MemberProject, MeOut, RegisterIn
from app.core.config import get_settings
from app.models import AppUser, Project, ProjectMember
from app.services.auth import (
    COOKIE,
    SESSION_DAYS,
    close_session,
    hash_password,
    open_session,
    verify_password,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

DUMMY_HASH = hash_password("pult-timing-equalizer")


def set_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE,
        token,
        max_age=SESSION_DAYS * 86400,
        httponly=True,
        secure=get_settings().cookie_secure,
        samesite="lax",
        path="/",
    )


def me_out(session: SessionDep, user: AppUser) -> MeOut:
    rows = session.execute(
        select(Project.id, Project.name, ProjectMember.role)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(ProjectMember.user_id == user.id)
        .order_by(Project.id)
    ).all()
    return MeOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        projects=[MemberProject(id=row.id, name=row.name, role=row.role) for row in rows],
    )


@router.post("/register", response_model=MeOut, status_code=201)
def register(payload: RegisterIn, session: SessionDep, response: Response) -> MeOut:
    if not get_settings().allow_signup:
        raise ProblemError(403, "signup-closed", "Forbidden", "registration is closed")
    user = AppUser(
        email=payload.email,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise ProblemError(409, "conflict", "Conflict", "this email is already registered") from error
    set_cookie(response, open_session(session, user))
    return me_out(session, user)


@router.post("/login", response_model=MeOut)
def login(payload: Credentials, session: SessionDep, response: Response) -> MeOut:
    user = session.scalar(select(AppUser).where(AppUser.email == payload.email))
    if not verify_password(user.password_hash if user else DUMMY_HASH, payload.password) or user is None:
        raise ProblemError(401, "unauthenticated", "Unauthorized", "wrong email or password")
    set_cookie(response, open_session(session, user))
    return me_out(session, user)


@router.post("/logout", status_code=204)
def logout(session: SessionDep, pult_session: Annotated[str | None, Cookie()] = None) -> Response:
    close_session(session, pult_session)
    response = Response(status_code=204)
    response.delete_cookie(COOKIE, path="/")
    return response


@router.get("/me", response_model=MeOut)
def me(session: SessionDep, user: CurrentUser) -> MeOut:
    return me_out(session, user)
