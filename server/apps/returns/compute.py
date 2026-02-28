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

    # Schedule K — auto-flows from Page 1 and sub-schedules
    # K1 = ordinary business income (from Page 1 Line 21)
    ("K1", lambda v: _d(v, "21")),
    # K18 = total income/loss reconciliation
    # (income items positive, deduction items negative)
    ("K18", lambda v: (
        _sum(v, "K1", "K2", "K3", "K4", "K5a", "K6", "K7", "K8a", "K9", "K10")
        - _d(v, "K11") - _d(v, "K12a")
        + _d(v, "K16a") + _d(v, "K16b") - _d(v, "K16c")
    )),

    # Schedule L — Balance Sheet
    # Inventory flows from COGS (Schedule A)
    ("L3a", lambda v: _d(v, "A1")),   # BOY inventory = COGS beginning inventory
    ("L3d", lambda v: _d(v, "A7")),   # EOY inventory = COGS ending inventory
    # Total assets = cash + AR + inventories + shareholder loans + other current
    #              + (buildings − accum depr)
    ("L14a", lambda v: _sum(v, "L1a", "L2a", "L3a", "L5a", "L7a")
     + _d(v, "L9a") - _d(v, "L9b")),
    ("L14d", lambda v: _sum(v, "L1d", "L2d", "L3d", "L5d", "L7d")
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

    # Schedule M-2 — AAA tracking
    # Line 2: ordinary income (positive only, from K1 via line 21)
    ("M2_2", lambda v: max(ZERO, _d(v, "K1"))),
    # Line 4: loss (from K1, shown as positive amount)
    ("M2_4", lambda v: max(ZERO, -_d(v, "K1"))),
    # Line 5: other reductions = charitable + sec 179 + nondeductible expenses
    ("M2_5", lambda v: _sum(v, "K12a", "K11", "K16c")),
    # Line 6: combine lines 1 through 5
    ("M2_6", lambda v: (
        _d(v, "M2_1") + _d(v, "M2_2") + _d(v, "M2_3")
        - _d(v, "M2_4") - _d(v, "M2_5")
    )),
    # Line 7: distributions (from Schedule K line 16d)
    ("M2_7", lambda v: _d(v, "K16d")),
    # Line 8: ending balance
    ("M2_8", lambda v: _d(v, "M2_6") - _d(v, "M2_7")),
]

# ---------------------------------------------------------------------------
# 1065 Formulas  (line_number, callable(values) -> Decimal)
# ORDER MATTERS — dependencies must come before dependents.
# ---------------------------------------------------------------------------

FORMULAS_1065: list[tuple[str, callable]] = [
    # Page 1 Income
    ("1c", lambda v: _d(v, "1a") - _d(v, "1b")),
    ("3", lambda v: _d(v, "1c") - _d(v, "2")),
    ("8", lambda v: _sum(v, "3", "4", "5", "6", "7")),
    # Page 1 Deductions
    ("21", lambda v: _sum(v, "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20")),
    ("22", lambda v: _d(v, "8") - _d(v, "21")),
    # Schedule L
    ("L14a", lambda v: _sum(v, "L1a", "L2a", "L3a", "L6a", "L7a") + _d(v, "L9a") - _d(v, "L9b") + _d(v, "L11a") + _d(v, "L13a")),
    ("L14d", lambda v: _sum(v, "L1d", "L2d", "L3d", "L6d", "L7d") + _d(v, "L9d") - _d(v, "L9e") + _d(v, "L11d") + _d(v, "L13d")),
    ("L23a", lambda v: _sum(v, "L15a", "L16a", "L17a", "L19a", "L21a", "L22a")),
    ("L23d", lambda v: _sum(v, "L15d", "L16d", "L17d", "L19d", "L21d", "L22d")),
    # M-1
    ("M1_5", lambda v: _sum(v, "M1_1", "M1_2", "M1_3", "M1_4")),
    ("M1_8", lambda v: _d(v, "M1_6") + _d(v, "M1_7")),
    ("M1_9", lambda v: _d(v, "M1_5") - _d(v, "M1_8")),
    # M-2
    ("M2_5", lambda v: _d(v, "M2_1") + _d(v, "M2_2a") + _d(v, "M2_2b") + _d(v, "M2_3") + _d(v, "M2_4")),
    ("M2_8", lambda v: _d(v, "M2_6a") + _d(v, "M2_6b") + _d(v, "M2_7")),
    ("M2_9", lambda v: _d(v, "M2_5") - _d(v, "M2_8")),
]

# ---------------------------------------------------------------------------
# 1120 Formulas  (line_number, callable(values) -> Decimal)
# ORDER MATTERS — dependencies must come before dependents.
# ---------------------------------------------------------------------------

