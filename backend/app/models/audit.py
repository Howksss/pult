from typing import Any

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, JsonDocument


class AuditEvent(CreatedAtMixin, Base):
    __tablename__ = "audit_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("app_user.id", ondelete="RESTRICT"))
    block_id: Mapped[int | None] = mapped_column(ForeignKey("block.id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(String(100))
    payload: Mapped[Any] = mapped_column(JsonDocument, nullable=True)
