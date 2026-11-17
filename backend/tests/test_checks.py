import socket
import ssl
from datetime import UTC, datetime

import httpx
import pytest

from app.models import CheckMethod, CheckStatus, HealthCheck
from app.services.checks import (
    Guard,
    is_public,
    network_failure,
    resolve_addresses,
    run_check,
    run_http,
    run_tcp,
    run_tls,
    seconds,
    split_host,
)

NOW = datetime(2026, 11, 17, 8, 0, tzinfo=UTC)
PUBLIC = "93.184.216.34"


@pytest.fixture(autouse=True)
def public_dns(monkeypatch):
    monkeypatch.setattr("app.services.checks.resolve_addresses", lambda host, port: [PUBLIC])


def make_check(
    method: CheckMethod, target: str, config: dict | None = None, timeout: int = 10
) -> HealthCheck:
    return HealthCheck(
        id=1, block_id=1, method=method, target=target, timeout_sec=timeout, config=config or {}
    )


def client_for(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)


def respond(status: int, text: str = "ok", headers: dict | None = None):
    return lambda request: httpx.Response(
        status, text=text, headers=headers or {"content-type": "text/plain"}
    )


def fail_with(error: Exception):
    def handler(request: httpx.Request) -> httpx.Response:
        raise error

    return handler


def test_http_ok_keeps_response_details():
    outcome = run_http(make_check(CheckMethod.http, "https://pos.example/ping"), client_for(respond(200)))
    assert outcome.status is CheckStatus.ok
    assert outcome.message is None
    assert outcome.details["status_code"] == 200
    assert outcome.details["content_type"] == "text/plain"
    assert "body_excerpt" not in outcome.details


def test_http_unexpected_status_is_failure_with_body_excerpt():
    client = client_for(respond(502, "upstream connect error " * 50))
    outcome = run_http(make_check(CheckMethod.http, "https://pos.example/ping"), client)
    assert outcome.status is CheckStatus.fail
    assert outcome.error_kind == "http_status"
    assert outcome.message == "HTTP 502 Bad Gateway"
    assert outcome.details["body_excerpt"].startswith("upstream connect error")
    assert len(outcome.details["body_excerpt"]) == 500


def test_http_expected_status_list_overrides_default_range():
    check = make_check(CheckMethod.http, "https://pos.example/ping", {"expect_status": [204]})
    assert run_http(check, client_for(respond(204, ""))).status is CheckStatus.ok
    assert run_http(check, client_for(respond(200))).error_kind == "http_status"


def test_http_missing_text_is_content_failure():
    check = make_check(CheckMethod.http, "https://pos.example/ping", {"contains": '"status":"ok"'})
    outcome = run_http(check, client_for(respond(200, '{"status":"degraded"}')))
    assert outcome.status is CheckStatus.fail
    assert outcome.error_kind == "content"
    assert outcome.message == 'В ответе нет «"status":"ok"»'


def test_http_slow_answer_is_warning(monkeypatch):
    ticks = iter([0.0, 2.4])
    monkeypatch.setattr("app.services.checks.clock", lambda: next(ticks))
    check = make_check(CheckMethod.http, "https://pos.example/ping", {"warn_latency_ms": 1000})
    outcome = run_http(check, client_for(respond(200)))
    assert outcome.status is CheckStatus.warn
    assert outcome.error_kind == "slow"
    assert outcome.message == "Ответ за 2,4 с, порог 1,0 с"


def test_http_redirect_records_final_url():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/old":
            return httpx.Response(301, headers={"location": "https://pos.example/new"})
        return httpx.Response(200, text="ok")

    outcome = run_http(make_check(CheckMethod.http, "https://pos.example/old"), client_for(handler))
    assert outcome.details["final_url"] == "https://pos.example/new"


@pytest.mark.parametrize(
    ("error", "kind", "message"),
    [
        (httpx.ReadTimeout("timed out"), "timeout", "Не ответил за 5 с"),
        (httpx.ConnectError("[Errno 11001] getaddrinfo failed"), "dns", "Адрес pos.example не найден"),
        (httpx.ConnectError("[Errno 111] Connection refused"), "connection", "Соединение отклонено"),
        (
            httpx.ConnectError("[SSL: CERTIFICATE_VERIFY_FAILED] certificate has expired"),
            "tls",
            "Сертификат не прошёл проверку",
        ),
        (
            httpx.ConnectError("network is unreachable"),
            "connection",
            "Не удалось подключиться: network is unreachable",
        ),
    ],
)
def test_http_network_errors_are_classified(error, kind, message):
    check = make_check(CheckMethod.http, "https://pos.example/ping", timeout=5)
    outcome = run_http(check, client_for(fail_with(error)))
    assert outcome.status is CheckStatus.fail
    assert (outcome.error_kind, outcome.message) == (kind, message)
    assert outcome.details["error"]


