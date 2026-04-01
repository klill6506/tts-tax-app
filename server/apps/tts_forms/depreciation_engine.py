"""
Depreciation calculation engine for tax return assets.

Implements IRS Publication 946 MACRS percentage tables for:
- 200% Declining Balance (3, 5, 7, 10, 15, 20 year)
- 150% Declining Balance (3, 5, 7, 10, 15, 20 year)
- Straight-Line (any life, HY/MQ/MM conventions)
- Section 179 expense election
- Bonus depreciation (OBBBA rules)
- AMT depreciation (150DB for 200DB assets)
- Georgia state depreciation (no bonus conformity)
- Luxury auto limits
- Section 197/195 amortization

Usage:
    from apps.tts_forms.depreciation_engine import calculate_asset_depreciation
    result = calculate_asset_depreciation(asset, tax_year=2025)
"""

from __future__ import annotations

import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.returns.models import DepreciationAsset

ZERO = Decimal("0")
ONE = Decimal("1")
HUNDRED = Decimal("100")
PENNY = Decimal("0.01")

# ---------------------------------------------------------------------------
# Section 179 limits
# ---------------------------------------------------------------------------

# Federal (OBBBA — property placed in service after Dec 31, 2024)
FEDERAL_179_LIMIT = Decimal("2500000")
FEDERAL_179_PHASEOUT = Decimal("4000000")

# Georgia (pre-OBBBA — static conformity date Jan 1, 2025)
GA_179_LIMIT = Decimal("1050000")
GA_179_PHASEOUT = Decimal("2620000")

# ---------------------------------------------------------------------------
# OBBBA bonus depreciation date threshold
# ---------------------------------------------------------------------------
OBBBA_CUTOFF_DATE = datetime.date(2025, 1, 20)  # Jan 20, 2025

# ---------------------------------------------------------------------------
# Luxury auto limits (Rev. Proc. 2025-13 — passenger automobiles)
# Year 1, Year 2, Year 3, Year 4+
# ---------------------------------------------------------------------------
LUXURY_AUTO_LIMITS = {
    2025: {
        "with_bonus": [20200, 19500, 11800, 7060],
        "without_bonus": [12400, 19500, 11800, 7060],
    },
}

# Fallback to 2025 if year not found
def _get_auto_limit(tax_year: int, year_in_service: int, has_bonus: bool) -> Decimal:
    """Get luxury auto depreciation limit for a given year in service."""
    limits = LUXURY_AUTO_LIMITS.get(tax_year, LUXURY_AUTO_LIMITS[2025])
    key = "with_bonus" if has_bonus else "without_bonus"
    table = limits[key]
    idx = min(year_in_service - 1, len(table) - 1)
    return Decimal(str(table[idx]))


# ---------------------------------------------------------------------------
# MACRS Percentage Tables — IRS Publication 946, Appendix A
# Tables keyed by (method, life_years) → list of annual percentages
# Index 0 = Year 1, Index 1 = Year 2, etc.
# All percentages expressed as decimals (e.g., 0.3333 = 33.33%)
# ---------------------------------------------------------------------------

# 200% Declining Balance — Half-Year Convention
MACRS_200DB_HY: dict[int, list[str]] = {
    3: [
        "0.3333", "0.4445", "0.1481", "0.0741",
    ],
    5: [
        "0.2000", "0.3200", "0.1920", "0.1152", "0.1152", "0.0576",
    ],
    7: [
        "0.1429", "0.2449", "0.1749", "0.1249", "0.0893", "0.0892",
        "0.0893", "0.0446",
    ],
    10: [
        "0.1000", "0.1800", "0.1440", "0.1152", "0.0922", "0.0737",
        "0.0655", "0.0655", "0.0656", "0.0655", "0.0328",
    ],
    15: [
        "0.0500", "0.0950", "0.0855", "0.0770", "0.0693", "0.0623",
        "0.0590", "0.0590", "0.0591", "0.0590", "0.0591", "0.0590",
        "0.0591", "0.0590", "0.0591", "0.0295",
    ],
    20: [
        "0.0375", "0.0722", "0.0668", "0.0618", "0.0571", "0.0528",
        "0.0489", "0.0452", "0.0447", "0.0447", "0.0446", "0.0447",
        "0.0446", "0.0447", "0.0446", "0.0447", "0.0446", "0.0447",
        "0.0446", "0.0447", "0.0223",
    ],
}

