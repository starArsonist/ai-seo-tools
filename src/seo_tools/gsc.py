"""Google Search Console через сервисный аккаунт (только чтение)."""
from __future__ import annotations

from collections import defaultdict
from functools import cached_property
from typing import Any

from .config import Settings
from .errors import SeoToolsError
from .sites import pick_gsc_property

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
MAX_ROWS = 25_000  # предел одного запроса Search Analytics
DATA_LAG_DAYS = 3


def normalize_row(raw: dict, dimensions: list[str]) -> dict:
    row = dict(zip(dimensions, raw.get("keys", [])))
    row.update(
        clicks=raw.get("clicks", 0),
        impressions=raw.get("impressions", 0),
        ctr=round(raw.get("ctr", 0) * 100, 2),
        position=round(raw.get("position", 0), 1),
    )
    return row


def find_cannibalization(rows: list[dict], *, min_impressions: int, max_position: float) -> list[dict]:
    """Запросы, по которым видны 2+ страницы. Строки должны содержать query и page.

    Владелец запроса: страница с наибольшим числом кликов, при равенстве показов.
    """
    by_query: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r["impressions"] >= min_impressions and r["position"] <= max_position:
            by_query[r["query"]].append(r)
    conflicts = []
    for query, pages in by_query.items():
        if len(pages) < 2:
            continue
        pages.sort(key=lambda p: (p["clicks"], p["impressions"]), reverse=True)
        conflicts.append({
            "query": query,
            "total_impressions": sum(p["impressions"] for p in pages),
            "total_clicks": sum(p["clicks"] for p in pages),
            "owner": pages[0]["page"],
            "pages": [{k: p[k] for k in ("page", "clicks", "impressions", "position")} for p in pages],
        })
    conflicts.sort(key=lambda c: c["total_impressions"], reverse=True)
    return conflicts


class SearchConsole:
    def __init__(self, settings: Settings):
        self.settings = settings

    @cached_property
    def _api(self):
        # Импорт здесь: без ключа Google остальные инструменты должны работать.
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        creds = service_account.Credentials.from_service_account_file(
            str(self.settings.google_credentials()), scopes=SCOPES)
        return build("searchconsole", "v1", credentials=creds, cache_discovery=False)

    @staticmethod
    def _run(request) -> dict:
        from googleapiclient.errors import HttpError

        try:
            return request.execute()
        except HttpError as e:
            reason = e._get_reason() if hasattr(e, "_get_reason") else str(e)
            if e.resp.status == 403:
                reason += (" Проверь, что сервисный аккаунт добавлен пользователем "
                           "этого ресурса в Search Console.")
            raise SeoToolsError(f"GSC {e.resp.status}: {reason}") from None

    @cached_property
    def properties(self) -> list[dict]:
        entries = self._run(self._api.sites().list()).get("siteEntry", [])
        return [{"site": s["siteUrl"], "permission": s["permissionLevel"]} for s in entries]

    def resolve(self, site: str) -> str:
        urls = [p["site"] for p in self.properties]
        try:
            return pick_gsc_property(site, urls)
        except LookupError:
            raise SeoToolsError(
                f"Сайт {site} не найден в GSC. Доступны: {', '.join(urls) or 'ничего'}") from None

    def search_analytics(self, site_url: str, body: dict[str, Any], limit: int) -> list[dict]:
        dims = body.get("dimensions", [])
        out: list[dict] = []
        start_row = 0
        while len(out) < limit:
            page_size = min(MAX_ROWS, limit - len(out))
            page = {**body, "startRow": start_row, "rowLimit": page_size}
            rows = self._run(self._api.searchanalytics().query(siteUrl=site_url, body=page)).get("rows", [])
            out.extend(normalize_row(r, dims) for r in rows)
            if len(rows) < page_size:
                break
            start_row += len(rows)
        return out

    def sitemaps(self, site_url: str) -> list[dict]:
        items = self._run(self._api.sitemaps().list(siteUrl=site_url)).get("sitemap", [])
        return [{
            "path": m["path"],
            "last_downloaded": m.get("lastDownloaded"),
            "last_submitted": m.get("lastSubmitted"),
            "pending": m.get("isPending"),
            "errors": int(m.get("errors", 0)),
            "warnings": int(m.get("warnings", 0)),
            "contents": [{"type": c.get("type"), "submitted": c.get("submitted")} for c in m.get("contents", [])],
        } for m in items]

    def inspect(self, site_url: str, url: str) -> dict:
        r = self._run(self._api.urlInspection().index().inspect(
            body={"inspectionUrl": url, "siteUrl": site_url, "languageCode": "ru"}))
        res = r.get("inspectionResult", {})
        idx = res.get("indexStatusResult", {})
        rich = res.get("richResultsResult", {}).get("detectedItems", [])
        return {
            "verdict": idx.get("verdict"),
            "coverage": idx.get("coverageState"),
            "indexing_state": idx.get("indexingState"),
            "robots_txt": idx.get("robotsTxtState"),
            "page_fetch": idx.get("pageFetchState"),
            "last_crawl": idx.get("lastCrawlTime"),
            "crawled_as": idx.get("crawledAs"),
            "google_canonical": idx.get("googleCanonical"),
            "user_canonical": idx.get("userCanonical"),
            "referring_urls": idx.get("referringUrls", [])[:10],
            "sitemaps": idx.get("sitemap", []),
            "mobile": res.get("mobileUsabilityResult", {}).get("verdict"),
            "rich_results": [{
                "type": d.get("richResultType"),
                "issues": [i.get("issueMessage") for item in d.get("items", []) for i in item.get("issues", [])],
            } for d in rich],
            "link": res.get("inspectionResultLink"),
        }
