"""Постоянные клавиатуры VK (one_time=False, inline=False)."""

from __future__ import annotations

from vkbottle import Keyboard, KeyboardButtonColor, Text

from app import texts
from app.catalog import Catalog
from app.router import (
    CMD_CONTACT,
    CMD_MENU,
    CMD_PRICE,
    CMD_SERVICE,
    CMD_SERVICES,
    KeyboardKind,
    make_payload,
)


def _new() -> Keyboard:
    return Keyboard(one_time=False, inline=False)


def _menu_button(kb: Keyboard) -> Keyboard:
    return kb.add(Text(texts.BTN_MENU, payload=make_payload(CMD_MENU)), color=KeyboardButtonColor.SECONDARY)


def main_menu() -> str:
    kb = (
        _new()
        .add(Text(texts.BTN_SERVICES, payload=make_payload(CMD_SERVICES)), color=KeyboardButtonColor.PRIMARY)
        .add(Text(texts.BTN_PRICE, payload=make_payload(CMD_PRICE)), color=KeyboardButtonColor.PRIMARY)
        .row()
        .add(Text(texts.BTN_CONTACT, payload=make_payload(CMD_CONTACT)), color=KeyboardButtonColor.POSITIVE)
    )
    return kb.get_json()


def catalog_menu(catalog: Catalog) -> str:
    kb = _new()
    for service in catalog.services:
        kb.add(
            Text(service.title, payload=make_payload(CMD_SERVICE, id=service.id)),
            color=KeyboardButtonColor.PRIMARY,
        ).row()
    return _menu_button(kb).get_json()


def service_menu() -> str:
    kb = _new().add(
        Text(texts.BTN_BACK_TO_SERVICES, payload=make_payload(CMD_SERVICES)),
        color=KeyboardButtonColor.SECONDARY,
    )
    return _menu_button(kb).get_json()


def back_menu() -> str:
    return _menu_button(_new()).get_json()


class KeyboardSet:
    """Клавиатуры строятся один раз при запуске — каталог не меняется во время работы."""

    def __init__(self, catalog: Catalog) -> None:
        self._by_kind = {
            KeyboardKind.MAIN: main_menu(),
            KeyboardKind.CATALOG: catalog_menu(catalog),
            KeyboardKind.SERVICE: service_menu(),
            KeyboardKind.BACK: back_menu(),
        }

    def get(self, kind: KeyboardKind) -> str:
        return self._by_kind[kind]
