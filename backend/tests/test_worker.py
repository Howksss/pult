from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app import worker
from app.models import Block, BlockKind, CheckMethod, CheckResult, CheckStatus, HealthCheck, Project
from app.services.checks import Outcome

NOW = datetime.now(UTC)


class FakeNotifier:
    enabled = True

    def __init__(self) -> None:
        self.sent: list[str] = []

    def send(self, text: str) -> bool:
        self.sent.append(text)
        return True


def seed(db: sessionmaker[Session]) -> dict[str, int]:
    with db() as session:
        project = Project(name="pilot", repo_full_name="example/pilot")
        pos = Block(project=project, kind=BlockKind.integration, name="POS-система")
        session.add(pos)
        session.flush()
        checks = {
            "fresh": HealthCheck(
                block_id=pos.id, method=CheckMethod.http, target="https://pos.example", interval_sec=60
            ),
            "never": HealthCheck(
                block_id=pos.id, method=CheckMethod.tls, target="pos.example", interval_sec=60
            ),
            "old": HealthCheck(
                block_id=pos.id, method=CheckMethod.tcp, target="pos.example:5432", interval_sec=60
            ),
            "push": HealthCheck(
                block_id=pos.id, method=CheckMethod.exit_code, target="main.py", interval_sec=60
            ),
            "off": HealthCheck(
                block_id=pos.id, method=CheckMethod.http, target="https://old.example", enabled=False
            ),
        }
        session.add_all(checks.values())
        session.flush()
        session.add_all(
            [
                CheckResult(
                    health_check_id=checks["fresh"].id,
                    status=CheckStatus.ok,
                    checked_at=NOW - timedelta(seconds=20),
                ),
                CheckResult(
                    health_check_id=checks["old"].id,
                    status=CheckStatus.ok,
                    checked_at=NOW - timedelta(seconds=61),
                ),
            ]
        )
        session.commit()
        return {"block": pos.id, **{key: check.id for key, check in checks.items()}}


def test_due_checks_are_pull_checks_whose_interval_passed(db):
    ids = seed(db)
    with db() as session:
        due = {check.id for check in worker.due_checks(session, NOW)}
    assert due == {ids["never"], ids["old"]}


def test_run_due_records_outcomes_with_details_and_notifies(db):
    ids = seed(db)
    notifier = FakeNotifier()

    def runner(check: HealthCheck, client: httpx.Client) -> Outcome:
        if check.method is CheckMethod.tcp:
            return Outcome(
                CheckStatus.fail, 3, "Порт 5432 закрыт", "connection", {"host": "pos.example", "port": 5432}
            )
        return Outcome(CheckStatus.ok, 40, None, None, {"days_left": 60})

    with httpx.Client() as client:
        assert worker.run_due(db, client, notifier, runner=runner, now=NOW) == 2
    with db() as session:
        failed = session.scalars(
            select(CheckResult)
            .where(CheckResult.health_check_id == ids["old"])
            .order_by(CheckResult.id.desc())
        ).first()
        tls = session.scalars(select(CheckResult).where(CheckResult.health_check_id == ids["never"])).one()
    assert failed is not None
    assert (failed.status, failed.message, failed.error_kind) == (
        CheckStatus.fail,
        "Порт 5432 закрыт",
        "connection",
    )
    assert failed.details == {"host": "pos.example", "port": 5432}
    assert tls.details == {"days_left": 60}
    assert notifier.sent == ["Сбой блока «POS-система» в проекте «pilot»: нет данных → сбой"]


def test_crashed_runner_becomes_internal_failure(db):
    ids = seed(db)

    def runner(check: HealthCheck, client: httpx.Client) -> Outcome:
        raise KeyError("notAfter")

    with httpx.Client() as client:
        worker.run_due(db, client, FakeNotifier(), runner=runner, now=NOW)
    with db() as session:
        result = session.scalars(select(CheckResult).where(CheckResult.health_check_id == ids["never"])).one()
    assert (result.status, result.error_kind, result.message) == (
        CheckStatus.fail,
        "internal",
        "Проверка не выполнилась: 'notAfter'",
    )


def test_nothing_due_does_nothing(db):
    with httpx.Client() as client:
        assert worker.run_due(db, client, FakeNotifier(), now=NOW) == 0


def test_main_keeps_running_after_a_failed_tick(monkeypatch):
    calls: list[str] = []

    def fake_run_due(*args, **kwargs):
        calls.append("tick")
        if len(calls) == 1:
            return 3
        raise OperationalError("select 1", {}, Exception("database is down"))

    def fake_sleep(seconds: float) -> None:
        if len(calls) >= 2:
            raise SystemExit

    monkeypatch.setattr(worker, "run_due", fake_run_due)
    with pytest.raises(SystemExit):
        worker.main(sleep=fake_sleep)
    assert calls == ["tick", "tick"]
