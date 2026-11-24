from collections.abc import Sequence

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_health_check_block_id", "health_check", ["block_id"])
    op.create_index("ix_block_link_target_block_id", "block_link", ["target_block_id"])
    op.create_index("ix_project_member_user_id", "project_member", ["user_id"])
    op.drop_index("ix_block_scope_block_id", table_name="block_scope")
    op.drop_index("ix_user_session_user_id", table_name="user_session")


def downgrade() -> None:
    op.create_index("ix_user_session_user_id", "user_session", ["user_id"])
    op.create_index("ix_block_scope_block_id", "block_scope", ["block_id"])
    op.drop_index("ix_project_member_user_id", table_name="project_member")
    op.drop_index("ix_block_link_target_block_id", table_name="block_link")
    op.drop_index("ix_health_check_block_id", table_name="health_check")
