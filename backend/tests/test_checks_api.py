import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.checks import get_runner
from app.api.probe import get_notifier
from app.core.config import Settings
from app.main import app
from app.models import Block, BlockKind, CheckMethod, CheckResult, CheckStatus, HealthCheck, Project
from app.services.checks import Outcome
from tests.contract import assert_matches_contract

CHECKS = "/api/v1/blocks/{block_id}/checks"
CHECK = "/api/v1/checks/{check_id}"
RUN = "/api/v1/checks/{check_id}/run"


class FakeNotifier:
    enabled = True

    def __init__(self) -> None:
        self.sent: list[str] = []

    def send(self, text: str) -> bool:
        self.sent.append(text)
        return True


@pytest.fixture
def block_id(db: sessionmaker[Session], tester) -> int:
    with db() as session:
        block = Block(
            project=Project(name="pilot", repo_full_name="example/pilot"),
            kind=BlockKind.integration,
            name="POS-система",
        )
        session.add(block)
        session.commit()
        tester.join(block.project_id)
        return block.id


def call(client, method, template, expected, *, json=None, **params):
    response = client.request(method, template.format(**params), json=json)
    assert response.status_code == expected, response.text
    assert_matches_contract(method, template, response)
    return response


def create(client, block_id, expected=201, **payload):
    return call(client, "POST", CHECKS, expected, json=payload, block_id=block_id)


def test_create_http_check_normalizes_config(client, block_id):
    body = create(
        client,
        block_id,
        name="  POS отвечает ",
        method="http",
        target="https://pos.example/api/ping",
        config={"contains": "ok", "warn_latency_ms": 1500},
    ).json()
    assert body["title"] == "POS отвечает"
    assert body["config"] == {"method": "GET", "contains": "ok", "warn_latency_ms": 1500}
    assert (body["interval_sec"], body["timeout_sec"], body["enabled"]) == (60, 10, True)
    assert (body["status"], body["reason"], body["last"]) == ("unknown", "результатов ещё не было", None)


def test_blank_name_falls_back_to_method_and_target(client, block_id):
    body = create(client, block_id, name="   ", method="tcp", target="db.example:5432").json()
    assert (body["name"], body["title"]) == (None, "Порт db.example:5432")


@pytest.mark.parametrize(
    "payload",
    [
        {"method": "http", "target": "pos.example/api"},
        {"method": "http", "target": "ftp://pos.example"},
        {"method": "tcp", "target": "db.example"},
        {"method": "tcp", "target": "db.example:70000"},
        {"method": "tls", "target": "https://pos.example/path"},
        {"method": "http", "target": "https://pos.example", "config": {"warn_latency_ms": 0}},
        {"method": "http", "target": "https://pos.example", "config": {"expect_status": [700]}},
        {"method": "http", "target": "https://pos.example", "config": {"retries": 3}},
        {"method": "tls", "target": "pos.example", "config": {"warn_days": 5, "fail_days": 5}},
        {"method": "exit_code", "target": "main.py", "config": {"anything": 1}},
        {"method": "http", "target": "https://pos.example", "interval_sec": 5},
        {"method": "exit_code", "target": "   "},
    ],
)
def test_invalid_checks_are_rejected(client, block_id, payload):
    create(client, block_id, 422, **payload)


@pytest.mark.parametrize(
    ("method", "target"),
    [
        ("http", "http://127.0.0.1:8000/admin"),
        ("http", "http://localhost/"),
        ("http", "http://[::1]/"),
        ("tcp", "10.0.0.5:5432"),
        ("tls", "169.254.169.254"),
    ],
)
def test_internal_targets_are_refused(client, block_id, method, target):
    body = create(client, block_id, 422, method=method, target=target).json()
    assert body["detail"] == "адрес во внутренней сети: такие проверки запрещены"


