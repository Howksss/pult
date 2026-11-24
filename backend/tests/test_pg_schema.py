import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    AgentTask,
    AppUser,
    AuditEvent,
    Base,
    Block,
    BlockKind,
    BlockLink,
    CheckStatus,
    MessageRole,
    Project,
    TaskMessage,
)
from app.services.results import NewResult, insert_new

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
    "user_session",
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
    user = AppUser(email="jsonb-test@example.com", full_name="Owner", password_hash="argon2-hash-placeholder")
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


def test_user_with_audit_events_cannot_be_deleted(session):
    user = AppUser(email="audit-test@example.com", full_name="Dev", password_hash="argon2-hash-placeholder")
    session.add(user)
    session.flush()
    session.add(AuditEvent(user_id=user.id, action="change_request.approved", payload={"pr": 1}))
    session.flush()
    with pytest.raises(IntegrityError, match="audit_event"):
        session.connection().exec_driver_sql("delete from app_user where id = %s", (user.id,))


def test_schema_after_migrations_matches_models(session):
    context = MigrationContext.configure(session.connection(), opts={"compare_type": True})
    drift = [str(item) for item in compare_metadata(context, Base.metadata) if "comment" not in str(item)]
    assert drift == []


DEPLOY = "insert into deployment (change_request_id, commit_sha, status) values (900, "


def run(session: Session, statement: str) -> None:
    session.connection().exec_driver_sql(statement)


def fixture_rows(session: Session) -> None:
    run(
        session,
        "insert into app_user (id, email, full_name, password_hash) "
        "values (900, 'rules@example.com', 'R', '-')",
    )
    run(
        session,
        "insert into project (id, name, repo_full_name, default_branch) values (900, 'p', 'o/r', 'main')",
    )
    run(
        session,
        "insert into block (id, project_id, kind, name, pos_x, pos_y) values (900, 900, 'bot', 'a', 0, 0)",
    )
    run(
        session,
        "insert into block (id, project_id, kind, name, pos_x, pos_y) values (901, 900, 'bot', 'b', 0, 0)",
    )
    run(
        session,
        "insert into health_check (id, block_id, method, target, interval_sec, timeout_sec) "
        "values (900, 900, 'http', 'https://a.example', 60, 10)",
    )
    run(
        session,
        "insert into agent_task (id, block_id, author_id, title, status) values (900, 900, 900, 't', 'new')",
    )
    run(
        session,
        "insert into change_request (id, task_id, branch_name, pr_number, status) "
        "values (900, 900, 'agent/900', 1, 'open')",
    )


@pytest.mark.parametrize(
    ("statement", "constraint"),
    [
        (
            "update health_check set interval_sec = 10, timeout_sec = 30 where id = 900",
            "ck_health_check_timeout_within_interval",
        ),
        ("update health_check set interval_sec = 5 where id = 900", "ck_health_check_interval_range"),
        (
            "insert into block_scope (block_id, path_glob, access) values (900, '../secrets/**', 'read')",
            "ck_block_scope_relative_path",
        ),
        (
            "insert into block_scope (block_id, path_glob, access) values (900, '/etc/passwd', 'read')",
            "ck_block_scope_relative_path",
        ),
        ("update app_user set email = 'Rules@Example.com' where id = 900", "ck_app_user_email_format"),
        (
            "update project set repo_full_name = 'just-a-name' where id = 900",
            "ck_project_repo_full_name_format",
        ),
        ("update block set name = '   ' where id = 900", "ck_block_name_not_blank"),
        (
            "insert into check_result (health_check_id, status, latency_ms) values (900, 'ok', -1)",
            "ck_check_result_latency_not_negative",
        ),
        (
            DEPLOY + "repeat('a', 40), 'succeeded')",
            "ck_deployment_finished_when_done",
        ),
        (
            DEPLOY + "repeat('z', 40), 'running')",
            "ck_deployment_commit_sha_format",
        ),
        (
            "update change_request set reviewed_at = now() where id = 900",
            "ck_change_request_reviewed_by_reviewer",
        ),
        (
            "update agent_task set finished_at = created_at - interval '1 hour' where id = 900",
            "ck_agent_task_finished_after_created",
        ),
    ],
)
def test_domain_rules_are_enforced_by_database(session, statement, constraint):
    fixture_rows(session)
    with pytest.raises(IntegrityError, match=constraint):
        run(session, statement)


def test_blocks_are_linked_once_per_direction(session):
    fixture_rows(session)
    run(session, "insert into block_link (source_block_id, target_block_id) values (900, 901)")
    run(session, "insert into block_link (source_block_id, target_block_id) values (901, 900)")
    with pytest.raises(IntegrityError, match="uq_block_link_source_target"):
        run(session, "insert into block_link (source_block_id, target_block_id) values (900, 901)")


def test_only_one_running_deployment_per_change_request(session):
    fixture_rows(session)
    run(
        session,
        DEPLOY + "repeat('a', 40), 'running')",
    )
    with pytest.raises(IntegrityError, match="uq_deployment_one_running"):
        run(
            session,
            DEPLOY + "repeat('b', 40), 'running')",
        )


def test_task_author_cannot_be_deleted(session):
    fixture_rows(session)
    with pytest.raises(IntegrityError, match="agent_task_author_id_fkey"):
        run(session, "delete from app_user where id = 900")


def undocumented(session: Session, query: str) -> list[str]:
    return [row[0] for row in session.connection().exec_driver_sql(query)]


def test_every_table_column_type_constraint_and_index_is_commented(session):
    assert (
        undocumented(
            session,
            "select c.relname || coalesce('.' || a.attname, '') from pg_class c "
            "join pg_namespace n on n.oid = c.relnamespace and n.nspname = 'public' "
            "left join pg_attribute a on a.attrelid = c.oid and a.attnum > 0 and not a.attisdropped "
            "where c.relkind in ('r', 'v') "
            "and coalesce(col_description(c.oid, a.attnum), obj_description(c.oid, 'pg_class')) is null",
        )
        == []
    )
    assert (
        undocumented(
            session,
            "select conrelid::regclass || '.' || conname from pg_constraint "
            "where connamespace = 'public'::regnamespace and obj_description(oid, 'pg_constraint') is null",
        )
        == []
    )
    assert (
        undocumented(
            session,
            "select i.relname from pg_index x join pg_class i on i.oid = x.indexrelid "
            "join pg_namespace n on n.oid = i.relnamespace and n.nspname = 'public' "
            "where not exists (select 1 from pg_constraint k where k.conindid = x.indexrelid) "
            "and obj_description(i.oid, 'pg_class') is null",
        )
        == []
    )
    assert (
        undocumented(
            session,
            "select typname from pg_type where typnamespace = 'public'::regnamespace and typtype = 'e' "
            "and obj_description(oid, 'pg_type') is null",
        )
        == []
    )


def test_repeated_probe_results_are_counted_on_postgres(session):
    fixture_rows(session)
    moment = datetime(2026, 11, 24, 8, 0, tzinfo=UTC)
    batch = [
        NewResult(health_check_id=900, status=CheckStatus.ok, checked_at=moment),
        NewResult(health_check_id=900, status=CheckStatus.fail, checked_at=moment + timedelta(minutes=1)),
    ]
    assert insert_new(session, batch) == 2
    assert insert_new(session, batch) == 0
    assert (
        insert_new(
            session,
            [
                *batch,
                NewResult(
                    health_check_id=900, status=CheckStatus.ok, checked_at=moment + timedelta(minutes=2)
                ),
            ],
        )
        == 1
    )
