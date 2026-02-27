"""
Computation engine for Form 7203 -- S Corporation Shareholder
Stock and Debt Basis Limitations.

Computes all line values for a single shareholder from:
    - Shareholder model fields (entered data)
    - Schedule K FormFieldValues x ownership % (auto from K-1)
    - ShareholderLoan records (Part II debt tracking)

Returns a flat dict mapping line keys to Decimal values, suitable for
rendering via the coordinate map in coordinates/f7203.py.

Line keys match the FIELD_MAP keys:
    Part I:  "1", "2", "3a"-"3m", "4"-"15"
    Part II: "16a"-"34d" (line + debt column a/b/c/d)
    Part III: "35a"-"47e" (line + column a/b/c/d/e)
"""

from decimal import Decimal, InvalidOperation

ZERO = Decimal("0")
TWO_PLACES = Decimal("0.01")
SIX_PLACES = Decimal("0.000001")


def compute_7203(tax_return, shareholder) -> dict[str, Decimal]:
    """
    Compute all Form 7203 values for a single shareholder.

    Returns a dict mapping line keys (e.g., "1", "3a", "16a", "35c")
    to Decimal values. Zero values are included; the renderer will
    skip them when formatting.
    """
    ownership_pct = shareholder.ownership_percentage / Decimal("100")
    k_values = _load_schedule_k_values(tax_return)
    loans = list(shareholder.loans.order_by("sort_order", "description")[:3])

    v: dict[str, Decimal] = {}

    # ---- Part I: Shareholder Stock Basis ----
    _compute_part_i(v, shareholder, ownership_pct, k_values)

    # ---- Part II: Shareholder Debt Basis ----
    _compute_part_ii(v, loans)

    # ---- Part III: Loss Limitations (only if losses exceed stock basis) ----
    stock_basis_available = v["10"]
    debt_basis_available = v.get("29d", ZERO)
    _compute_part_iii(v, shareholder, ownership_pct, k_values,
                      stock_basis_available, debt_basis_available)

    # ---- Wire Part III totals back into Part I and Part II ----
    # Line 11 = Part III line 47 column (c) total allowed from stock basis
    v["11"] = v.get("47c", ZERO)
    # Line 12 = debt basis restoration (zero for first implementation)
    v["12"] = ZERO
    # Line 13 = other items that decrease stock basis (usually zero)
    v["13"] = ZERO
    # Line 14 = 11 + 12 + 13
    v["14"] = v["11"] + v["12"] + v["13"]
    # Line 15 = max(0, 10 - 14)
    v["15"] = max(ZERO, v["10"] - v["14"])

    # Part II line 30: total allowable losses from debt basis
    total_debt_loss = v.get("47d", ZERO)
    if loans and total_debt_loss > ZERO:
        # Allocate total debt loss across loans proportionally by debt basis
        _allocate_debt_loss_to_loans(v, loans, total_debt_loss)
    elif not loans:
        v["30d"] = total_debt_loss

    # Recompute line 31 (debt basis at end) after loss allocation
    for suffix in ("a", "b", "c"):
        ln29 = v.get(f"29{suffix}", ZERO)
        ln30 = v.get(f"30{suffix}", ZERO)
        v[f"31{suffix}"] = max(ZERO, ln29 - ln30)
    ln29d = v.get("29d", ZERO)
    ln30d = v.get("30d", ZERO)
    v["31d"] = max(ZERO, ln29d - ln30d)

    return v


# =====================================================================
# Part I: Shareholder Stock Basis
# =====================================================================