def test_internal_targets_allowed_when_configured(client, block_id, monkeypatch):
    monkeypatch.setattr("app.api.checks.get_settings", lambda: Settings(allow_private_targets=True))
    create(client, block_id, method="http", target="http://localhost:8000/api/health")


def test_create_for_unknown_block_is_404(client, block_id):
    create(client, 999, 404, method="tcp", target="db.example:5432")


def test_update_check(client, block_id):
    check_id = create(client, block_id, method="http", target="https://pos.example").json()["id"]
    body = call(
        client,
        "PATCH",
        CHECK,
        200,
        json={
            "name": "POS отвечает",
            "interval_sec": 300,
            "enabled": False,
            "config": {"expect_status": [204]},
        },
        check_id=check_id,
    ).json()
    assert (body["title"], body["interval_sec"], body["enabled"]) == ("POS отвечает", 300, False)
    assert body["config"] == {"method": "GET", "expect_status": [204]}
    assert body["reason"] == "проверка выключена"
    body = call(
        client,
        "PATCH",
        CHECK,
        200,
        json={"name": "", "target": " https://pos.example/v2 "},
        check_id=check_id,
    )
    assert (body.json()["name"], body.json()["target"]) == (None, "https://pos.example/v2")


@pytest.mark.parametrize(
    "payload",
    [{"target": "pos.example"}, {"config": {"contains": ""}}, {"target": "http://192.168.0.1/"}, {}],
)
def test_invalid_updates_are_rejected(client, block_id, payload):
    check_id = create(client, block_id, method="http", target="https://pos.example").json()["id"]
    call(client, "PATCH", CHECK, 422, json=payload, check_id=check_id)


def test_update_and_delete_unknown_check_is_404(client, block_id):
    call(client, "PATCH", CHECK, 404, json={"enabled": False}, check_id=999)
    call(client, "DELETE", CHECK, 404, check_id=999)


def test_delete_check_removes_history(client, block_id, db):
    check_id = create(client, block_id, method="tcp", target="db.example:5432").json()["id"]
    with db() as session:
        session.add(CheckResult(health_check_id=check_id, status=CheckStatus.ok))
        session.commit()
    call(client, "DELETE", CHECK, 204, check_id=check_id)
    with db() as session:
        assert session.get(HealthCheck, check_id) is None
        assert session.scalar(select(func.count()).select_from(CheckResult)) == 0


def test_run_now_records_result_and_notifies(client, block_id):
    notifier = FakeNotifier()
    outcome = Outcome(CheckStatus.fail, 1200, "HTTP 502 Bad Gateway", "http_status", {"status_code": 502})
    app.dependency_overrides[get_runner] = lambda: lambda check: outcome
    app.dependency_overrides[get_notifier] = lambda: notifier
    check_id = create(
        client, block_id, name="POS отвечает", method="http", target="https://pos.example"
    ).json()["id"]
    body = call(client, "POST", RUN, 200, check_id=check_id).json()
    assert (body["status"], body["reason"], body["error_kind"]) == (
        "fail",
        "HTTP 502 Bad Gateway",
        "http_status",
    )
    assert body["last"]["details"] == {"status_code": 502}
    assert len(body["history"]) == 1
    assert notifier.sent == ["Сбой блока «POS-система» в проекте «pilot»: нет данных → сбой"]


def test_run_now_refuses_client_reported_checks(client, block_id):
    check_id = create(client, block_id, method="exit_code", target="python main.py").json()["id"]
    body = call(client, "POST", RUN, 409, check_id=check_id).json()
    assert body["type"].endswith("/client-reported")


def test_run_now_of_unknown_check_is_404(client, block_id):
    call(client, "POST", RUN, 404, check_id=999)


def test_default_runner_uses_guard(monkeypatch):
    seen = {}

    def fake_run_check(check, client, guard):
        seen["guard"] = guard
        return Outcome(CheckStatus.ok)

    monkeypatch.setattr("app.api.checks.run_check", fake_run_check)
    runner = get_runner()
    check = HealthCheck(method=CheckMethod.http, target="https://pos.example")
    assert runner(check).status is CheckStatus.ok
    assert seen["guard"].allow_private is False


