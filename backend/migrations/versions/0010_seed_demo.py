from collections.abc import Sequence
from pathlib import Path

from alembic import context, op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEED = Path(__file__).resolve().parents[1] / "seed_demo.sql"
TABLES = (
    "agent_task",
    "check_result",
    "health_check",
    "block_scope",
    "block_link",
    "block",
    "project_member",
    "project",
    "app_user",
)


def requested() -> bool:
    return context.get_x_argument(as_dictionary=True).get("seed") == "demo"


def statements(script: str) -> list[str]:
    body = "\n".join(line for line in script.splitlines() if not line.startswith("--"))
    return [part.strip() for part in body.split(";\n") if part.strip()]


def upgrade() -> None:
    if not requested():
        return
    connection = op.get_bind()
    for statement in statements(SEED.read_text(encoding="utf-8")):
        connection.exec_driver_sql(statement)


def downgrade() -> None:
    if not requested():
        return
    op.execute(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY CASCADE")
