import enum
from datetime import datetime
from typing import Any

from sqlalchemy import CHAR, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, JsonDocument


class TaskStatus(str, enum.Enum):
    new = "new"
    running = "running"
    awaiting_review = "awaiting_review"
    approved = "approved"
    rejected = "rejected"
    deployed = "deployed"
    failed = "failed"


class MessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    tool = "tool"


class ChangeRequestStatus(str, enum.Enum):
    open = "open"
    approved = "approved"
    changes_requested = "changes_requested"
    merged = "merged"
    closed = "closed"


class DeployStatus(str, enum.Enum):
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    rolled_back = "rolled_back"


class AgentTask(CreatedAtMixin, Base):
    __tablename__ = "agent_task"

    id: Mapped[int] = mapped_column(primary_key=True)
    block_id: Mapped[int] = mapped_column(ForeignKey("block.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("app_user.id"))
    title: Mapped[str] = mapped_column(String(200))
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus, name="task_status"), default=TaskStatus.new)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TaskMessage(CreatedAtMixin, Base):
    __tablename__ = "task_message"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("agent_task.id", ondelete="CASCADE"), index=True)
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole, name="message_role"))
    content: Mapped[Any] = mapped_column(JsonDocument)
    input_tokens: Mapped[int | None]
    output_tokens: Mapped[int | None]


class ChangeRequest(Base):
    __tablename__ = "change_request"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("agent_task.id", ondelete="CASCADE"), unique=True)
    branch_name: Mapped[str] = mapped_column(String(200))
    pr_number: Mapped[int]
    status: Mapped[ChangeRequestStatus] = mapped_column(
        Enum(ChangeRequestStatus, name="cr_status"), default=ChangeRequestStatus.open
    )
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("app_user.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Deployment(Base):
    __tablename__ = "deployment"

    id: Mapped[int] = mapped_column(primary_key=True)
    change_request_id: Mapped[int] = mapped_column(ForeignKey("change_request.id", ondelete="CASCADE"))
    commit_sha: Mapped[str] = mapped_column(CHAR(40))
    status: Mapped[DeployStatus] = mapped_column(Enum(DeployStatus, name="deploy_status"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
