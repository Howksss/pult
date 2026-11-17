import os
import secrets
import sys
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

STDERR_TAIL = """Traceback (most recent call last):
  File "/opt/pilot/main_orders.py", line 41, in <module>
    run(date.today())
  File "/opt/pilot/orders/build.py", line 88, in build_order
    store = stores[row["store_id"]]
KeyError: 'store_id'"""


def jitter(low: int, high: int) -> int:
    return low + secrets.randbelow(high - low + 1)


def scenario(now: datetime) -> dict[str, dict[str, Any]]:
    expires = now + timedelta(days=9)
    return {
        "Сервер на связи": {"status": "ok", "details": {"load_avg": jitter(20, 90) / 100}},
        "SSH отвечает": {"status": "ok", "latency_ms": jitter(18, 40)},
        "Расчёт отработал": {
            "status": "ok",
            "details": {
                "exit_code": 0,
                "command": "python main.py",
                "duration_ms": jitter(40000, 52000),
            },
        },
        "Автозаказ отработал": {
            "status": "fail",
            "message": "Код выхода 1: KeyError: 'store_id'",
            "error_kind": "exit_code",
            "details": {
                "exit_code": 1,
                "command": "python main_orders.py",
                "duration_ms": 3120,
                "stderr_tail": STDERR_TAIL,
            },
        },
        "POS отвечает": {"status": "ok", "latency_ms": jitter(120, 260)},
        "Остатки отдаются": {"status": "ok", "latency_ms": jitter(200, 420)},
        "Сертификат POS": {
            "status": "warn",
            "message": f"Сертификат истекает через 9 дн, {expires:%d.%m.%Y}",
            "error_kind": "cert_expiring",
            "details": {
                "host": "pos.example",
                "port": 443,
                "not_after": expires.isoformat(),
                "days_left": 9,
                "issuer": "Let's Encrypt",
            },
        },
        "Прогноз отдаётся": {
            "status": "warn",
            "latency_ms": 2400,
            "message": "Ответ за 2,4 с, порог 1,5 с",
            "error_kind": "slow",
            "details": {"url": "https://weather.example/forecast", "status_code": 200, "latency_ms": 2400},
        },
        "Конфигурация читается": {"status": "ok", "details": {"pattern": "ConfigError", "lines": []}},
        "Бот отвечает": {"status": "ok", "latency_ms": jitter(80, 160)},
    }


def check_ids(client: httpx.Client, project_id: int) -> dict[str, int]:
    graph = client.get(f"/api/v1/projects/{project_id}/graph").raise_for_status().json()
    ids = {}
    for block in graph["blocks"]:
        for check in client.get(f"/api/v1/blocks/{block['id']}/checks").raise_for_status().json()["checks"]:
            ids[check["title"]] = check["id"]
    return ids


def push(client: httpx.Client, token: str, ids: dict[str, int]) -> int:
    now = datetime.now(UTC)
    results = [
        {"health_check_id": ids[title], "checked_at": now.isoformat(), **result}
        for title, result in scenario(now).items()
        if title in ids
    ]
    response = client.post(
        "/api/v1/probe/results", json={"results": results}, headers={"X-Probe-Token": token}
    )
    response.raise_for_status()
    return len(results)


def main() -> None:
    base_url = os.environ.get("PULT_URL", "http://localhost:8000")
    token = os.environ.get("PROBE_TOKEN", "demo-probe-token")
    project_id = int(os.environ.get("PROJECT_ID", "1"))
    once = "--once" in sys.argv
    with httpx.Client(base_url=base_url, timeout=10) as client:
        ids = check_ids(client, project_id)
        while True:
            print(f"{datetime.now(UTC):%H:%M:%S} sent {push(client, token, ids)} results", flush=True)
            if once:
                return
            time.sleep(60)


if __name__ == "__main__":
    main()
