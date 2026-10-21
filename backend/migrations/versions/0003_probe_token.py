from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("project", sa.Column("probe_token_hash", sa.String(length=64), nullable=True))
    op.create_unique_constraint("uq_project_probe_token_hash", "project", ["probe_token_hash"])


def downgrade() -> None:
    op.drop_constraint("uq_project_probe_token_hash", "project", type_="unique")
    op.drop_column("project", "probe_token_hash")
