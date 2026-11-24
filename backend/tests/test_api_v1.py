from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.orm import Session, sessionmaker

from app.db import get_session
from app.main import app
from app.models import ApiKey, AppUser, CheckResult, CheckStatus, MemberRole, ProjectMember
from tests.conftest import PROBE_TOKEN
from tests.contract import contract_operations
from tests.test_api import call, probe_batch

PROJECTS = "/api/v1/projects"
PROJECT = "/api/v1/projects/{project_id}"
MEMBERS = "/api/v1/projects/{project_id}/members"
BLOCKS = "/api/v1/projects/{project_id}/blocks"
BLOCK = "/api/v1/blocks/{block_id}"
LINKS = "/api/v1/projects/{project_id}/links"
LINK = "/api/v1/links/{link_id}"
CHECK = "/api/v1/checks/{check_id}"
RESULTS = "/api/v1/checks/{check_id}/results"
SCOPES = "/api/v1/blocks/{block_id}/scopes"
KEYS = "/api/v1/api-keys"
KEY = "/api/v1/api-keys/{key_id}"
ME = "/api/v1/auth/me"
PROBE = "/api/v1/probe/results"


def demote(db: sessionmaker[Session], tester, project_id: int, role: MemberRole) -> None:
    with db() as session:
        session.execute(
            update(ProjectMember)
            .where(ProjectMember.project_id == project_id, ProjectMember.user_id == tester.user_id)
            .values(role=role)
        )
        session.commit()


def keyed(client: TestClient, key: str) -> TestClient:
    keyed_client = TestClient(app)
    keyed_client.headers["X-API-Key"] = key
    return keyed_client


def test_implementation_and_contract_have_the_same_operations():
    implemented = {(method.upper(), path) for path, item in app.openapi()["paths"].items() for method in item}
    assert implemented == contract_operations()


def test_api_key_lifecycle(client, pilot, db):
    created = call(client, "POST", KEYS, 201, json={"name": "Bruno", "expires_in_days": 30}).json()
    assert created["key"].startswith("pult_") and created["key"].startswith(created["prefix"])
    listed = call(client, "GET", KEYS, 200).json()
    assert [item["name"] for item in listed] == ["Bruno"] and "key" not in listed[0]

    integration = keyed(client, created["key"])
    me = call(integration, "GET", ME, 200).json()
    assert me["projects"][0]["id"] == pilot["project"]
    with db() as session:
        assert session.get(ApiKey, created["id"]).last_used_at is not None

    call(client, "DELETE", KEY, 204, key_id=created["id"])
    call(integration, "GET", ME, 401)


def test_wrong_and_expired_keys_are_401_not_a_fallback_to_cookie(client, pilot, db):
    call(keyed(client, "pult_wrong"), "GET", PROJECTS, 401)
    created = call(client, "POST", KEYS, 201, json={"name": "старый"}).json()
    with db() as session:
        now = datetime.now(UTC)
        session.execute(
            update(ApiKey).values(created_at=now - timedelta(days=100), expires_at=now - timedelta(minutes=1))
        )
        session.commit()
    body = call(keyed(client, created["key"]), "GET", PROJECTS, 401).json()
    assert body["detail"] == "API key is invalid or expired"


def test_someone_elses_key_cannot_be_revoked(client, pilot, db):
    created = call(client, "POST", KEYS, 201, json={"name": "чужой"}).json()
    with db() as session:
        stranger = AppUser(email="stranger@example.com", full_name="Чужой", password_hash="-")
        session.add(stranger)
        session.flush()
        session.execute(update(ApiKey).values(user_id=stranger.id))
        session.commit()
    call(client, "DELETE", KEY, 404, key_id=created["id"])


@pytest.mark.parametrize(
    "payload", [{"name": ""}, {"name": "x", "expires_in_days": 0}, {"name": "x", "extra": 1}]
)
def test_invalid_key_request_is_422(client, payload):
    call(client, "POST", KEYS, 422, json=payload)


def test_key_with_insufficient_role_is_403(client, pilot, db, tester):
    key = call(client, "POST", KEYS, 201, json={"name": "заказчик"}).json()["key"]
    demote(db, tester, pilot["project"], MemberRole.client)
    call(keyed(client, key), "PATCH", PROJECT, 403, json={"name": "новое"}, project_id=pilot["project"])


