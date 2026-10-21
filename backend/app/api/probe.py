import hashlib
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.problems import ProblemError
from app.api.schemas import ProbeAccepted, ProbeBatchIn, StatusChange
from app.core.config import get_settings
from app.db import get_session
from app.integrations.telegram import TelegramNotifier, format_message, is_notable
from app.models import Block, CheckResult, HealthCheck, Project
from app.services.graph_status import as_utc, block_statuses

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


@router.post("/results", response_model=ProbeAccepted, status_code=202)
def submit_results(
    payload: ProbeBatchIn,
    session: SessionDep,
    notifier: NotifierDep,
    x_probe_token: Annotated[str | None, Header()] = None,
) -> ProbeAccepted:
    project = authenticate(session, x_probe_token)
    check_ids = {result.health_check_id for result in payload.results}
    rows = session.execute(
        select(HealthCheck.id, HealthCheck.block_id)
        .join(Block, Block.id == HealthCheck.block_id)
        .where(HealthCheck.id.in_(check_ids), Block.project_id == project.id)
    ).all()
    owned = {check_id: block_id for check_id, block_id in rows}
    rejected = sorted(check_ids - owned.keys())
    if rejected:
        raise ProblemError(
            422,
            "validation",
            "Unprocessable Entity",
            "batch contains checks that do not belong to the project",
            [{"health_check_id": check_id, "message": "unknown check"} for check_id in rejected],
        )

    block_ids = sorted(set(owned.values()))
    now = datetime.now(UTC)
    before = block_statuses(session, block_ids, now)
    session.add_all(
        CheckResult(
            health_check_id=result.health_check_id,
            status=result.status,
            checked_at=as_utc(result.checked_at),
            latency_ms=result.latency_ms,
            message=result.message,
        )
        for result in payload.results
    )
    session.flush()
    after = block_statuses(session, block_ids, now)
    session.commit()

    changes = [
        StatusChange(block_id=block_id, previous=before[block_id], current=after[block_id])
        for block_id in block_ids
        if before[block_id] != after[block_id]
    ]
    notable = [change for change in changes if is_notable(change.previous, change.current)]
    if notable and notifier.enabled:
        name_rows = session.execute(
            select(Block.id, Block.name).where(Block.id.in_([change.block_id for change in notable]))
        ).all()
        names = {block_id: name for block_id, name in name_rows}
        for change in notable:
            notifier.send(
                format_message(project.name, names[change.block_id], change.previous, change.current)
            )
    return ProbeAccepted(accepted=len(payload.results), status_changes=changes)
