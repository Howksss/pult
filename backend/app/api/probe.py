import hashlib
from typing import Annotated

from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.problems import ProblemError
from app.api.schemas import ProbeAccepted, ProbeBatchIn, StatusChange
from app.core.config import get_settings
from app.db import get_session
from app.integrations.telegram import TelegramNotifier
from app.models import Block, HealthCheck, Project
from app.services.results import NewResult, notify, record_results

router = APIRouter(prefix="/api/v1/probe", tags=["probe"])

SessionDep = Annotated[Session, Depends(get_session)]


def get_notifier() -> TelegramNotifier:
    settings = get_settings()
    return TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id)


NotifierDep = Annotated[TelegramNotifier, Depends(get_notifier)]


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def authenticate(session: Session, token: str | None) -> Project:
    unauthorized = ProblemError(401, "unauthorized", "Unauthorized", "missing or invalid X-Probe-Token")
    if not token:
        raise unauthorized
    project = session.scalar(select(Project).where(Project.probe_token_hash == hash_token(token)))
    if project is None:
        raise unauthorized
    return project


def owned_checks(session: Session, project: Project, check_ids: set[int]) -> dict[int, int]:
    rows = (
        session.execute(
            select(HealthCheck.id, HealthCheck.block_id)
            .join(Block, Block.id == HealthCheck.block_id)
            .where(HealthCheck.id.in_(check_ids), Block.project_id == project.id)
        )
        .tuples()
        .all()
    )
    owned = dict(rows)
    rejected = sorted(check_ids - owned.keys())
    if rejected:
        raise ProblemError(
            422,
            "validation",
            "Unprocessable Entity",
            "batch contains checks that do not belong to the project",
            [{"health_check_id": check_id, "message": "unknown check"} for check_id in rejected],
        )
    return owned


@router.post("/results", response_model=ProbeAccepted, status_code=202)
def submit_results(
    payload: ProbeBatchIn,
    session: SessionDep,
    notifier: NotifierDep,
    x_probe_token: Annotated[str | None, Header()] = None,
) -> ProbeAccepted:
    project = authenticate(session, x_probe_token)
    owned = owned_checks(session, project, {result.health_check_id for result in payload.results})
    results = [NewResult(**result.model_dump()) for result in payload.results]
    changes = record_results(session, results, sorted(set(owned.values())))
    notify(session, notifier, project, changes)
    return ProbeAccepted(
        accepted=len(payload.results),
        status_changes=[
            StatusChange(block_id=change.block_id, previous=change.previous, current=change.current)
            for change in changes
        ],
    )
