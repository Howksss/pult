from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CHECKS = [
    ("project", "ck_project_name_not_blank", "trim(name) <> ''"),
    ("project", "ck_project_default_branch_not_blank", "trim(default_branch) <> ''"),
    ("project", "ck_project_repo_full_name_format", "repo_full_name ~ '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$'"),
    (
        "app_user",
        "ck_app_user_email_format",
        "email ~ '^[^@[:space:]]+@[^@[:space:]]+[.][^@[:space:]]+$' AND email = lower(email)",
    ),
    ("app_user", "ck_app_user_full_name_not_blank", "trim(full_name) <> ''"),
    ("block", "ck_block_name_not_blank", "trim(name) <> ''"),
    (
        "block_scope",
        "ck_block_scope_relative_path",
        "path_glob <> '' AND left(path_glob, 1) <> '/' AND strpos(path_glob, chr(92)) = 0 "
        "AND path_glob !~ '(^|/)[.][.](/|$)'",
    ),
    ("health_check", "ck_health_check_interval_range", "interval_sec BETWEEN 10 AND 604800"),
    ("health_check", "ck_health_check_timeout_range", "timeout_sec BETWEEN 1 AND 60"),
    ("health_check", "ck_health_check_timeout_within_interval", "timeout_sec <= interval_sec"),
    ("health_check", "ck_health_check_target_not_blank", "trim(target) <> ''"),
    ("check_result", "ck_check_result_latency_not_negative", "latency_ms IS NULL OR latency_ms >= 0"),
    (
        "check_result",
        "ck_check_result_error_kind_format",
        "error_kind IS NULL OR error_kind ~ '^[a-z_]{1,40}$'",
    ),
    ("user_session", "ck_user_session_expires_after_created", "expires_at > created_at"),
    ("agent_task", "ck_agent_task_title_not_blank", "trim(title) <> ''"),
    (
        "agent_task",
        "ck_agent_task_finished_after_created",
        "finished_at IS NULL OR finished_at >= created_at",
    ),
    (
        "task_message",
        "ck_task_message_tokens_not_negative",
        "(input_tokens IS NULL OR input_tokens >= 0) AND (output_tokens IS NULL OR output_tokens >= 0)",
    ),
    ("change_request", "ck_change_request_pr_number_positive", "pr_number > 0"),
    (
        "change_request",
        "ck_change_request_reviewed_by_reviewer",
        "reviewed_at IS NULL OR reviewer_id IS NOT NULL",
    ),
    ("deployment", "ck_deployment_commit_sha_format", "commit_sha ~ '^[0-9a-f]{40}$'"),
    (
        "deployment",
        "ck_deployment_finished_after_started",
        "finished_at IS NULL OR finished_at >= started_at",
    ),
    ("deployment", "ck_deployment_finished_when_done", "(status = 'running') = (finished_at IS NULL)"),
    ("audit_event", "ck_audit_event_action_not_blank", "trim(action) <> ''"),
]

RESTRICTED = [
    ("agent_task", "agent_task_author_id_fkey", "author_id"),
    ("change_request", "change_request_reviewer_id_fkey", "reviewer_id"),
]


def upgrade() -> None:
    for table, name, condition in CHECKS:
        op.create_check_constraint(name, table, condition)
    op.execute(
        """
        DELETE FROM block_link AS duplicate
        USING block_link AS kept
        WHERE duplicate.source_block_id = kept.source_block_id
            AND duplicate.target_block_id = kept.target_block_id
            AND duplicate.id > kept.id
        """
    )
    op.create_unique_constraint(
        "uq_block_link_source_target", "block_link", ["source_block_id", "target_block_id"]
    )
    op.create_index(
        "uq_deployment_one_running",
        "deployment",
        ["change_request_id"],
        unique=True,
        postgresql_where="status = 'running'",
    )
    for table, name, column in RESTRICTED:
        op.drop_constraint(name, table, type_="foreignkey")
        op.create_foreign_key(name, table, "app_user", [column], ["id"], ondelete="RESTRICT")


def downgrade() -> None:
    for table, name, column in RESTRICTED:
        op.drop_constraint(name, table, type_="foreignkey")
        op.create_foreign_key(name, table, "app_user", [column], ["id"])
    op.drop_index("uq_deployment_one_running", table_name="deployment")
    op.drop_constraint("uq_block_link_source_target", "block_link", type_="unique")
    for table, name, _ in reversed(CHECKS):
        op.drop_constraint(name, table, type_="check")