def certificate(not_after: str) -> dict:
    return {
        "notAfter": not_after,
        "issuer": ((("countryName", "US"),), (("organizationName", "Let's Encrypt"),)),
        "subject": ((("commonName", "pos.example"),),),
    }


@pytest.mark.parametrize(
    ("not_after", "status", "kind", "message"),
    [
        ("Feb 15 08:00:00 2027 GMT", CheckStatus.ok, None, None),
        (
            "Nov 27 08:00:00 2026 GMT",
            CheckStatus.warn,
            "cert_expiring",
            "Сертификат истекает через 10 дн, 27.11.2026",
        ),
        (
            "Nov 19 08:00:00 2026 GMT",
            CheckStatus.fail,
            "cert_expiring",
            "Сертификат истекает через 2 дн, 19.11.2026",
        ),
        ("Nov 10 08:00:00 2026 GMT", CheckStatus.fail, "cert_expired", "Сертификат истёк 10.11.2026"),
    ],
)
def test_tls_expiry_thresholds(not_after, status, kind, message):
    check = make_check(CheckMethod.tls, "pos.example")
    outcome = run_tls(check, fetch=lambda host, address, port, timeout: certificate(not_after), now=NOW)
    assert (outcome.status, outcome.error_kind, outcome.message) == (status, kind, message)
    assert outcome.details["issuer"] == "Let's Encrypt"
    assert outcome.details["subject"] == "pos.example"
    assert (outcome.details["host"], outcome.details["port"]) == ("pos.example", 443)


def test_tls_thresholds_come_from_config():
    check = make_check(CheckMethod.tls, "pos.example:8443", {"warn_days": 120, "fail_days": 30})
    outcome = run_tls(
        check, fetch=lambda host, address, port, timeout: certificate("Feb 15 08:00:00 2027 GMT"), now=NOW
    )
    assert outcome.status is CheckStatus.warn
    assert outcome.details["port"] == 8443


def test_tls_verification_error_names_the_reason():
    error = ssl.SSLCertVerificationError(1, "certificate verify failed")
    error.verify_message = "certificate has expired"

    def fetch(host, address, port, timeout):
        raise error

    outcome = run_tls(make_check(CheckMethod.tls, "pos.example"), fetch=fetch, now=NOW)
    assert outcome.error_kind == "tls"
    assert outcome.message == "Сертификат не прошёл проверку: certificate has expired"


def test_tls_unknown_host_is_dns_failure():
    def fetch(host, address, port, timeout):
        raise socket.gaierror(11001, "getaddrinfo failed")

    outcome = run_tls(make_check(CheckMethod.tls, "pos.example"), fetch=fetch, now=NOW)
    assert (outcome.error_kind, outcome.message) == ("dns", "Адрес pos.example не найден")


class FakeSocket:
    closed = False

    def close(self) -> None:
        self.closed = True


def test_tcp_open_port_is_ok():
    sock = FakeSocket()
    outcome = run_tcp(
        make_check(CheckMethod.tcp, "db.example:5432"), open_connection=lambda address, timeout: sock
    )
    assert outcome.status is CheckStatus.ok
    assert sock.closed
    assert (outcome.details["host"], outcome.details["port"]) == ("db.example", 5432)


@pytest.mark.parametrize(
    ("error", "kind", "message"),
    [
        (ConnectionRefusedError(111, "Connection refused"), "connection", "Порт 5432 закрыт"),
        (TimeoutError("timed out"), "timeout", "Порт 5432 не ответил за 3 с"),
        (socket.gaierror(-2, "Name or service not known"), "dns", "Адрес db.example не найден"),
    ],
)
def test_tcp_failures(error, kind, message):
    def connect(address, timeout):
        raise error

    outcome = run_tcp(make_check(CheckMethod.tcp, "db.example:5432", timeout=3), open_connection=connect)
    assert outcome.status is CheckStatus.fail
    assert (outcome.error_kind, outcome.message) == (kind, message)


def test_run_check_dispatches_by_method(monkeypatch):
    monkeypatch.setattr("app.services.checks.run_tls", lambda check, guard: "tls")
    monkeypatch.setattr("app.services.checks.run_tcp", lambda check, guard: "tcp")
    client = client_for(respond(200))
    assert run_check(make_check(CheckMethod.http, "https://pos.example"), client).status is CheckStatus.ok
    assert run_check(make_check(CheckMethod.tls, "pos.example"), client) == "tls"
    assert run_check(make_check(CheckMethod.tcp, "pos.example:22"), client) == "tcp"


def test_run_check_refuses_client_reported_methods():
    with pytest.raises(ValueError, match="reported by the client"):
        run_check(make_check(CheckMethod.exit_code, "main.py"), client_for(respond(200)))


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        ("pos.example", ("pos.example", 443)),
        ("pos.example:8443", ("pos.example", 8443)),
        ("[::1]:5432", ("::1", 5432)),
        ("pos.example:abc", ("pos.example:abc", 443)),
    ],
)
def test_split_host(target, expected):
    assert split_host(target, 443) == expected


