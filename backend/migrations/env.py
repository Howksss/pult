from logging.config import fileConfig

from alembic import context
from alembic.operations import ops
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
config.set_main_option("sqlalchemy.url", get_settings().database_url.replace("%", "%%"))
target_metadata = Base.metadata
COMMENT_OPS = (ops.CreateTableCommentOp, ops.DropTableCommentOp)


def only_comment(operation: ops.MigrateOperation) -> bool:
    if isinstance(operation, COMMENT_OPS):
        return True
    return (
        isinstance(operation, ops.AlterColumnOp)
        and operation.modify_comment is not False
        and operation.modify_type is None
        and operation.modify_nullable is None
        and operation.modify_server_default is False
        and operation.modify_name is None
    )


def skip_comments(_context: object, _revision: object, directives: list[ops.MigrationScript]) -> None:
    for script in directives:
        for upgrade in script.upgrade_ops_list:
            kept: list[ops.MigrateOperation] = []
            for operation in upgrade.ops:
                if isinstance(operation, ops.ModifyTableOps):
                    operation.ops = [item for item in operation.ops if not only_comment(item)]
                    if operation.ops:
                        kept.append(operation)
                elif not only_comment(operation):
                    kept.append(operation)
            upgrade.ops = kept


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            process_revision_directives=skip_comments,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