# 200% Declining Balance — Mid-Quarter Convention
# Q1 = property placed in service in 1st quarter, etc.
MACRS_200DB_MQ: dict[int, dict[int, list[str]]] = {
    5: {
        1: ["0.3500", "0.2600", "0.1560", "0.1110", "0.1110", "0.0120"],
        2: ["0.2500", "0.3000", "0.1800", "0.1198", "0.1198", "0.0304"],
        3: ["0.1500", "0.3400", "0.2040", "0.1224", "0.1122", "0.0620"],
        4: ["0.0500", "0.3800", "0.2280", "0.1368", "0.1094", "0.0858"],
    },
    7: {
        1: ["0.2500", "0.2143", "0.1531", "0.1093", "0.0781", "0.0781", "0.0781", "0.0390"],
        2: ["0.1786", "0.2388", "0.1706", "0.1219", "0.0871", "0.0871", "0.0871", "0.0288"],
        3: ["0.1071", "0.2633", "0.1880", "0.1344", "0.0960", "0.0960", "0.0960", "0.0192"],
        4: ["0.0357", "0.2878", "0.2055", "0.1468", "0.1049", "0.1049", "0.1049", "0.0095"],
    },
}

# 150% Declining Balance — Half-Year Convention
# 150% Declining Balance — Half-Year Convention
# IRS Publication 946, Table A-14 (3yr, 5yr, 7yr, 10yr) and Table A-1 (15yr, 20yr).
# All include automatic switch to straight-line in the optimal year.
# Every table MUST sum to 1.0000 (±0.001).
MACRS_150DB_HY: dict[int, list[str]] = {
    3: [
        "0.2500", "0.3750", "0.2500", "0.1250",
    ],
    5: [
        "0.1500", "0.2550", "0.1785", "0.1666", "0.1666", "0.0833",
    ],
    7: [
        "0.1071", "0.1913", "0.1503", "0.1225", "0.1225", "0.1225",
        "0.1225", "0.0613",
    ],
    10: [
        "0.0750", "0.1388", "0.1180", "0.1003", "0.0853", "0.0872",
        "0.0872", "0.0872", "0.0872", "0.0872", "0.0466",
    ],
    15: [
        "0.0500", "0.0950", "0.0855", "0.0770", "0.0693", "0.0623",
        "0.0590", "0.0590", "0.0591", "0.0590", "0.0591", "0.0590",
        "0.0591", "0.0590", "0.0591", "0.0295",
    ],
    20: [
        "0.0375", "0.0722", "0.0668", "0.0618", "0.0571", "0.0528",
        "0.0489", "0.0452", "0.0447", "0.0446", "0.0446", "0.0446",
        "0.0446", "0.0446", "0.0446", "0.0446", "0.0446", "0.0446",
        "0.0446", "0.0446", "0.0223",
    ],
}

# Straight-Line — Mid-Month Convention (for 27.5-yr and 39-yr property)
# Keyed by month placed in service (1-12) → first-year percentage
SL_MM_FIRST_YEAR: dict[str, dict[int, str]] = {
    "27.5": {
        1: "0.03485", 2: "0.03182", 3: "0.02879", 4: "0.02576",
        5: "0.02273", 6: "0.01970", 7: "0.01667", 8: "0.01364",
        9: "0.01061", 10: "0.00758", 11: "0.00455", 12: "0.00152",
    },
    "39.0": {
        1: "0.02461", 2: "0.02247", 3: "0.02033", 4: "0.01819",
        5: "0.01605", 6: "0.01391", 7: "0.01177", 8: "0.00963",
        9: "0.00749", 10: "0.00535", 11: "0.00321", 12: "0.00107",
    },
}