def _compute_part_i(v, shareholder, ownership_pct, k_values):
    """Compute Part I lines 1-10 (before loss items, which need Part III)."""

    # Line 1: Stock basis at beginning (entered)
    v["1"] = shareholder.stock_basis_boy or ZERO

    # Line 2: Capital contributions (entered)
    v["2"] = shareholder.capital_contributions or ZERO

    # Lines 3a-3m: Income items from Schedule K (positive amounts only)
    v["3a"] = _prorate_positive(k_values.get("K1", ZERO), ownership_pct)
    v["3b"] = _prorate_positive(k_values.get("K2", ZERO), ownership_pct)
    v["3c"] = _prorate_positive(k_values.get("K3c", ZERO), ownership_pct)
    v["3d"] = _prorate(k_values.get("K4", ZERO), ownership_pct)
    v["3e"] = _prorate(k_values.get("K5a", ZERO), ownership_pct)
    v["3f"] = _prorate(k_values.get("K6", ZERO), ownership_pct)
    v["3g"] = _prorate_positive(k_values.get("K7", ZERO), ownership_pct)
    v["3h"] = _prorate_positive(k_values.get("K8a", ZERO), ownership_pct)
    v["3i"] = _prorate_positive(k_values.get("K10", ZERO), ownership_pct)
    v["3j"] = ZERO  # Excess depletion adjustment (rarely used, entered)
    # 3k: Tax-exempt income = K16a + K16b
    k16a = k_values.get("K16a", ZERO)
    k16b = k_values.get("K16b", ZERO)
    v["3k"] = _prorate(k16a + k16b, ownership_pct)
    v["3l"] = ZERO  # Recapture of business credits (entered)
    v["3m"] = ZERO  # Other items that increase stock basis (entered)

    # Line 4: Total of 3a-3m
    v["4"] = sum(v[f"3{c}"] for c in "abcdefghijklm")

    # Line 5: Stock basis before distributions = 1 + 2 + 4
    v["5"] = v["1"] + v["2"] + v["4"]

    # Line 6: Distributions
    v["6"] = shareholder.distributions or ZERO

    # Line 7: Stock basis after distributions = max(0, 5 - 6)
    v["7"] = max(ZERO, v["5"] - v["6"])

    # Lines 8a-8c: Non-deductible items that reduce basis
    # 8a: Nondeductible expenses (K16c x ownership %)
    k16c = k_values.get("K16c", ZERO)
    v["8a"] = _prorate(k16c, ownership_pct)
    # 8b: Depletion for oil and gas (entered)
    v["8b"] = shareholder.depletion or ZERO
    # 8c: Business credits (usually zero)
    v["8c"] = ZERO

    # Line 9: Total of 8a-8c
    v["9"] = v["8a"] + v["8b"] + v["8c"]

    # Line 10: Stock basis before loss items = max(0, 7 - 9)
    v["10"] = max(ZERO, v["7"] - v["9"])

    # Lines 11-15 are computed after Part III


# =====================================================================
# Part II: Shareholder Debt Basis
# =====================================================================

def _compute_part_ii(v, loans):
    """Compute Part II lines 16-31 from ShareholderLoan records."""

    # Initialize all debt columns to zero
    for line in range(16, 35):
        for suffix in ("a", "b", "c", "d"):
            v[f"{line}{suffix}"] = ZERO

    # Fill per-loan columns (a, b, c for up to 3 loans)
    suffixes = ("a", "b", "c")
    for i, loan in enumerate(loans):
        if i >= 3:
            break
        s = suffixes[i]

        # Section A: Amount of Debt
        v[f"16{s}"] = loan.loan_balance_boy or ZERO
        v[f"17{s}"] = loan.additional_loans or ZERO
        v[f"18{s}"] = v[f"16{s}"] + v[f"17{s}"]
        v[f"19{s}"] = loan.loan_repayments or ZERO
        v[f"20{s}"] = v[f"18{s}"] - v[f"19{s}"]

        # Section B: Adjustments to Debt Basis
        v[f"21{s}"] = loan.debt_basis_boy or ZERO
        v[f"22{s}"] = loan.new_loans_increasing_basis or ZERO
        v[f"23{s}"] = ZERO  # Debt basis restoration (computed later or entered)
        v[f"24{s}"] = v[f"21{s}"] + v[f"22{s}"] + v[f"23{s}"]

        # Line 25: Ratio = line 24 / line 18 (capped at 1.0)
        if v[f"18{s}"] > ZERO:
            ratio = (v[f"24{s}"] / v[f"18{s}"]).quantize(SIX_PLACES)
            v[f"25{s}"] = min(ratio, Decimal("1"))
        else:
            v[f"25{s}"] = ZERO

        # Line 26: Nontaxable debt repayment = 25 * 19
        v[f"26{s}"] = (v[f"25{s}"] * v[f"19{s}"]).quantize(TWO_PLACES)

        # Line 27: Debt basis before nondeductible = 24 - 26
        v[f"27{s}"] = v[f"24{s}"] - v[f"26{s}"]

        # Line 28: Nondeductible expenses in excess of stock basis
        # (computed from Part I: if line 9 > line 7, excess = line 9 - line 7)
        # For now allocated proportionally if multiple loans
        v[f"28{s}"] = ZERO

        # Line 29: Debt basis before losses = max(0, 27 - 28)
        v[f"29{s}"] = max(ZERO, v[f"27{s}"] - v[f"28{s}"])

        # Lines 30-31 computed after Part III

        # Section C: Gain on Repayment
        v[f"32{s}"] = v[f"19{s}"]  # Same as line 19
        v[f"33{s}"] = v[f"26{s}"]  # Same as line 26
        v[f"34{s}"] = max(ZERO, v[f"32{s}"] - v[f"33{s}"])

    # Compute (d) Total column = sum of a + b + c
    for line in range(16, 35):
        v[f"{line}d"] = sum(v.get(f"{line}{s}", ZERO) for s in suffixes)


