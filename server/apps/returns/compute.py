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
    # Total assets
    ("L15a", lambda v: (
        _sum(v, "L1a", "L3a", "L4a", "L5a", "L6a", "L7a", "L8a", "L9a", "L12a", "L14a")
        + _d(v, "L2a") - _d(v, "L2b")
        + _d(v, "L10a") - _d(v, "L10b")
        + _d(v, "L11a") - _d(v, "L11b")
        + _d(v, "L13a") - _d(v, "L13b")
    )),
    ("L15d", lambda v: (
        _sum(v, "L1d", "L3d", "L4d", "L5d", "L6d", "L7d", "L8d", "L9d", "L12d", "L14d")
        + _d(v, "L2d") - _d(v, "L2e")
        + _d(v, "L10d") - _d(v, "L10e")
        + _d(v, "L11d") - _d(v, "L11e")
        + _d(v, "L13d") - _d(v, "L13e")
    )),
    # Total liabilities & equity
    ("L28a", lambda v: _sum(
        v, "L16a", "L17a", "L18a", "L19a", "L20a", "L21a",
        "L22a", "L23a", "L24a", "L25a", "L27a",
    ) - _d(v, "L26a")),
    ("L28d", lambda v: _sum(
        v, "L16d", "L17d", "L18d", "L19d", "L20d", "L21d",
        "L22d", "L23d", "L24d", "L25d", "L27d",
    ) - _d(v, "L26d")),

    # Schedule M-1
    ("M1_4", lambda v: _sum(v, "M1_1", "M1_2", "M1_3a", "M1_3b", "M1_3c")),
    ("M1_7", lambda v: _sum(v, "M1_5a", "M1_5b", "M1_6a", "M1_6b")),
    ("M1_8", lambda v: _d(v, "M1_4") - _d(v, "M1_7")),

    # Schedule M-2 — 4 columns: (a) AAA, (b) OAA, (c) STPI, (d) Accu E&P
    # Column (a) AAA — auto-computed
    ("M2_2a", lambda v: max(ZERO, _d(v, "K1"))),
    ("M2_4a", lambda v: max(ZERO, -_d(v, "K1"))),
    ("M2_5a", lambda v: _sum(v, "K12a", "K11", "K16c")),
    ("M2_6a", lambda v: (
        _d(v, "M2_1a") + _d(v, "M2_2a") + _d(v, "M2_3a")
        - _d(v, "M2_4a") - _d(v, "M2_5a")
    )),
    ("M2_7a", lambda v: _d(v, "K16d")),
    ("M2_8a", lambda v: _d(v, "M2_6a") - _d(v, "M2_7a")),
    # Column (b) OAA — line 6 and 8 computed, rest manual
    ("M2_6b", lambda v: (
        _d(v, "M2_1b") + _d(v, "M2_2b") + _d(v, "M2_3b")
        - _d(v, "M2_4b") - _d(v, "M2_5b")
    )),
    ("M2_8b", lambda v: _d(v, "M2_6b") - _d(v, "M2_7b")),
    # Column (c) STPI — line 6 and 8 computed, rest manual
    ("M2_6c", lambda v: (
        _d(v, "M2_1c") + _d(v, "M2_2c") + _d(v, "M2_3c")
        - _d(v, "M2_4c") - _d(v, "M2_5c")
    )),
    ("M2_8c", lambda v: _d(v, "M2_6c") - _d(v, "M2_7c")),
    # Column (d) Accu E&P — line 6 and 8 computed, rest manual
    ("M2_6d", lambda v: (
        _d(v, "M2_1d") + _d(v, "M2_2d") + _d(v, "M2_3d")
        - _d(v, "M2_4d") - _d(v, "M2_5d")
    )),
    ("M2_8d", lambda v: _d(v, "M2_6d") - _d(v, "M2_7d")),
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

# ---------------------------------------------------------------------------
# GA 600S Formulas (Georgia S Corporation Tax Return)
# ORDER MATTERS — dependencies must come before dependents.
# ---------------------------------------------------------------------------

# GA Net Worth Tax — flat dollar amounts by bracket (from IT-611S instructions)
GA_NET_WORTH_TAX_TABLE: list[tuple[int, int]] = [
    (100_000,        0),
    (150_000,      125),
    (200_000,      150),
    (300_000,      200),
    (500_000,      250),
    (750_000,      300),
    (1_000_000,    500),
    (2_000_000,    750),
    (4_000_000,  1_000),
    (6_000_000,  1_250),
    (8_000_000,  1_500),
    (10_000_000, 1_750),
    (12_000_000, 2_000),
    (14_000_000, 2_500),
    (16_000_000, 3_000),
    (18_000_000, 3_500),
    (20_000_000, 4_000),
    (22_000_000, 4_500),
]
GA_NET_WORTH_TAX_MAX = 5_000  # Over $22M


def _ga_net_worth_tax(net_worth: Decimal) -> Decimal:
    """Look up the GA net worth tax from the tiered bracket table."""
    nw = int(net_worth)
    if nw <= 0:
        return ZERO
    for threshold, tax in GA_NET_WORTH_TAX_TABLE:
        if nw <= threshold:
            return Decimal(str(tax))
    return Decimal(str(GA_NET_WORTH_TAX_MAX))


