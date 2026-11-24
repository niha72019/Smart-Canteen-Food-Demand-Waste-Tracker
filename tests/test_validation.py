"""Tests for the form input checks."""

from datetime import date

import pytest

from app import validation


def test_valid_values_are_cleaned():
    assert validation.check_text("  Samosa ", "Name") == "Samosa"
    assert validation.check_quantity(" 40 ", "Quantity") == 40
    assert validation.check_price("15.456", "Price") == 15.46
    assert validation.check_date("2026-11-24") == date(2026, 11, 24)


@pytest.mark.parametrize("check, value, message", [
    (validation.check_text, "   ", "is required"),
    (validation.check_quantity, "abc", "whole number"),
    (validation.check_quantity, "-3", "cannot be negative"),
    (validation.check_quantity, "2.5", "whole number"),
    (validation.check_price, "ten", "must be a number"),
    (validation.check_price, "-1", "cannot be negative"),
])
def test_bad_values_are_refused(check, value, message):
    with pytest.raises(ValueError, match=message):
        check(value, "Field")


def test_bad_date_and_sold_more_than_prepared():
    with pytest.raises(ValueError, match="must be a date"):
        validation.check_date("24/11/2026")
    with pytest.raises(ValueError, match="cannot be more"):
        validation.check_sold(10, 12)
