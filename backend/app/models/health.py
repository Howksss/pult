import enum
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, String, Text, desc, func, true
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, JsonDocument, pg_check


class CheckMethod(str, enum.Enum):
    heartbeat = "heartbeat"
    http = "http"
    log_pattern = "log_pattern"
    exit_code = "exit_code"
    tls = "tls"
    tcp = "tcp"


class CheckStatus(str, enum.Enum):
    ok = "ok"
    warn = "warn"
    fail = "fail"


class HealthCheck(Base):
    __tablename__ = "health_check"
    __table_args__ = (
        CheckConstraint("interval_sec BETWEEN 10 AND 604800", name="ck_health_check_interval_range"),
        CheckConstraint("timeout_sec BETWEEN 1 AND 60", name="ck_health_check_timeout_range"),
        CheckConstraint("timeout_sec <= interval_sec", name="ck_health_check_timeout_within_interval"),
        CheckConstraint("trim(target) <> ''", name="ck_health_check_target_not_blank"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    block_id: Mapped[int] = mapped_column(ForeignKey("block.id", ondelete="CASCADE"), index=True)
    method: Mapped[CheckMethod] = mapped_column(Enum(CheckMethod, name="check_method"))
    target: Mapped[str] = mapped_column(String(500))
    interval_sec: Mapped[int] = mapped_column(default=60)
    timeout_sec: Mapped[int] = mapped_column(default=10)
    name: Mapped[str | None] = mapped_column(String(120))
    config: Mapped[dict[str, Any]] = mapped_column(JsonDocument, default=dict, server_default="{}")
    enabled: Mapped[bool] = mapped_column(default=True, server_default=true())


class CheckResult(Base):
    __tablename__ = "check_result"
    __table_args__ = (
        Index("ix_check_result_check_time", "health_check_id", desc("checked_at")),
        Index(
            "ix_check_result_checked_at_brin",
            "checked_at",
            postgresql_using="brin",
            postgresql_with={"autosummarize": "on"},
        ),
        CheckConstraint("latency_ms IS NULL OR latency_ms >= 0", name="ck_check_result_latency_not_negative"),
        pg_check("error_kind IS NULL OR error_kind ~ '^[a-z_]{1,40}$'", "ck_check_result_error_kind_format"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    health_check_id: Mapped[int] = mapped_column(ForeignKey("health_check.id", ondelete="CASCADE"))
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status: Mapped[CheckStatus] = mapped_column(Enum(CheckStatus, name="check_status"))
    latency_ms: Mapped[int | None]
    message: Mapped[str | None] = mapped_column(Text)
    error_kind: Mapped[str | None] = mapped_column(String(40))
    details: Mapped[dict[str, Any] | None] = mapped_column(JsonDocument)
