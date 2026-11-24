"""Приведение адресов сайтов к одному виду.

GSC знает сайт как `sc-domain:example.ru` или `https://example.ru/`,
Вебмастер как `https:example.ru:443`. Пользователь пишет `example.ru`.
"""
from __future__ import annotations

_PREFIXES = ("sc-domain:", "https://", "http://", "https:", "http:")


def bare_domain(site: str) -> str:
    """`https://www.Example.ru/path` → `example.ru`; `https:example.ru:443` → `example.ru`."""
    s = site.strip().lower()
    for prefix in _PREFIXES:
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    s = s.split("/", 1)[0]
    if ":" in s and s.rsplit(":", 1)[1].isdigit():
        s = s.rsplit(":", 1)[0]
    return s.removeprefix("www.")


def pick_gsc_property(site: str, properties: list[str]) -> str:
    """Выбрать ресурс GSC под домен. Доменный ресурс полнее URL-префикса, он в приоритете."""
    if site in properties:
        return site
    want = bare_domain(site)
    matches = [p for p in properties if bare_domain(p) == want]
    if not matches:
        raise LookupError(want)
    return sorted(matches, key=lambda p: (not p.startswith("sc-domain:"), not p.startswith("https")))[0]


def pick_webmaster_host(site: str, hosts: list[dict]) -> str:
    """Выбрать host_id Вебмастера: сначала https и подтверждённый."""
    if any(h.get("host_id") == site for h in hosts):
        return site
    want = bare_domain(site)
    matches = [
        h for h in hosts
        if want in {bare_domain(h.get("host_id", "")),
                    bare_domain(h.get("ascii_host_url") or ""),
                    bare_domain(h.get("unicode_host_url") or "")}
    ]
    if not matches:
        raise LookupError(want)
    matches.sort(key=lambda h: (not h["host_id"].startswith("https"), not h.get("verified")))
    return matches[0]["host_id"]
