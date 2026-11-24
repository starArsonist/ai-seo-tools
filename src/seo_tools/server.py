"""MCP-сервер: описания инструментов и разбор аргументов.

Вся работа с API лежит в gsc.py, webmaster.py и wordstat.py. Здесь только
проводка. В stdout ничего не печатать: это канал протокола.
"""
from __future__ import annotations

from functools import cache
from typing import Any, Literal

from mcp.server.mcpserver import MCPServer

from . import __version__
from .config import Settings
from .gsc import DATA_LAG_DAYS, SearchConsole, find_cannibalization
from .periods import WordstatPeriod, date_range, wordstat_window
from .reports import package
from .webmaster import Webmaster
from .wordstat import Wordstat

Dimension = Literal["query", "page", "date", "country", "device", "searchAppearance"]
Device = Literal["DEVICE_ALL", "DEVICE_DESKTOP", "DEVICE_PHONE", "DEVICE_TABLET"]

mcp = MCPServer(
    name="seo",
    version=__version__,
    instructions=(
        "Поисковые данные по сайтам пользователя: Google Search Console (gsc_*), "
        "Яндекс.Вебмастер (ya_*) и Вордстат (wordstat_*). Всё только на чтение. "
        "Сайт можно передавать доменом (example.ru). Перед правками title/H1 "
        "вызывай gsc_cannibalization. Большие выгрузки сохраняй через save_csv=true "
        "и читай файл."
    ),
)


@cache
def settings() -> Settings:
    return Settings.load()


@cache
def gsc() -> SearchConsole:
    return SearchConsole(settings())


@cache
def webmaster() -> Webmaster:
    return Webmaster(settings())


@cache
def wordstat() -> Wordstat:
    return Wordstat(settings())


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(value, high))


# ---------- Google Search Console ----------

@mcp.tool()
def gsc_sites() -> list[dict]:
    """Ресурсы Google Search Console, доступные сервисному аккаунту, и уровень доступа."""
    return gsc().properties


@mcp.tool()
def gsc_query(
    site: str,
    dimensions: list[Dimension] = ["query"],
    days: int = 28,
    start_date: str | None = None,
    end_date: str | None = None,
    query_contains: str | None = None,
    query_regex: str | None = None,
    page_contains: str | None = None,
    country: str | None = None,
    device: Literal["DESKTOP", "MOBILE", "TABLET"] | None = None,
    search_type: Literal["web", "image", "video", "news", "discover"] = "web",
    row_limit: int = 500,
    save_csv: bool = False,
) -> dict:
    """Search Analytics: клики, показы, CTR (%), средняя позиция.

    dimensions=["page","query"] даёт связку страница-запрос. Даты YYYY-MM-DD; без дат
    берётся `days` дней, заканчивая 3 днями назад (задержка данных GSC).
    country: ISO-3166 alpha-3 (rus, blr, kaz). row_limit до 100000.
    save_csv=true пишет всё в CSV и возвращает путь и первые 50 строк.
    """
    site_url = gsc().resolve(site)
    start, end = date_range(days, start_date, end_date, lag=DATA_LAG_DAYS)
    filters = [
        {"dimension": dim, "operator": op, "expression": expr}
        for dim, op, expr in (
            ("query", "contains", query_contains),
            ("query", "includingRegex", query_regex),
            ("page", "contains", page_contains),
            ("country", "equals", country.lower() if country else None),
            ("device", "equals", device),
        ) if expr
    ]
    body: dict[str, Any] = {"startDate": start, "endDate": end,
                            "dimensions": list(dimensions), "type": search_type}
    if filters:
        body["dimensionFilterGroups"] = [{"groupType": "and", "filters": filters}]
    rows = gsc().search_analytics(site_url, body, _clamp(row_limit, 1, 100_000))
    return {"site": site_url, "period": [start, end],
            **package(rows, save=save_csv, reports_dir=settings().reports_dir,
                      site=site_url, name="gsc_" + "_".join(dimensions))}


@mcp.tool()
def gsc_cannibalization(
    site: str,
    days: int = 90,
    query_contains: str | None = None,
    min_impressions: int = 10,
    max_position: float = 20,
    limit: int = 200,
) -> dict:
    """Запросы, по которым в Google видны 2+ страницы сайта (каннибализация).

    Учитываются пары страница-запрос с показами >= min_impressions и позицией <= max_position.
    Владелец запроса: страница с наибольшим числом кликов, при равенстве показов.
    Отсортировано по суммарным показам.
    """
    site_url = gsc().resolve(site)
    start, end = date_range(days, lag=DATA_LAG_DAYS)
    body: dict[str, Any] = {"startDate": start, "endDate": end, "dimensions": ["query", "page"]}
    if query_contains:
        body["dimensionFilterGroups"] = [{"filters": [
            {"dimension": "query", "operator": "contains", "expression": query_contains}]}]
    rows = gsc().search_analytics(site_url, body, 100_000)
    conflicts = find_cannibalization(rows, min_impressions=min_impressions, max_position=max_position)
    return {"site": site_url, "period": [start, end], "pairs_checked": len(rows),
            "conflicts": len(conflicts), "items": conflicts[:limit]}


@mcp.tool()
def gsc_sitemaps(site: str) -> list[dict]:
    """Sitemap-файлы в GSC: когда скачан, ошибки, предупреждения, число URL."""
    return gsc().sitemaps(gsc().resolve(site))


