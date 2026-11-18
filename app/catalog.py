"""Загрузка, валидация и форматирование каталога услуг.

Модуль не зависит от vkbottle, поэтому его можно тестировать без сети и токена.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Ограничение VK на длину подписи кнопки клавиатуры.
MAX_TITLE_LENGTH = 40
ID_PATTERN = re.compile(r"^[a-z0-9_]{1,32}$")
NBSP = " "


class CatalogError(Exception):
    """Каталог отсутствует, повреждён или содержит некорректные данные."""


@dataclass(frozen=True, slots=True)
class Service:
    id: str
    title: str
    price_from: int
    currency: str
    description: str


@dataclass(frozen=True, slots=True)
class Catalog:
    services: tuple[Service, ...]

    @property
    def is_empty(self) -> bool:
        return not self.services

    def get(self, service_id: Any) -> Service | None:
        if not isinstance(service_id, str):
            return None
        for service in self.services:
            if service.id == service_id:
                return service
        return None


def format_price(amount: int, currency: str = "₽") -> str:
    """15000 -> 'от 15 000 ₽' (разделители — неразрывные пробелы)."""
    grouped = f"{amount:,}".replace(",", NBSP)
    return f"от{NBSP}{grouped}{NBSP}{currency}"


def format_service_card(service: Service) -> str:
    return (
        f"{service.title}\n\n"
        f"{service.description}\n\n"
        f"Стоимость: {format_price(service.price_from, service.currency)}"
    )


def format_price_list(catalog: Catalog) -> str:
    if catalog.is_empty:
        return "Прайс-лист пока пуст. Загляните позже или напишите менеджеру."
    lines = ["Прайс-лист:", ""]
    for service in catalog.services:
        lines.append(f"• {service.title} — {format_price(service.price_from, service.currency)}")
    lines += ["", "Точная стоимость зависит от задачи и обсуждается с менеджером."]
    return "\n".join(lines)


def _require_str(item: dict[str, Any], field: str, index: int) -> str:
    value = item.get(field)
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"Услуга #{index}: поле '{field}' должно быть непустой строкой.")
    return value.strip()


def _parse_service(item: Any, index: int) -> Service:
    if not isinstance(item, dict):
        raise CatalogError(f"Услуга #{index}: ожидается объект, получено {type(item).__name__}.")

    service_id = _require_str(item, "id", index)
    if not ID_PATTERN.match(service_id):
        raise CatalogError(
            f"Услуга #{index}: id '{service_id}' должен состоять из a-z, 0-9, '_' (до 32 символов)."
        )

    title = _require_str(item, "title", index)
    if len(title) > MAX_TITLE_LENGTH:
        raise CatalogError(
            f"Услуга '{service_id}': название длиннее {MAX_TITLE_LENGTH} символов (лимит кнопки VK)."
        )

    price = item.get("price_from")
    # bool — подкласс int, поэтому исключаем его явно.
    if isinstance(price, bool) or not isinstance(price, int) or price < 0:
        raise CatalogError(f"Услуга '{service_id}': 'price_from' должно быть целым числом >= 0.")

    return Service(
        id=service_id,
        title=title,
        price_from=price,
        currency=_require_str(item, "currency", index),
        description=_require_str(item, "description", index),
    )


def parse_catalog(data: Any) -> Catalog:
    """Проверяет уже разобранный JSON и возвращает Catalog."""
    if not isinstance(data, dict):
        raise CatalogError("Корень каталога должен быть JSON-объектом с ключом 'services'.")
    raw_services = data.get("services")
    if not isinstance(raw_services, list):
        raise CatalogError("Ключ 'services' должен содержать список услуг.")

    services = tuple(_parse_service(item, i) for i, item in enumerate(raw_services, start=1))

    ids = [s.id for s in services]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise CatalogError(f"Повторяющиеся id услуг: {', '.join(duplicates)}.")

    return Catalog(services=services)


def load_catalog(path: Path) -> Catalog:
    """Читает JSON-файл каталога (UTF-8) и валидирует его."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise CatalogError(f"Файл каталога не найден: {path}") from exc
    except OSError as exc:
        raise CatalogError(f"Не удалось прочитать файл каталога: {exc}") from exc

    if not text.strip():
        raise CatalogError(f"Файл каталога пуст: {path}")

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CatalogError(f"Некорректный JSON в каталоге (строка {exc.lineno}): {exc.msg}") from exc

    return parse_catalog(data)
