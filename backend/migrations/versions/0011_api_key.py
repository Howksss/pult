from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COMMENTS = [
    ("TABLE api_key", "API-ключ пользователя для интеграций: заголовок X-API-Key вместо cookie сессии"),
    ("COLUMN api_key.id", "Идентификатор ключа"),
    ("COLUMN api_key.user_id", "Владелец ключа: запросы с ключом выполняются с его правами"),
    ("COLUMN api_key.name", "Название ключа, чтобы отличать интеграции: n8n, Bruno, скрипт выгрузки"),
    (
        "COLUMN api_key.prefix",
        "Первые символы ключа для списка ключей. По ним ключ узнают, но не восстанавливают",
    ),
    ("COLUMN api_key.token_hash", "SHA-256 ключа. Сам ключ показывается один раз при выпуске и не хранится"),
    ("COLUMN api_key.created_at", "Момент выпуска ключа"),
    ("COLUMN api_key.expires_at", "Момент, после которого ключ не принимается"),
    ("COLUMN api_key.last_used_at", "Когда ключ последний раз предъявляли, с точностью до минуты"),
    ("CONSTRAINT api_key_pkey ON api_key", "Ключ однозначно определяется идентификатором"),
    (
        "CONSTRAINT api_key_user_id_fkey ON api_key",
        "Ключи удалённого пользователя отзываются вместе с ним. CASCADE",
    ),
    ("CONSTRAINT api_key_token_hash_key ON api_key", "Предъявленный ключ указывает ровно на одну запись"),
    (
        "CONSTRAINT ck_api_key_expires_after_created ON api_key",
        "Бессрочных ключей нет: срок действия позже момента выпуска",
    ),
    ("CONSTRAINT ck_api_key_name_not_blank ON api_key", "У ключа есть название"),
    ("INDEX ix_api_key_user_id", "Список ключей пользователя GET /api-keys"),
    (
        "INDEX uq_check_result_check_time",
        "Последний результат и история проверки, плюс защита от дублей: повтор пачки probe "
        "с тем же моментом проверки не создаёт вторую строку",
    ),
]


def quote(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def upgrade() -> None:
    op.create_table(
        "api_key",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("prefix", sa.String(length=16), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("expires_at > created_at", name="ck_api_key_expires_after_created"),
        sa.CheckConstraint("trim(name) <> ''", name="ck_api_key_name_not_blank"),
    )
    op.create_index("ix_api_key_user_id", "api_key", ["user_id"])
    op.execute(
        """
        DELETE FROM check_result AS duplicate
        USING check_result AS kept
        WHERE duplicate.health_check_id = kept.health_check_id
            AND duplicate.checked_at = kept.checked_at
            AND duplicate.id > kept.id
        """
    )
    op.create_index(
        "uq_check_result_check_time",
        "check_result",
        ["health_check_id", sa.text("checked_at DESC")],
        unique=True,
    )
    op.drop_index("ix_check_result_check_time", table_name="check_result")
    for target, text in COMMENTS:
        op.execute(f"COMMENT ON {target} IS {quote(text)}")


def downgrade() -> None:
    op.create_index(
        "ix_check_result_check_time", "check_result", ["health_check_id", sa.text("checked_at DESC")]
    )
    op.execute(
        "COMMENT ON INDEX ix_check_result_check_time IS "
        "'Последний результат и история проверки: представление v_block_status, панель проверок, "
        "расчёт начала сбоя'"
    )
    op.drop_index("uq_check_result_check_time", table_name="check_result")
    op.drop_index("ix_api_key_user_id", table_name="api_key")
    op.drop_table("api_key")
