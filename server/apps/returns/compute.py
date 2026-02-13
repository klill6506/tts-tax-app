"""
Computation engine for tax return calculated fields.

Each form definition has an ordered list of formulas.  The engine loads all
field values for a return, evaluates formulas in dependency order, and saves
the results back to FormFieldValue rows.

Usage:
    from apps.returns.compute import compute_return
    compute_return(tax_return)
"""

from decimal import Decimal, InvalidOperation

from .models import FormFieldValue, FormLine

ZERO = Decimal("0.00")


def _d(values: dict[str, Decimal], line: str) -> Decimal:
    """Get the Decimal value for a line, defaulting to 0."""
    return values.get(line, ZERO)


def _sum(values: dict[str, Decimal], *lines: str) -> Decimal:
    """Sum multiple lines."""
    return sum((_d(values, ln) for ln in lines), ZERO)


# ---------------------------------------------------------------------------
# 1120-S Formulas  (line_number, callable(values) -> Decimal)
# ORDER MATTERS — dependencies must come before dependents.
# ---------------------------------------------------------------------------

FORMULAS_1120S: list[tuple[str, callable]] = [
    # Schedule A — Cost of Goods Sold
    ("A6", lambda v: _sum(v, "A1", "A2", "A3", "A4", "A5")),
    ("A8", lambda v: _d(v, "A6") - _d(v, "A7")),

    # Page 1 — Income  (Line 2 = Schedule A line 8)
    ("2", lambda v: _d(v, "A8")),
    ("1c", lambda v: _d(v, "1a") - _d(v, "1b")),
    ("3", lambda v: _d(v, "1c") - _d(v, "2")),
    ("6", lambda v: _d(v, "3") + _d(v, "4") + _d(v, "5")),

    # Page 1 — Deductions
    ("20", lambda v: _sum(
        v, "7", "8", "9", "10", "11", "12", "13",
        "14", "15", "16", "17", "18", "19",
    )),
    ("21", lambda v: _d(v, "6") - _d(v, "20")),

    # Page 1 — Tax and Payments
    ("22c", lambda v: _d(v, "22a") + _d(v, "22b")),
    ("23d", lambda v: _d(v, "23a") + _d(v, "23b") + _d(v, "23c")),
    ("25", lambda v: max(ZERO, _d(v, "22c") - _d(v, "23d"))),
    ("26", lambda v: max(ZERO, _d(v, "23d") - _d(v, "22c"))),

    # Schedule L — Balance Sheet
    # Total assets = cash + AR + shareholder loans + other current
    #              + (buildings − accum depr)
    ("L14a", lambda v: _sum(v, "L1a", "L2a", "L5a", "L7a")
     + _d(v, "L9a") - _d(v, "L9b")),
    ("L14d", lambda v: _sum(v, "L1d", "L2d", "L5d", "L7d")
     + _d(v, "L9d") - _d(v, "L9e")),
    # Total liabilities & equity
    ("L27a", lambda v: _sum(
        v, "L15a", "L17a", "L18a", "L20a",
        "L21a", "L23a", "L24a", "L25a",
    )),
    ("L27d", lambda v: _sum(
        v, "L15d", "L17d", "L18d", "L20d",
        "L21d", "L23d", "L24d", "L25d",
    )),

    # Schedule M-1
    ("M1_4", lambda v: _sum(v, "M1_1", "M1_2", "M1_3a", "M1_3b")),
    ("M1_7", lambda v: _d(v, "M1_5") + _d(v, "M1_6")),
    ("M1_8", lambda v: _d(v, "M1_4") - _d(v, "M1_7")),

    # Schedule M-2
    ("M2_2", lambda v: max(ZERO, _d(v, "21"))),   # ordinary income (positive)
    ("M2_4", lambda v: max(ZERO, -_d(v, "21"))),   # loss (positive amount)
    ("M2_6", lambda v: (
        _d(v, "M2_1") + _d(v, "M2_2") + _d(v, "M2_3")
        - _d(v, "M2_4") - _d(v, "M2_5")
    )),
    ("M2_8", lambda v: _d(v, "M2_6") - _d(v, "M2_7")),
]

# Registry by form code
FORMULA_REGISTRY: dict[str, list[tuple[str, callable]]] = {
    "1120-S": FORMULAS_1120S,
}


def compute_return(tax_return) -> int:
    """
    Evaluate all computed fields on a tax return and save them.

    Returns the number of fields updated.
    """
    form_code = tax_return.form_definition.code
    formulas = FORMULA_REGISTRY.get(form_code)
    if not formulas:
        return 0

    # Load all field values into a line_number → Decimal dict
    fvs = (
        FormFieldValue.objects.filter(tax_return=tax_return)
        .select_related("form_line")
    )

    values: dict[str, Decimal] = {}
    fv_by_line: dict[str, FormFieldValue] = {}

    for fv in fvs:
        ln = fv.form_line.line_number
        fv_by_line[ln] = fv
        if fv.value:
            try:
                values[ln] = Decimal(fv.value)
            except InvalidOperation:
                values[ln] = ZERO
        else:
            values[ln] = ZERO

    # Evaluate formulas in order, updating values dict as we go
    updated = 0
    for line_number, formula_fn in formulas:
        result = formula_fn(values).quantize(Decimal("0.01"))
        values[line_number] = result  # update for downstream formulas

        fv = fv_by_line.get(line_number)
        if fv:
            new_val = str(result)
            if fv.value != new_val:
                fv.value = new_val
                fv.save(update_fields=["value", "updated_at"])
                updated += 1

    return updated
