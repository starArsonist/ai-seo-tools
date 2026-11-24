"""Командная строка: проверка ключей и получение токена Яндекса.

    seo-tools doctor              проверить все источники
    seo-tools paths               где лежат ключи и отчёты
    seo-tools yandex-token        ссылка для авторизации в Яндексе
    seo-tools yandex-token КОД    обменять код на токен и записать в .env
"""
from __future__ import annotations

import argparse
import base64
import sys
import urllib.parse

from . import __version__, http
from .config import Settings, env_file, write_env_value
from .errors import SeoToolsError
from .gsc import SearchConsole
from .webmaster import Webmaster
from .wordstat import Wordstat


def _check(name: str, fn) -> bool:
    try:
        detail = fn()
        print(f"  [ok]   {name}: {detail}")
        return True
    except SeoToolsError as e:
        print(f"  [fail] {name}: {e}")
    except Exception as e:  # noqa: BLE001 — doctor должен дойти до конца
        print(f"  [fail] {name}: {type(e).__name__}: {e}")
    return False


def cmd_doctor(_: argparse.Namespace) -> int:
    s = Settings.load()
    print(f"seo-tools {__version__}, ключи: {s.home}")
    results = [
        _check("Google Search Console",
               lambda: ", ".join(p["site"] for p in SearchConsole(s).properties) or "ресурсов нет"),
        _check("Яндекс.Вебмастер",
               lambda: ", ".join(h["host_id"] for h in Webmaster(s).hosts) or "сайтов нет"),
        _check("Вордстат",
               lambda: f"«сайт» = {Wordstat(s).top('сайт', num_phrases=1, regions=None, devices=['DEVICE_ALL'])['total']} показов за 30 дней"),
    ]
    print(f"\nРаботает {sum(results)} из {len(results)}.")
    return 0 if all(results) else 1


def cmd_paths(_: argparse.Namespace) -> int:
    s = Settings.load()
    print(f"папка:    {s.home}")
    print(f".env:     {env_file()}{'' if env_file().exists() else '  (нет)'}")
    try:
        print(f"google:   {s.google_credentials()}")
    except SeoToolsError as e:
        print(f"google:   {e}")
    print(f"отчёты:   {s.reports_dir}")
    return 0


def cmd_yandex_token(args: argparse.Namespace) -> int:
    s = Settings.load()
    cid = s.require("YANDEX_CLIENT_ID", f"Добавь YANDEX_CLIENT_ID в {env_file()}.")
    secret = s.require("YANDEX_CLIENT_SECRET", f"Добавь YANDEX_CLIENT_SECRET в {env_file()}.")
    if not args.code:
        url = "https://oauth.yandex.ru/authorize?" + urllib.parse.urlencode(
            {"response_type": "code", "client_id": cid})
        print("Открой ссылку, войди и разреши доступ:\n\n" + url +
              "\n\nПотом запусти: seo-tools yandex-token <код со страницы>")
        return 0
    auth = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    r = http.request("https://oauth.yandex.ru/token", headers={"Authorization": f"Basic {auth}"},
                     form={"grant_type": "authorization_code", "code": args.code}, timeout=30)
    if not r.ok:
        print(f"Яндекс OAuth {r.status}: {r.text[:300]}", file=sys.stderr)
        return 1
    data = r.json()
    path = write_env_value("YANDEX_OAUTH_TOKEN", data["access_token"])
    days = int(data.get("expires_in", 0)) // 86400
    print(f"Токен записан в {path}, живёт {days} дн. Перезапусти сессию Claude Code, "
          "чтобы MCP-сервер его подхватил.")
    return 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # кириллица в консоли Windows
    parser = argparse.ArgumentParser(prog="seo-tools", description="Ключи и диагностика seo-tools")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="проверить все источники").set_defaults(fn=cmd_doctor)
    sub.add_parser("paths", help="где лежат ключи и отчёты").set_defaults(fn=cmd_paths)
    tok = sub.add_parser("yandex-token", help="получить OAuth-токен Яндекса")
    tok.add_argument("code", nargs="?", help="код подтверждения со страницы Яндекса")
    tok.set_defaults(fn=cmd_yandex_token)
    args = parser.parse_args(argv)
    try:
        return args.fn(args)
    except SeoToolsError as e:
        print(e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
