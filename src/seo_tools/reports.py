"""Сохранение выгрузок в CSV: reports/<домен>/<дата>/<имя>.csv."""
from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path

from .sites import bare_domain

PREVIEW_ROWS = 50


def save_rows(reports_dir: Path, site: str, name: str, rows: list[dict]) -> Path:
    folder = reports_dir / bare_domain(site) / str(dt.date.today())
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.csv"
    fields: list[str] = []
    for row in rows:
        fields.extend(k for k in row if k not in fields)
    with path.open("w", encoding="utf-8-sig", newline="") as f:  # BOM: Excel откроет кириллицу
        writer = csv.DictWriter(f, fieldnames=fields or ["empty"])
        writer.writeheader()
        writer.writerows(rows)
    return path


def package(rows: list[dict], *, save: bool, reports_dir: Path, site: str, name: str) -> dict:
    """Вернуть строки целиком или сохранить в CSV и вернуть путь с превью."""
    if not save:
        return {"count": len(rows), "rows": rows}
    path = save_rows(reports_dir, site, name, rows)
    return {"count": len(rows), "saved_to": str(path), "preview": rows[:PREVIEW_ROWS]}
