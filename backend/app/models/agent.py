import enum
from datetime import datetime
from typing import Any

from sqlalchemy import CHAR, CheckConstraint, DateTime, Enum, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, JsonDocument, pg_check


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
    __table_args__ = (
        CheckConstraint("trim(title) <> ''", name="ck_agent_task_title_not_blank"),
        CheckConstraint(
            "finished_at IS NULL OR finished_at >= created_at", name="ck_agent_task_finished_after_created"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    block_id: Mapped[int] = mapped_column(ForeignKey("block.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("app_user.id", ondelete="RESTRICT"))
    title: Mapped[str] = mapped_column(String(200))
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus, name="task_status"), default=TaskStatus.new)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TaskMessage(CreatedAtMixin, Base):
    __tablename__ = "task_message"
    __table_args__ = (
        CheckConstraint(
            "(input_tokens IS NULL OR input_tokens >= 0) AND (output_tokens IS NULL OR output_tokens >= 0)",
            name="ck_task_message_tokens_not_negative",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("agent_task.id", ondelete="CASCADE"), index=True)
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole, name="message_role"))
    content: Mapped[Any] = mapped_column(JsonDocument)
    input_tokens: Mapped[int | None]
    output_tokens: Mapped[int | None]


class ChangeRequest(Base):
    __tablename__ = "change_request"
    __table_args__ = (
        CheckConstraint("pr_number > 0", name="ck_change_request_pr_number_positive"),
        CheckConstraint(
            "reviewed_at IS NULL OR reviewer_id IS NOT NULL", name="ck_change_request_reviewed_by_reviewer"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("agent_task.id", ondelete="CASCADE"), unique=True)
    branch_name: Mapped[str] = mapped_column(String(200))
    pr_number: Mapped[int]
    status: Mapped[ChangeRequestStatus] = mapped_column(
        Enum(ChangeRequestStatus, name="cr_status"), default=ChangeRequestStatus.open
    )
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("app_user.id", ondelete="RESTRICT"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Deployment(Base):
    __tablename__ = "deployment"
    __table_args__ = (
        pg_check("commit_sha ~ '^[0-9a-f]{40}$'", "ck_deployment_commit_sha_format"),
        CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at", name="ck_deployment_finished_after_started"
        ),
        CheckConstraint(
            "(status = 'running') = (finished_at IS NULL)", name="ck_deployment_finished_when_done"
        ),
        Index(
            "uq_deployment_one_running",
            "change_request_id",
            unique=True,
            postgresql_where=text("status = 'running'"),
            sqlite_where=text("status = 'running'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    change_request_id: Mapped[int] = mapped_column(ForeignKey("change_request.id", ondelete="CASCADE"))
    commit_sha: Mapped[str] = mapped_column(CHAR(40))
    status: Mapped[DeployStatus] = mapped_column(Enum(DeployStatus, name="deploy_status"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
