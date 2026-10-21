import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CheckMethod(str, enum.Enum):
    heartbeat = "heartbeat"
    http = "http"
    log_pattern = "log_pattern"
    exit_code = "exit_code"


class CheckStatus(str, enum.Enum):
    ok = "ok"
    warn = "warn"
    fail = "fail"


class HealthCheck(Base):
    __tablename__ = "health_check"

    id: Mapped[int] = mapped_column(primary_key=True)
    block_id: Mapped[int] = mapped_column(ForeignKey("block.id", ondelete="CASCADE"))
    method: Mapped[CheckMethod] = mapped_column(Enum(CheckMethod, name="check_method"))
    target: Mapped[str] = mapped_column(String(500))
    interval_sec: Mapped[int] = mapped_column(default=60)
    timeout_sec: Mapped[int] = mapped_column(default=10)


class CheckResult(Base):
    __tablename__ = "check_result"

    id: Mapped[int] = mapped_column(primary_key=True)
    health_check_id: Mapped[int] = mapped_column(
        ForeignKey("health_check.id", ondelete="CASCADE"), index=True
    )
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    status: Mapped[CheckStatus] = mapped_column(Enum(CheckStatus, name="check_status"))
    latency_ms: Mapped[int | None]
    message: Mapped[str | None] = mapped_column(Text)
