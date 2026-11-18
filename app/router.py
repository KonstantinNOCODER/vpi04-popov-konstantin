"""Маршрутизация: payload/текст -> ответ. Без зависимостей от vkbottle.

Обработчик vkbottle передаёт сюда сырой payload и текст сообщения, а получает
объект Reply: текст ответа и тип клавиатуры, которую нужно показать.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any

from app import texts
from app.catalog import Catalog, format_price_list, format_service_card

CMD_KEY = "cmd"
CMD_MENU = "menu"
CMD_SERVICES = "services"
CMD_SERVICE = "service"
CMD_PRICE = "price"
CMD_CONTACT = "contact"

# VK ограничивает payload кнопки 255 символами.
MAX_PAYLOAD_LENGTH = 255

# Текстовые синонимы на случай, если пользователь пишет вместо нажатия кнопок.
TEXT_COMMANDS: dict[str, str] = {
    "начать": CMD_MENU,
    "старт": CMD_MENU,
    "start": CMD_MENU,
    "/start": CMD_MENU,
    "меню": CMD_MENU,
    "главное меню": CMD_MENU,
    "привет": CMD_MENU,
    "услуги": CMD_SERVICES,
    "каталог": CMD_SERVICES,
    "прайс": CMD_PRICE,
    "прайс-лист": CMD_PRICE,
    "цены": CMD_PRICE,
    "менеджер": CMD_CONTACT,
    "связаться с менеджером": CMD_CONTACT,
}


class KeyboardKind(Enum):
    MAIN = "main"          # главное меню
    CATALOG = "catalog"    # список услуг + «в меню»
    SERVICE = "service"    # «к услугам» + «в меню»
    BACK = "back"          # только «в меню»


@dataclass(frozen=True, slots=True)
class Reply:
    text: str
    keyboard: KeyboardKind


def make_payload(cmd: str, **extra: str) -> dict[str, str]:
    return {CMD_KEY: cmd, **extra}


def payload_to_json(payload: dict[str, str]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if len(raw) > MAX_PAYLOAD_LENGTH:
        raise ValueError(f"Payload длиннее {MAX_PAYLOAD_LENGTH} символов: {raw!r}")
    return raw


def parse_payload(raw: Any) -> dict[str, Any] | None:
    """Возвращает payload как dict или None, если его нет или он некорректен."""
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def is_incoming_user_message(out: Any, from_id: Any) -> bool:
    """True только для входящих сообщений от пользователя (не от сообщества)."""
    if out:  # out=1 — исходящее сообщение сообщества
        return False
    return isinstance(from_id, int) and not isinstance(from_id, bool) and from_id > 0


def _resolve_command(payload: dict[str, Any] | None, text: str | None) -> tuple[str | None, dict[str, Any]]:
    if payload is not None:
        # Системная кнопка VK «Начать» присылает {"command": "start"}.
        if payload.get("command") == "start":
            return CMD_MENU, payload
        cmd = payload.get(CMD_KEY)
        return (cmd if isinstance(cmd, str) else None), payload
    normalized = (text or "").strip().lower()
    return TEXT_COMMANDS.get(normalized), {}


def route(catalog: Catalog, raw_payload: Any, text: str | None) -> Reply:
    payload = parse_payload(raw_payload)
    cmd, data = _resolve_command(payload, text)

    if cmd == CMD_MENU:
        is_start = payload is None or payload.get("command") == "start"
        return Reply(texts.WELCOME if is_start else texts.MAIN_MENU, KeyboardKind.MAIN)

    if cmd == CMD_SERVICES:
        if catalog.is_empty:
            return Reply(texts.CATALOG_EMPTY, KeyboardKind.BACK)
        return Reply(texts.CATALOG, KeyboardKind.CATALOG)

    if cmd == CMD_SERVICE:
        service = catalog.get(data.get("id"))
        if service is None:
            kind = KeyboardKind.BACK if catalog.is_empty else KeyboardKind.CATALOG
            return Reply(texts.SERVICE_NOT_FOUND, kind)
        return Reply(format_service_card(service), KeyboardKind.SERVICE)

    if cmd == CMD_PRICE:
        return Reply(format_price_list(catalog), KeyboardKind.BACK)

    if cmd == CMD_CONTACT:
        return Reply(texts.CONTACT, KeyboardKind.BACK)

    # Неизвестный payload, некорректный JSON или произвольный текст.
    return Reply(texts.UNKNOWN, KeyboardKind.MAIN)
