import httpx
import pytest

from app.api.probe import get_notifier
from app.integrations.telegram import TelegramNotifier, format_message, is_notable
from app.main import app
from app.services.status import BlockStatus
from tests.test_api import PROBE, TOKEN, pilot, probe_batch

__all__ = ["pilot"]


def recording_client(sent: list[httpx.Request], status_code: int = 200) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(status_code, json={"ok": status_code == 200})

    return httpx.Client(base_url="https://api.telegram.org", transport=httpx.MockTransport(handler))


@pytest.mark.parametrize(
    ("previous", "current", "expected"),
    [
        (BlockStatus.ok, BlockStatus.fail, True),
        (BlockStatus.unknown, BlockStatus.fail, True),
        (BlockStatus.fail, BlockStatus.ok, True),
        (BlockStatus.ok, BlockStatus.warn, False),
        (BlockStatus.fail, BlockStatus.unknown, False),
    ],
)
def test_only_failures_and_recoveries_are_notable(previous, current, expected):
    assert is_notable(previous, current) is expected


def test_message_text():
    text = format_message("pilot", "POS-система", BlockStatus.ok, BlockStatus.fail)
    assert text == "Сбой блока «POS-система» в проекте «pilot»: работает → сбой"


def test_disabled_without_token():
    sent: list[httpx.Request] = []
    assert TelegramNotifier("", "", recording_client(sent)).send("x") is False
    assert sent == []


def test_failed_delivery_does_not_raise():
    sent: list[httpx.Request] = []
    assert TelegramNotifier("t", "c", recording_client(sent, status_code=502)).send("x") is False
    assert len(sent) == 1


def test_probe_failure_sends_message(client, pilot):
    sent: list[httpx.Request] = []
    app.dependency_overrides[get_notifier] = lambda: TelegramNotifier(
        "bot-token", "42", recording_client(sent)
    )
    client.post(PROBE, json=probe_batch(pilot["pos_check"], "fail"), headers={"X-Probe-Token": TOKEN})
    client.post(PROBE, json=probe_batch(pilot["pos_check"], "fail"), headers={"X-Probe-Token": TOKEN})
    client.post(PROBE, json=probe_batch(pilot["pos_check"], "ok"), headers={"X-Probe-Token": TOKEN})
    texts = [request.read().decode() for request in sent]
    assert len(sent) == 2
    assert sent[0].url.path == "/botbot-token/sendMessage"
    assert "Сбой блока" in texts[0]
    assert "восстановлен" in texts[1]
