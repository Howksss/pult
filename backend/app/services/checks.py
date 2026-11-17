import socket
import ssl
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit

import httpx

from app.models import CheckMethod, CheckStatus, HealthCheck

BODY_EXCERPT = 500
clock = time.perf_counter
DEFAULT_TLS_WARN_DAYS = 14
DEFAULT_TLS_FAIL_DAYS = 3
DNS_MARKERS = (
    "getaddrinfo",
    "Name or service not known",
    "Temporary failure in name resolution",
    "nodename nor servname",
)


@dataclass(frozen=True)
class Outcome:
    status: CheckStatus
    latency_ms: int | None = None
    message: str | None = None
    error_kind: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


def seconds(ms: float) -> str:
    return f"{ms / 1000:.1f}".replace(".", ",") + " с"


def split_host(target: str, default_port: int) -> tuple[str, int]:
    host, sep, port = target.rpartition(":")
    if sep and port.isdigit() and host:
        return host.strip("[]"), int(port)
    return target, default_port


def network_failure(error: BaseException, host: str, timeout: int) -> tuple[str, str]:
    text = str(error)
    if isinstance(error, TimeoutError | httpx.TimeoutException):
        return "timeout", f"Не ответил за {timeout} с"
    if isinstance(error, socket.gaierror) or any(marker in text for marker in DNS_MARKERS):
        return "dns", f"Адрес {host} не найден"
    if isinstance(error, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in text:
        return "tls", "Сертификат не прошёл проверку"
    if isinstance(error, ConnectionRefusedError) or "refused" in text.lower():
        return "connection", "Соединение отклонено"
    return "connection", f"Не удалось подключиться: {text[:200]}"


def expected_status(config: dict[str, Any], code: int) -> bool:
    allowed = config.get("expect_status")
    if allowed:
        return code in allowed
    return 200 <= code < 400


def run_http(check: HealthCheck, client: httpx.Client) -> Outcome:
    config = check.config or {}
    method = config.get("method", "GET")
    details: dict[str, Any] = {"url": check.target, "method": method}
    started = clock()
    try:
        response = client.request(method, check.target, timeout=check.timeout_sec)
    except httpx.HTTPError as error:
        latency = round((clock() - started) * 1000)
        kind, message = network_failure(
            error, urlsplit(check.target).hostname or check.target, check.timeout_sec
        )
        details["error"] = str(error)[:300]
        return Outcome(CheckStatus.fail, latency, message, kind, details)
    latency = round((clock() - started) * 1000)
    details.update(
        status_code=response.status_code,
        reason=response.reason_phrase,
        latency_ms=latency,
        content_type=response.headers.get("content-type"),
    )
    if str(response.url) != check.target:
        details["final_url"] = str(response.url)
    if not expected_status(config, response.status_code):
        details["body_excerpt"] = response.text[:BODY_EXCERPT]
        message = f"HTTP {response.status_code} {response.reason_phrase}".strip()
        return Outcome(CheckStatus.fail, latency, message, "http_status", details)
    contains = config.get("contains")
    if contains and contains not in response.text:
        details["body_excerpt"] = response.text[:BODY_EXCERPT]
        return Outcome(CheckStatus.fail, latency, f"В ответе нет «{contains}»", "content", details)
    warn_latency = config.get("warn_latency_ms")
    if warn_latency and latency > warn_latency:
        message = f"Ответ за {seconds(latency)}, порог {seconds(warn_latency)}"
        return Outcome(CheckStatus.warn, latency, message, "slow", details)
    return Outcome(CheckStatus.ok, latency, None, None, details)


CertFetcher = Callable[[str, int, int], dict[str, Any]]


def fetch_certificate(host: str, port: int, timeout: int) -> dict[str, Any]:
    context = ssl.create_default_context()
    with (
        socket.create_connection((host, port), timeout=timeout) as raw,
        context.wrap_socket(raw, server_hostname=host) as wrapped,
    ):
        return wrapped.getpeercert() or {}


def cert_name(parts: Any) -> str | None:
    for group in parts or ():
        for key, value in group:
            if key in ("organizationName", "commonName"):
                return str(value)
    return None


def run_tls(
    check: HealthCheck, fetch: CertFetcher = fetch_certificate, now: datetime | None = None
) -> Outcome:
    config = check.config or {}
    host, port = split_host(check.target, 443)
    details: dict[str, Any] = {"host": host, "port": port}
    started = clock()
    try:
        cert = fetch(host, port, check.timeout_sec)
    except (OSError, ssl.SSLError) as error:
        latency = round((clock() - started) * 1000)
        kind, message = network_failure(error, host, check.timeout_sec)
        if isinstance(error, ssl.SSLCertVerificationError):
            message = f"Сертификат не прошёл проверку: {error.verify_message}"
        details["error"] = str(error)[:300]
        return Outcome(CheckStatus.fail, latency, message, kind, details)
    latency = round((clock() - started) * 1000)
    expires = datetime.fromtimestamp(ssl.cert_time_to_seconds(cert["notAfter"]), UTC)
    days_left = ((expires - (now or datetime.now(UTC))).total_seconds()) // 86400
    details.update(
        not_after=expires.isoformat(),
        days_left=int(days_left),
        issuer=cert_name(cert.get("issuer")),
        subject=cert_name(cert.get("subject")),
    )
    date = expires.strftime("%d.%m.%Y")
    if days_left < 0:
        return Outcome(CheckStatus.fail, latency, f"Сертификат истёк {date}", "cert_expired", details)
    message = f"Сертификат истекает через {int(days_left)} дн, {date}"
    if days_left < config.get("fail_days", DEFAULT_TLS_FAIL_DAYS):
        return Outcome(CheckStatus.fail, latency, message, "cert_expiring", details)
    if days_left < config.get("warn_days", DEFAULT_TLS_WARN_DAYS):
        return Outcome(CheckStatus.warn, latency, message, "cert_expiring", details)
    return Outcome(CheckStatus.ok, latency, None, None, details)


Connector = Callable[[tuple[str, int], int], socket.socket]


def connect(address: tuple[str, int], timeout: int) -> socket.socket:
    return socket.create_connection(address, timeout=timeout)


def run_tcp(check: HealthCheck, open_connection: Connector = connect) -> Outcome:
    host, port = split_host(check.target, 0)
    details: dict[str, Any] = {"host": host, "port": port}
    started = clock()
    try:
        open_connection((host, port), check.timeout_sec).close()
    except OSError as error:
        latency = round((clock() - started) * 1000)
        kind, message = network_failure(error, host, check.timeout_sec)
        if kind == "connection":
            message = f"Порт {port} закрыт"
        elif kind == "timeout":
            message = f"Порт {port} не ответил за {check.timeout_sec} с"
        details["error"] = str(error)[:300]
        return Outcome(CheckStatus.fail, latency, message, kind, details)
    latency = round((clock() - started) * 1000)
    details["latency_ms"] = latency
    return Outcome(CheckStatus.ok, latency, None, None, details)


PULL_METHODS = frozenset({CheckMethod.http, CheckMethod.tls, CheckMethod.tcp})


def run_check(check: HealthCheck, client: httpx.Client) -> Outcome:
    if check.method is CheckMethod.http:
        return run_http(check, client)
    if check.method is CheckMethod.tls:
        return run_tls(check)
    if check.method is CheckMethod.tcp:
        return run_tcp(check)
    raise ValueError(f"{check.method} is reported by the client, Pult does not run it")
