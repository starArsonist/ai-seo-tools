"""Где лежат ключи и отчёты.

Порядок поиска каждого значения:
1. переменная окружения (их выставляет плагин из userConfig);
2. файл `.env` в домашней папке seo-tools.

Домашняя папка: `$SEO_TOOLS_HOME`, по умолчанию `~/.seo-tools`.
Сервисный аккаунт Google: `$GOOGLE_SERVICE_ACCOUNT_FILE` или первый JSON
с `"type": "service_account"` в домашней папке.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from .errors import NotConfigured

KEYS = (
    "YANDEX_OAUTH_TOKEN",
    "YANDEX_WEBMASTER_USER_ID",
    "YANDEX_CLIENT_ID",
    "YANDEX_CLIENT_SECRET",
    "YANDEX_CLOUD_API_KEY",
    "YANDEX_CLOUD_FOLDER_ID",
    "GOOGLE_SERVICE_ACCOUNT_FILE",
    "SEO_TOOLS_REPORTS",
)


def home() -> Path:
    raw = os.environ.get("SEO_TOOLS_HOME", "").strip()
    return Path(raw).expanduser() if raw else Path.home() / ".seo-tools"


def env_file() -> Path:
    return home() / ".env"


def read_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    data: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def write_env_value(key: str, value: str) -> Path:
    """Записать или заменить одну переменную в .env, не трогая остальные."""
    path = env_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    out, done = [], False
    for line in lines:
        if line.split("=", 1)[0].strip() == key:
            out.append(f"{key}={value}")
            done = True
        else:
            out.append(line)
    if not done:
        out.append(f"{key}={value}")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return path


@dataclass(frozen=True)
class Settings:
    values: dict[str, str]
    home: Path

    @classmethod
    def load(cls) -> "Settings":
        merged = read_env_file(env_file())
        for key in KEYS:
            value = os.environ.get(key, "").strip()
            # Пустая строка или неподставленный ${user_config.*} = опция плагина
            # не заполнена, берём значение из файла.
            if value and not value.startswith("${"):
                merged[key] = value
        return cls(values=merged, home=home())

    def get(self, key: str) -> str | None:
        return self.values.get(key) or None

    def require(self, key: str, hint: str) -> str:
        value = self.get(key)
        if not value:
            raise NotConfigured(f"Не задан {key}. {hint}")
        return value

    @property
    def reports_dir(self) -> Path:
        raw = self.get("SEO_TOOLS_REPORTS")
        return Path(raw).expanduser() if raw else self.home / "reports"

    def google_credentials(self) -> Path:
        explicit = self.get("GOOGLE_SERVICE_ACCOUNT_FILE")
        if explicit:
            path = Path(explicit).expanduser()
            if not path.is_file():
                raise NotConfigured(f"Файл сервисного аккаунта не найден: {path}")
            return path
        for path in sorted(self.home.glob("*.json")):
            try:
                if json.loads(path.read_text(encoding="utf-8")).get("type") == "service_account":
                    return path
            except (OSError, ValueError):
                continue
        raise NotConfigured(
            f"Нет JSON-ключа сервисного аккаунта Google в {self.home}. "
            "Положи его туда или укажи путь в GOOGLE_SERVICE_ACCOUNT_FILE."
        )