# Full-year rate for mid-month property
SL_MM_FULL_YEAR: dict[str, str] = {
    "27.5": "0.03636",  # 1/27.5
    "39.0": "0.02564",  # 1/39
}


def _year_in_service(date_acquired: datetime.date, tax_year: int) -> int:
    """Calculate which year of service this asset is in for the given tax year."""
    return tax_year - date_acquired.year + 1


def _quarter(date: datetime.date) -> int:
    """Return the quarter (1-4) for a date."""
    return (date.month - 1) // 3 + 1


# ---------------------------------------------------------------------------
# Core MACRS depreciation percentage lookup
# ---------------------------------------------------------------------------

def _macrs_pct(
    method: str,
    life: int | float,
    convention: str,
    year_num: int,
    month_placed: int = 1,
    quarter_placed: int = 1,
) -> Decimal:
    """
    Look up the MACRS depreciation percentage for a given year.

    Args:
        method: "200DB", "150DB", or "SL"
        life: Recovery period in years
        convention: "HY", "MQ", or "MM"
        year_num: Year number (1-based) in the recovery period
        month_placed: Month placed in service (1-12), used for MM convention
        quarter_placed: Quarter placed in service (1-4), used for MQ convention

    Returns:
        Decimal percentage (e.g., Decimal("0.2000"))
    """
    life_int = int(life) if float(life) == int(life) else None
    life_str = f"{float(life):.1f}"

    # Straight-Line with Mid-Month convention (27.5-yr, 39-yr)
    if method == "SL" and convention == "MM" and life_str in SL_MM_FIRST_YEAR:
        total_years = int(float(life) + 1)  # 27.5 → 29 years, 39 → 41 years
        if year_num < 1 or year_num > total_years:
            return ZERO
        if year_num == 1:
            return Decimal(SL_MM_FIRST_YEAR[life_str].get(month_placed, "0"))
        full_rate = Decimal(SL_MM_FULL_YEAR[life_str])
        # Last year gets remainder
        if year_num == total_years:
            first_yr = Decimal(SL_MM_FIRST_YEAR[life_str].get(month_placed, "0"))
            full_years = total_years - 2
            remaining = ONE - first_yr - (full_rate * full_years)
            return max(ZERO, remaining)
        return full_rate

    # Straight-Line with Half-Year convention (any life)
    if method == "SL" and convention == "HY" and life_int:
        total_years = life_int + 1  # HY adds one extra year
        if year_num < 1 or year_num > total_years:
            return ZERO
        annual = ONE / Decimal(str(life_int))
        if year_num == 1 or year_num == total_years:
            return (annual / 2).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        return annual.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    # Straight-Line with Mid-Quarter convention
    if method == "SL" and convention == "MQ" and life_int:
        total_years = life_int + 1
        if year_num < 1 or year_num > total_years:
            return ZERO
        annual = ONE / Decimal(str(life_int))
        if year_num == 1:
            # First year: (4 - quarter + 0.5) / 4 of annual rate
            factor = Decimal(str(4 - quarter_placed + 0.5)) / Decimal("4")
            return (annual * factor).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        if year_num == total_years:
            # Last year: complement of first year
            first = (annual * Decimal(str(4 - quarter_placed + 0.5)) / Decimal("4"))
            full_years = total_years - 2
            remaining = ONE - first - (annual * full_years)
            return max(ZERO, remaining.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))
        return annual.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    # 200DB table lookup
    if method == "200DB" and life_int:
        if convention == "MQ" and life_int in MACRS_200DB_MQ:
            q_table = MACRS_200DB_MQ[life_int].get(quarter_placed)
            if q_table and 1 <= year_num <= len(q_table):
                return Decimal(q_table[year_num - 1])
            return ZERO
        # Half-Year (default)
        table = MACRS_200DB_HY.get(life_int)
        if table and 1 <= year_num <= len(table):
            return Decimal(table[year_num - 1])
        return ZERO

    # 150DB table lookup
    if method == "150DB" and life_int:
        table = MACRS_150DB_HY.get(life_int)
        if table and 1 <= year_num <= len(table):
            return Decimal(table[year_num - 1])
        return ZERO

    return ZERO


