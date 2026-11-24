from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update

from app.core.config import Settings
from app.main import app
from app.models import Block, BlockKind, MemberRole, UserSession
from tests.contract import assert_matches_contract

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"
PROJECTS = "/api/v1/projects"
MEMBERS = "/api/v1/projects/{project_id}/members"
MEMBER = "/api/v1/projects/{project_id}/members/{user_id}"
GRAPH = "/api/v1/projects/{project_id}/graph"
BLOCKS = "/api/v1/projects/{project_id}/blocks"
CHECKS = "/api/v1/blocks/{block_id}/checks"
RUN = "/api/v1/checks/{check_id}/run"
PROBE = "/api/v1/probe/results"
PASSWORD = "correct horse battery"


@pytest.fixture(autouse=True)
def plain_cookies(monkeypatch):
    monkeypatch.setattr("app.api.auth.get_settings", lambda: Settings(cookie_secure=False))


@pytest.fixture
def anon(db) -> TestClient:
    return TestClient(app)


def call(client, method, template, expected, *, json=None, headers=None, **params):
    response = client.request(method, template.format(**params), json=json, headers=headers)
    assert response.status_code == expected, response.text
    assert_matches_contract(method, template, response)
    return response


def register(client, email="owner@example.com", name="Владелец"):
    return call(client, "POST", REGISTER, 201, json={"email": email, "password": PASSWORD, "full_name": name})


def test_register_signs_in_and_me_lists_projects(anon):
    body = register(anon, email="  Owner@Example.com ").json()
    assert (body["email"], body["projects"]) == ("owner@example.com", [])
    cookie = anon.cookies.get("pult_session")
    assert cookie and len(cookie) > 30
    assert call(anon, "GET", ME, 200).json()["full_name"] == "Владелец"


def test_session_cookie_is_http_only_and_lax(db):
    client = TestClient(app)
    response = client.post(REGISTER, json={"email": "a@example.com", "password": PASSWORD, "full_name": "А"})
    header = response.headers["set-cookie"].lower()
    assert "httponly" in header and "samesite=lax" in header and "max-age=2592000" in header


def test_duplicate_email_is_conflict(anon):
    register(anon)
    call(
        anon,
        "POST",
        REGISTER,
        409,
        json={"email": "OWNER@example.com", "password": PASSWORD, "full_name": "Х"},
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "owner@example.com", "password": "short", "full_name": "Х"},
        {"email": "not-an-email", "password": PASSWORD, "full_name": "Х"},
        {"email": "owner@example.com", "password": PASSWORD, "full_name": ""},
    ],
)
def test_bad_registration_is_rejected(anon, payload):
    call(anon, "POST", REGISTER, 422, json=payload)


def test_signup_can_be_closed(anon, monkeypatch):
    monkeypatch.setattr("app.api.auth.get_settings", lambda: Settings(allow_signup=False))
    call(anon, "POST", REGISTER, 403, json={"email": "x@example.com", "password": PASSWORD, "full_name": "Х"})


def test_login_and_logout(anon, db):
    register(anon)
    anon.cookies.clear()
    call(anon, "POST", LOGIN, 401, json={"email": "owner@example.com", "password": "wrong password"})
    call(anon, "POST", LOGIN, 401, json={"email": "nobody@example.com", "password": PASSWORD})
    call(anon, "POST", LOGIN, 200, json={"email": "OWNER@example.com", "password": PASSWORD})
    call(anon, "GET", ME, 200)
    token = anon.cookies.get("pult_session")
    call(anon, "POST", LOGOUT, 204)
    anon.cookies.set("pult_session", token)
    call(anon, "GET", ME, 401)


def test_expired_session_is_rejected(client, db):
    with db() as session:
        now = datetime.now(UTC)
        session.execute(
            update(UserSession).values(
                created_at=now - timedelta(days=31), expires_at=now - timedelta(seconds=1)
            )
        )
        session.commit()
    call(client, "GET", ME, 401)
    call(client, "GET", ME, 401)


def test_everything_except_health_and_probe_needs_a_session(anon):
    call(anon, "GET", ME, 401)
    call(anon, "GET", PROJECTS, 401)
    call(anon, "GET", GRAPH, 401, project_id=1)
    call(anon, "GET", CHECKS, 401, block_id=1)
    assert anon.get("/api/health").status_code == 200