# =====================================================================
# Part III: Shareholder Allowable Loss and Deduction Items
# =====================================================================

# Maps Part III line numbers to the K-1 schedule line they pull from.
# Column (a) = current year loss amount (positive = loss).
_PART_III_K_MAP = {
    35: "K1",     # Ordinary business loss
    36: "K2",     # Net rental real estate loss
    37: "K3c",    # Other net rental loss
    38: "K7",     # Net capital loss (short-term + long-term combined)
    39: "K8a",    # Net section 1231 loss
    40: "K10",    # Other loss
    41: "K11",    # Section 179 deductions
    # Lines 42-46 are typically entered by preparer (not direct K-line mapping)
}

# Maps Part III lines to the suspended loss fields on Shareholder model
_SUSPENDED_FIELDS = {
    35: "suspended_ordinary_loss",
    36: "suspended_rental_re_loss",
    37: "suspended_other_rental_loss",
    38: "suspended_st_capital_loss",
    39: "suspended_1231_loss",
    40: "suspended_other_loss",
    # 41-46: No pre-built fields; these would be zero for most returns
}


def _compute_part_iii(v, shareholder, ownership_pct, k_values,
                      stock_basis_available, debt_basis_available):
    """
    Compute Part III loss limitations.

    For each loss category (lines 35-46):
        (a) Current year loss from K-1 (positive amounts = losses)
        (b) Carryover from previous year (entered on Shareholder model)
        (c) Allowable from stock basis (pro-rata)
        (d) Allowable from debt basis (pro-rata)
        (e) Carryover to next year = (a) + (b) - (c) - (d)
    """
    # Step 1: Populate columns (a) and (b) for each loss line
    loss_lines = list(range(35, 47))

    for line in loss_lines:
        # Column (a): Current year loss from K-1
        k_line = _PART_III_K_MAP.get(line)
        if k_line:
            raw = k_values.get(k_line, ZERO)
            # For income/loss lines (K1, K2, etc.), losses are negative
            # Convert to positive for Part III display
            if line == 41:
                # Section 179 is always positive on K-1
                v[f"{line}a"] = _prorate(raw, ownership_pct)
            else:
                v[f"{line}a"] = _prorate_negative_as_positive(raw, ownership_pct)
        else:
            v[f"{line}a"] = ZERO

        # Column (b): Carryover from previous year
        field_name = _SUSPENDED_FIELDS.get(line)
        if field_name:
            v[f"{line}b"] = getattr(shareholder, field_name, ZERO) or ZERO
        else:
            v[f"{line}b"] = ZERO

    # Step 2: Calculate total losses per category and grand total
    category_totals = {}
    for line in loss_lines:
        category_totals[line] = v[f"{line}a"] + v[f"{line}b"]
    grand_total = sum(category_totals.values())

    # Step 3: Allocate losses against stock basis, then debt basis
    if grand_total <= ZERO:
        # No losses — everything is zero
        for line in loss_lines:
            v[f"{line}c"] = ZERO
            v[f"{line}d"] = ZERO
            v[f"{line}e"] = ZERO
    elif grand_total <= stock_basis_available:
        # All losses covered by stock basis
        for line in loss_lines:
            v[f"{line}c"] = category_totals[line]
            v[f"{line}d"] = ZERO
            v[f"{line}e"] = ZERO
    else:
        # Losses exceed stock basis — pro-rata allocation
        # First: allocate stock basis proportionally
        for line in loss_lines:
            if grand_total > ZERO and category_totals[line] > ZERO:
                share = (category_totals[line] / grand_total * stock_basis_available)
                v[f"{line}c"] = share.quantize(TWO_PLACES)
            else:
                v[f"{line}c"] = ZERO

        # Adjust for rounding (ensure column c total = stock_basis_available)
        col_c_total = sum(v[f"{line}c"] for line in loss_lines)
        if col_c_total != stock_basis_available and loss_lines:
            rounding_diff = stock_basis_available - col_c_total
            # Apply rounding difference to the largest category
            largest_line = max(loss_lines, key=lambda ln: category_totals[ln])
            v[f"{largest_line}c"] += rounding_diff

        # Second: remaining losses allocated against debt basis
        remaining_per_category = {}
        for line in loss_lines:
            remaining_per_category[line] = category_totals[line] - v[f"{line}c"]
        total_remaining = sum(remaining_per_category.values())

        if total_remaining <= ZERO or debt_basis_available <= ZERO:
            for line in loss_lines:
                v[f"{line}d"] = ZERO
        elif total_remaining <= debt_basis_available:
            # All remaining covered by debt basis
            for line in loss_lines:
                v[f"{line}d"] = remaining_per_category[line]
        else:
            # Pro-rata allocation of debt basis
            for line in loss_lines:
                if total_remaining > ZERO and remaining_per_category[line] > ZERO:
                    share = (remaining_per_category[line] / total_remaining
                             * debt_basis_available)
                    v[f"{line}d"] = share.quantize(TWO_PLACES)
                else:
                    v[f"{line}d"] = ZERO

            # Adjust for rounding
            col_d_total = sum(v[f"{line}d"] for line in loss_lines)
            if col_d_total != debt_basis_available and loss_lines:
                rounding_diff = debt_basis_available - col_d_total
                largest_line = max(loss_lines,
                                   key=lambda ln: remaining_per_category[ln])
                v[f"{largest_line}d"] += rounding_diff

        # Column (e): Carryover to next year = total - (c) - (d)
        for line in loss_lines:
            v[f"{line}e"] = category_totals[line] - v[f"{line}c"] - v[f"{line}d"]

    # Step 4: Compute line 47 totals per column
    for col in "abcde":
        v[f"47{col}"] = sum(v.get(f"{line}{col}", ZERO) for line in loss_lines)


