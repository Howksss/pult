from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_session
from app.main import app
from app.models import AppUser, Base, MemberRole, ProjectMember
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
