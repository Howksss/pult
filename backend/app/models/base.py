from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

JsonDocument = JSON().with_variant(JSONB, "postgresql")


class Base(DeclarativeBase):
    pass


def pg_check(sqltext: str, name: str) -> CheckConstraint:
    return CheckConstraint(sqltext, name=name).ddl_if(dialect="postgresql")


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