def test_project_read_update_delete(client, pilot):
    project = call(client, "GET", PROJECT, 200, project_id=pilot["project"]).json()
    assert (project["repo_full_name"], project["default_branch"], project["role"]) == (
        "example/pilot-system",
        "main",
        "owner",
    )
    updated = call(
        client,
        "PATCH",
        PROJECT,
        200,
        json={"name": " Пилот ", "description": "Пекарни", "default_branch": "master"},
        project_id=pilot["project"],
    ).json()
    assert (updated["name"], updated["description"], updated["default_branch"]) == (
        "Пилот",
        "Пекарни",
        "master",
    )
    call(client, "PATCH", PROJECT, 422, json={}, project_id=pilot["project"])
    call(client, "GET", PROJECT, 404, project_id=pilot["other"])
    call(client, "DELETE", PROJECT, 204, project_id=pilot["project"])
    call(client, "GET", PROJECT, 404, project_id=pilot["project"])
    call(client, "GET", BLOCK, 404, block_id=pilot["job"])


def test_second_project_for_the_same_repository_is_a_conflict(client):
    payload = {"name": "Пилот", "repo_full_name": "example/pilot-system"}
    call(client, "POST", PROJECTS, 201, json=payload)
    body = call(client, "POST", PROJECTS, 409, json=payload).json()
    assert "example/pilot-system" in body["detail"]


def test_project_list_filters_and_pages(client):
    for number in range(3):
        call(
            client, "POST", PROJECTS, 201, json={"name": f"p{number}", "repo_full_name": f"example/p{number}"}
        )
    page = call(client, "GET", PROJECTS, 200, query={"limit": "2", "offset": "1", "role": "owner"})
    assert page.headers["X-Total-Count"] == "3"
    assert [item["name"] for item in page.json()] == ["p1", "p2"]
    assert call(client, "GET", PROJECTS, 200, query={"role": "client"}).json() == []
    call(client, "GET", PROJECTS, 422, query={"limit": "0"})
    call(client, "GET", PROJECTS, 422, query={"role": "admin"})


def test_member_list_filters_by_role(client, pilot):
    owners = call(client, "GET", MEMBERS, 200, query={"role": "owner"}, project_id=pilot["project"])
    assert owners.headers["X-Total-Count"] == "1"
    assert (
        call(client, "GET", MEMBERS, 200, query={"role": "client"}, project_id=pilot["project"]).json() == []
    )


def test_block_list_filters_and_single_block(client, pilot):
    every = call(client, "GET", BLOCKS, 200, project_id=pilot["project"])
    assert every.headers["X-Total-Count"] == "2"
    jobs = call(
        client, "GET", BLOCKS, 200, query={"kind": "scheduled_job"}, project_id=pilot["project"]
    ).json()
    assert [block["name"] for block in jobs] == ["Расчёт плана"]
    healthy = call(client, "GET", BLOCKS, 200, query={"status": "ok"}, project_id=pilot["project"]).json()
    assert [block["id"] for block in healthy] == [pilot["pos"]]
    named = call(client, "GET", BLOCKS, 200, query={"q": "POS"}, project_id=pilot["project"]).json()
    assert [block["id"] for block in named] == [pilot["pos"]]
    second = call(
        client, "GET", BLOCKS, 200, query={"limit": "1", "offset": "1"}, project_id=pilot["project"]
    ).json()
    assert [block["id"] for block in second] == [pilot["pos"]]
    assert call(client, "GET", BLOCK, 200, block_id=pilot["pos"]).json()["status"] == "ok"
    call(client, "GET", BLOCK, 404, block_id=pilot["foreign"])
    call(client, "GET", BLOCKS, 422, query={"kind": "robot"}, project_id=pilot["project"])


def test_link_list_update_delete(client, pilot, db, tester):
    created = call(
        client,
        "POST",
        LINKS,
        201,
        json={"source_block_id": pilot["job"], "target_block_id": pilot["pos"], "label": "продажи"},
        project_id=pilot["project"],
    ).json()
    listed = call(client, "GET", LINKS, 200, query={"block_id": pilot["pos"]}, project_id=pilot["project"])
    assert listed.headers["X-Total-Count"] == "1"
    assert (
        call(client, "GET", LINKS, 200, query={"block_id": "999"}, project_id=pilot["project"]).json() == []
    )
    renamed = call(client, "PATCH", LINK, 200, json={"label": " остатки "}, link_id=created["id"]).json()
    assert renamed["label"] == "остатки"
    assert (
        call(client, "PATCH", LINK, 200, json={"label": None}, link_id=created["id"]).json()["label"] is None
    )
    call(client, "PATCH", LINK, 422, json={}, link_id=created["id"])
    demote(db, tester, pilot["project"], MemberRole.developer)
    call(client, "DELETE", LINK, 403, link_id=created["id"])
    demote(db, tester, pilot["project"], MemberRole.owner)
    call(client, "DELETE", LINK, 204, link_id=created["id"])
    call(client, "DELETE", LINK, 404, link_id=created["id"])


