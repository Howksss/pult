from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.probe import hash_token
from app.db import get_session
from app.main import app
from app.models import (
    AppUser,
    Base,
    Block,
    BlockKind,
    CheckMethod,
    CheckResult,
    CheckStatus,
    HealthCheck,
    MemberRole,
    Project,
    ProjectMember,
)
from app.services.auth import open_session


@pytest.fixture
def db() -> Iterator[sessionmaker[Session]]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    event.listen(engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override() -> Iterator[Session]:
        with factory() as session:
            yield session

    app.dependency_overrides[get_session] = override
    yield factory
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture
def client(db: sessionmaker[Session], tester: "Tester") -> TestClient:
    test_client = TestClient(app)
    test_client.cookies.set("pult_session", tester.token)
    return test_client


class Tester:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self.factory = factory
        with factory() as session:
            user = AppUser(email="tester@example.com", full_name="Тестер", password_hash="-")
            session.add(user)
            session.commit()
            self.user_id = user.id
            self.token = open_session(session, user)

    def join(self, project_id: int, role: MemberRole = MemberRole.owner) -> None:
        with self.factory() as session:
            session.add(ProjectMember(project_id=project_id, user_id=self.user_id, role=role))
            session.commit()


@pytest.fixture
def tester(db: sessionmaker[Session]) -> Tester:
    return Tester(db)


PROBE_TOKEN = "test-probe-token"


@pytest.fixture
def pilot(db: sessionmaker[Session], tester) -> dict[str, int]:
    with db() as session:
        project = Project(
            name="pilot", repo_full_name="example/pilot-system", probe_token_hash=hash_token(PROBE_TOKEN)
        )
        other = Project(
            name="other", repo_full_name="example/other", probe_token_hash=hash_token("other-token")
        )
        session.add_all([project, other])
        session.flush()
        job = Block(
            project_id=project.id, kind=BlockKind.scheduled_job, name="Расчёт плана", pos_x=10, pos_y=20
        )
        pos = Block(project_id=project.id, kind=BlockKind.integration, name="POS-система")
        foreign = Block(project_id=other.id, kind=BlockKind.bot, name="Чужой бот")
        session.add_all([job, pos, foreign])
        session.flush()
        pos_check = HealthCheck(block_id=pos.id, method=CheckMethod.http, target="https://pos.example")
        foreign_check = HealthCheck(
            block_id=foreign.id, method=CheckMethod.http, target="https://bot.example"
        )
        session.add_all([pos_check, foreign_check])
        session.flush()
        session.add(
            CheckResult(
                health_check_id=pos_check.id,
                status=CheckStatus.ok,
                checked_at=datetime.now(UTC) - timedelta(seconds=30),
            )
        )
        session.commit()
        tester.join(project.id)
        return {
            "project": project.id,
            "other": other.id,
            "job": job.id,
            "pos": pos.id,
            "foreign": foreign.id,
            "pos_check": pos_check.id,
            "foreign_check": foreign_check.id,
        }
