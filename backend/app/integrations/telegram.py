import logging

import httpx

from app.services.status import BlockStatus

logger = logging.getLogger(__name__)

API_URL = "https://api.telegram.org"

LABELS = {
    BlockStatus.ok: "работает",
    BlockStatus.warn: "предупреждение",
    BlockStatus.fail: "сбой",
    BlockStatus.unknown: "нет данных",
}


def is_notable(previous: BlockStatus, current: BlockStatus) -> bool:
    return current is BlockStatus.fail or (previous is BlockStatus.fail and current is BlockStatus.ok)


def format_message(project: str, block: str, previous: BlockStatus, current: BlockStatus) -> str:
    headline = "Сбой блока" if current is BlockStatus.fail else "Блок восстановлен"
    return f"{headline} «{block}» в проекте «{project}»: {LABELS[previous]} → {LABELS[current]}"


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str, client: httpx.Client | None = None) -> None:
        self.token = token
        self.chat_id = chat_id
        self.client = client or httpx.Client(base_url=API_URL, timeout=5)

    @property
    def enabled(self) -> bool:
        return bool(self.token and self.chat_id)

    def send(self, text: str) -> bool:
        if not self.enabled:
            return False
        try:
            response = self.client.post(
                f"/bot{self.token}/sendMessage",
                json={"chat_id": self.chat_id, "text": text, "disable_web_page_preview": True},
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            logger.warning("telegram notification failed: %s", error.__class__.__name__)
            return False
        return True
