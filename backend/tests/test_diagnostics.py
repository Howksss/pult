from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.models import Block, BlockKind, CheckMethod, CheckResult, CheckStatus, HealthCheck, Project
from app.services.graph_status import block_diagnoses, check_title, format_age
from app.services.status import BlockStatus

NOW = datetime(2026, 11, 17, 8, 0, tzinfo=UTC)


@pytest.fixture
def session(db: sessionmaker[Session]) -> Iterator[Session]:
    with db() as session:
        yield session


@pytest.fixture
def block(session: Session) -> Block:
    project = Project(name="demo", repo_full_name="example/demo")
    block = Block(project=project, kind=BlockKind.integration, name="POS-система")
    session.add(block)
    session.flush()
    return block


def add_check(
    session: Session,
    block: Block,
    method: CheckMethod = CheckMethod.http,
    name: str | None = None,
    enabled: bool = True,
) -> HealthCheck:
    check = HealthCheck(
        block_id=block.id, method=method, target="https://pos.example", name=name, enabled=enabled
    )
    session.add(check)
    session.flush()
    return check


def add_result(
    session: Session,
    check: HealthCheck,
    status: CheckStatus,
    seconds_ago: int = 10,
    message: str | None = None,
    error_kind: str | None = None,
) -> None:
    session.add(
        CheckResult(
            health_check_id=check.id,
            status=status,
            checked_at=NOW - timedelta(seconds=seconds_ago),
            message=message,
            error_kind=error_kind,
        )
    )
    session.flush()


def test_block_without_checks_says_so(session, block):
    diagnosis = block_diagnoses(session, [block.id], NOW)[block.id]
    assert diagnosis.status is BlockStatus.unknown
    assert diagnosis.reason == "Проверки не настроены"
    assert (diagnosis.checks_total, diagnosis.checks_problem) == (0, 0)


def test_healthy_block_has_no_reason(session, block):
    add_result(session, add_check(session, block, name="POS отвечает"), CheckStatus.ok)
    diagnosis = block_diagnoses(session, [block.id], NOW)[block.id]
    assert (diagnosis.status, diagnosis.reason, diagnosis.checks_total) == (BlockStatus.ok, None, 1)


def test_reason_names_the_worst_check_and_its_message(session, block):
    add_result(
        session, add_check(session, block, name="Отвечает быстро"), CheckStatus.warn, message="Ответ за 2,4 с"
    )
    add_result(
        session,
        add_check(session, block, name="POS отвечает"),
        CheckStatus.fail,
        message="HTTP 502 Bad Gateway",
    )
    add_result(session, add_check(session, block, name="Остатки свежие"), CheckStatus.ok)
    diagnosis = block_diagnoses(session, [block.id], NOW)[block.id]
    assert diagnosis.status is BlockStatus.fail
    assert diagnosis.reason == "POS отвечает: HTTP 502 Bad Gateway"
    assert (diagnosis.checks_total, diagnosis.checks_problem) == (3, 2)


def test_failure_without_message_falls_back_to_status_word(session, block):
    add_result(session, add_check(session, block, name="POS отвечает"), CheckStatus.fail)
    assert block_diagnoses(session, [block.id], NOW)[block.id].reason == "POS отвечает: сбой"


def test_unnamed_check_is_titled_by_method_and_target(session, block):
    add_result(session, add_check(session, block), CheckStatus.fail, message="Соединение отклонено")
    assert (
        block_diagnoses(session, [block.id], NOW)[block.id].reason
        == "HTTP https://pos.example: Соединение отклонено"
    )


def test_silent_job_is_a_missed_run(session, block):
    job = add_check(session, block, method=CheckMethod.exit_code, name="Автозаказ отработал")
    add_result(session, job, CheckStatus.ok, seconds_ago=25 * 60)
    diagnosis = block_diagnoses(session, [block.id], NOW)[block.id]
    assert diagnosis.status is BlockStatus.fail
    assert diagnosis.reason == "Автозаказ отработал: нет отчёта 25 мин"


def test_stale_pull_check_is_unknown_with_age(session, block):
    add_result(session, add_check(session, block, name="POS отвечает"), CheckStatus.ok, seconds_ago=2 * 3600)
    diagnosis = block_diagnoses(session, [block.id], NOW)[block.id]
    assert (diagnosis.status, diagnosis.reason) == (BlockStatus.unknown, "POS отвечает: нет данных 2 ч")


def test_check_without_results_is_waiting(session, block):
    add_check(session, block, name="POS отвечает")
    diagnosis = block_diagnoses(session, [block.id], NOW)[block.id]
    assert (diagnosis.status, diagnosis.reason) == (
        BlockStatus.unknown,
        "POS отвечает: результатов ещё не было",
    )


def test_disabled_checks_do_not_count(session, block):
    add_result(session, add_check(session, block, name="Старый адрес", enabled=False), CheckStatus.fail)
    add_result(session, add_check(session, block, name="POS отвечает"), CheckStatus.ok)
    diagnosis = block_diagnoses(session, [block.id], NOW)[block.id]
    assert (diagnosis.status, diagnosis.checks_total) == (BlockStatus.ok, 1)


def test_second_result_for_the_same_moment_is_rejected(session, block):
    check = add_check(session, block, name="POS отвечает")
    add_result(session, check, CheckStatus.fail, seconds_ago=10, message="старый")
    with pytest.raises(IntegrityError):
        add_result(session, check, CheckStatus.ok, seconds_ago=10)


def test_naive_now_is_rejected(session, block):
    with pytest.raises(ValueError, match="timezone-aware"):
        block_diagnoses(session, [block.id], datetime(2026, 11, 17, 8, 0))


def test_empty_block_list(session):
    assert block_diagnoses(session, [], NOW) == {}


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (30, "меньше минуты"),
        (25 * 60, "25 мин"),
        (3600, "1 ч"),
        (3 * 3600 + 600, "3 ч 10 мин"),
        (3 * 86400, "3 дн"),
    ],
)
def test_format_age(seconds, expected):
    assert format_age(seconds) == expected


def test_check_title_prefers_name():
    assert (
        check_title(HealthCheck(method=CheckMethod.tcp, target="db:5432", name="База принимает"))
        == "База принимает"
    )
    assert check_title(HealthCheck(method=CheckMethod.tcp, target="db:5432")) == "Порт db:5432"
