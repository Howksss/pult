from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from app.models.health import CheckStatus

STALE_AFTER_INTERVALS = 3


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


def check_status(snapshot: CheckSnapshot | None, now: datetime) -> BlockStatus:
    if snapshot is None:
        return BlockStatus.unknown
    stale_after = timedelta(seconds=snapshot.interval_sec * STALE_AFTER_INTERVALS)
    if now - snapshot.checked_at > stale_after:
        return BlockStatus.unknown
    return BlockStatus(snapshot.status.value)


def block_status(latest: Iterable[CheckSnapshot | None], now: datetime) -> BlockStatus:
    statuses = [check_status(snapshot, now) for snapshot in latest]
    if not statuses:
        return BlockStatus.unknown
    return max(statuses, key=SEVERITY.__getitem__)
