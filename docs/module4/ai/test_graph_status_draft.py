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


def test_as_utc_keeps_aware_datetime():
    krasnoyarsk = timezone(timedelta(hours=7))
    moment = datetime(2026, 10, 27, 19, 0, tzinfo=krasnoyarsk)
    assert as_utc(moment) is moment
    assert as_utc(moment) == NOW


@pytest.fixture
def session(db: sessionmaker[Session]):
    with db() as session:
        project = Project(name="demo", repo_full_name="example/demo", probe_token_hash="x")
        session.add(project)
        session.flush()
        yield session, project


def add_block(session, project, name="block"):
    block = Block(project_id=project.id, kind=BlockKind.server, name=name)
    session.add(block)
    session.flush()
    return block


def add_check(session, block, interval_sec=60):
    check = HealthCheck(
        block_id=block.id, method=CheckMethod.http, target="https://example.org", interval_sec=interval_sec
    )
    session.add(check)
    session.flush()
    return check


def add_result(session, check, status, seconds_ago):
    session.add(
        CheckResult(health_check_id=check.id, status=status, checked_at=NOW - timedelta(seconds=seconds_ago))
    )
    session.flush()


def test_block_without_checks_is_unknown(session):
    s, project = session
    block = add_block(s, project)
    assert block_statuses(s, [block.id], NOW) == {block.id: BlockStatus.unknown}


def test_check_without_results_is_unknown(session):
    s, project = session
    block = add_block(s, project)
    add_check(s, block)
    assert block_statuses(s, [block.id], NOW) == {block.id: BlockStatus.unknown}


def test_latest_result_wins(session):
    s, project = session
    block = add_block(s, project)
    check = add_check(s, block)
    add_result(s, check, CheckStatus.fail, seconds_ago=120)
    add_result(s, check, CheckStatus.ok, seconds_ago=10)
    assert block_statuses(s, [block.id], NOW) == {block.id: BlockStatus.ok}


def test_stale_result_is_unknown(session):
    s, project = session
    block = add_block(s, project)
    check = add_check(s, block, interval_sec=60)
    add_result(s, check, CheckStatus.ok, seconds_ago=181)
    assert block_statuses(s, [block.id], NOW) == {block.id: BlockStatus.unknown}


def test_worst_check_defines_block_status(session):
    s, project = session
    block = add_block(s, project)
    add_result(s, add_check(s, block), CheckStatus.ok, seconds_ago=10)
    add_result(s, add_check(s, block), CheckStatus.warn, seconds_ago=10)
    assert block_statuses(s, [block.id], NOW) == {block.id: BlockStatus.warn}


def test_check_without_results_hides_ok_check(session):
    s, project = session
    block = add_block(s, project)
    add_result(s, add_check(s, block), CheckStatus.ok, seconds_ago=10)
    add_check(s, block)
    assert block_statuses(s, [block.id], NOW) == {block.id: BlockStatus.unknown}


def test_statuses_for_several_blocks(session):
    s, project = session
    healthy = add_block(s, project, "healthy")
    broken = add_block(s, project, "broken")
    add_result(s, add_check(s, healthy), CheckStatus.ok, seconds_ago=10)
    add_result(s, add_check(s, broken), CheckStatus.fail, seconds_ago=10)
    assert block_statuses(s, [healthy.id, broken.id], NOW) == {
        healthy.id: BlockStatus.ok,
        broken.id: BlockStatus.fail,
    }


def test_unknown_block_id_is_unknown(session):
    s, _ = session
    assert block_statuses(s, [999], NOW) == {999: BlockStatus.unknown}


def test_empty_block_ids_returns_empty_dict(session):
    s, _ = session
    assert block_statuses(s, [], NOW) == {}


def test_naive_now_is_rejected(session):
    s, project = session
    block = add_block(s, project)
    add_result(s, add_check(s, block), CheckStatus.ok, seconds_ago=10)
    with pytest.raises(ValueError):
        block_statuses(s, [block.id], NOW.replace(tzinfo=None))
