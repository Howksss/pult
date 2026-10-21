from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "app_user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "project",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("repo_full_name", sa.String(length=200), nullable=False),
        sa.Column("default_branch", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "block",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("server", "scheduled_job", "bot", "integration", "config", "storage", name="block_kind"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("pos_x", sa.Float(), nullable=False),
        sa.Column("pos_y", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "name"),
    )
    op.create_index(op.f("ix_block_project_id"), "block", ["project_id"], unique=False)
    op.create_table(
        "project_member",
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.Enum("owner", "developer", "client", name="member_role"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["app_user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("project_id", "user_id"),
    )
    op.create_table(
        "agent_task",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("block_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "new",
                "running",
                "awaiting_review",
                "approved",
                "rejected",
                "deployed",
                "failed",
                name="task_status",
            ),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["app_user.id"],
        ),
        sa.ForeignKeyConstraint(["block_id"], ["block.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_task_block_id"), "agent_task", ["block_id"], unique=False)
    op.create_table(
        "audit_event",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("block_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column(
            "payload",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["block_id"], ["block.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_event_block_id"), "audit_event", ["block_id"], unique=False)
    op.create_table(
        "block_link",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_block_id", sa.Integer(), nullable=False),
        sa.Column("target_block_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=True),
        sa.CheckConstraint("source_block_id <> target_block_id", name="block_link_not_self"),
        sa.ForeignKeyConstraint(["source_block_id"], ["block.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_block_id"], ["block.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "block_scope",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("block_id", sa.Integer(), nullable=False),
        sa.Column("path_glob", sa.String(length=300), nullable=False),
        sa.Column("access", sa.Enum("read", "write", name="scope_access"), nullable=False),
        sa.ForeignKeyConstraint(["block_id"], ["block.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_block_scope_block_id"), "block_scope", ["block_id"], unique=False)
    op.create_table(
        "health_check",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("block_id", sa.Integer(), nullable=False),
        sa.Column(
            "method",
            sa.Enum("heartbeat", "http", "log_pattern", "exit_code", name="check_method"),
            nullable=False,
        ),
        sa.Column("target", sa.String(length=500), nullable=False),
        sa.Column("interval_sec", sa.Integer(), nullable=False),
        sa.Column("timeout_sec", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["block_id"], ["block.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "change_request",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("branch_name", sa.String(length=200), nullable=False),
        sa.Column("pr_number", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("open", "approved", "changes_requested", "merged", "closed", name="cr_status"),
            nullable=False,
        ),
        sa.Column("reviewer_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["reviewer_id"],
            ["app_user.id"],
        ),
        sa.ForeignKeyConstraint(["task_id"], ["agent_task.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id"),
    )
    op.create_table(
        "check_result",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("health_check_id", sa.Integer(), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("status", sa.Enum("ok", "warn", "fail", name="check_status"), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["health_check_id"], ["health_check.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_check_result_checked_at"), "check_result", ["checked_at"], unique=False)
    op.create_index(
        op.f("ix_check_result_health_check_id"), "check_result", ["health_check_id"], unique=False
    )
    op.create_table(
        "task_message",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.Enum("user", "assistant", "tool", name="message_role"), nullable=False),
        sa.Column(
            "content",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["agent_task.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_task_message_task_id"), "task_message", ["task_id"], unique=False)
    op.create_table(
        "deployment",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("change_request_id", sa.Integer(), nullable=False),
        sa.Column("commit_sha", sa.CHAR(length=40), nullable=False),
        sa.Column(
            "status",
            sa.Enum("running", "succeeded", "failed", "rolled_back", name="deploy_status"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["change_request_id"], ["change_request.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("deployment")
    op.drop_index(op.f("ix_task_message_task_id"), table_name="task_message")
    op.drop_table("task_message")
    op.drop_index(op.f("ix_check_result_health_check_id"), table_name="check_result")
    op.drop_index(op.f("ix_check_result_checked_at"), table_name="check_result")
    op.drop_table("check_result")
    op.drop_table("change_request")
    op.drop_table("health_check")
    op.drop_index(op.f("ix_block_scope_block_id"), table_name="block_scope")
    op.drop_table("block_scope")
    op.drop_table("block_link")
    op.drop_index(op.f("ix_audit_event_block_id"), table_name="audit_event")
    op.drop_table("audit_event")
    op.drop_index(op.f("ix_agent_task_block_id"), table_name="agent_task")
    op.drop_table("agent_task")
    op.drop_table("project_member")
    op.drop_index(op.f("ix_block_project_id"), table_name="block")
    op.drop_table("block")
    op.drop_table("project")
    op.drop_table("app_user")
    for enum_name in (
        "deploy_status",
        "message_role",
        "check_status",
        "cr_status",
        "check_method",
        "scope_access",
        "task_status",
        "member_role",
        "block_kind",
    ):
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
