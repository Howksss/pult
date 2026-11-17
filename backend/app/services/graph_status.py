from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CheckMethod, CheckResult, HealthCheck
from app.services.status import SEVERITY, BlockStatus, CheckSnapshot, check_status, is_missed

METHOD_LABELS = {
    CheckMethod.http: "HTTP",
    CheckMethod.tls: "Сертификат",
    CheckMethod.tcp: "Порт",
    CheckMethod.heartbeat: "Heartbeat",
    CheckMethod.exit_code: "Задание",
    CheckMethod.log_pattern: "Лог",
}

STATUS_WORDS = {
    BlockStatus.ok: "работает",
    BlockStatus.warn: "предупреждение",
    BlockStatus.fail: "сбой",
    BlockStatus.unknown: "нет данных",
}


def as_utc(moment: datetime) -> datetime:
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)


def format_age(seconds: float) -> str:
    minutes = int(seconds // 60)
    if minutes < 1:
        return "меньше минуты"
    if minutes < 60:
        return f"{minutes} мин"
    hours, rest = divmod(minutes, 60)
    if hours < 24:
        return f"{hours} ч {rest} мин" if rest else f"{hours} ч"
    return f"{hours // 24} дн"


def check_title(check: HealthCheck) -> str:
    return check.name or f"{METHOD_LABELS[check.method]} {check.target}"


@dataclass(frozen=True)
class CheckState:
    status: BlockStatus
    reason: str | None
    error_kind: str | None


@dataclass(frozen=True)
class BlockDiagnosis:
    status: BlockStatus
    reason: str | None
    checks_total: int
    checks_problem: int


def snapshot_of(check: HealthCheck, result: CheckResult | None) -> CheckSnapshot | None:
    if result is None:
        return None
    return CheckSnapshot(
        status=result.status,
        checked_at=as_utc(result.checked_at),
        interval_sec=check.interval_sec,
        method=check.method,
    )


def check_state(check: HealthCheck, result: CheckResult | None, now: datetime) -> CheckState:
    snapshot = snapshot_of(check, result)
    status = check_status(snapshot, now)
    if snapshot is None or result is None:
        return CheckState(status, "результатов ещё не было", None)
    age = format_age((now - snapshot.checked_at).total_seconds())
    if is_missed(snapshot, now):
        return CheckState(status, f"нет отчёта {age}", "missed")
    if status is BlockStatus.unknown:
        return CheckState(status, f"нет данных {age}", None)
    if status is BlockStatus.ok:
        return CheckState(status, None, None)
    return CheckState(status, result.message or STATUS_WORDS[status], result.error_kind)


def latest_results(
    session: Session, block_ids: Sequence[int]
) -> Sequence[tuple[HealthCheck, CheckResult | None]]:
    if not block_ids:
        return []
    latest_id = (
        select(CheckResult.id)
        .where(CheckResult.health_check_id == HealthCheck.id)
        .order_by(CheckResult.checked_at.desc(), CheckResult.id.desc())
        .limit(1)
        .correlate(HealthCheck)
        .scalar_subquery()
    )
    return (
        session.execute(
            select(HealthCheck, CheckResult)
            .outerjoin(CheckResult, CheckResult.id == latest_id)
            .where(HealthCheck.block_id.in_(block_ids), HealthCheck.enabled.is_(True))
            .order_by(HealthCheck.id)
        )
        .tuples()
        .all()
    )


def block_diagnoses(session: Session, block_ids: Sequence[int], now: datetime) -> dict[int, BlockDiagnosis]:
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    states: dict[int, list[tuple[HealthCheck, CheckState]]] = defaultdict(list)
    for check, result in latest_results(session, block_ids):
        states[check.block_id].append((check, check_state(check, result, now)))
    diagnoses = {}
    for block_id in block_ids:
        checks = states.get(block_id, [])
        if not checks:
            diagnoses[block_id] = BlockDiagnosis(BlockStatus.unknown, "Проверки не настроены", 0, 0)
            continue
        problems = [(check, state) for check, state in checks if state.status is not BlockStatus.ok]
        if not problems:
            diagnoses[block_id] = BlockDiagnosis(BlockStatus.ok, None, len(checks), 0)
            continue
        worst_check, worst = max(problems, key=lambda item: SEVERITY[item[1].status])
        diagnoses[block_id] = BlockDiagnosis(
            worst.status, f"{check_title(worst_check)}: {worst.reason}", len(checks), len(problems)
        )
    return diagnoses


def block_statuses(session: Session, block_ids: Sequence[int], now: datetime) -> dict[int, BlockStatus]:
    return {
        block_id: diagnosis.status for block_id, diagnosis in block_diagnoses(session, block_ids, now).items()
    }
