import os
from collections.abc import Iterator
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.models import Block, BlockKind, CheckMethod, CheckResult, CheckStatus, HealthCheck, Project
from app.services.status import CheckSnapshot, block_status

DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(DATABASE_URL is None, reason="TEST_DATABASE_URL не задан")

OK, WARN, FAIL = CheckStatus.ok, CheckStatus.warn, CheckStatus.fail

SCENARIOS = {
    "all_ok": [[(OK, 10)], [(OK, 40)]],
    "one_fail": [[(OK, 10)], [(FAIL, 30)]],
    "warn_and_fail": [[(WARN, 5)], [(FAIL, 30)]],
    "ok_and_warn": [[(OK, 5)], [(WARN, 30)]],
    "ok_and_silent": [[(OK, 5)], []],
    "stale_fail_and_ok": [[(FAIL, 1000)], [(OK, 5)]],
    "boundary": [[(OK, 180)]],
    "latest_wins": [[(FAIL, 300), (OK, 10)]],
    "no_checks": [],
}


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine(str(DATABASE_URL))
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session
        transaction.rollback()
    engine.dispose()


def build_block(session: Session, checks: list[list[tuple[CheckStatus, int]]], now: datetime) -> Block:
    block = Block(
        project=Project(name="pilot", repo_full_name="example/pilot-system"),
        kind=BlockKind.integration,
        name="POS-система",
    )
    session.add(block)
    session.flush()
    for results in checks:
        check = HealthCheck(
            block_id=block.id, method=CheckMethod.http, target="https://pos.example", interval_sec=60
        )
        session.add(check)
        session.flush()
        for status, seconds_ago in results:
            session.add(
                CheckResult(
                    health_check_id=check.id,
                    status=status,
                    checked_at=now - timedelta(seconds=seconds_ago),
                )
            )
    session.flush()
    return block


def python_status(checks: list[list[tuple[CheckStatus, int]]], now: datetime) -> str:
    latest = []
    for results in checks:
        if not results:
            latest.append(None)
            continue
        status, seconds_ago = min(results, key=lambda item: item[1])
        latest.append(
            CheckSnapshot(status=status, checked_at=now - timedelta(seconds=seconds_ago), interval_sec=60)
        )
    return block_status(latest, now).value


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_view_matches_python_service(session, scenario):
    now = session.execute(text("select now()")).scalar_one()
    checks = SCENARIOS[scenario]
    block = build_block(session, checks, now)
    view_status = session.execute(
        text("select status from v_block_status where block_id = :id"), {"id": block.id}
    ).scalar_one()
    assert view_status == python_status(checks, now)
