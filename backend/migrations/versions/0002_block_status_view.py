from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BLOCK_STATUS_VIEW = """
CREATE VIEW v_block_status AS
WITH check_state AS (
    SELECT
        hc.block_id,
        CASE
            WHEN latest.checked_at IS NULL
                OR now() - latest.checked_at > make_interval(secs => hc.interval_sec * 3) THEN 1
            WHEN latest.status = 'fail' THEN 3
            WHEN latest.status = 'warn' THEN 2
            ELSE 0
        END AS severity
    FROM health_check AS hc
    LEFT JOIN LATERAL (
        SELECT cr.status, cr.checked_at
        FROM check_result AS cr
        WHERE cr.health_check_id = hc.id
        ORDER BY cr.checked_at DESC
        LIMIT 1
    ) AS latest ON true
)
SELECT
    b.id AS block_id,
    b.project_id,
    b.name,
    CASE COALESCE(max(cs.severity), 1)
        WHEN 3 THEN 'fail'
        WHEN 2 THEN 'warn'
        WHEN 1 THEN 'unknown'
        ELSE 'ok'
    END AS status
FROM block AS b
LEFT JOIN check_state AS cs ON cs.block_id = b.id
GROUP BY b.id, b.project_id, b.name
"""


def upgrade() -> None:
    op.drop_index("ix_check_result_health_check_id", table_name="check_result")
    op.drop_index("ix_check_result_checked_at", table_name="check_result")
    op.create_index(
        "ix_check_result_check_time",
        "check_result",
        ["health_check_id", sa.text("checked_at DESC")],
    )
    op.create_index(
        "ix_check_result_checked_at_brin",
        "check_result",
        ["checked_at"],
        postgresql_using="brin",
        postgresql_with={"autosummarize": "on"},
    )
    op.execute(BLOCK_STATUS_VIEW)


def downgrade() -> None:
    op.execute("DROP VIEW v_block_status")
    op.drop_index("ix_check_result_checked_at_brin", table_name="check_result")
    op.drop_index("ix_check_result_check_time", table_name="check_result")
    op.create_index("ix_check_result_checked_at", "check_result", ["checked_at"])
    op.create_index("ix_check_result_health_check_id", "check_result", ["health_check_id"])
