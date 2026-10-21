# -*- coding: utf-8 -*-
"""Telegram inbound adapter for the Rocky MCP business-tool flow.

The bot is intentionally a separate process from the MCP HTTP/OAuth service.
It uses Telegram long polling, so it needs no public webhook endpoint.  Incoming
chat IDs are an explicit allow-list and the AI layer receives a restricted tool
set: raw SQL, schema exploration and write/notification actions stay unavailable.
"""
from __future__ import annotations

import json
import logging
import os
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Callable, Iterable

import httpx

from .ai_chat import chat

LOGGER = logging.getLogger(__name__)
TELEGRAM_API_BASE = "https://api.telegram.org"
TELEGRAM_MESSAGE_LIMIT = 4096

# These are read-only business tools. Never add raw SQL/schema tools or a
# notification trigger here: a Telegram allow-list is not a SQL-console role.
TELEGRAM_ALLOWED_TOOLS = frozenset({
    "get_revenue",
    "get_revenue_legacy",
    "get_subtotal",
    "get_dashboard_order_overview",
    "get_dashboard_order_by_site",
    "get_dashboard_revenue",
    "get_dashboard_sales_by_customer",
    "get_dashboard_metric",
    "get_dashboard_debt_overview",
    "get_dashboard_debt_customers",
    "get_debt",
    "get_customer_debt_profile",
    "get_staff_revenue",
    "get_orders",
    "get_order_operations",
    "get_inventory",
    "get_customers",
    "get_products",
    "get_stores",
    "get_return_exchange_requests",
    "get_return_orders",
    "explain",
})


def _parse_chat_ids(value: str) -> frozenset[str]:
    return frozenset(item.strip() for item in value.split(",") if item.strip())


@dataclass(frozen=True)
class TelegramBotConfig:
    token: str
    allowed_chat_ids: frozenset[str]
    poll_timeout_seconds: int = 30
    max_history_messages: int = 12
    max_input_characters: int = 3000

    @classmethod
    def from_env(cls) -> "TelegramBotConfig":
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        allowed = _parse_chat_ids(os.environ.get("TELEGRAM_ALLOWED_CHAT_IDS", ""))
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN is not configured")
        if not allowed:
            raise ValueError("TELEGRAM_ALLOWED_CHAT_IDS must contain at least one chat ID")
        return cls(
            token=token,
            allowed_chat_ids=allowed,
            poll_timeout_seconds=max(5, min(int(os.environ.get("TELEGRAM_POLL_TIMEOUT_SECONDS", "30")), 50)),
            max_history_messages=max(0, min(int(os.environ.get("TELEGRAM_MAX_HISTORY_MESSAGES", "12")), 40)),
            max_input_characters=max(200, min(int(os.environ.get("TELEGRAM_MAX_INPUT_CHARACTERS", "3000")), 12000)),
        )


class TelegramApi:
    """Small Telegram Bot API client with no framework dependency."""

    def __init__(self, token: str, client: httpx.Client | None = None):
        self._base_url = f"{TELEGRAM_API_BASE}/bot{token}"
        self._client = client or httpx.Client(timeout=httpx.Timeout(65.0, connect=10.0))

    def get_updates(self, offset: int | None, timeout: int) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"timeout": timeout, "allowed_updates": ["message"]}
        if offset is not None:
            payload["offset"] = offset
        response = self._client.post(f"{self._base_url}/getUpdates", json=payload)
        response.raise_for_status()
        body = response.json()
        if not body.get("ok"):
            raise RuntimeError("Telegram getUpdates was rejected")
        return body.get("result", [])

    def send_message(self, chat_id: str, text: str) -> None:
        response = self._client.post(
            f"{self._base_url}/sendMessage",
            json={"chat_id": chat_id, "text": text},
        )
        response.raise_for_status()
        if not response.json().get("ok"):
            raise RuntimeError("Telegram sendMessage was rejected")

    def close(self) -> None:
        self._client.close()