@mcp.tool()
def gsc_inspect_url(site: str, url: str) -> dict:
    """URL Inspection: индексирована ли страница в Google, какой canonical выбрал Google,
    мобильность, найденные rich results. Квота Google: 2000 проверок в день на ресурс."""
    return gsc().inspect(gsc().resolve(site), url)


# ---------- Яндекс.Вебмастер ----------

@mcp.tool()
def ya_hosts() -> list[dict]:
    """Сайты в Яндекс.Вебмастере: host_id, подтверждён ли, главное зеркало."""
    return [{
        "host_id": h["host_id"],
        "url": h.get("unicode_host_url") or h.get("ascii_host_url"),
        "verified": h.get("verified"),
        "main_mirror": (h.get("main_mirror") or {}).get("host_id"),
    } for h in webmaster().hosts]


@mcp.tool()
def ya_summary(site: str) -> dict:
    """Сводка Вебмастера: ИКС (sqi), страниц в поиске, исключено, загружено роботом,
    проблемы сайта и активные пункты диагностики с уровнем критичности."""
    return webmaster().summary(webmaster().resolve(site))


@mcp.tool()
def ya_search_queries(
    site: str,
    days: int = 28,
    start_date: str | None = None,
    end_date: str | None = None,
    order_by: Literal["TOTAL_SHOWS", "TOTAL_CLICKS"] = "TOTAL_SHOWS",
    device: Literal["ALL", "DESKTOP", "MOBILE_AND_TABLET", "MOBILE", "TABLET"] = "ALL",
    limit: int = 500,
    save_csv: bool = False,
) -> dict:
    """Популярные запросы сайта в Яндексе (до 3000): показы, клики, CTR, средние позиции
    показа и клика. Вебмастер хранит эти данные примерно за последние 2-3 месяца."""
    host_id = webmaster().resolve(site)
    start, end = date_range(days, start_date, end_date, lag=1)
    rows = webmaster().popular_queries(host_id, start=start, end=end, order_by=order_by,
                                       device=device, limit=_clamp(limit, 1, 3000))
    return {"host_id": host_id, "period": [start, end],
            **package(rows, save=save_csv, reports_dir=settings().reports_dir,
                      site=host_id, name="ya_queries")}


@mcp.tool()
def ya_indexing_history(site: str, days: int = 90) -> dict:
    """Яндекс по дням: сколько страниц в поиске и сколько загружено роботом по HTTP-кодам."""
    host_id = webmaster().resolve(site)
    start, end = date_range(days)
    return {"host_id": host_id, "period": [start, end],
            **webmaster().indexing_history(host_id, start=start, end=end)}


@mcp.tool()
def ya_search_events(site: str, limit: int = 100) -> list[dict]:
    """Последние страницы, которые появились в поиске Яндекса или выпали из него,
    с причиной исключения (дубль, неканоническая, малоценная, ошибка HTTP и т. п.)."""
    return webmaster().search_events(webmaster().resolve(site), _clamp(limit, 1, 100))


@mcp.tool()
def ya_sitemaps(site: str) -> list[dict]:
    """Sitemap-файлы, которые видит Яндекс: откуда узнал, число URL, ошибки, дата загрузки."""
    return webmaster().sitemaps(webmaster().resolve(site))


# ---------- Вордстат ----------

@mcp.tool()
def wordstat_top(
    phrase: str,
    num_phrases: int = 50,
    regions: list[int] | None = None,
    devices: list[Device] = ["DEVICE_ALL"],
) -> dict:
    """Вордстат: частотность фразы за 30 дней, вложенные запросы и похожие (associations).

    Операторы Вордстата работают: "кавычки" (только эта фраза без хвостов),
    !слово (точная форма), +предлог, -минус-слово.
    regions: id регионов Яндекса (225 Россия, 213 Москва, 2 Санкт-Петербург); без них все.
    """
    return wordstat().top(phrase, num_phrases=_clamp(num_phrases, 1, 2000),
                          regions=regions, devices=devices)


@mcp.tool()
def wordstat_dynamics(
    phrase: str,
    period: WordstatPeriod = "PERIOD_MONTHLY",
    months: int = 12,
    regions: list[int] | None = None,
    devices: list[Device] = ["DEVICE_ALL"],
) -> dict:
    """Вордстат: динамика частотности по месяцам, неделям или дням (сезонность).
    Для PERIOD_DAILY берётся не больше 60 последних дней."""
    start, end = wordstat_window(period, months)
    return wordstat().dynamics(phrase, period=period, start=start, end=end,
                               regions=regions, devices=devices)


@mcp.tool()
def wordstat_regions(
    phrase: str,
    region_type: Literal["REGION_ALL", "REGION_CITIES", "REGION_REGIONS"] = "REGION_REGIONS",
    devices: list[Device] = ["DEVICE_ALL"],
    limit: int = 30,
) -> dict:
    """Вордстат: спрос на фразу по регионам или городам. affinity больше 100 означает,
    что в регионе фразу ищут чаще, чем в среднем."""
    return wordstat().regions(phrase, region_type=region_type, devices=devices,
                              limit=_clamp(limit, 1, 500))


def main() -> None:
    mcp.run("stdio")


if __name__ == "__main__":
    main()
