from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.telegram import TelegramNotifier, format_message, is_notable
from app.models import Block, CheckResult, CheckStatus, Project
from app.services.graph_status import as_utc, block_statuses
from app.services.status import BlockStatus


@dataclass(frozen=True)
class NewResult:
    health_check_id: int
    status: CheckStatus
    checked_at: datetime
    latency_ms: int | None = None
    message: str | None = None
    error_kind: str | None = None
    details: dict[str, Any] | None = field(default=None)


@dataclass(frozen=True)
class Change:
    block_id: int
    previous: BlockStatus
    current: BlockStatus


def record_results(session: Session, results: Sequence[NewResult], block_ids: list[int]) -> list[Change]:
    now = datetime.now(UTC)
    before = block_statuses(session, block_ids, now)
    session.add_all(
        CheckResult(
            health_check_id=result.health_check_id,
            status=result.status,
            checked_at=as_utc(result.checked_at),
            latency_ms=result.latency_ms,
            message=result.message,
            error_kind=result.error_kind,
            details=result.details,
        )
        for result in results
    )
    session.flush()
    after = block_statuses(session, block_ids, now)
    session.commit()
    return [
        Change(block_id=block_id, previous=before[block_id], current=after[block_id])
        for block_id in block_ids
        if before[block_id] != after[block_id]
    ]


def notify(session: Session, notifier: TelegramNotifier, project: Project, changes: Sequence[Change]) -> None:
    notable = [change for change in changes if is_notable(change.previous, change.current)]
    if not notable or not notifier.enabled:
        return
    names = dict(
        session.execute(
            select(Block.id, Block.name).where(Block.id.in_([change.block_id for change in notable]))
        )
        .tuples()
        .all()
    )
    session.commit()
    for change in notable:
        notifier.send(format_message(project.name, names[change.block_id], change.previous, change.current))