def test_seconds_use_decimal_comma():
    assert seconds(1234) == "1,2 с"


def test_unknown_error_text_is_cut():
    kind, message = network_failure(OSError("x" * 500), "pos.example", 10)
    assert kind == "connection"
    assert len(message) == len("Не удалось подключиться: ") + 200


def test_http_request_is_pinned_to_checked_address_with_original_host():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["host"] = request.url.host
        seen["header"] = request.headers["host"]
        seen["sni"] = request.extensions.get("sni_hostname")
        return httpx.Response(200, text="ok")

    run_http(make_check(CheckMethod.http, "https://pos.example:8443/ping"), client_for(handler))
    assert seen == {"host": PUBLIC, "header": "pos.example:8443", "sni": "pos.example"}


@pytest.mark.parametrize(
    "address", ["127.0.0.1", "10.0.0.5", "192.168.1.10", "169.254.169.254", "::1", "::ffff:10.0.0.1"]
)
def test_internal_addresses_are_blocked_for_every_method(address):
    guard = Guard(resolve=lambda host, port: [address])
    called = []

    def handler(request: httpx.Request) -> httpx.Response:
        called.append(request)
        return httpx.Response(200)

    http = run_http(make_check(CheckMethod.http, "https://pos.example"), client_for(handler), guard)
    tls = run_tls(
        make_check(CheckMethod.tls, "pos.example"), fetch=lambda *args: called.append(args), guard=guard
    )
    tcp = run_tcp(
        make_check(CheckMethod.tcp, "pos.example:22"),
        open_connection=lambda *args: called.append(args),
        guard=guard,
    )
    for outcome in (http, tls, tcp):
        assert (outcome.status, outcome.error_kind) == (CheckStatus.fail, "blocked")
        assert outcome.message == f"Адрес {address} во внутренней сети, такие проверки запрещены"
        assert outcome.details["address"] == address
    assert called == []


def test_any_internal_address_among_several_blocks():
    guard = Guard(resolve=lambda host, port: [PUBLIC, "10.1.2.3"])
    outcome = run_tcp(
        make_check(CheckMethod.tcp, "pos.example:22"), open_connection=lambda *a: FakeSocket(), guard=guard
    )
    assert outcome.error_kind == "blocked"


def test_redirect_into_internal_network_is_blocked():
    def resolve(host, port):
        return ["127.0.0.1"] if host == "internal.example" else [PUBLIC]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "http://internal.example:8000/admin"})

    outcome = run_http(
        make_check(CheckMethod.http, "https://pos.example"), client_for(handler), Guard(resolve=resolve)
    )
    assert outcome.error_kind == "blocked"
    assert outcome.details["address"] == "127.0.0.1"


def test_private_addresses_allowed_when_configured():
    guard = Guard(allow_private=True, resolve=lambda host, port: ["127.0.0.1"])
    outcome = run_http(
        make_check(CheckMethod.http, "http://localhost:8000/api/health"), client_for(respond(200)), guard
    )
    assert outcome.status is CheckStatus.ok


def test_endless_redirects_stop():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(301, headers={"location": "/again"})

    outcome = run_http(make_check(CheckMethod.http, "https://pos.example/start"), client_for(handler))
    assert (outcome.status, outcome.message) == (CheckStatus.fail, "Больше 5 перенаправлений подряд")


def test_redirect_to_other_scheme_is_final():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "ftp://files.example/plan.xlsx"})

    outcome = run_http(make_check(CheckMethod.http, "https://pos.example"), client_for(handler))
    assert outcome.details["final_url"] == "ftp://files.example/plan.xlsx"


def test_empty_dns_answer_is_dns_failure():
    outcome = run_tcp(
        make_check(CheckMethod.tcp, "pos.example:22"), guard=Guard(resolve=lambda host, port: [])
    )
    assert outcome.error_kind == "dns"


@pytest.mark.parametrize(
    ("address", "public"),
    [
        (PUBLIC, True),
        ("10.0.0.1", False),
        ("fe80::1%eth0", False),
        ("224.0.0.1", False),
        ("2606:4700::1111", True),
    ],
)
def test_is_public(address, public):
    assert is_public(address) is public


def test_resolve_addresses_deduplicates(monkeypatch):
    infos = [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", (PUBLIC, 443)),
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", (PUBLIC, 443)),
        (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("2606:4700::1111", 443, 0, 0)),
    ]
    monkeypatch.setattr("app.services.checks.socket.getaddrinfo", lambda *args, **kwargs: infos)
    assert resolve_addresses("pos.example", 443) == [PUBLIC, "2606:4700::1111"]
