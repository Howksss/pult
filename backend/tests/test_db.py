from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

from app import db
from app.models import AppUser, Base


@pytest.fixture
def engine(monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    memory = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(memory)
    monkeypatch.setattr(db, "get_engine", lambda: memory)
    yield memory
    memory.dispose()


def users(engine: Engine) -> int:
    with engine.connect() as connection:
        return connection.scalar(select(func.count()).select_from(AppUser)) or 0


def test_error_inside_request_rolls_back_unfinished_changes(engine):
    requests = db.get_session()
    session = next(requests)
    session.add(AppUser(email="half@example.com", full_name="Half", password_hash="-"))
    session.flush()
    with pytest.raises(RuntimeError):
        requests.throw(RuntimeError("notification failed"))
    assert users(engine) == 0


def test_committed_changes_survive_the_end_of_request(engine):
    requests = db.get_session()
    session = next(requests)
    session.add(AppUser(email="kept@example.com", full_name="Kept", password_hash="-"))
    session.commit()
    requests.close()
    assert users(engine) == 1
