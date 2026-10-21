import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Base, Block, BlockKind, BlockLink, CheckResult, CheckStatus, HealthCheck, Project


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    event.listen(engine, "connect", lambda conn, _: conn.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def make_project(session):
    project = Project(name="pilot", repo_full_name="example/pilot-system")
    session.add(project)
    session.flush()
    return project


def test_block_graph(session):
    project = make_project(session)
    cron = Block(project=project, kind=BlockKind.scheduled_job, name="Расчёт плана")
    bot = Block(project=project, kind=BlockKind.bot, name="Telegram-бот")
    session.add_all([cron, bot])
    session.flush()
    session.add(BlockLink(source_block_id=cron.id, target_block_id=bot.id, label="Excel-планы"))
    session.flush()
    assert [b.name for b in project.blocks] == ["Расчёт плана", "Telegram-бот"]


def test_block_name_unique_in_project(session):
    project = make_project(session)
    session.add_all([
        Block(project=project, kind=BlockKind.bot, name="Бот"),
        Block(project=project, kind=BlockKind.bot, name="Бот"),
    ])
    with pytest.raises(IntegrityError):
        session.flush()


def test_link_to_itself_rejected(session):
    project = make_project(session)
    block = Block(project=project, kind=BlockKind.server, name="VPS")
    session.add(block)
    session.flush()
    session.add(BlockLink(source_block_id=block.id, target_block_id=block.id))
    with pytest.raises(IntegrityError):
        session.flush()


def test_check_result(session):
    project = make_project(session)
    block = Block(project=project, kind=BlockKind.integration, name="POS-система")
    session.add(block)
    session.flush()
    check = HealthCheck(block_id=block.id, method="http", target="https://pos.example/api/ping")
    session.add(check)
    session.flush()
    session.add(CheckResult(health_check_id=check.id, status=CheckStatus.fail, message="timeout"))
    session.flush()
    assert session.query(CheckResult).one().status is CheckStatus.fail
