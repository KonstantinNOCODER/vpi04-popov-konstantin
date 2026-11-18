"""Тесты маршрутизации payload/текста. Не требуют vkbottle и токена."""

import unittest
from pathlib import Path

from app import texts
from app.catalog import Catalog, format_price, load_catalog
from app.router import (
    CMD_CONTACT,
    CMD_MENU,
    CMD_PRICE,
    CMD_SERVICE,
    CMD_SERVICES,
    KeyboardKind,
    is_incoming_user_message,
    make_payload,
    parse_payload,
    payload_to_json,
    route,
)

CATALOG = load_catalog(Path(__file__).resolve().parent.parent / "data" / "services.json")
EMPTY = Catalog(services=())


def press(cmd, catalog=CATALOG, **extra):
    return route(catalog, payload_to_json(make_payload(cmd, **extra)), "любой текст")


class ParsePayloadTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(parse_payload('{"cmd":"menu"}'), {"cmd": "menu"})
        self.assertEqual(parse_payload({"cmd": "menu"}), {"cmd": "menu"})

    def test_invalid_or_missing(self):
        for raw in (None, "", "   ", "not json", "[1,2]", '"str"', "123", 5, '{"cmd":'):
            with self.subTest(raw=raw):
                self.assertIsNone(parse_payload(raw))


class ButtonRoutingTests(unittest.TestCase):
    def test_menu(self):
        reply = press(CMD_MENU)
        self.assertEqual((reply.text, reply.keyboard), (texts.MAIN_MENU, KeyboardKind.MAIN))

    def test_vk_start_button(self):
        reply = route(CATALOG, '{"command":"start"}', "Начать")
        self.assertEqual((reply.text, reply.keyboard), (texts.WELCOME, KeyboardKind.MAIN))

    def test_services(self):
        self.assertEqual(press(CMD_SERVICES).keyboard, KeyboardKind.CATALOG)

    def test_each_service(self):
        for service in CATALOG.services:
            with self.subTest(service=service.id):
                reply = press(CMD_SERVICE, id=service.id)
                self.assertEqual(reply.keyboard, KeyboardKind.SERVICE)
                self.assertIn(service.description, reply.text)
                self.assertIn(format_price(service.price_from, service.currency), reply.text)

    def test_unknown_service_id(self):
        reply = press(CMD_SERVICE, id="deleted_service")
        self.assertEqual((reply.text, reply.keyboard), (texts.SERVICE_NOT_FOUND, KeyboardKind.CATALOG))

    def test_service_without_id(self):
        self.assertEqual(press(CMD_SERVICE).text, texts.SERVICE_NOT_FOUND)
        self.assertEqual(route(CATALOG, '{"cmd":"service","id":42}', None).text, texts.SERVICE_NOT_FOUND)

    def test_price(self):
        reply = press(CMD_PRICE)
        self.assertEqual(reply.keyboard, KeyboardKind.BACK)
        for service in CATALOG.services:
            self.assertIn(service.title, reply.text)

    def test_contact(self):
        reply = press(CMD_CONTACT)
        self.assertEqual((reply.text, reply.keyboard), (texts.CONTACT, KeyboardKind.BACK))


class FallbackTests(unittest.TestCase):
    def test_unknown_payload(self):
        for raw in ('{"cmd":"hack"}', '{"foo":"bar"}', '{"cmd":123}', "broken{", "[]"):
            with self.subTest(raw=raw):
                reply = route(CATALOG, raw, None)
                self.assertEqual((reply.text, reply.keyboard), (texts.UNKNOWN, KeyboardKind.MAIN))

    def test_free_text(self):
        for text in ("Сколько стоит сайт?", "", None, "   "):
            with self.subTest(text=text):
                self.assertEqual(route(CATALOG, None, text).text, texts.UNKNOWN)

    def test_text_synonyms(self):
        self.assertEqual(route(CATALOG, None, "  Начать ").text, texts.WELCOME)
        self.assertEqual(route(CATALOG, None, "УСЛУГИ").keyboard, KeyboardKind.CATALOG)
        self.assertEqual(route(CATALOG, None, "прайс").keyboard, KeyboardKind.BACK)
        self.assertEqual(route(CATALOG, None, "менеджер").text, texts.CONTACT)


class EmptyCatalogRoutingTests(unittest.TestCase):
    def test_services_on_empty_catalog(self):
        reply = press(CMD_SERVICES, catalog=EMPTY)
        self.assertEqual((reply.text, reply.keyboard), (texts.CATALOG_EMPTY, KeyboardKind.BACK))

    def test_service_on_empty_catalog(self):
        self.assertEqual(press(CMD_SERVICE, catalog=EMPTY, id="telegram_bot").keyboard, KeyboardKind.BACK)

    def test_price_on_empty_catalog(self):
        self.assertIn("пуст", press(CMD_PRICE, catalog=EMPTY).text)


class IncomingFilterTests(unittest.TestCase):
    def test_user_incoming(self):
        self.assertTrue(is_incoming_user_message(0, 12345))
        self.assertTrue(is_incoming_user_message(None, 12345))

    def test_outgoing_or_from_group(self):
        self.assertFalse(is_incoming_user_message(1, 12345))
        self.assertFalse(is_incoming_user_message(0, -123456))
        self.assertFalse(is_incoming_user_message(0, 0))
        self.assertFalse(is_incoming_user_message(0, None))
        self.assertFalse(is_incoming_user_message(0, True))


class VkLimitsTests(unittest.TestCase):
    def test_payloads_fit_vk_limit(self):
        payloads = [make_payload(c) for c in (CMD_MENU, CMD_SERVICES, CMD_PRICE, CMD_CONTACT)]
        payloads += [make_payload(CMD_SERVICE, id=s.id) for s in CATALOG.services]
        for payload in payloads:
            payload_to_json(payload)  # бросает ValueError при превышении 255 символов

    def test_oversized_payload_rejected(self):
        with self.assertRaises(ValueError):
            payload_to_json(make_payload(CMD_SERVICE, id="x" * 300))

    def test_button_labels_fit_vk_limit(self):
        labels = [texts.BTN_SERVICES, texts.BTN_PRICE, texts.BTN_CONTACT, texts.BTN_MENU, texts.BTN_BACK_TO_SERVICES]
        labels += [s.title for s in CATALOG.services]
        for label in labels:
            self.assertLessEqual(len(label), 40, label)


if __name__ == "__main__":
    unittest.main()
