"""
Shared value formatting functions for IRS form PDF rendering.

Used by both the coordinate-overlay renderer and the AcroForm filler.
"""

from decimal import Decimal, InvalidOperation


def format_currency(value: str) -> str:
    """Format a numeric string as currency for display on the form."""
    if not value or value.strip() == "":
        return ""
    try:
        d = Decimal(value)
    except InvalidOperation:
        return value
    if d == 0:
        return ""
    # Negative amounts in parentheses per IRS convention
    if d < 0:
        return f"({abs(d):,.0f})"
    return f"{d:,.0f}"


def format_value(value: str, field_type: str) -> str:
    """Format a field value based on its type."""
    if field_type == "currency":
        return format_currency(value)
    if field_type == "boolean":
        return "X" if value.lower() in ("true", "yes", "1", "x") else ""
    if field_type == "percentage":
        if not value:
            return ""
        try:
            return f"{Decimal(value):.1f}%"
        except InvalidOperation:
            return value
    # text, integer — return as-is
    return value


def expand_yes_no(field_values: dict[str, tuple[str, str]]) -> None:
    """Expand Schedule B boolean fields into _yes / _no coordinate keys.

    The coordinate map uses suffixed keys (e.g. B3_yes, B3_no) so the "X"
    lands in the correct column.  This mutates *field_values* in place:

    - B3 = ("true", "boolean")  -> B3_yes = ("X", "text")
    - B3 = ("false", "boolean") -> B3_no  = ("X", "text")

    Non-boolean B-lines (like B8 currency) are left unchanged.
    """
    to_expand = [
        (k, v) for k, v in field_values.items()
        if k.startswith("B") and v[1] == "boolean"
    ]
    for key, (value, _ftype) in to_expand:
        del field_values[key]
        if value.lower() in ("true", "yes", "1", "x"):
            field_values[f"{key}_yes"] = ("X", "text")
        else:
            field_values[f"{key}_no"] = ("X", "text")


def is_truthy(value: str) -> bool:
    """Check if a string value represents a truthy boolean."""
    return value.lower() in ("true", "yes", "1", "x") if value else False
