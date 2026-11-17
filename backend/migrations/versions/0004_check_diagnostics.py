from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LATEST = """
    FROM health_check AS hc
    LEFT JOIN LATERAL (
        SELECT cr.status, cr.checked_at
        FROM check_result AS cr
        WHERE cr.health_check_id = hc.id
        ORDER BY cr.checked_at DESC
        LIMIT 1
    ) AS latest ON true
"""

AGGREGATE = """
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

VIEW_WITH_MISSED = f"""
CREATE VIEW v_block_status AS
WITH check_state AS (
    SELECT
        hc.block_id,
        CASE
            WHEN latest.checked_at IS NULL THEN 1
            WHEN hc.method IN ('heartbeat', 'exit_code', 'log_pattern')
                AND now() - latest.checked_at > make_interval(secs => hc.interval_sec * 1.5::float8) THEN 3
            WHEN now() - latest.checked_at > make_interval(secs => hc.interval_sec * 3) THEN 1
            WHEN latest.status = 'fail' THEN 3
            WHEN latest.status = 'warn' THEN 2
            ELSE 0
        END AS severity
    {LATEST}
    WHERE hc.enabled
)
{AGGREGATE}
"""

VIEW_BEFORE = f"""
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
    {LATEST}
)
{AGGREGATE}
"""


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE check_method ADD VALUE IF NOT EXISTS 'tls'")
        op.execute("ALTER TYPE check_method ADD VALUE IF NOT EXISTS 'tcp'")
    op.add_column("health_check", sa.Column("name", sa.String(length=120), nullable=True))
    op.add_column(
        "health_check",
        sa.Column("config", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.add_column(
        "health_check", sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true())
    )
    op.add_column("check_result", sa.Column("error_kind", sa.String(length=40), nullable=True))
    op.add_column("check_result", sa.Column("details", JSONB(), nullable=True))
    op.execute("DROP VIEW v_block_status")
    op.execute(VIEW_WITH_MISSED)


def downgrade() -> None:
    op.execute("DROP VIEW v_block_status")
    op.execute(VIEW_BEFORE)
    op.drop_column("check_result", "details")
    op.drop_column("check_result", "error_kind")
    op.drop_column("health_check", "enabled")
    op.drop_column("health_check", "config")
    op.drop_column("health_check", "name")