# ---------------------------------------------------------------------------
# Bonus depreciation suggestion
# ---------------------------------------------------------------------------

def suggest_bonus_pct(
    date_acquired: datetime.date,
    group_label: str = "",
    is_amortization: bool = False,
) -> Decimal:
    """
    Suggest bonus depreciation percentage based on acquisition date.

    OBBBA rules:
    - Acquired after Jan 19, 2025: 100%
    - Acquired on/before Jan 19, 2025: 40% phasedown
    - Land or amortization: 0%
    """
    if group_label == "Land" or is_amortization:
        return ZERO

    if date_acquired > OBBBA_CUTOFF_DATE:
        return HUNDRED
    # Pre-OBBBA binding contract rule: 40% phasedown
    return Decimal("40")


# ---------------------------------------------------------------------------
# Main calculation function
# ---------------------------------------------------------------------------

def calculate_asset_depreciation(
    asset: DepreciationAsset,
    tax_year: int,
) -> dict:
    """
    Calculate depreciation for a single asset for a given tax year.

    Returns dict with:
        current_depreciation: Decimal
        bonus_amount: Decimal
        amt_current_depreciation: Decimal
        state_current_depreciation: Decimal
        state_bonus_disallowed: Decimal

    Does NOT save — caller is responsible for saving.

    NOTE: Pass tax_year+1 to get projected depreciation for next year.
    """
    result = {
        "current_depreciation": ZERO,
        "bonus_amount": ZERO,
        "amt_current_depreciation": ZERO,
        "state_current_depreciation": ZERO,
        "state_bonus_disallowed": ZERO,
    }

    # Land is not depreciable
    if asset.group_label == "Land" or asset.method == "NONE":
        return result

    # No date acquired — cannot calculate
    if not asset.date_acquired:
        return result

    # Asset not yet placed in service
    if asset.date_acquired.year > tax_year:
        return result

    # Asset sold before this tax year (no depreciation in years after disposal)
    if asset.date_sold and asset.date_sold.year < tax_year:
        return result

    year_num = _year_in_service(asset.date_acquired, tax_year)
    month_placed = asset.date_acquired.month
    quarter_placed = _quarter(asset.date_acquired)
    business_pct = asset.business_pct / HUNDRED

    # -----------------------------------------------------------------------
    # Amortization path (Section 197, startup costs, etc.)
    # -----------------------------------------------------------------------
    if asset.is_amortization and asset.amort_months and asset.amort_months > 0:
        return _calculate_amortization(asset, tax_year, business_pct)

    # -----------------------------------------------------------------------
    # Federal depreciation
    # -----------------------------------------------------------------------

    depreciable_basis = asset.cost_basis * business_pct

    # 1. Section 179 — permanently reduces depreciable basis
    sec_179 = min(asset.sec_179_elected, depreciable_basis)
    depreciable_basis -= sec_179

    # 2. Bonus depreciation — permanently reduces basis after 179
    bonus_amount = ZERO
    if asset.bonus_pct > ZERO:
        bonus_pct_dec = asset.bonus_pct / HUNDRED
        bonus_amount = (depreciable_basis * bonus_pct_dec).quantize(PENNY, rounding=ROUND_HALF_UP)
        depreciable_basis -= bonus_amount

    # 3. Regular MACRS/SL on remaining basis
    regular_depr = ZERO
    if depreciable_basis > ZERO and asset.life and asset.life > 0:
        pct = _macrs_pct(
            method=asset.method,
            life=float(asset.life),
            convention=asset.convention,
            year_num=year_num,
            month_placed=month_placed,
            quarter_placed=quarter_placed,
        )
        # For year 1 with bonus, the MACRS table already assumes full basis,
        # so we apply the percentage to the post-bonus basis
        regular_depr = (depreciable_basis * pct).quantize(PENNY, rounding=ROUND_HALF_UP)

    # Disposal year: half-year / mid-quarter / mid-month conventions
    # already handled by table lookup (last year in table is partial)
    # For sold assets in the current year, the table percentages apply
    if asset.date_sold and asset.date_sold.year == tax_year and year_num > 1:
        # Use the convention to determine partial year
        if asset.convention == "HY":
            regular_depr = (regular_depr / 2).quantize(PENNY, rounding=ROUND_HALF_UP)
        elif asset.convention == "MQ":
            sold_quarter = _quarter(asset.date_sold)
            factor = Decimal(str(sold_quarter - 0.5)) / Decimal("4")
            regular_depr = (regular_depr * factor).quantize(PENNY, rounding=ROUND_HALF_UP)
        # MM: partial month in disposal year
        elif asset.convention == "MM":
            sold_month = asset.date_sold.month
            factor = Decimal(str(sold_month - 0.5)) / Decimal("12")
            regular_depr = (regular_depr * factor).quantize(PENNY, rounding=ROUND_HALF_UP)

    # sec_179 and bonus are year-1-only expense items
    if year_num == 1:
        current_depr = sec_179 + bonus_amount + regular_depr
    else:
        current_depr = regular_depr

    # Luxury auto cap
    if asset.is_listed_property and asset.group_label == "Vehicles":
        current_depr, regular_depr, bonus_amount = _apply_luxury_auto_cap(
            asset, tax_year, year_num, current_depr, regular_depr,
            bonus_amount, sec_179, business_pct,
        )

    # Listed property business use <= 50%: force SL
    if asset.is_listed_property and asset.business_pct <= Decimal("50"):
        # Recalculate using SL — basis always reduced by 179
        sl_basis = asset.cost_basis * business_pct - sec_179
        # No bonus for listed property under 50%
        bonus_amount = ZERO
        pct = _macrs_pct("SL", float(asset.life or 5), asset.convention, year_num,
                         month_placed, quarter_placed)
        regular_depr = (sl_basis * pct).quantize(PENNY, rounding=ROUND_HALF_UP)
        current_depr = regular_depr
        if year_num == 1:
            current_depr += sec_179

    result["current_depreciation"] = current_depr
    result["bonus_amount"] = bonus_amount if year_num == 1 else ZERO

    # -----------------------------------------------------------------------
    # AMT depreciation
    # -----------------------------------------------------------------------
    result["amt_current_depreciation"] = _calculate_amt(
        asset, tax_year, year_num, month_placed, quarter_placed,
        business_pct, sec_179, bonus_amount,
    )

    # -----------------------------------------------------------------------
    # State (Georgia) depreciation
    # -----------------------------------------------------------------------
    state_result = _calculate_state_ga(
        asset, tax_year, year_num, month_placed, quarter_placed,
        business_pct, sec_179, bonus_amount,
    )
    result["state_current_depreciation"] = state_result["current"]
    result["state_bonus_disallowed"] = state_result["bonus_disallowed"]

    return result


