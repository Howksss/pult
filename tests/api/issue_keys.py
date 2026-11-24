import json
import os
import sys
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.request import HTTPCookieProcessor, Request, build_opener

BASE = os.environ.get("PULT_URL", "http://localhost:8000")
PASSWORD = os.environ.get("PULT_DEMO_PASSWORD", "pult-demo-2026")
USERS = {"PULT_OWNER_KEY": "owner@example.com", "PULT_DEVELOPER_KEY": "dev@example.com"}


def post(opener, path: str, payload: dict) -> dict:
    request = Request(
        BASE + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with opener.open(request, timeout=10) as response:
        return json.loads(response.read())


def issue(email: str) -> str:
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    post(opener, "/api/v1/auth/login", {"email": email, "password": PASSWORD})
    return post(opener, "/api/v1/api-keys", {"name": "Bruno", "expires_in_days": 1})["key"]


def main() -> None:
    lines = [f"{name}={issue(email)}" for name, email in USERS.items()]
    lines.append(f"PULT_PROBE_TOKEN={os.environ.get('PULT_PROBE_TOKEN', 'demo-probe-token')}")
    target = Path(__file__).with_name(".env")
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    sys.stdout.write(f"keys for {', '.join(USERS.values())} written to {target}\n")


if __name__ == "__main__":
    main()
