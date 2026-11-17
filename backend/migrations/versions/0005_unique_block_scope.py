from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM block_scope AS duplicate
        USING block_scope AS kept
        WHERE duplicate.block_id = kept.block_id
            AND duplicate.path_glob = kept.path_glob
            AND duplicate.id > kept.id
        """
    )
    op.create_unique_constraint("uq_block_scope_block_id_path_glob", "block_scope", ["block_id", "path_glob"])


def downgrade() -> None:
    op.drop_constraint("uq_block_scope_block_id_path_glob", "block_scope", type_="unique")