def split_telegram_message(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    """Split long responses without cutting a Unicode code point or word if possible."""
    text = text.strip() or "Không có nội dung trả về."
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    remaining = text
    while len(remaining) > limit:
        boundary = max(remaining.rfind("\n", 0, limit), remaining.rfind(" ", 0, limit))
        if boundary < limit // 2:
            boundary = limit
        chunks.append(remaining[:boundary].rstrip())
        remaining = remaining[boundary:].lstrip()
    if remaining:
        chunks.append(remaining)
    return chunks


class RockyTelegramBot:
    """Stateful, allow-listed Telegram adapter for the read-only MCP tool flow."""

    def __init__(
        self,
        config: TelegramBotConfig,
        api: TelegramApi,
        responder: Callable[[str, list[dict[str, str]], set[str]], str] = chat,
    ):
        self.config = config
        self.api = api
        self.responder = responder
        self.history: dict[str, deque[dict[str, str]]] = defaultdict(
            lambda: deque(maxlen=config.max_history_messages)
        )
        self._last_request_at: dict[str, float] = {}

    def _send(self, chat_id: str, text: str) -> None:
        for chunk in split_telegram_message(text):
            self.api.send_message(chat_id, chunk)

    def handle_update(self, update: dict[str, Any]) -> None:
        message = update.get("message") or {}
        chat_info = message.get("chat") or {}
        chat_id = str(chat_info.get("id", ""))
        text = (message.get("text") or "").strip()

        # Ignore groups and all unregistered chats without replying. This avoids
        # exposing a bot presence or an enrollment channel to strangers.
        if chat_info.get("type") != "private" or chat_id not in self.config.allowed_chat_ids:
            return
        if not text:
            self._send(chat_id, "Chỉ hỗ trợ câu hỏi dạng văn bản.")
            return
        if len(text) > self.config.max_input_characters:
            self._send(chat_id, "Câu hỏi quá dài. Vui lòng rút gọn dưới 3.000 ký tự.")
            return

        command = text.split(maxsplit=1)[0].lower()
        if command == "/start":
            self._send(chat_id, "Rocky Assistant đã sẵn sàng. Hãy hỏi doanh số, đơn hàng, tồn kho hoặc công nợ.")
            return
        if command == "/help":
            self._send(chat_id, "Ví dụ: 'Doanh số hôm nay', 'Top 10 khách hàng tuần này', hoặc 'Tồn kho 1.56 BLUECUT'.")
            return
        if command == "/reset":
            self.history.pop(chat_id, None)
            self._send(chat_id, "Đã xóa ngữ cảnh cuộc trò chuyện này.")
            return

        now = time.monotonic()
        if now - self._last_request_at.get(chat_id, 0) < 1.0:
            self._send(chat_id, "Vui lòng chờ phản hồi trước khi gửi câu hỏi tiếp theo.")
            return
        self._last_request_at[chat_id] = now

        history = list(self.history[chat_id])
        try:
            answer = self.responder(text, history, set(TELEGRAM_ALLOWED_TOOLS))
        except Exception:
            LOGGER.exception("Telegram AI request failed for allowed chat")
            self._send(chat_id, "Rocky đang không thể xử lý yêu cầu. Vui lòng thử lại sau ít phút.")
            return

        self.history[chat_id].append({"role": "user", "content": text})
        self.history[chat_id].append({"role": "assistant", "content": answer})
        self._send(chat_id, answer)

    def run_forever(self) -> None:
        offset: int | None = None
        LOGGER.info("Rocky Telegram adapter started with %s allowed chats", len(self.config.allowed_chat_ids))
        while True:
            try:
                for update in self.api.get_updates(offset, self.config.poll_timeout_seconds):
                    update_id = update.get("update_id")
                    if isinstance(update_id, int):
                        offset = update_id + 1
                    self.handle_update(update)
            except KeyboardInterrupt:
                raise
            except Exception:
                LOGGER.exception("Telegram polling failed; retrying in 5 seconds")
                time.sleep(5)


def main() -> None:
    config = TelegramBotConfig.from_env()
    api = TelegramApi(config.token)
    try:
        RockyTelegramBot(config, api).run_forever()
    finally:
        api.close()


if __name__ == "__main__":
    main()