FORMULAS_1120: list[tuple[str, callable]] = [
    # Page 1 Income
    ("1c", lambda v: _d(v, "1a") - _d(v, "1b")),
    ("3", lambda v: _d(v, "1c") - _d(v, "2")),
    ("11", lambda v: _sum(v, "3", "4", "5", "6", "7", "8", "9", "10")),
    # Page 1 Deductions
    ("27", lambda v: _sum(v, "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26")),
    ("28", lambda v: _d(v, "11") - _d(v, "27")),
    ("29c", lambda v: _d(v, "29a") + _d(v, "29b")),
    ("30", lambda v: _d(v, "28") - _d(v, "29c")),
    # Schedule C
    ("C9", lambda v: _sum(v, "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8")),
    ("C20", lambda v: _d(v, "C9") + _sum(v, "C10", "C11", "C12", "C13", "C14", "C15", "C16", "C17", "C18")),
    ("C21", lambda v: _d(v, "C19")),
    # Schedule J
    ("J1", lambda v: _d(v, "30")),
    ("J2", lambda v: (_d(v, "J1") * Decimal("0.21")).quantize(Decimal("0.01"))),
    ("J4", lambda v: _d(v, "J2") + _d(v, "J3")),
    ("J5e", lambda v: _sum(v, "J5a", "J5b", "J5c", "J5d")),
    ("J6", lambda v: max(ZERO, _d(v, "J4") - _d(v, "J5e"))),
    ("J9", lambda v: _d(v, "J6") + _d(v, "J7") + _d(v, "J8")),
    # Page 1 Tax
    ("31", lambda v: _d(v, "J9")),
    ("34", lambda v: max(ZERO, _d(v, "31") - _d(v, "32"))),
    ("35", lambda v: max(ZERO, _d(v, "32") - _d(v, "31"))),
    # Schedule L
    ("L15a", lambda v: _sum(v, "L1a", "L2a", "L3a", "L4a", "L5a", "L6a", "L7a", "L8a", "L9a") + _d(v, "L10a") - _d(v, "L10b") + _d(v, "L11a") - _d(v, "L11b") + _d(v, "L12a") + _d(v, "L13a") - _d(v, "L13b") + _d(v, "L14a")),
    ("L15d", lambda v: _sum(v, "L1d", "L2d", "L3d", "L4d", "L5d", "L6d", "L7d", "L8d", "L9d") + _d(v, "L10d") - _d(v, "L10e") + _d(v, "L11d") - _d(v, "L11e") + _d(v, "L12d") + _d(v, "L13d") - _d(v, "L13e") + _d(v, "L14d")),
    ("L28a", lambda v: _sum(v, "L16a", "L17a", "L18a", "L19a", "L20a", "L21a", "L22a_pref", "L22a_com", "L23a", "L24a", "L25a", "L26a") - _d(v, "L27a")),
    ("L28d", lambda v: _sum(v, "L16d", "L17d", "L18d", "L19d", "L20d", "L21d", "L22d_pref", "L22d_com", "L23d", "L24d", "L25d", "L26d") - _d(v, "L27d")),
    # M-1
    ("M1_6", lambda v: _sum(v, "M1_1", "M1_2", "M1_3", "M1_4", "M1_5a", "M1_5b", "M1_5c", "M1_5d")),
    ("M1_9", lambda v: _d(v, "M1_7a") + _d(v, "M1_7b") + _d(v, "M1_8a") + _d(v, "M1_8b")),
    ("M1_10", lambda v: _d(v, "M1_6") - _d(v, "M1_9")),
    # M-2
    ("M2_4", lambda v: _d(v, "M2_1") + _d(v, "M2_2") + _d(v, "M2_3")),
    ("M2_7", lambda v: _d(v, "M2_5a") + _d(v, "M2_5b") + _d(v, "M2_5c") + _d(v, "M2_6")),
    ("M2_8", lambda v: _d(v, "M2_4") - _d(v, "M2_7")),
]

# Registry by form code
FORMULA_REGISTRY: dict[str, list[tuple[str, callable]]] = {
    "1120-S": FORMULAS_1120S,
    "1065": FORMULAS_1065,
    "1120": FORMULAS_1120,
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
        fv = fv_by_line.get(line_number)

        # Respect manual overrides — if a user manually set a computed field,
        # keep their value and use it for downstream formulas.
        if fv and fv.is_overridden:
            continue

        result = formula_fn(values).quantize(Decimal("0.01"))
        values[line_number] = result  # update for downstream formulas

        if fv:
            new_val = str(result)
            if fv.value != new_val:
                fv.value = new_val
                fv.save(update_fields=["value", "updated_at"])
                updated += 1

    return updated
