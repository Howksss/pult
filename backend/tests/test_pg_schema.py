import os
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    AgentTask,
    AppUser,
    Block,
    BlockKind,
    BlockLink,
    MessageRole,
    Project,
    TaskMessage,
)

DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(DATABASE_URL is None, reason="TEST_DATABASE_URL не задан")

EXPECTED_TABLES = {
    "agent_task",
    "app_user",
    "audit_event",
    "block",
    "block_link",
    "block_scope",
    "change_request",
    "check_result",
    "deployment",
    "health_check",
    "project",
    "project_member",
    "task_message",
}


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine(str(DATABASE_URL))
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session
        transaction.rollback()
    engine.dispose()


def make_block(session: Session, name: str = "Расчёт плана") -> Block:
    project = Project(name="pilot", repo_full_name="example/pilot-system")
    block = Block(project=project, kind=BlockKind.scheduled_job, name=name)
    session.add(block)
    session.flush()
    return block


def test_migration_created_all_tables(session):
    tables = set(inspect(session.connection()).get_table_names())
    assert tables >= EXPECTED_TABLES


def test_enum_rejects_unknown_value(session):
    block = make_block(session)
    with pytest.raises(DataError, match="invalid input value for enum block_kind"):
        session.connection().exec_driver_sql("update block set kind = 'robot' where id = %s", (block.id,))


def test_self_link_rejected_by_check_constraint(session):
    block = make_block(session)
    session.add(BlockLink(source_block_id=block.id, target_block_id=block.id))
    with pytest.raises(IntegrityError, match="block_link_not_self"):
        session.flush()


def test_project_delete_cascades_to_blocks(session):
    block = make_block(session)
    project_id = block.project_id
    session.connection().exec_driver_sql("delete from project where id = %s", (project_id,))
    session.expire_all()
    assert session.scalars(select(Block).where(Block.project_id == project_id)).all() == []


def test_task_message_content_stored_as_jsonb(session):
    block = make_block(session)
    user = AppUser(email="owner@example.com", full_name="Owner", password_hash="argon2-hash-placeholder")
    session.add(user)
    session.flush()
    task = AgentTask(block_id=block.id, author_id=user.id, title="Прогон упал")
    session.add(task)
    session.flush()
    content = [{"type": "text", "text": "Проверь логи прогона за 08:00"}]
    session.add(TaskMessage(task_id=task.id, role=MessageRole.user, content=content))
    session.flush()
    column_type = session.connection().exec_driver_sql(
        "select data_type from information_schema.columns "
        "where table_name = 'task_message' and column_name = 'content'"
    )
    assert column_type.scalar_one() == "jsonb"
    stored = session.scalars(select(TaskMessage.content)).one()
    assert stored == content
