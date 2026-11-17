from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app import __version__
from app.api.access import EDIT, OPERATE, VIEW, CurrentUser, require_block
from app.api.probe import NotifierDep
from app.api.problems import ProblemError, not_found
from app.api.schemas import BlockChecksOut, CheckCreate, CheckOut, CheckUpdate, HistoryPoint, ResultOut
from app.core.config import get_settings
from app.db import get_session
from app.models import AppUser, Block, CheckResult, HealthCheck, MemberRole, Project
from app.services.check_config import internal_target, normalize_config, normalize_target
from app.services.checks import PULL_METHODS, Guard, Outcome, run_check
from app.services.graph_status import CheckState, check_state, check_title
from app.services.results import NewResult, notify, record_results
from app.services.status import SEVERITY, BlockStatus

router = APIRouter(prefix="/api/v1", tags=["checks"])

SessionDep = Annotated[Session, Depends(get_session)]

HISTORY_POINTS = 40
DISABLED = CheckState(BlockStatus.unknown, "проверка выключена", None)


def recent_results(session: Session, check_ids: list[int]) -> dict[int, list[CheckResult]]:
    if not check_ids:
        return {}
    ranked = (
        select(
            CheckResult,
            func.row_number()
            .over(
                partition_by=CheckResult.health_check_id,
                order_by=(CheckResult.checked_at.desc(), CheckResult.id.desc()),
            )
            .label("position"),
        )
        .where(CheckResult.health_check_id.in_(check_ids))
        .subquery()
    )
    result = aliased(CheckResult, ranked)
    rows = session.scalars(
        select(result).where(ranked.c.position <= HISTORY_POINTS).order_by(ranked.c.position)
    ).all()
    grouped: dict[int, list[CheckResult]] = defaultdict(list)
    for row in rows:
        grouped[row.health_check_id].append(row)
    return grouped


def check_out(check: HealthCheck, results: list[CheckResult], now: datetime) -> CheckOut:
    last = results[0] if results else None
    state = check_state(check, last, now) if check.enabled else DISABLED
    return CheckOut(
        id=check.id,
        title=check_title(check),
        name=check.name,
        method=check.method,
        target=check.target,
        interval_sec=check.interval_sec,
        timeout_sec=check.timeout_sec,
        enabled=check.enabled,
        config=check.config or {},
        status=state.status,
        reason=state.reason,
        error_kind=state.error_kind,
        last=None
        if last is None
        else ResultOut(
            checked_at=last.checked_at,
            status=last.status,
            latency_ms=last.latency_ms,
            message=last.message,
            error_kind=last.error_kind,
            details=last.details,
        ),
        history=[
            HistoryPoint(checked_at=row.checked_at, status=row.status, latency_ms=row.latency_ms)
            for row in reversed(results)
        ],
    )


@router.get("/blocks/{block_id}/checks", response_model=BlockChecksOut)
def list_block_checks(block_id: int, session: SessionDep, user: CurrentUser) -> BlockChecksOut:
    require_block(session, user, block_id, VIEW)
    now = datetime.now(UTC)
    checks = session.scalars(
        select(HealthCheck).where(HealthCheck.block_id == block_id).order_by(HealthCheck.id)
    ).all()
    results = recent_results(session, [check.id for check in checks])
    items = [check_out(check, results.get(check.id, []), now) for check in checks]
    items.sort(key=lambda item: (not item.enabled, -SEVERITY[item.status], item.id))
    return BlockChecksOut(block_id=block_id, generated_at=now, checks=items)


CheckRunner = Callable[[HealthCheck], Outcome]


def get_runner() -> CheckRunner:
    guard = Guard(allow_private=get_settings().allow_private_targets)

    def run(check: HealthCheck) -> Outcome:
        with httpx.Client(headers={"User-Agent": f"Pult/{__version__} health check"}) as client:
            return run_check(check, client, guard)

    return run


RunnerDep = Annotated[CheckRunner, Depends(get_runner)]


def load_check(session: Session, user: AppUser, check_id: int, roles: frozenset[MemberRole]) -> HealthCheck:
    check = session.get(HealthCheck, check_id)
    if check is None:
        raise not_found("check", check_id)
    try:
        require_block(session, user, check.block_id, roles)
    except ProblemError as error:
        if error.status == 404:
            raise not_found("check", check_id) from error
        raise
    return check


def invalid(detail: str) -> ProblemError:
    return ProblemError(422, "validation", "Unprocessable Entity", detail)


def guard_target(check: HealthCheck) -> None:
    if not get_settings().allow_private_targets and internal_target(check.method, check.target):
        raise invalid("адрес во внутренней сети: такие проверки запрещены")


def fresh_out(session: Session, check: HealthCheck) -> CheckOut:
    return check_out(check, recent_results(session, [check.id]).get(check.id, []), datetime.now(UTC))


@router.post("/blocks/{block_id}/checks", response_model=CheckOut, status_code=201)
def create_check(block_id: int, payload: CheckCreate, session: SessionDep, user: CurrentUser) -> CheckOut:
    require_block(session, user, block_id, EDIT)
    check = HealthCheck(block_id=block_id, **payload.model_dump())
    guard_target(check)
    session.add(check)
    session.commit()
    return fresh_out(session, check)


@router.patch("/checks/{check_id}", response_model=CheckOut)
def update_check(check_id: int, payload: CheckUpdate, session: SessionDep, user: CurrentUser) -> CheckOut:
    check = load_check(session, user, check_id, EDIT)
    changes = payload.model_dump(exclude_unset=True)
    try:
        if "target" in changes:
            changes["target"] = normalize_target(check.method, changes["target"] or "")
        if "config" in changes:
            changes["config"] = normalize_config(check.method, changes["config"] or {})
    except ValueError as error:
        raise invalid(str(error)) from error
    if "name" in changes:
        changes["name"] = (changes["name"] or "").strip() or None
    for key, value in changes.items():
        if value is not None or key == "name":
            setattr(check, key, value)
    guard_target(check)
    session.commit()
    return fresh_out(session, check)


@router.delete("/checks/{check_id}", status_code=204)
def delete_check(check_id: int, session: SessionDep, user: CurrentUser) -> Response:
    session.delete(load_check(session, user, check_id, EDIT))
    session.commit()
    return Response(status_code=204)


@router.post("/checks/{check_id}/run", response_model=CheckOut)
def run_check_now(
    check_id: int, session: SessionDep, user: CurrentUser, runner: RunnerDep, notifier: NotifierDep
) -> CheckOut:
    check = load_check(session, user, check_id, OPERATE)
    if check.method not in PULL_METHODS:
        raise ProblemError(
            409,
            "client-reported",
            "Conflict",
            "this check is reported by the client server, Pult cannot run it",
        )
    outcome = runner(check)
    result = NewResult(
        health_check_id=check.id,
        status=outcome.status,
        checked_at=datetime.now(UTC),
        latency_ms=outcome.latency_ms,
        message=outcome.message,
        error_kind=outcome.error_kind,
        details=outcome.details or None,
    )
    changes = record_results(session, [result], [check.block_id])
    block = session.get(Block, check.block_id)
    project = session.get(Project, block.project_id) if block else None
    if project is not None:
        notify(session, notifier, project, changes)
    return fresh_out(session, check)
