"""Обработчики vkbottle: тонкий слой между VK и app.router."""

from __future__ import annotations

import logging

from vkbottle.bot import BotLabeler, Message
from vkbottle.dispatch.rules import ABCRule

from app.catalog import Catalog
from app.keyboards import KeyboardSet
from app.router import is_incoming_user_message, route

log = logging.getLogger(__name__)


class IncomingFromUserRule(ABCRule[Message]):
    """Пропускает только входящие сообщения от пользователей.

    Исходящие сообщения сообщества (out=1) и сообщения от имени групп
    (отрицательный from_id) игнорируются, чтобы бот не отвечал сам себе.
    """

    async def check(self, event: Message) -> bool:
        return is_incoming_user_message(getattr(event, "out", 0), event.from_id)


def build_labeler(catalog: Catalog) -> BotLabeler:
    labeler = BotLabeler()
    keyboards = KeyboardSet(catalog)

    # Только личные сообщения сообществу; беседы бот не обслуживает.
    @labeler.private_message(IncomingFromUserRule())
    async def handle_message(message: Message) -> None:
        reply = route(catalog, message.payload, message.text)
        log.info("from_id=%s -> %s", message.from_id, reply.keyboard.value)
        await message.answer(reply.text, keyboard=keyboards.get(reply.keyboard))

    return labeler