def create_project(client):
    return call(
        client, "POST", PROJECTS, 201, json={"name": "Пилот", "repo_full_name": "example/pilot"}
    ).json()


def test_project_creator_is_owner_and_gets_probe_token_once(client):
    project = create_project(client)
    assert project["role"] == "owner"
    assert call(client, "GET", PROJECTS, 200).json() == [
        {"id": project["id"], "name": "Пилот", "role": "owner"}
    ]
    call(client, "GET", GRAPH, 200, project_id=project["id"])
    batch = {
        "results": [{"health_check_id": 999, "status": "ok", "checked_at": datetime.now(UTC).isoformat()}]
    }
    response = call(client, "POST", PROBE, 422, json=batch, headers={"X-Probe-Token": project["probe_token"]})
    assert response.json()["errors"][0]["health_check_id"] == 999


def test_bad_project_is_rejected(client):
    call(client, "POST", PROJECTS, 422, json={"name": "Пилот", "repo_full_name": "not a repo"})


def second_user(db, email="client@example.com"):
    client = TestClient(app)
    response = client.post(REGISTER, json={"email": email, "password": PASSWORD, "full_name": "Управляющий"})
    return client, response.json()["id"]


def test_roles_limit_what_members_can_do(client, db, tester):
    project = create_project(client)
    pid = project["id"]
    with db() as session:
        block = Block(project_id=pid, kind=BlockKind.integration, name="POS-система")
        session.add(block)
        session.commit()
        block_id = block.id
    check = call(
        client, "POST", CHECKS, 201, json={"method": "tcp", "target": "pos.example:443"}, block_id=block_id
    ).json()
    other, other_id = second_user(db)

    call(other, "GET", GRAPH, 404, project_id=pid)
    call(other, "GET", CHECKS, 404, block_id=block_id)

    call(client, "POST", MEMBERS, 201, json={"email": "client@example.com", "role": "client"}, project_id=pid)
    call(other, "GET", GRAPH, 200, project_id=pid)
    call(other, "GET", CHECKS, 200, block_id=block_id)
    call(other, "POST", BLOCKS, 403, json={"kind": "bot", "name": "Бот"}, project_id=pid)
    call(other, "POST", RUN, 403, check_id=check["id"])
    call(other, "GET", MEMBERS, 200, project_id=pid)
    call(other, "POST", MEMBERS, 403, json={"email": "tester@example.com", "role": "owner"}, project_id=pid)

    call(client, "PATCH", MEMBER, 200, json={"role": "developer"}, project_id=pid, user_id=other_id)
    call(other, "POST", CHECKS, 403, json={"method": "tcp", "target": "a.example:1"}, block_id=block_id)


def test_member_management_keeps_an_owner(client, db, tester):
    pid = create_project(client)["id"]
    _, other_id = second_user(db)
    call(client, "POST", MEMBERS, 404, json={"email": "ghost@example.com", "role": "client"}, project_id=pid)
    call(client, "POST", MEMBERS, 201, json={"email": "client@example.com", "role": "client"}, project_id=pid)
    call(client, "POST", MEMBERS, 409, json={"email": "client@example.com", "role": "owner"}, project_id=pid)
    members = call(client, "GET", MEMBERS, 200, project_id=pid).json()
    assert {(m["email"], m["role"]) for m in members} == {
        ("tester@example.com", "owner"),
        ("client@example.com", "client"),
    }
    call(client, "PATCH", MEMBER, 409, json={"role": "client"}, project_id=pid, user_id=tester.user_id)
    call(client, "DELETE", MEMBER, 409, project_id=pid, user_id=tester.user_id)
    call(client, "PATCH", MEMBER, 200, json={"role": "owner"}, project_id=pid, user_id=other_id)
    call(client, "DELETE", MEMBER, 204, project_id=pid, user_id=other_id)
    call(client, "DELETE", MEMBER, 404, project_id=pid, user_id=other_id)


def test_tester_role_fixture(client, db, tester):
    with db() as session:
        from app.models import Project

        project = Project(name="Чужой", repo_full_name="example/other")
        session.add(project)
        session.commit()
        pid = project.id
    tester.join(pid, MemberRole.client)
    call(client, "GET", GRAPH, 200, project_id=pid)
    call(client, "POST", BLOCKS, 403, json={"kind": "bot", "name": "Бот"}, project_id=pid)