def _calculate_amortization(
    asset: DepreciationAsset,
    tax_year: int,
    business_pct: Decimal,
) -> dict:
    """Calculate amortization (Section 197, startup costs, etc.)."""
    result = {
        "current_depreciation": ZERO,
        "bonus_amount": ZERO,
        "amt_current_depreciation": ZERO,
        "state_current_depreciation": ZERO,
        "state_bonus_disallowed": ZERO,
    }

    basis = asset.cost_basis * business_pct
    monthly_rate = basis / Decimal(str(asset.amort_months))

    acq_year = asset.date_acquired.year
    acq_month = asset.date_acquired.month

    if tax_year == acq_year:
        # Pro-rate first year: months from acquisition through December
        months = 12 - acq_month + 1
        current = (monthly_rate * Decimal(str(months))).quantize(PENNY, rounding=ROUND_HALF_UP)
    elif asset.date_sold and asset.date_sold.year == tax_year:
        # Pro-rate last year: months from January through sale month
        months = asset.date_sold.month
        current = (monthly_rate * Decimal(str(months))).quantize(PENNY, rounding=ROUND_HALF_UP)
    else:
        # Full year
        current = (monthly_rate * Decimal("12")).quantize(PENNY, rounding=ROUND_HALF_UP)

    # Check if fully amortized
    total_prior = asset.prior_depreciation + asset.sec_179_prior
    remaining = basis - total_prior
    current = min(current, max(ZERO, remaining))

    result["current_depreciation"] = current
    # AMT and state are same as regular for amortization
    result["amt_current_depreciation"] = current
    result["state_current_depreciation"] = current

    return result


