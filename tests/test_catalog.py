"""Тесты каталога и форматирования цен. Не требуют vkbottle и токена."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from app.catalog import (
    NBSP,
    Catalog,
    CatalogError,
    format_price,
    format_price_list,
    format_service_card,
    load_catalog,
    parse_catalog,
)

CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "services.json"

VALID_ITEM = {
    "id": "test_service",
    "title": "Тестовая услуга",
    "price_from": 1000,
    "currency": "₽",
    "description": "Описание.",
}


def with_item(**changes):
    item = copy.deepcopy(VALID_ITEM)
    item.update(changes)
    return {"services": [item]}


class FormatPriceTests(unittest.TestCase):
    def test_thousands(self):
        self.assertEqual(format_price(15000), f"от{NBSP}15{NBSP}000{NBSP}₽")

    def test_small_and_large(self):
        self.assertEqual(format_price(500), f"от{NBSP}500{NBSP}₽")
        self.assertEqual(format_price(1250000), f"от{NBSP}1{NBSP}250{NBSP}000{NBSP}₽")

    def test_readable_with_regular_spaces(self):
        self.assertEqual(format_price(40000).replace(NBSP, " "), "от 40 000 ₽")

    def test_custom_currency(self):
        self.assertTrue(format_price(10, "$").endswith("$"))


class RealCatalogTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_catalog(CATALOG_PATH)

    def test_three_services_with_required_prices(self):
        prices = {s.title: s.price_from for s in self.catalog.services}
        self.assertEqual(
            prices,
            {
                "Разработка Telegram-бота": 15000,
                "Автоматизация через Make": 10000,
                "Приложение на FlutterFlow": 40000,
            },
        )

    def test_get_by_id(self):
        self.assertEqual(self.catalog.get("make_automation").price_from, 10000)
        self.assertIsNone(self.catalog.get("unknown"))
        self.assertIsNone(self.catalog.get(None))
        self.assertIsNone(self.catalog.get(123))

    def test_card_contains_description_and_price(self):
        service = self.catalog.get("telegram_bot")
        card = format_service_card(service)
        self.assertIn(service.title, card)
        self.assertIn(service.description, card)
        self.assertIn(format_price(15000), card)

    def test_price_list_contains_all_services(self):
        text = format_price_list(self.catalog)
        for service in self.catalog.services:
            self.assertIn(service.title, text)
            self.assertIn(format_price(service.price_from, service.currency), text)

    def test_no_contacts_or_guarantees_in_descriptions(self):
        for service in self.catalog.services:
            lowered = service.description.lower()
            for word in ("гарант", "+7", "@", "дней", "срок"):
                self.assertNotIn(word, lowered, f"{service.id}: '{word}'")


class EmptyCatalogTests(unittest.TestCase):
    def test_empty_list_is_allowed(self):
        catalog = parse_catalog({"services": []})
        self.assertTrue(catalog.is_empty)
        self.assertIn("пуст", format_price_list(catalog))

    def test_empty_catalog_object(self):
        self.assertTrue(Catalog(services=()).is_empty)


class InvalidCatalogTests(unittest.TestCase):
    def assertInvalid(self, data):
        with self.assertRaises(CatalogError):
            parse_catalog(data)

    def test_wrong_root(self):
        for data in (None, [], "text", 42, {}, {"services": None}, {"services": {}}):
            with self.subTest(data=data):
                self.assertInvalid(data)

    def test_item_not_object(self):
        self.assertInvalid({"services": ["строка"]})

    def test_missing_or_empty_fields(self):
        for field in ("id", "title", "currency", "description"):
            with self.subTest(field=field):
                self.assertInvalid(with_item(**{field: ""}))
                data = with_item()
                del data["services"][0][field]
                self.assertInvalid(data)

    def test_bad_price(self):
        for price in (None, "15000", -1, 15.5, True):
            with self.subTest(price=price):
                self.assertInvalid(with_item(price_from=price))

    def test_bad_id(self):
        for service_id in ("Bad Id", "кириллица", "a" * 33, "x-y"):
            with self.subTest(service_id=service_id):
                self.assertInvalid(with_item(id=service_id))

    def test_title_too_long_for_vk_button(self):
        self.assertInvalid(with_item(title="Т" * 41))

    def test_duplicate_ids(self):
        self.assertInvalid({"services": [VALID_ITEM, VALID_ITEM]})


class LoadCatalogFileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, content: str) -> Path:
        path = self.dir / "services.json"
        path.write_text(content, encoding="utf-8")
        return path

    def test_missing_file(self):
        with self.assertRaises(CatalogError):
            load_catalog(self.dir / "nope.json")

    def test_empty_file(self):
        with self.assertRaises(CatalogError):
            load_catalog(self.write("   \n"))

    def test_broken_json(self):
        with self.assertRaises(CatalogError):
            load_catalog(self.write('{"services": [}'))

    def test_valid_file(self):
        catalog = load_catalog(self.write(json.dumps({"services": [VALID_ITEM]}, ensure_ascii=False)))
        self.assertEqual(catalog.get("test_service").title, "Тестовая услуга")


if __name__ == "__main__":
    unittest.main()
