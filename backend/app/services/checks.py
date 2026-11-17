import ipaddress
import socket
import ssl
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx

from app.models import CheckMethod, CheckStatus, HealthCheck

BODY_EXCERPT = 500
MAX_REDIRECTS = 5
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


class BlockedAddressError(Exception):
    def __init__(self, host: str, address: str) -> None:
        super().__init__(f"{host} resolves to non-public address {address}")
        self.host = host
        self.address = address


Resolver = Callable[[str, int], list[str]]


def resolve_addresses(host: str, port: int) -> list[str]:
    addresses: list[str] = []
    for *_, sockaddr in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM):
        address = str(sockaddr[0])
        if address not in addresses:
            addresses.append(address)
    return addresses


def is_public(address: str) -> bool:
    ip = ipaddress.ip_address(address.split("%", 1)[0])
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


@dataclass(frozen=True)
class Guard:
    allow_private: bool = False
    resolve: Resolver | None = None

    def address(self, host: str, port: int) -> str:
        addresses = (self.resolve or resolve_addresses)(host, port)
        if not addresses:
            raise socket.gaierror(f"getaddrinfo returned nothing for {host}")
        if not self.allow_private:
            for address in addresses:
                if not is_public(address):
                    raise BlockedAddressError(host, address)
        return addresses[0]


def blocked(error: BlockedAddressError, details: dict[str, Any]) -> Outcome:
    details["address"] = error.address
    message = f"Адрес {error.address} во внутренней сети, такие проверки запрещены"
    return Outcome(CheckStatus.fail, None, message, "blocked", details)


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


def default_port(url: httpx.URL) -> int:
    return url.port or (443 if url.scheme == "https" else 80)


def fetch_pinned(
    client: httpx.Client, method: str, url: httpx.URL, guard: Guard, timeout: int
) -> tuple[httpx.Response, httpx.URL]:
    for _ in range(MAX_REDIRECTS + 1):
        address = guard.address(url.host, default_port(url))
        response = client.request(
            method,
            url.copy_with(host=address),
            headers={"Host": url.netloc.decode("ascii")},
            extensions={"sni_hostname": url.host},
            timeout=timeout,
            follow_redirects=False,
        )
        location = response.headers.get("location")
        if not response.is_redirect or not location:
            return response, url
        url = url.join(location)
        if url.scheme not in ("http", "https"):
            return response, url
    raise httpx.TooManyRedirects(f"more than {MAX_REDIRECTS} redirects")


def run_http(check: HealthCheck, client: httpx.Client, guard: Guard | None = None) -> Outcome:
    config = check.config or {}
    method = config.get("method", "GET")
    details: dict[str, Any] = {"url": check.target, "method": method}
    url = httpx.URL(check.target)
    started = clock()
    try:
        response, final_url = fetch_pinned(client, method, url, guard or Guard(), check.timeout_sec)
    except BlockedAddressError as error:
        return blocked(error, details)
    except httpx.TooManyRedirects:
        latency = round((clock() - started) * 1000)
        message = f"Больше {MAX_REDIRECTS} перенаправлений подряд"
        return Outcome(CheckStatus.fail, latency, message, "http_status", details)
    except (httpx.HTTPError, OSError) as error:
        latency = round((clock() - started) * 1000)
        kind, message = network_failure(error, url.host or check.target, check.timeout_sec)
        details["error"] = str(error)[:300]
        return Outcome(CheckStatus.fail, latency, message, kind, details)
    latency = round((clock() - started) * 1000)
    details.update(
        status_code=response.status_code,
        reason=response.reason_phrase,
        latency_ms=latency,
        content_type=response.headers.get("content-type"),
    )
    if final_url != url:
        details["final_url"] = str(final_url)
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


CertFetcher = Callable[[str, str, int, int], dict[str, Any]]


def fetch_certificate(host: str, address: str, port: int, timeout: int) -> dict[str, Any]:
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    with (
        socket.create_connection((address, port), timeout=timeout) as raw,
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
    check: HealthCheck,
    fetch: CertFetcher = fetch_certificate,
    now: datetime | None = None,
    guard: Guard | None = None,
) -> Outcome:
    config = check.config or {}
    host, port = split_host(check.target, 443)
    details: dict[str, Any] = {"host": host, "port": port}
    started = clock()
    try:
        cert = fetch(host, (guard or Guard()).address(host, port), port, check.timeout_sec)
    except BlockedAddressError as error:
        return blocked(error, details)
    except (OSError, ssl.SSLError) as error:
        latency = round((clock() - started) * 1000)
        kind, message = network_failure(error, host, check.timeout_sec)
        if isinstance(error, ssl.SSLCertVerificationError):
            message = f"Сертификат не прошёл проверку: {error.verify_message}"
        details["error"] = str(error)[:300]
        return Outcome(CheckStatus.fail, latency, message, kind, details)
    latency = round((clock() - started) * 1000)
    return certificate_outcome(cert, config, details, latency, now or datetime.now(UTC))


def certificate_outcome(
    cert: dict[str, Any], config: dict[str, Any], details: dict[str, Any], latency: int, now: datetime
) -> Outcome:
    expires = datetime.fromtimestamp(ssl.cert_time_to_seconds(cert["notAfter"]), UTC)
    days_left = ((expires - now).total_seconds()) // 86400
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


def run_tcp(check: HealthCheck, open_connection: Connector = connect, guard: Guard | None = None) -> Outcome:
    host, port = split_host(check.target, 0)
    details: dict[str, Any] = {"host": host, "port": port}
    started = clock()
    try:
        open_connection(((guard or Guard()).address(host, port), port), check.timeout_sec).close()
    except BlockedAddressError as error:
        return blocked(error, details)
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


def run_check(check: HealthCheck, client: httpx.Client, guard: Guard | None = None) -> Outcome:
    if check.method is CheckMethod.http:
        return run_http(check, client, guard)
    if check.method is CheckMethod.tls:
        return run_tls(check, guard=guard)
    if check.method is CheckMethod.tcp:
        return run_tcp(check, guard=guard)
    raise ValueError(f"{check.method} is reported by the client, Pult does not run it")
