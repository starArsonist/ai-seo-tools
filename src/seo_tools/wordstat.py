"""Вордстат через Yandex Cloud Search API v2.

Старый api.wordstat.yandex.net больше не отвечает, поэтому только облачный вариант.
"""
from __future__ import annotations

import datetime as dt

from . import http
from .config import Settings
from .errors import SeoToolsError
from .periods import WordstatPeriod

API = "https://searchapi.api.cloud.yandex.net/v2/wordstat"
HINT = "Нужен API-ключ сервисного аккаунта Yandex Cloud с ролью search-api.webSearch.user (см. README)."


def _phrases(items: list[dict] | None) -> list[dict]:
    return [{"phrase": x["phrase"], "count": int(x["count"])} for x in items or []]


class Wordstat:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _post(self, method: str, body: dict) -> dict:
        key = self.settings.require("YANDEX_CLOUD_API_KEY", HINT)
        folder = self.settings.require("YANDEX_CLOUD_FOLDER_ID", "Укажи id каталога Yandex Cloud.")
        r = http.request(f"{API}/{method}", headers={"Authorization": f"Api-Key {key}"},
                         body={**body, "folderId": folder})
        if r.status in (401, 403):
            raise SeoToolsError(f"Вордстат {r.status}: доступ запрещён. {HINT}")
        if not r.ok:
            raise SeoToolsError(f"Вордстат {r.status}: {r.text[:400]}")
        return r.json()

    @staticmethod
    def _filters(regions: list[int] | None, devices: list[str]) -> dict:
        body: dict = {"devices": list(devices)}
        if regions:
            body["regions"] = [str(r) for r in regions]
        return body

    def top(self, phrase: str, *, num_phrases: int, regions: list[int] | None, devices: list[str]) -> dict:
        r = self._post("topRequests", {"phrase": phrase, "numPhrases": num_phrases,
                                       **self._filters(regions, devices)})
        return {"phrase": phrase, "total": int(r.get("totalCount", 0)),
                "top": _phrases(r.get("results")), "associations": _phrases(r.get("associations"))}

    def dynamics(self, phrase: str, *, period: WordstatPeriod, start: dt.date, end: dt.date,
                 regions: list[int] | None, devices: list[str]) -> dict:
        r = self._post("dynamics", {"phrase": phrase, "period": period,
                                    "fromDate": f"{start}T00:00:00Z", "toDate": f"{end}T00:00:00Z",
                                    **self._filters(regions, devices)})
        return {"phrase": phrase, "period": period, "from": str(start), "to": str(end),
                "points": [{"date": p["date"][:10], "count": int(p["count"]), "share": p.get("share")}
                           for p in r.get("results", [])]}

    def regions(self, phrase: str, *, region_type: str, devices: list[str], limit: int) -> dict:
        r = self._post("regions", {"phrase": phrase, "region": region_type, "devices": list(devices)})
        items = [{"region_id": x.get("region"), "count": int(x.get("count", 0)),
                  "share": x.get("share"), "affinity": x.get("affinityIndex")}
                 for x in r.get("results", [])]
        items.sort(key=lambda x: x["count"], reverse=True)
        return {"phrase": phrase, "region_type": region_type, "items": items[:limit]}
