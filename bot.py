"""Точка входа: запуск VK-бота через Group LongPoll."""

from __future__ import annotations

import logging
import sys

from app.catalog import CatalogError, load_catalog
from app.config import ConfigError, load_config


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    log = logging.getLogger("bot")

    try:
        config = load_config()
        catalog = load_catalog(config.catalog_path)
    except (ConfigError, CatalogError) as exc:
        log.error("%s", exc)
        sys.exit(1)

    if catalog.is_empty:
        log.warning("Каталог услуг пуст — бот будет сообщать об этом пользователям.")

    # vkbottle импортируется после проверки настроек, чтобы ошибки конфигурации
    # были понятны даже без установленных зависимостей.
    from vkbottle.bot import Bot

    from app.handlers import build_labeler

    bot = Bot(token=config.vk_token, labeler=build_labeler(catalog))
    log.info("Бот запущен, услуг в каталоге: %d. Остановка — Ctrl+C.", len(catalog.services))
    bot.run()


if __name__ == "__main__":
    main()
