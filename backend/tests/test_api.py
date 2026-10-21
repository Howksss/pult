from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.api.probe import hash_token
from app.main import app
from app.models import Block, BlockKind, CheckMethod, CheckResult, CheckStatus, HealthCheck, Project
from tests.contract import assert_matches_contract, contract_operations

TOKEN = "test-probe-token"
GRAPH = "/api/v1/projects/{project_id}/graph"
BLOCKS = "/api/v1/projects/{project_id}/blocks"
BLOCK = "/api/v1/blocks/{block_id}"
LINKS = "/api/v1/projects/{project_id}/links"
PROBE = "/api/v1/probe/results"


@pytest.fixture
def pilot(db: sessionmaker[Session]) -> dict[str, int]:
    with db() as session:
        project = Project(
            name="pilot", repo_full_name="example/pilot-system", probe_token_hash=hash_token(TOKEN)
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
        return {
            "project": project.id,
            "other": other.id,
            "job": job.id,
            "pos": pos.id,
            "foreign": foreign.id,
            "pos_check": pos_check.id,
            "foreign_check": foreign_check.id,
        }


def call(client, method, template, expected, *, json=None, headers=None, **params):
    response = client.request(method, template.format(**params), json=json, headers=headers)
    assert response.status_code == expected, response.text
    assert_matches_contract(method, template, response)
    return response


def probe_batch(check_id: int, status: str, seconds_ago: int = 0) -> dict:
    checked_at = (datetime.now(UTC) - timedelta(seconds=seconds_ago)).isoformat()
    return {"results": [{"health_check_id": check_id, "status": status, "checked_at": checked_at}]}


def test_every_contract_operation_is_implemented():
    implemented = {(method.upper(), path) for path, item in app.openapi()["paths"].items() for method in item}
    assert contract_operations() <= implemented


def test_graph_shows_blocks_statuses_and_links(client, pilot):
    call(
        client,
        "POST",
        LINKS,
        201,
        project_id=pilot["project"],
        json={"source_block_id": pilot["job"], "target_block_id": pilot["pos"], "label": "продажи"},
    )
    graph = call(client, "GET", GRAPH, 200, project_id=pilot["project"]).json()
    statuses = {block["name"]: block["status"] for block in graph["blocks"]}
    assert statuses == {"Расчёт плана": "unknown", "POS-система": "ok"}
    assert graph["links"][0]["label"] == "продажи"
    assert "Чужой бот" not in statuses


def test_unknown_project_is_problem_404(client, pilot):
    body = call(client, "GET", GRAPH, 404, project_id=999).json()
    assert body["type"].endswith("/not-found")
    assert body["detail"] == "project 999 not found"


def test_create_update_delete_block(client, pilot):
    created = call(
        client,
        "POST",
        BLOCKS,
        201,
        project_id=pilot["project"],
        json={"kind": "bot", "name": "Telegram-бот", "x": 300, "y": 40},
    ).json()
    assert created["status"] == "unknown"
    moved = call(client, "PATCH", BLOCK, 200, block_id=created["id"], json={"x": 320, "y": 60}).json()
    assert (moved["x"], moved["y"], moved["name"]) == (320, 60, "Telegram-бот")
    call(client, "DELETE", BLOCK, 204, block_id=created["id"])
    call(client, "DELETE", BLOCK, 404, block_id=created["id"])


def test_duplicate_block_name_is_conflict(client, pilot):
    body = call(
        client, "POST", BLOCKS, 409, project_id=pilot["project"], json={"kind": "bot", "name": "POS-система"}
    ).json()
    assert body["type"].endswith("/conflict")


def test_rename_to_existing_name_is_conflict(client, pilot):
    call(client, "PATCH", BLOCK, 409, block_id=pilot["job"], json={"name": "POS-система"})


@pytest.mark.parametrize(
    "payload",
    [{"kind": "robot", "name": "X"}, {"kind": "bot", "name": ""}, {"kind": "bot", "name": "X", "extra": 1}],
)
def test_invalid_block_is_problem_422_with_errors(client, pilot, payload):
    body = call(client, "POST", BLOCKS, 422, project_id=pilot["project"], json=payload).json()
    assert body["errors"]


def test_empty_update_is_rejected(client, pilot):
    call(client, "PATCH", BLOCK, 422, block_id=pilot["job"], json={})


def test_link_validation(client, pilot):
    call(
        client,
        "POST",
        LINKS,
        422,
        project_id=pilot["project"],
        json={"source_block_id": pilot["job"], "target_block_id": pilot["job"]},
    )
    body = call(
        client,
        "POST",
        LINKS,
        422,
        project_id=pilot["project"],
        json={"source_block_id": pilot["job"], "target_block_id": pilot["foreign"]},
    ).json()
    assert body["errors"] == [
        {"block_id": pilot["foreign"], "message": "block does not belong to the project"}
    ]


@pytest.mark.parametrize("headers", [None, {"X-Probe-Token": "wrong"}])
def test_probe_requires_valid_token(client, pilot, headers):
    call(client, "POST", PROBE, 401, json=probe_batch(pilot["pos_check"], "fail"), headers=headers)


def test_probe_rejects_checks_of_other_project(client, pilot):
    body = call(
        client,
        "POST",
        PROBE,
        422,
        json=probe_batch(pilot["foreign_check"], "fail"),
        headers={"X-Probe-Token": TOKEN},
    ).json()
    assert body["errors"] == [{"health_check_id": pilot["foreign_check"], "message": "unknown check"}]


def test_probe_reports_status_changes(client, pilot):
    failed = call(
        client,
        "POST",
        PROBE,
        202,
        json=probe_batch(pilot["pos_check"], "fail"),
        headers={"X-Probe-Token": TOKEN},
    ).json()
    assert failed == {
        "accepted": 1,
        "status_changes": [{"block_id": pilot["pos"], "previous": "ok", "current": "fail"}],
    }
    still_failing = call(
        client,
        "POST",
        PROBE,
        202,
        json=probe_batch(pilot["pos_check"], "fail"),
        headers={"X-Probe-Token": TOKEN},
    ).json()
    assert still_failing["status_changes"] == []
    recovered = call(
        client,
        "POST",
        PROBE,
        202,
        json=probe_batch(pilot["pos_check"], "ok"),
        headers={"X-Probe-Token": TOKEN},
    ).json()
    assert recovered["status_changes"] == [{"block_id": pilot["pos"], "previous": "fail", "current": "ok"}]


def test_probe_accepts_naive_time_as_utc(client, pilot):
    naive = datetime.now(UTC).replace(tzinfo=None).isoformat()
    batch = {"results": [{"health_check_id": pilot["pos_check"], "status": "warn", "checked_at": naive}]}
    body = call(client, "POST", PROBE, 202, json=batch, headers={"X-Probe-Token": TOKEN}).json()
    assert body["status_changes"][0]["current"] == "warn"
