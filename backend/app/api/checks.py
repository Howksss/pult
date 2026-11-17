from collections import defaultdict
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.api.graph import load_block
from app.api.schemas import BlockChecksOut, CheckOut, HistoryPoint, ResultOut
from app.db import get_session
from app.models import CheckResult, HealthCheck
from app.services.graph_status import CheckState, check_state, check_title
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
def list_block_checks(block_id: int, session: SessionDep) -> BlockChecksOut:
    load_block(session, block_id)
    now = datetime.now(UTC)
    checks = session.scalars(
        select(HealthCheck).where(HealthCheck.block_id == block_id).order_by(HealthCheck.id)
    ).all()
    results = recent_results(session, [check.id for check in checks])
    items = [check_out(check, results.get(check.id, []), now) for check in checks]
    items.sort(key=lambda item: (not item.enabled, -SEVERITY[item.status], item.id))
    return BlockChecksOut(block_id=block_id, generated_at=now, checks=items)