def _calculate_amt(
    asset: DepreciationAsset,
    tax_year: int,
    year_num: int,
    month_placed: int,
    quarter_placed: int,
    business_pct: Decimal,
    sec_179: Decimal,
    bonus_amount: Decimal,
) -> Decimal:
    """
    Calculate AMT depreciation.
    - 200DB assets: recalculate using 150DB, same life and convention
    - SL assets: same as regular (no AMT preference)
    """
    if asset.method == "SL" or asset.method == "150DB":
        # No AMT preference for SL or 150DB — AMT = regular
        # Recalculate using same method (since the caller's current_depreciation
        # hasn't been saved to the asset yet)
        depreciable_basis = asset.cost_basis * business_pct
        depreciable_basis -= sec_179
        depreciable_basis -= bonus_amount
        pct = _macrs_pct(
            method=asset.method,
            life=float(asset.life or 0),
            convention=asset.convention,
            year_num=year_num,
            month_placed=month_placed,
            quarter_placed=quarter_placed,
        )
        amt_depr = (depreciable_basis * pct).quantize(PENNY, rounding=ROUND_HALF_UP)
        if year_num == 1:
            amt_depr += sec_179 + bonus_amount

        # Disposal convention for sold assets (same as regular depreciation)
        if asset.date_sold and asset.date_sold.year == tax_year and year_num > 1:
            if asset.convention == "HY":
                amt_depr = (amt_depr / 2).quantize(PENNY, rounding=ROUND_HALF_UP)
            elif asset.convention == "MQ":
                sold_quarter = _quarter(asset.date_sold)
                factor = Decimal(str(sold_quarter - 0.5)) / Decimal("4")
                amt_depr = (amt_depr * factor).quantize(PENNY, rounding=ROUND_HALF_UP)
            elif asset.convention == "MM":
                sold_month = asset.date_sold.month
                factor = Decimal(str(sold_month - 0.5)) / Decimal("12")
                amt_depr = (amt_depr * factor).quantize(PENNY, rounding=ROUND_HALF_UP)

        return amt_depr

    # 200DB → use 150DB for AMT
    amt_method = asset.amt_method or "150DB"
    amt_life = float(asset.amt_life or asset.life or 0)

    if amt_life <= 0:
        return ZERO

    depreciable_basis = asset.cost_basis * business_pct
    depreciable_basis -= sec_179
    depreciable_basis -= bonus_amount  # Bonus is same for AMT post-TCJA

    pct = _macrs_pct(
        method=amt_method,
        life=amt_life,
        convention=asset.convention,
        year_num=year_num,
        month_placed=month_placed,
        quarter_placed=quarter_placed,
    )

    amt_depr = (depreciable_basis * pct).quantize(PENNY, rounding=ROUND_HALF_UP)

    # Add back 179 and bonus for first year
    if year_num == 1:
        amt_depr += sec_179 + bonus_amount

    # Disposal convention for sold assets (same as regular depreciation)
    if asset.date_sold and asset.date_sold.year == tax_year and year_num > 1:
        if asset.convention == "HY":
            amt_depr = (amt_depr / 2).quantize(PENNY, rounding=ROUND_HALF_UP)
        elif asset.convention == "MQ":
            sold_quarter = _quarter(asset.date_sold)
            factor = Decimal(str(sold_quarter - 0.5)) / Decimal("4")
            amt_depr = (amt_depr * factor).quantize(PENNY, rounding=ROUND_HALF_UP)
        elif asset.convention == "MM":
            sold_month = asset.date_sold.month
            factor = Decimal(str(sold_month - 0.5)) / Decimal("12")
            amt_depr = (amt_depr * factor).quantize(PENNY, rounding=ROUND_HALF_UP)

    return amt_depr


