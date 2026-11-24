"""Tests for the recommendation rule (no database needed)."""

from datetime import date, timedelta

from app.recommend import recommend_quantity

MONDAY = date(2026, 11, 2)


def week(prepared, sold):
    """7 days of history, Monday to Sunday, with the same numbers every day."""
    return [{"date": MONDAY + timedelta(days=i), "prepared": prepared[i], "sold": sold[i]} for i in range(7)]


def test_steady_demand_gives_the_average():
    quantity, basis = recommend_quantity(week([50] * 7, [40] * 7), MONDAY + timedelta(days=7))
    assert quantity == 40
    assert "7-day weighted avg 40.0" in basis


def test_recent_days_count_more():
    # older days sold 10, newest sold 70: plain average 18.6, weighted (10x21 + 70x7) / 28 = 25.0
    _, basis = recommend_quantity(week([80] * 7, [10] * 6 + [70]), MONDAY + timedelta(days=7))
    assert "7-day weighted avg 25.0" in basis


def test_high_waste_reduces_by_10_percent():
    quantity, basis = recommend_quantity(week([60] * 7, [40] * 7), MONDAY + timedelta(days=7))
    assert quantity == 36                       # 40 x 0.9
    assert "-10%" in basis


def test_frequent_sell_outs_increase_by_10_percent():
    quantity, basis = recommend_quantity(week([40] * 7, [40] * 7), MONDAY + timedelta(days=7))
    assert quantity == 44                       # 40 x 1.1
    assert "+10%" in basis


def test_quiet_weekday_gets_less():
    sold = [50, 50, 50, 50, 50, 20, 10]         # quiet weekend
    quantity, basis = recommend_quantity(week([60] * 7, sold), MONDAY + timedelta(days=13))   # a Sunday
    assert quantity < 15
    assert "Sunday factor" in basis


def test_no_history():
    assert recommend_quantity([], MONDAY) == (0, "No sales history.")
