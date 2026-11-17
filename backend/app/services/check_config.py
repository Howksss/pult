import ipaddress
from typing import Any, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.models import CheckMethod
from app.services.checks import is_public, split_host


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HttpConfig(Strict):
    method: Literal["GET", "HEAD"] = "GET"
    expect_status: list[int] | None = Field(default=None, min_length=1, max_length=10)
    contains: str | None = Field(default=None, min_length=1, max_length=200)
    warn_latency_ms: int | None = Field(default=None, ge=1, le=60_000)

    @model_validator(mode="after")
    def codes_are_http(self) -> "HttpConfig":
        if self.expect_status and any(not 100 <= code <= 599 for code in self.expect_status):
            raise ValueError("коды ответа должны быть от 100 до 599")
        return self


class TlsConfig(Strict):
    warn_days: int = Field(default=14, ge=1, le=365)
    fail_days: int = Field(default=3, ge=0, le=365)

    @model_validator(mode="after")
    def fail_before_warn(self) -> "TlsConfig":
        if self.fail_days >= self.warn_days:
            raise ValueError("порог сбоя должен быть меньше порога предупреждения")
        return self


class NoConfig(Strict):
    pass


CONFIG_MODELS: dict[CheckMethod, type[Strict]] = {
    CheckMethod.http: HttpConfig,
    CheckMethod.tls: TlsConfig,
    CheckMethod.tcp: NoConfig,
    CheckMethod.heartbeat: NoConfig,
    CheckMethod.exit_code: NoConfig,
    CheckMethod.log_pattern: NoConfig,
}


def normalize_config(method: CheckMethod, config: dict[str, Any]) -> dict[str, Any]:
    try:
        return CONFIG_MODELS[method].model_validate(config).model_dump(exclude_none=True)
    except ValidationError as error:
        problems = "; ".join(str(item["msg"]) for item in error.errors())
        raise ValueError(f"настройки проверки: {problems}") from error


def target_host(method: CheckMethod, target: str) -> str | None:
    if method is CheckMethod.http:
        return httpx.URL(target).host
    if method in (CheckMethod.tls, CheckMethod.tcp):
        return split_host(target, 0)[0]
    return None


def normalize_target(method: CheckMethod, target: str) -> str:
    target = target.strip()
    if not target:
        raise ValueError("цель проверки не указана")
    if method is CheckMethod.http:
        try:
            url = httpx.URL(target)
        except httpx.InvalidURL as error:
            raise ValueError("адрес не разобрать") from error
        if url.scheme not in ("http", "https") or not url.host:
            raise ValueError("адрес должен начинаться с http:// или https://")
        return target
    if method in (CheckMethod.tls, CheckMethod.tcp):
        if "://" in target or "/" in target:
            raise ValueError("укажите хост без схемы и пути, например pos.example или pos.example:5432")
        host, port = split_host(target, 0)
        if method is CheckMethod.tcp and not 1 <= port <= 65535:
            raise ValueError("укажите порт, например db.example:5432")
        if not host:
            raise ValueError("укажите хост")
    return target


def internal_target(method: CheckMethod, target: str) -> bool:
    host = target_host(method, target)
    if host is None:
        return False
    if host.lower() in ("localhost", "localhost.localdomain") or host.lower().endswith(".localhost"):
        return True
    try:
        ipaddress.ip_address(host.split("%", 1)[0])
    except ValueError:
        return False
    return not is_public(host)