def _calculate_state_ga(
    asset: DepreciationAsset,
    tax_year: int,
    year_num: int,
    month_placed: int,
    quarter_placed: int,
    business_pct: Decimal,
    sec_179: Decimal,
    bonus_amount: Decimal,
) -> dict:
    """
    Calculate Georgia state depreciation.
    - Bonus: always disallowed
    - State 179 capped at GA_179_LIMIT
    - Use federal method/life/convention on full basis (no bonus reduction)
    """
    result = {"current": ZERO, "bonus_disallowed": ZERO}

    # Georgia disallows all federal bonus depreciation (year-1 only)
    result["bonus_disallowed"] = bonus_amount if year_num == 1 else ZERO

    # State depreciable basis: same as federal but without bonus
    depreciable_basis = asset.cost_basis * business_pct

    # State Section 179 (capped at GA limit, permanently reduces basis)
    state_179 = min(sec_179, GA_179_LIMIT)
    depreciable_basis -= state_179

    # State uses federal method/life/convention but on full basis (no bonus)
    state_method = asset.state_method or asset.method
    state_life = float(asset.state_life or asset.life or 0)

    if state_life <= 0:
        result["current"] = state_179 if year_num == 1 else ZERO
        return result

    pct = _macrs_pct(
        method=state_method,
        life=state_life,
        convention=asset.convention,
        year_num=year_num,
        month_placed=month_placed,
        quarter_placed=quarter_placed,
    )

    state_depr = (depreciable_basis * pct).quantize(PENNY, rounding=ROUND_HALF_UP)

    # Disposal year adjustments same as federal
    if asset.date_sold and asset.date_sold.year == tax_year and year_num > 1:
        if asset.convention == "HY":
            state_depr = (state_depr / 2).quantize(PENNY, rounding=ROUND_HALF_UP)
        elif asset.convention == "MQ":
            sold_quarter = _quarter(asset.date_sold)
            factor = Decimal(str(sold_quarter - 0.5)) / Decimal("4")
            state_depr = (state_depr * factor).quantize(PENNY, rounding=ROUND_HALF_UP)
        elif asset.convention == "MM":
            sold_month = asset.date_sold.month
            factor = Decimal(str(sold_month - 0.5)) / Decimal("12")
            state_depr = (state_depr * factor).quantize(PENNY, rounding=ROUND_HALF_UP)

    # state_179 is a year-1-only expense item
    if year_num == 1:
        result["current"] = state_179 + state_depr
    else:
        result["current"] = state_depr
    return result


def _apply_luxury_auto_cap(
    asset: DepreciationAsset,
    tax_year: int,
    year_num: int,
    current_depr: Decimal,
    regular_depr: Decimal,
    bonus_amount: Decimal,
    sec_179: Decimal,
    business_pct: Decimal,
) -> tuple[Decimal, Decimal, Decimal]:
    """Apply luxury auto depreciation limits. Returns (total, regular, bonus)."""
    has_bonus = bonus_amount > ZERO
    limit = _get_auto_limit(tax_year, year_num, has_bonus) * business_pct

    if current_depr <= limit:
        return current_depr, regular_depr, bonus_amount

    # Cap total depreciation at limit
    # Reduce bonus first, then regular
    excess = current_depr - limit
    if bonus_amount >= excess:
        bonus_amount -= excess
    else:
        excess -= bonus_amount
        bonus_amount = ZERO
        regular_depr = max(ZERO, regular_depr - excess)

    return limit, regular_depr, bonus_amount
