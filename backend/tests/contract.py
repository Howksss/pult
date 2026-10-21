from functools import cache
from pathlib import Path
from typing import Any

import yaml
from httpx import Response
from jsonschema import Draft202012Validator

CONTRACT_PATH = Path(__file__).resolve().parents[2] / "docs" / "api" / "openapi.yaml"


@cache
def contract() -> dict[str, Any]:
    with CONTRACT_PATH.open(encoding="utf-8") as file:
        return yaml.safe_load(file)


def resolve(node: dict[str, Any]) -> dict[str, Any]:
    ref = node.get("$ref")
    if ref is None:
        return node
    target: Any = contract()
    for part in ref.removeprefix("#/").split("/"):
        target = target[part]
    return target


def contract_operations() -> set[tuple[str, str]]:
    return {
        (method.upper(), path)
        for path, item in contract()["paths"].items()
        for method in item
        if method in {"get", "post", "put", "patch", "delete"}
    }


def assert_matches_contract(method: str, path_template: str, response: Response) -> None:
    operation = contract()["paths"][path_template][method.lower()]
    status = str(response.status_code)
    assert (
        status in operation["responses"]
    ), f"{method} {path_template}: status {status} is not in the contract"
    declared = resolve(operation["responses"][status])
    content = declared.get("content")
    if not content:
        assert not response.content, f"{method} {path_template}: contract declares no body for {status}"
        return
    media_type = response.headers["content-type"].split(";")[0]
    assert media_type in content, f"{method} {path_template}: unexpected media type {media_type}"
    schema = {**content[media_type]["schema"], "components": contract()["components"]}
    errors = sorted(Draft202012Validator(schema).iter_errors(response.json()), key=str)
    assert not errors, f"{method} {path_template}: " + "; ".join(error.message for error in errors)