# =====================================================================
# Helpers
# =====================================================================

def _allocate_debt_loss_to_loans(v, loans, total_debt_loss):
    """Allocate Part III debt loss total across individual loans."""
    suffixes = ("a", "b", "c")
    total_debt_basis = sum(v.get(f"29{suffixes[i]}", ZERO)
                          for i in range(min(len(loans), 3)))

    for i, loan in enumerate(loans[:3]):
        s = suffixes[i]
        if total_debt_basis > ZERO:
            share = (v[f"29{s}"] / total_debt_basis * total_debt_loss)
            v[f"30{s}"] = share.quantize(TWO_PLACES)
        else:
            v[f"30{s}"] = ZERO

    v["30d"] = sum(v.get(f"30{s}", ZERO) for s in suffixes)


def _load_schedule_k_values(tax_return) -> dict[str, Decimal]:
    """Load Schedule K line values as a dict of line_number -> Decimal."""
    from apps.returns.models import FormFieldValue

    fvs = FormFieldValue.objects.filter(
        tax_return=tax_return
    ).select_related("form_line")

    k_values: dict[str, Decimal] = {}
    for fv in fvs:
        ln = fv.form_line.line_number
        if ln.startswith("K") and fv.value:
            try:
                k_values[ln] = Decimal(fv.value)
            except InvalidOperation:
                pass
    return k_values


def _prorate(total: Decimal, ownership_pct: Decimal) -> Decimal:
    """Pro-rate a total by ownership percentage."""
    if not total:
        return ZERO
    return (total * ownership_pct).quantize(TWO_PLACES)


def _prorate_positive(total: Decimal, ownership_pct: Decimal) -> Decimal:
    """Pro-rate only if total is positive (income). Return 0 if negative."""
    if not total or total <= ZERO:
        return ZERO
    return (total * ownership_pct).quantize(TWO_PLACES)


def _prorate_negative_as_positive(total: Decimal, ownership_pct: Decimal) -> Decimal:
    """If total is negative (a loss), return the absolute value pro-rated."""
    if not total or total >= ZERO:
        return ZERO
    return (abs(total) * ownership_pct).quantize(TWO_PLACES)
