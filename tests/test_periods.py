import datetime as dt

import pytest

from seo_tools.periods import date_range, wordstat_window

TODAY = dt.date(2026, 11, 24)  # вторник


def test_date_range_default_with_lag():
    assert date_range(28, lag=3, today=TODAY) == ("2026-10-25", "2026-11-21")


def test_date_range_explicit():
    assert date_range(28, "2026-01-01", "2026-01-31", today=TODAY) == ("2026-01-01", "2026-01-31")


def test_date_range_only_end():
    assert date_range(7, end="2026-03-10", today=TODAY) == ("2026-03-04", "2026-03-10")


def test_date_range_rejects_inverted():
    with pytest.raises(ValueError):
        date_range(7, "2026-02-01", "2026-01-01")


def test_wordstat_monthly_crosses_year():
    assert wordstat_window("PERIOD_MONTHLY", 12, TODAY) == (dt.date(2025, 11, 1), dt.date(2026, 10, 31))


def test_wordstat_weekly_monday_to_sunday():
    start, end = wordstat_window("PERIOD_WEEKLY", 1, TODAY)
    assert end == dt.date(2026, 11, 22) and end.weekday() == 6
    assert start.weekday() == 0 and (end - start).days == 27


def test_wordstat_daily_capped_at_60():
    start, end = wordstat_window("PERIOD_DAILY", 12, TODAY)
    assert end == dt.date(2026, 11, 23) and (end - start).days == 59
