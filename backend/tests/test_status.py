from datetime import UTC, datetime, timedelta

import pytest

from app.models.health import CheckStatus
from app.services.status import BlockStatus, CheckSnapshot, block_status, check_status

NOW = datetime(2026, 10, 21, 8, 0, tzinfo=UTC)


def snapshot(status: CheckStatus, seconds_ago: int, interval_sec: int = 60) -> CheckSnapshot:
    return CheckSnapshot(
        status=status,
        checked_at=NOW - timedelta(seconds=seconds_ago),
        interval_sec=interval_sec,
    )


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (CheckStatus.ok, BlockStatus.ok),
        (CheckStatus.warn, BlockStatus.warn),
        (CheckStatus.fail, BlockStatus.fail),
    ],
)
def test_fresh_result_keeps_its_status(status, expected):
    assert check_status(snapshot(status, seconds_ago=10), NOW) is expected


def test_no_result_is_unknown():
    assert check_status(None, NOW) is BlockStatus.unknown


def test_result_on_stale_boundary_is_still_valid():
    assert check_status(snapshot(CheckStatus.ok, seconds_ago=180), NOW) is BlockStatus.ok


def test_result_older_than_three_intervals_is_unknown():
    assert check_status(snapshot(CheckStatus.ok, seconds_ago=181), NOW) is BlockStatus.unknown


def test_stale_threshold_depends_on_check_interval():
    assert check_status(snapshot(CheckStatus.ok, seconds_ago=500, interval_sec=300), NOW) is BlockStatus.ok


def test_block_without_checks_is_unknown():
    assert block_status([], NOW) is BlockStatus.unknown


@pytest.mark.parametrize(
    ("snapshots", "expected"),
    [
        ([snapshot(CheckStatus.ok, 5), snapshot(CheckStatus.ok, 30)], BlockStatus.ok),
        ([snapshot(CheckStatus.ok, 5), snapshot(CheckStatus.fail, 30)], BlockStatus.fail),
        ([snapshot(CheckStatus.warn, 5), snapshot(CheckStatus.fail, 30)], BlockStatus.fail),
        ([snapshot(CheckStatus.ok, 5), snapshot(CheckStatus.warn, 30)], BlockStatus.warn),
        ([snapshot(CheckStatus.ok, 5), None], BlockStatus.unknown),
        ([snapshot(CheckStatus.warn, 5), None], BlockStatus.warn),
        ([snapshot(CheckStatus.fail, 1000), snapshot(CheckStatus.ok, 5)], BlockStatus.unknown),
    ],
)
def test_block_takes_worst_check_status(snapshots, expected):
    assert block_status(snapshots, NOW) is expected
