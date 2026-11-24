"""Яндекс.Вебмастер API v4 (только чтение)."""
from __future__ import annotations

from functools import cached_property
from typing import Any

from . import http
from .config import Settings
from .errors import SeoToolsError
from .sites import pick_webmaster_host

API = "https://api.webmaster.yandex.net/v4"
TOKEN_HINT = "Получи токен: seo-tools yandex-token (см. README, раздел «Ключи»)."
QUERY_INDICATORS = ("TOTAL_SHOWS", "TOTAL_CLICKS", "AVG_SHOW_POSITION", "AVG_CLICK_POSITION")


def _round(value: Any) -> float | None:
    return round(value, 1) if isinstance(value, (int, float)) else None


def normalize_query(raw: dict) -> dict:
    ind = raw.get("indicators", {})
    shows = ind.get("TOTAL_SHOWS") or 0
    clicks = ind.get("TOTAL_CLICKS") or 0
    return {
        "query": raw.get("query_text"),
        "shows": shows,
        "clicks": clicks,
        "ctr": round(clicks / shows * 100, 2) if shows else 0.0,
        "avg_show_position": _round(ind.get("AVG_SHOW_POSITION")),
        "avg_click_position": _round(ind.get("AVG_CLICK_POSITION")),
    }


class Webmaster:
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def _headers(self) -> dict[str, str]:
        token = self.settings.require("YANDEX_OAUTH_TOKEN", TOKEN_HINT)
        return {"Authorization": f"OAuth {token}"}

    def _get(self, url: str, params: Any = None) -> dict:
        r = http.request(url, headers=self._headers, params=params, timeout=40)
        if r.status == 401:
            raise SeoToolsError(f"Токен Яндекса недействителен или истёк. {TOKEN_HINT}")
        if r.status == 404 and "HOST_NOT_LOADED" in r.text:
            raise SeoToolsError("Яндекс ещё не загрузил данные по этому хосту (HOST_NOT_LOADED): "
                                "сайт недавно добавлен в Вебмастер, данных пока нет.")
        if not r.ok:
            raise SeoToolsError(f"Вебмастер {r.status}: {r.text[:300]}")
        return r.json()

    @cached_property
    def user_id(self) -> str:
        return self.settings.get("YANDEX_WEBMASTER_USER_ID") or str(self._get(f"{API}/user")["user_id"])

    def get(self, path: str, params: Any = None) -> dict:
        return self._get(f"{API}/user/{self.user_id}{path}", params)

    @cached_property
    def hosts(self) -> list[dict]:
        return self.get("/hosts").get("hosts", [])

    def resolve(self, site: str) -> str:
        try:
            return pick_webmaster_host(site, self.hosts)
        except LookupError:
            raise SeoToolsError(f"Хост {site} не найден в Вебмастере. Доступны: "
                                + (", ".join(h["host_id"] for h in self.hosts) or "ничего")) from None

    def summary(self, host_id: str) -> dict:
        summary = self.get(f"/hosts/{host_id}/summary")
        diagnostics = self.get(f"/hosts/{host_id}/diagnostics").get("problems") or {}
        present = {k: v for k, v in diagnostics.items() if isinstance(v, dict) and v.get("state") == "PRESENT"}
        return {"host_id": host_id, **summary, "diagnostics_present": present}

    def popular_queries(self, host_id: str, *, start: str, end: str, order_by: str,
                        device: str, limit: int) -> list[dict]:
        rows: list[dict] = []
        while len(rows) < limit:
            page_size = min(500, limit - len(rows))
            params = [("order_by", order_by), ("device_type_indicator", device),
                      ("date_from", start), ("date_to", end),
                      ("offset", len(rows)), ("limit", page_size)]
            params += [("query_indicator", q) for q in QUERY_INDICATORS]
            batch = self.get(f"/hosts/{host_id}/search-queries/popular", params).get("queries", [])
            rows.extend(normalize_query(q) for q in batch)
            if len(batch) < page_size:
                break
        return rows

    def indexing_history(self, host_id: str, *, start: str, end: str) -> dict:
        params = {"date_from": f"{start}T00:00:00+03:00", "date_to": f"{end}T23:59:59+03:00"}
        in_search = self.get(f"/hosts/{host_id}/search-urls/in-search/history", params).get("history", [])
        crawl = self.get(f"/hosts/{host_id}/indexing/history", params).get("indicators", {})
        point = lambda h: {"date": h["date"][:10], "pages": h["value"]}
        return {
            "in_search": [point(h) for h in in_search],
            "crawled_by_status": {status: [point(h) for h in hist] for status, hist in crawl.items()},
        }

    def search_events(self, host_id: str, limit: int) -> list[dict]:
        samples = self.get(f"/hosts/{host_id}/search-urls/events/samples",
                           {"offset": 0, "limit": limit}).get("samples", [])
        return [{
            "url": s.get("url"),
            "event": s.get("event"),
            "date": (s.get("event_date") or "")[:10],
            "title": s.get("title"),
            "excluded_status": s.get("excluded_url_status"),
            "http_code": s.get("bad_http_status"),
            "target_url": s.get("target_url"),
        } for s in samples]

    def sitemaps(self, host_id: str) -> list[dict]:
        return [{
            "url": m.get("sitemap_url"),
            "sources": m.get("sources"),
            "urls": m.get("urls_count"),
            "errors": m.get("errors_count"),
            "last_access": m.get("last_access_date"),
            "type": m.get("sitemap_type"),
        } for m in self.get(f"/hosts/{host_id}/sitemaps").get("sitemaps", [])]
