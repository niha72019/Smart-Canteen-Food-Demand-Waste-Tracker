"""Checks for form input: each returns the cleaned value or raises ValueError."""

from datetime import date


def check_text(value, field, max_length=100):
    """Non-empty text of at most max_length characters, without extra spaces."""
    value = str(value).strip()
    if not value:
        raise ValueError(f"{field} is required.")
    if len(value) > max_length:
        raise ValueError(f"{field} must be at most {max_length} characters.")
    return value


def check_quantity(value, field):
    """A whole number that is 0 or more."""
    try:
        number = int(str(value).strip())
    except ValueError:
        raise ValueError(f"{field} must be a whole number.") from None
    if number < 0:
        raise ValueError(f"{field} cannot be negative.")
    return number


def check_price(value, field):
    """A money amount that is 0 or more, rounded to 2 decimals."""
    try:
        number = float(str(value).strip())
    except ValueError:
        raise ValueError(f"{field} must be a number.") from None
    if number < 0:
        raise ValueError(f"{field} cannot be negative.")
    return round(number, 2)


def check_date(value, field="Date"):
    """A date written as YYYY-MM-DD."""
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError:
        raise ValueError(f"{field} must be a date like 2026-11-24.") from None


def check_sold(prepared, sold):
    """Quantity sold cannot be more than quantity prepared."""
    if sold > prepared:
        raise ValueError("Quantity sold cannot be more than quantity prepared.")