FORMULAS_GA600S: list[tuple[str, callable]] = [
    # Schedule 7 — Additions to Federal Taxable Income
    ("S7_8", lambda v: _sum(v, "S7_1", "S7_2", "S7_3", "S7_5", "S7_6", "S7_7")),

    # Schedule 8 — Subtractions from Federal Taxable Income
    ("S8_5", lambda v: _sum(v, "S8_1", "S8_2", "S8_3", "S8_4")),

    # Schedule 6 — Total Income for GA Purposes
    ("S6_3c", lambda v: _d(v, "S6_3a") - _d(v, "S6_3b")),
    ("S6_7", lambda v: _sum(
        v, "S6_1", "S6_2", "S6_3c",
        "S6_4a", "S6_4b", "S6_4c", "S6_4d", "S6_4e", "S6_4f",
        "S6_5", "S6_6",
    )),
    ("S6_8", lambda v: _d(v, "S7_8")),
    ("S6_9", lambda v: _d(v, "S6_7") + _d(v, "S6_8")),
    ("S6_10", lambda v: _d(v, "S8_5")),
    ("S6_11", lambda v: _d(v, "S6_9") - _d(v, "S6_10")),

    # Schedule 5 — GA Net Income (apportionment)
    ("S5_1", lambda v: _d(v, "S6_11")),
    ("S5_3", lambda v: _d(v, "S5_1") - _d(v, "S5_2")),
    ("S5_5", lambda v: _d(v, "S5_3") * _d(v, "S5_4")),
    ("S5_7", lambda v: _d(v, "S5_5") + _d(v, "S5_6")),

    # Schedule 1 — GA Taxable Income and Tax
    ("S1_1", lambda v: _d(v, "S5_7")),
    ("S1_3", lambda v: _d(v, "S1_1") + _d(v, "S1_2")),
    ("S1_6", lambda v: _d(v, "S1_3") - _d(v, "S1_4") - _d(v, "S1_5")),
    ("S1_7", lambda v: max(ZERO, _d(v, "S1_6")) * Decimal("0.0539")),

    # Schedule 3 — Net Worth Tax
    ("S3_4", lambda v: _sum(v, "S3_1", "S3_2", "S3_3")),
    ("S3_6", lambda v: _d(v, "S3_4") * _d(v, "S3_5")),
    ("S3_7", lambda v: _ga_net_worth_tax(_d(v, "S3_6"))),

    # Schedule 4 — Tax Due or Overpayment
    ("S4_1a", lambda v: _d(v, "S1_7")),
    ("S4_1b", lambda v: _d(v, "S3_7")),
    ("S4_1c", lambda v: _d(v, "S4_1a") + _d(v, "S4_1b")),
    ("S4_2c", lambda v: _d(v, "S4_2a") + _d(v, "S4_2b")),
    ("S4_3c", lambda v: _d(v, "S4_3a") + _d(v, "S4_3b")),
    ("S4_4c", lambda v: _d(v, "S4_4a") + _d(v, "S4_4b")),
    # Balance due = tax - payments - credits - withholding (if positive)
    ("S4_5a", lambda v: max(ZERO, _d(v, "S4_1a") - _d(v, "S4_2a") - _d(v, "S4_3a") - _d(v, "S4_4a"))),
    ("S4_5b", lambda v: max(ZERO, _d(v, "S4_1b") - _d(v, "S4_2b") - _d(v, "S4_3b") - _d(v, "S4_4b"))),
    ("S4_5c", lambda v: _d(v, "S4_5a") + _d(v, "S4_5b")),
    # Overpayment = payments + credits + withholding - tax (if positive)
    ("S4_6a", lambda v: max(ZERO, _d(v, "S4_2a") + _d(v, "S4_3a") + _d(v, "S4_4a") - _d(v, "S4_1a"))),
    ("S4_6b", lambda v: max(ZERO, _d(v, "S4_2b") + _d(v, "S4_3b") + _d(v, "S4_4b") - _d(v, "S4_1b"))),
    ("S4_6c", lambda v: _d(v, "S4_6a") + _d(v, "S4_6b")),
    # Interest & penalty totals
    ("S4_7c", lambda v: _d(v, "S4_7a") + _d(v, "S4_7b")),
    ("S4_8c", lambda v: _d(v, "S4_8a") + _d(v, "S4_8b")),
    ("S4_9c", lambda v: _d(v, "S4_9a") + _d(v, "S4_9b")),
    # Amount Due = balance due + interest + penalties
    ("S4_10a", lambda v: _d(v, "S4_5a") + _d(v, "S4_7a") + _d(v, "S4_8a") + _d(v, "S4_9a")),
    ("S4_10b", lambda v: _d(v, "S4_5b") + _d(v, "S4_7b") + _d(v, "S4_8b") + _d(v, "S4_9b")),
    ("S4_10c", lambda v: _d(v, "S4_10a") + _d(v, "S4_10b")),
    # Credit to next year estimated tax (from overpayment)
    ("S4_11a", lambda v: _d(v, "S4_6a")),
    ("S4_11b", lambda v: _d(v, "S4_6b")),
    ("S4_11c", lambda v: _d(v, "S4_11a") + _d(v, "S4_11b")),
]


# Registry by form code
FORMULA_REGISTRY: dict[str, list[tuple[str, callable]]] = {
    "1120-S": FORMULAS_1120S,
    "1065": FORMULAS_1065,
    "1120": FORMULAS_1120,
    "GA-600S": FORMULAS_GA600S,
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
