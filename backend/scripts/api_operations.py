import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "docs" / "api" / "openapi.yaml"
TARGET = ROOT / "docs" / "api" / "operations.md"
METHODS = ("get", "post", "put", "patch", "delete")
TAGS = {
    "projects": "Проекты и участники",
    "graph": "Граф, блоки и связи",
    "checks": "Проверки и история результатов",
    "scopes": "Область агента",
    "probe": "Probe",
    "auth": "Вход, сессии и API-ключи",
    "service": "Служебные",
}
AUTH = {"userSession": "сессия", "apiKey": "ключ", "probeToken": "токен probe"}


def parameters(operation: dict[str, Any], spec: dict[str, Any]) -> str:
    names = []
    for item in operation.get("parameters", []):
        if "$ref" in item:
            item = spec["components"]["parameters"][item["$ref"].split("/")[-1]]
        if item["in"] == "query":
            names.append(item["name"])
    return ", ".join(f"`{name}`" for name in names)


def render(spec: dict[str, Any]) -> str:
    rows: dict[str, list[str]] = {}
    for path, item in spec["paths"].items():
        for method in METHODS:
            if method not in item:
                continue
            operation = item[method]
            security = operation.get("security", [])
            auth = " или ".join(AUTH[name] for entry in security for name in entry) or "нет"
            codes = ", ".join(sorted(operation["responses"]))
            row = (
                f"| `{method.upper()} {path.removeprefix('/api/v1')}` | {operation['summary']} | "
                f"{parameters(operation, spec)} | {auth} | {codes} |"
            )
            rows.setdefault(TAGS[operation["tags"][0]], []).append(row)
    lines = [
        "# Ресурсы и операции API v1",
        "",
        "Таблица собрана из [openapi.yaml](openapi.yaml) скриптом `backend/scripts/api_operations.py`, тест "
        "`test_operations_table_matches_contract` следит, чтобы она не отставала. Пути даны от `/api/v1`. "
        "Тела ответов и примеры — в [документации Redoc](redoc.html).",
        "",
        "Коды: 400 — тело не JSON; 401 — нет сессии, ключа или токена; 403 — роли не хватает; "
        "404 — объекта нет или он в чужом проекте; 409 — нарушена уникальность; "
        "422 — запрос не прошёл проверку по схеме; "
        "500 — непредвиденная ошибка. Все ошибки — `application/problem+json` (RFC 9457).",
        "",
    ]
    for name in TAGS.values():
        if name not in rows:
            continue
        lines += [f"## {name}", "", "| Операция | Что делает | Фильтры и пагинация | Доступ | Коды ответов |"]
        lines += ["|---|---|---|---|---|", *rows[name], ""]
    return "\n".join(lines).rstrip() + "\n"


def build() -> str:
    with CONTRACT.open(encoding="utf-8") as file:
        return render(yaml.safe_load(file))


if __name__ == "__main__":
    TARGET.write_text(build(), encoding="utf-8", newline="\n")
    sys.stdout.write(f"written {TARGET}\n")
