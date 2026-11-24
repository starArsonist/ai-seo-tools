"""Периоды для отчётов."""
from __future__ import annotations

import datetime as dt
from typing import Literal

WordstatPeriod = Literal["PERIOD_MONTHLY", "PERIOD_WEEKLY", "PERIOD_DAILY"]


def date_range(
    days: int,
    start: str | None = None,
    end: str | None = None,
    *,
    lag: int = 0,
    today: dt.date | None = None,
) -> tuple[str, str]:
    """Период длиной `days`, заканчивающийся `lag` дней назад, если даты не заданы явно.

    lag нужен из-за задержки данных: GSC отдаёт данные примерно через 2-3 дня.
    """
    today = today or dt.date.today()
    end_d = dt.date.fromisoformat(end) if end else today - dt.timedelta(days=lag)
    start_d = dt.date.fromisoformat(start) if start else end_d - dt.timedelta(days=max(days, 1) - 1)
    if start_d > end_d:
        raise ValueError(f"Начало периода {start_d} позже конца {end_d}")
    return str(start_d), str(end_d)


def wordstat_window(period: WordstatPeriod, months: int, today: dt.date | None = None) -> tuple[dt.date, dt.date]:
    """Окно для динамики Вордстата из целых периодов.

    Месяцы: с первого числа, до конца прошлого месяца.
    Недели: с понедельника, до прошлого воскресенья.
    Дни: не больше 60, до вчера (такой предел у API).
    """
    today = today or dt.date.today()
    months = max(months, 1)
    if period == "PERIOD_MONTHLY":
        end = today.replace(day=1) - dt.timedelta(days=1)
        y, m = end.year, end.month - months + 1
        while m <= 0:
            y, m = y - 1, m + 12
        return dt.date(y, m, 1), end
    if period == "PERIOD_WEEKLY":
        end = today - dt.timedelta(days=today.weekday() + 1)
        return end - dt.timedelta(weeks=months * 4) + dt.timedelta(days=1), end
    end = today - dt.timedelta(days=1)
    return end - dt.timedelta(days=min(months * 30, 60) - 1), end
