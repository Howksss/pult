from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CheckResult, CheckStatus, HealthCheck
from app.services.status import BlockStatus, CheckSnapshot, block_status


def as_utc(moment: datetime) -> datetime:
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)


def block_statuses(session: Session, block_ids: Sequence[int], now: datetime) -> dict[int, BlockStatus]:
    latest = (
        select(CheckResult)
        .where(CheckResult.health_check_id == HealthCheck.id)
        .order_by(CheckResult.checked_at.desc())
        .limit(1)
        .correlate(HealthCheck)
    )
    latest_status = latest.with_only_columns(CheckResult.status).scalar_subquery()
    latest_time = latest.with_only_columns(CheckResult.checked_at).scalar_subquery()
    rows = session.execute(
        select(HealthCheck.block_id, HealthCheck.interval_sec, latest_status, latest_time).where(
            HealthCheck.block_id.in_(block_ids)
        )
    ).all()

    snapshots: dict[int, list[CheckSnapshot | None]] = defaultdict(list)
    for block_id, interval_sec, status, checked_at in rows:
        if status is None or checked_at is None:
            snapshots[block_id].append(None)
        else:
            snapshots[block_id].append(
                CheckSnapshot(
                    status=CheckStatus(status), checked_at=as_utc(checked_at), interval_sec=interval_sec
                )
            )
    return {block_id: block_status(snapshots.get(block_id, []), now) for block_id in block_ids}
