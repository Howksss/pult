from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from app.models.health import CheckMethod, CheckStatus

STALE_AFTER_INTERVALS = 3
MISSED_AFTER_INTERVALS = 1.5
PUSH_METHODS = frozenset({CheckMethod.heartbeat, CheckMethod.exit_code, CheckMethod.log_pattern})


class BlockStatus(StrEnum):
    ok = "ok"
    warn = "warn"
    fail = "fail"
    unknown = "unknown"


SEVERITY = {
    BlockStatus.ok: 0,
    BlockStatus.unknown: 1,
    BlockStatus.warn: 2,
    BlockStatus.fail: 3,
}


@dataclass(frozen=True)
class CheckSnapshot:
    status: CheckStatus
    checked_at: datetime
    interval_sec: int
    method: CheckMethod = CheckMethod.http


def is_missed(snapshot: CheckSnapshot, now: datetime) -> bool:
    if snapshot.method not in PUSH_METHODS:
        return False
    return now - snapshot.checked_at > timedelta(seconds=snapshot.interval_sec * MISSED_AFTER_INTERVALS)


def check_status(snapshot: CheckSnapshot | None, now: datetime) -> BlockStatus:
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if snapshot is None:
        return BlockStatus.unknown
    if is_missed(snapshot, now):
        return BlockStatus.fail
    stale_after = timedelta(seconds=snapshot.interval_sec * STALE_AFTER_INTERVALS)
    if now - snapshot.checked_at > stale_after:
        return BlockStatus.unknown
    return BlockStatus(snapshot.status.value)


def block_status(latest: Iterable[CheckSnapshot | None], now: datetime) -> BlockStatus:
    statuses = [check_status(snapshot, now) for snapshot in latest]
    if not statuses:
        return BlockStatus.unknown
    return max(statuses, key=SEVERITY.__getitem__)
