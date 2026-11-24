from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import Row, Select, func, or_, select
from sqlalchemy.orm import Session, aliased

from app import __version__
from app.api.access import EDIT, OPERATE, VIEW, CurrentUser, require_block
from app.api.paging import PageDep
from app.api.probe import NotifierDep
from app.api.problems import ProblemError, not_found
from app.api.schemas import (
    BlockChecksOut,
    CheckCreate,
    CheckOut,
    CheckUpdate,
    HistoryPoint,
    ResultOut,
    TimelineBucket,
)
from app.core.config import get_settings
from app.db import get_session
from app.models import AppUser, Block, CheckResult, CheckStatus, HealthCheck, MemberRole, Project
from app.services.check_config import internal_target, normalize_config, normalize_target
from app.services.checks import PULL_METHODS, Guard, Outcome, run_check
from app.services.graph_status import CheckState, as_utc, check_state, check_title
from app.services.results import NewResult, notify, record_results
from app.services.status import SEVERITY, BlockStatus

router = APIRouter(prefix="/api/v1", tags=["checks"])

SessionDep = Annotated[Session, Depends(get_session)]

HISTORY_POINTS = 40
TIMELINE_HOURS = 24


def hour_floor(moment: datetime) -> datetime:
    return moment.replace(minute=0, second=0, microsecond=0)


def bucketize(
    rows: list[Row[tuple[int, datetime, CheckStatus]]], since: datetime
) -> tuple[list[TimelineBucket], datetime | None, bool]:
    buckets = [
        TimelineBucket(start=since + timedelta(hours=hour), ok=0, warn=0, fail=0)
        for hour in range(TIMELINE_HOURS)
    ]
    streak: datetime | None = None
    seen_ok = False
    for row in rows:
        moment = as_utc(row.checked_at)
        index = min(int((moment - since).total_seconds() // 3600), TIMELINE_HOURS - 1)
        bucket = buckets[index]
        setattr(bucket, row.status.value, getattr(bucket, row.status.value) + 1)
        if row.status is CheckStatus.ok:
            streak, seen_ok = None, True
        else:
            streak = streak or moment
    return buckets, streak, seen_ok


def streak_start(session: Session, check_id: int, before: datetime) -> datetime | None:
    last_ok = (
        select(func.max(CheckResult.checked_at))
        .where(
            CheckResult.health_check_id == check_id,
            CheckResult.status == CheckStatus.ok,
            CheckResult.checked_at < before,
        )
        .scalar_subquery()
    )
    first = session.scalar(
        select(func.min(CheckResult.checked_at)).where(
            CheckResult.health_check_id == check_id,
            CheckResult.checked_at < before,
            or_(last_ok.is_(None), CheckResult.checked_at > last_ok),
        )
    )
    return as_utc(first) if first else None


def timelines(
    session: Session, check_ids: list[int], now: datetime
) -> dict[int, tuple[list[TimelineBucket], datetime | None]]:
    since = hour_floor(now) - timedelta(hours=TIMELINE_HOURS - 1)
    rows = session.execute(
        select(CheckResult.health_check_id, CheckResult.checked_at, CheckResult.status)
        .where(CheckResult.health_check_id.in_(check_ids), CheckResult.checked_at >= since)
        .order_by(CheckResult.health_check_id, CheckResult.checked_at, CheckResult.id)
    ).all()
    result: dict[int, tuple[list[TimelineBucket], datetime | None]] = {}
    for check_id in check_ids:
        own = [row for row in rows if row.health_check_id == check_id]
        buckets, streak, seen_ok = bucketize(own, since)
        if streak is not None and not seen_ok:
            streak = streak_start(session, check_id, since) or streak
        result[check_id] = (buckets, streak)
    return result


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


def check_out(
    check: HealthCheck,
    results: list[CheckResult],
    now: datetime,
    timeline: tuple[list[TimelineBucket], datetime | None],
) -> CheckOut:
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
        timeline=timeline[0],
        failing_since=timeline[1] if state.status in (BlockStatus.fail, BlockStatus.warn) else None,
    )


@router.get("/blocks/{block_id}/checks", response_model=BlockChecksOut)
def list_block_checks(block_id: int, session: SessionDep, user: CurrentUser) -> BlockChecksOut:
    require_block(session, user, block_id, VIEW)
    now = datetime.now(UTC)
    checks = session.scalars(
        select(HealthCheck).where(HealthCheck.block_id == block_id).order_by(HealthCheck.id)
    ).all()
    ids = [check.id for check in checks]
    results = recent_results(session, ids)
    lines = timelines(session, ids, now)
    items = [check_out(check, results.get(check.id, []), now, lines[check.id]) for check in checks]
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


def ensure_valid(check: HealthCheck) -> None:
    if check.timeout_sec > check.interval_sec:
        raise invalid("таймаут не может быть больше интервала проверки")
    guard_target(check)


def fresh_out(session: Session, check: HealthCheck) -> CheckOut:
    now = datetime.now(UTC)
    results = recent_results(session, [check.id]).get(check.id, [])
    return check_out(check, results, now, timelines(session, [check.id], now)[check.id])


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
    ensure_valid(check)
    session.commit()
    return fresh_out(session, check)


@router.get("/checks/{check_id}", response_model=CheckOut)
def get_check(check_id: int, session: SessionDep, user: CurrentUser) -> CheckOut:
    return fresh_out(session, load_check(session, user, check_id, VIEW))


class ResultFilter:
    def __init__(
        self,
        status: Annotated[CheckStatus | None, Query(description="Только результаты с этим итогом")] = None,
        since: Annotated[datetime | None, Query(description="Не раньше этого момента")] = None,
        until: Annotated[datetime | None, Query(description="Раньше этого момента")] = None,
    ) -> None:
        self.status = status
        self.since = as_utc(since) if since else None
        self.until = as_utc(until) if until else None
        if self.since is not None and self.until is not None and self.since >= self.until:
            raise invalid("since must be earlier than until")

    def apply(self, query: Select[tuple[CheckResult]]) -> Select[tuple[CheckResult]]:
        if self.status is not None:
            query = query.where(CheckResult.status == self.status)
        if self.since is not None:
            query = query.where(CheckResult.checked_at >= self.since)
        if self.until is not None:
            query = query.where(CheckResult.checked_at < self.until)
        return query


@router.get("/checks/{check_id}/results", response_model=list[ResultOut])
def list_results(
    check_id: int,
    session: SessionDep,
    user: CurrentUser,
    page: PageDep,
    filters: Annotated[ResultFilter, Depends()],
) -> list[ResultOut]:
    load_check(session, user, check_id, VIEW)
    query = filters.apply(
        select(CheckResult)
        .where(CheckResult.health_check_id == check_id)
        .order_by(CheckResult.checked_at.desc(), CheckResult.id.desc())
    )
    return [
        ResultOut(
            checked_at=row.checked_at,
            status=row.status,
            latency_ms=row.latency_ms,
            message=row.message,
            error_kind=row.error_kind,
            details=row.details,
        )
        for row in session.scalars(page.query(session, query))
    ]


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
    session.commit()
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
    changes = record_results(session, [result], [check.block_id]).changes
    block = session.get(Block, check.block_id)
    project = session.get(Project, block.project_id) if block else None
    if project is not None:
        notify(session, notifier, project, changes)
    return fresh_out(session, check)
