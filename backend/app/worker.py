import logging
import time
from collections import defaultdict
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app import __version__
from app.core.config import get_settings
from app.core.observability import configure_logging
from app.db import get_engine
from app.integrations.telegram import TelegramNotifier
from app.models import Block, CheckResult, CheckStatus, HealthCheck, Project
from app.services.checks import PULL_METHODS, Outcome, run_check
from app.services.graph_status import as_utc
from app.services.results import NewResult, notify, record_results

TICK_SEC = 5
PARALLEL_CHECKS = 8

logger = logging.getLogger("pult.worker")

Runner = Callable[[HealthCheck, httpx.Client], Outcome]


def due_checks(session: Session, now: datetime) -> list[HealthCheck]:
    last = (
        select(func.max(CheckResult.checked_at))
        .where(CheckResult.health_check_id == HealthCheck.id)
        .correlate(HealthCheck)
        .scalar_subquery()
    )
    rows = session.execute(
        select(HealthCheck, last)
        .where(HealthCheck.enabled.is_(True), HealthCheck.method.in_(PULL_METHODS))
        .order_by(HealthCheck.id)
    ).all()
    return [
        check
        for check, checked_at in rows
        if checked_at is None or now - as_utc(checked_at) >= timedelta(seconds=check.interval_sec)
    ]


def safe_run(runner: Runner, check: HealthCheck, client: httpx.Client) -> Outcome:
    try:
        return runner(check, client)
    except Exception as error:
        logger.exception("check crashed", extra={"fields": {"health_check_id": check.id}})
        return Outcome(CheckStatus.fail, None, f"Проверка не выполнилась: {error}"[:300], "internal")


def run_due(
    factory: sessionmaker[Session],
    client: httpx.Client,
    notifier: TelegramNotifier,
    runner: Runner = run_check,
    now: datetime | None = None,
) -> int:
    with factory() as session:
        due = due_checks(session, now or datetime.now(UTC))
    if not due:
        return 0
    with ThreadPoolExecutor(max_workers=PARALLEL_CHECKS) as pool:
        outcomes = list(pool.map(lambda check: safe_run(runner, check, client), due))
    checked_at = datetime.now(UTC)
    with factory() as session:
        projects = dict(
            session.execute(select(Block.id, Block.project_id).where(Block.id.in_({c.block_id for c in due})))
            .tuples()
            .all()
        )
        grouped: dict[int, list[tuple[HealthCheck, Outcome]]] = defaultdict(list)
        for check, outcome in zip(due, outcomes, strict=True):
            grouped[projects[check.block_id]].append((check, outcome))
        for project_id, items in grouped.items():
            results = [
                NewResult(
                    health_check_id=check.id,
                    status=outcome.status,
                    checked_at=checked_at,
                    latency_ms=outcome.latency_ms,
                    message=outcome.message,
                    error_kind=outcome.error_kind,
                    details=outcome.details or None,
                )
                for check, outcome in items
            ]
            changes = record_results(session, results, sorted({check.block_id for check, _ in items}))
            project = session.get(Project, project_id)
            if project is not None:
                notify(session, notifier, project, changes)
    return len(due)


def main(sleep: Callable[[float], None] = time.sleep) -> None:
    configure_logging()
    settings = get_settings()
    factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    notifier = TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id)
    headers = {"User-Agent": f"Pult/{__version__} health check"}
    with httpx.Client(follow_redirects=True, headers=headers) as client:
        while True:
            try:
                count = run_due(factory, client, notifier)
                if count:
                    logger.info("checks done", extra={"fields": {"count": count}})
            except Exception:
                logger.exception("worker tick failed")
            sleep(TICK_SEC)


if __name__ == "__main__":
    main()
