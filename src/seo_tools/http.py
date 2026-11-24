"""Минимальный JSON-клиент на urllib, чтобы не тянуть лишних зависимостей."""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

USER_AGENT = "seo-tools-mcp/0.1"


@dataclass
class Response:
    status: int
    text: str

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

    def json(self) -> Any:
        return json.loads(self.text) if self.text else {}


def request(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: Any = None,
    body: dict | None = None,
    form: dict | None = None,
    timeout: float = 60,
) -> Response:
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    hdrs = {"User-Agent": USER_AGENT, **(headers or {})}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
    elif form is not None:
        data = urllib.parse.urlencode(form).encode("utf-8")
        hdrs["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=data, headers=hdrs, method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return Response(r.status, r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return Response(e.code, e.read().decode("utf-8", errors="replace"))
