"""Загрузка настроек из .env. Значение токена никогда не логируется."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
DEFAULT_CATALOG_PATH = BASE_DIR / "data" / "services.json"
TOKEN_VAR = "VK_GROUP_TOKEN"
PLACEHOLDER = "your_token_here"


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    # repr=False — токен не попадёт в логи даже при выводе объекта целиком.
    vk_token: str = field(repr=False)
    catalog_path: Path = DEFAULT_CATALOG_PATH


def load_config() -> Config:
    load_dotenv(ENV_PATH)
    token = os.getenv(TOKEN_VAR, "").strip()
    if not token or token == PLACEHOLDER:
        raise ConfigError(
            f"Не задан {TOKEN_VAR}. Скопируйте .env.example в .env и укажите токен сообщества."
        )
    return Config(vk_token=token)
