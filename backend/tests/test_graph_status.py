from collections.abc import Iterator
from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.models import Block, BlockKind, CheckMethod, CheckResult, CheckStatus, HealthCheck, Project
from app.services.graph_status import as_utc, block_statuses
from app.services.status import BlockStatus

NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)


def test_as_utc_adds_utc_to_naive_datetime():
    naive = datetime(2026, 10, 27, 12, 0)
    assert as_utc(naive) == NOW
    assert as_utc(naive).tzinfo is UTC


def test_as_utc_keeps_moment_of_aware_datetime():
    krasnoyarsk = timezone(timedelta(hours=7))
    assert as_utc(datetime(2026, 10, 27, 19, 0, tzinfo=krasnoyarsk)) == NOW


@pytest.fixture
def session(db: sessionmaker[Session]) -> Iterator[Session]:
    with db() as session:
        yield session


@pytest.fixture
def project(session: Session) -> Project:
    project = Project(name="demo", repo_full_name="example/demo")
    session.add(project)
    session.flush()
    return project


def add_block(session: Session, project: Project, name: str = "block") -> Block:
    block = Block(project_id=project.id, kind=BlockKind.server, name=name)
    session.add(block)
    session.flush()
    return block


def add_check(session: Session, block: Block, interval_sec: int = 60) -> HealthCheck:
    check = HealthCheck(
        block_id=block.id, method=CheckMethod.http, target="https://example.org", interval_sec=interval_sec
    )
    session.add(check)
    session.flush()
    return check


def add_result(session: Session, check: HealthCheck, status: CheckStatus, seconds_ago: int) -> None:
    session.add(
        CheckResult(health_check_id=check.id, status=status, checked_at=NOW - timedelta(seconds=seconds_ago))
    )
    session.flush()


def test_block_without_checks_is_unknown(session, project):
    block = add_block(session, project)
    assert block_statuses(session, [block.id], NOW) == {block.id: BlockStatus.unknown}


def test_check_without_results_is_unknown(session, project):
    block = add_block(session, project)
    add_check(session, block)
    assert block_statuses(session, [block.id], NOW) == {block.id: BlockStatus.unknown}


def test_check_without_results_hides_ok_check(session, project):
    block = add_block(session, project)
    add_result(session, add_check(session, block), CheckStatus.ok, seconds_ago=10)
    add_check(session, block)
    assert block_statuses(session, [block.id], NOW) == {block.id: BlockStatus.unknown}


def test_latest_result_wins(session, project):
    block = add_block(session, project)
    check = add_check(session, block)
    add_result(session, check, CheckStatus.fail, seconds_ago=120)
    add_result(session, check, CheckStatus.ok, seconds_ago=10)
    assert block_statuses(session, [block.id], NOW) == {block.id: BlockStatus.ok}


@pytest.mark.parametrize(("seconds_ago", "expected"), [(180, BlockStatus.ok), (181, BlockStatus.unknown)])
def test_result_expires_after_three_check_intervals(session, project, seconds_ago, expected):
    block = add_block(session, project)
    add_result(session, add_check(session, block, interval_sec=60), CheckStatus.ok, seconds_ago)
    assert block_statuses(session, [block.id], NOW) == {block.id: expected}


def test_worst_check_defines_block_status(session, project):
    block = add_block(session, project)
    add_result(session, add_check(session, block), CheckStatus.ok, seconds_ago=10)
    add_result(session, add_check(session, block), CheckStatus.warn, seconds_ago=10)
    assert block_statuses(session, [block.id], NOW) == {block.id: BlockStatus.warn}


def test_statuses_for_several_blocks(session, project):
    healthy = add_block(session, project, "healthy")
    broken = add_block(session, project, "broken")
    add_result(session, add_check(session, healthy), CheckStatus.ok, seconds_ago=10)
    add_result(session, add_check(session, broken), CheckStatus.fail, seconds_ago=10)
    assert block_statuses(session, [healthy.id, broken.id], NOW) == {
        healthy.id: BlockStatus.ok,
        broken.id: BlockStatus.fail,
    }


def test_unknown_block_id_is_unknown(session):
    assert block_statuses(session, [999], NOW) == {999: BlockStatus.unknown}


def test_empty_block_ids_returns_empty_dict(session):
    assert block_statuses(session, [], NOW) == {}


def test_naive_now_is_rejected(session, project):
    block = add_block(session, project)
    add_result(session, add_check(session, block), CheckStatus.ok, seconds_ago=10)
    with pytest.raises(ValueError, match="timezone-aware"):
        block_statuses(session, [block.id], NOW.replace(tzinfo=None))