def test_timeline_counts_results_per_hour_and_finds_failure_start(client, block_id, db):
    from datetime import UTC, datetime, timedelta

    from app.api.checks import hour_floor

    check_id = create(client, block_id, method="tcp", target="db.example:5432").json()["id"]
    now = datetime.now(UTC)
    current = hour_floor(now)
    rows = [
        (current - timedelta(hours=30), CheckStatus.fail),
        (current - timedelta(hours=5, minutes=-10), CheckStatus.ok),
        (current - timedelta(hours=5, minutes=-20), CheckStatus.warn),
        (current - timedelta(hours=2, minutes=-5), CheckStatus.ok),
        (current - timedelta(hours=2, minutes=-15), CheckStatus.fail),
        (current - timedelta(hours=1, minutes=-15), CheckStatus.fail),
        (max(now - timedelta(seconds=5), current), CheckStatus.fail),
    ]
    with db() as session:
        session.add_all(
            CheckResult(health_check_id=check_id, checked_at=moment, status=status) for moment, status in rows
        )
        session.commit()
    [check] = call(client, "GET", CHECKS, 200, block_id=block_id).json()["checks"]
    timeline = check["timeline"]
    assert len(timeline) == 24
    assert datetime.fromisoformat(timeline[-1]["start"]) == current
    counts = {
        23 - index: (b["ok"], b["warn"], b["fail"])
        for index, b in enumerate(timeline)
        if b["ok"] or b["warn"] or b["fail"]
    }
    assert counts == {5: (1, 1, 0), 2: (1, 0, 1), 1: (0, 0, 1), 0: (0, 0, 1)}
    assert datetime.fromisoformat(check["failing_since"]) == current - timedelta(hours=2, minutes=-15)


def test_failure_start_older_than_timeline_is_found(client, block_id, db):
    from datetime import UTC, datetime, timedelta

    now = datetime.now(UTC)
    since_ok = create(client, block_id, method="tcp", target="db.example:5432").json()["id"]
    never_ok = create(client, block_id, method="tcp", target="cache.example:6379").json()["id"]
    rows = [
        (since_ok, now - timedelta(hours=60), CheckStatus.fail),
        (since_ok, now - timedelta(hours=50), CheckStatus.ok),
        (since_ok, now - timedelta(hours=40), CheckStatus.warn),
        (since_ok, now - timedelta(hours=30), CheckStatus.fail),
        (since_ok, now - timedelta(minutes=1), CheckStatus.fail),
        (never_ok, now - timedelta(hours=70), CheckStatus.fail),
        (never_ok, now - timedelta(minutes=1), CheckStatus.fail),
    ]
    with db() as session:
        session.add_all(
            CheckResult(health_check_id=check_id, checked_at=moment, status=status)
            for check_id, moment, status in rows
        )
        session.commit()
    checks = {c["id"]: c for c in call(client, "GET", CHECKS, 200, block_id=block_id).json()["checks"]}
    started = {check_id: datetime.fromisoformat(checks[check_id]["failing_since"]) for check_id in checks}
    assert abs(started[since_ok] - (now - timedelta(hours=40))) < timedelta(seconds=1)
    assert abs(started[never_ok] - (now - timedelta(hours=70))) < timedelta(seconds=1)


def test_healthy_check_has_no_failure_start(client, block_id, db):
    from datetime import UTC, datetime

    check_id = create(client, block_id, method="tcp", target="db.example:5432").json()["id"]
    with db() as session:
        session.add(
            CheckResult(health_check_id=check_id, checked_at=datetime.now(UTC), status=CheckStatus.ok)
        )
        session.commit()
    [check] = call(client, "GET", CHECKS, 200, block_id=block_id).json()["checks"]
    assert check["failing_since"] is None