def add_results(db: sessionmaker[Session], check_id: int, statuses: list[CheckStatus]) -> datetime:
    start = datetime.now(UTC) - timedelta(hours=1)
    with db() as session:
        session.add_all(
            CheckResult(health_check_id=check_id, status=status, checked_at=start + timedelta(minutes=minute))
            for minute, status in enumerate(statuses)
        )
        session.commit()
    return start


def test_check_and_its_result_history(client, pilot, db):
    start = add_results(
        db, pilot["pos_check"], [CheckStatus.ok, CheckStatus.fail, CheckStatus.ok, CheckStatus.fail]
    )
    assert call(client, "GET", CHECK, 200, check_id=pilot["pos_check"]).json()["id"] == pilot["pos_check"]
    history = call(client, "GET", RESULTS, 200, check_id=pilot["pos_check"])
    assert history.headers["X-Total-Count"] == "5"
    failed = call(
        client, "GET", RESULTS, 200, query={"status": "fail", "limit": "1"}, check_id=pilot["pos_check"]
    )
    assert failed.headers["X-Total-Count"] == "2"
    latest = datetime.fromisoformat(failed.json()[0]["checked_at"])
    assert latest.replace(tzinfo=latest.tzinfo or UTC) == start + timedelta(minutes=3)
    window = {
        "since": (start + timedelta(minutes=1)).isoformat(),
        "until": (start + timedelta(minutes=3)).isoformat(),
    }
    rows = call(client, "GET", RESULTS, 200, query=window, check_id=pilot["pos_check"]).json()
    assert [row["status"] for row in rows] == ["ok", "fail"]
    backwards = {"since": start.isoformat(), "until": start.isoformat()}
    call(client, "GET", RESULTS, 422, query=backwards, check_id=pilot["pos_check"])
    call(client, "GET", CHECK, 404, check_id=pilot["foreign_check"])
    call(client, "GET", RESULTS, 404, check_id=pilot["foreign_check"])


def test_scopes_are_replaced_as_a_whole_and_idempotently(client, pilot, db, tester):
    call(client, "POST", SCOPES, 201, json={"path_glob": "old/**", "access": "read"}, block_id=pilot["job"])
    payload = [{"path_glob": "pipeline/", "access": "write"}, {"path_glob": "docs/*.md"}]
    first = call(client, "PUT", SCOPES, 200, json=payload, block_id=pilot["job"]).json()
    second = call(client, "PUT", SCOPES, 200, json=payload, block_id=pilot["job"]).json()
    assert [(item["path_glob"], item["access"]) for item in second] == [
        ("docs/*.md", "read"),
        ("pipeline/**", "write"),
    ]
    assert [item["path_glob"] for item in first] == [item["path_glob"] for item in second]
    writable = call(client, "GET", SCOPES, 200, query={"access": "write"}, block_id=pilot["job"])
    assert writable.headers["X-Total-Count"] == "1"
    body = call(
        client, "PUT", SCOPES, 422, json=[{"path_glob": "a/"}, {"path_glob": "a/**"}], block_id=pilot["job"]
    ).json()
    assert body["errors"] == [{"path_glob": "a/**", "message": "repeated"}]
    assert call(client, "PUT", SCOPES, 200, json=[], block_id=pilot["job"]).json() == []
    demote(db, tester, pilot["project"], MemberRole.developer)
    call(client, "PUT", SCOPES, 403, json=payload, block_id=pilot["job"])


def test_malformed_json_is_400_and_wrong_shape_is_422(client, pilot):
    response = client.post(
        BLOCKS.format(project_id=pilot["project"]),
        content=b'{"kind": "bot", "name": ',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["type"].endswith("/bad-request")
    call(client, "POST", BLOCKS, 422, json={"kind": "bot"}, project_id=pilot["project"])


def test_unexpected_error_is_problem_500_without_details(tester):
    def broken():
        raise RuntimeError("database password is hunter2")
        yield

    app.dependency_overrides[get_session] = broken
    safe = TestClient(app, raise_server_exceptions=False)
    safe.cookies.set("pult_session", tester.token)
    body = call(safe, "GET", PROJECTS, 500).json()
    assert body["type"].endswith("/internal") and "hunter2" not in str(body)


def test_repeated_probe_batch_is_not_recorded_twice(client, pilot):
    batch = probe_batch(pilot["pos_check"], "fail", seconds_ago=5)
    headers = {"X-Probe-Token": PROBE_TOKEN}
    first = call(client, "POST", PROBE, 202, json=batch, headers=headers).json()
    again = call(client, "POST", PROBE, 202, json=batch, headers=headers).json()
    assert (first["accepted"], first["duplicates"]) == (1, 0)
    assert (again["accepted"], again["duplicates"], again["status_changes"]) == (0, 1, [])
