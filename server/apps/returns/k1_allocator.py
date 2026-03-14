"""
K-1 allocation engine for Form 1065 partnerships.

Allocates entity-level Schedule K values to individual partners based on:
1. PartnerAllocation overrides per category (Lacerte-style special allocations)
2. Default ownership % (profit_pct for income, loss_pct for losses)

Also computes per-partner:
- Guaranteed payments (Box 4): per-partner amounts, not allocated
- Self-employment earnings (Box 14): depends on partner type

Usage:
    from apps.returns.k1_allocator import allocate_k1
    k1_data = allocate_k1(tax_return, partner, k_values)
"""

from decimal import Decimal, InvalidOperation

from .models import AllocationCategory, Partner, PartnerAllocation

ZERO = Decimal("0")
HUNDRED = Decimal("100")


# ---------------------------------------------------------------------------
# K-line → allocation category mapping
# ---------------------------------------------------------------------------

# Maps Schedule K line numbers to AllocationCategory values.
# Lines not in this map are allocated by profit_pct (income) or loss_pct (loss).
K_LINE_CATEGORY: dict[str, str] = {
    "K1": AllocationCategory.ORDINARY,
    "K2": AllocationCategory.RENTAL_RE,
    "K3c": AllocationCategory.OTHER_RENTAL,
    "K5": AllocationCategory.INTEREST,
    "K6a": AllocationCategory.DIVIDENDS,
    "K6b": AllocationCategory.DIVIDENDS,
    "K7": AllocationCategory.ROYALTIES,
    "K8": AllocationCategory.ST_CAPITAL,
    "K9a": AllocationCategory.LT_CAPITAL,
    "K9b": AllocationCategory.LT_CAPITAL,
    "K9c": AllocationCategory.LT_CAPITAL,
    "K10": AllocationCategory.SEC_1231,
    "K11": AllocationCategory.OTHER_RENTAL,  # other income follows ordinary
    "K12": AllocationCategory.SEC_179,
    "K13a": AllocationCategory.CHARITABLE,
    "K13d": AllocationCategory.INTEREST,  # investment interest follows interest
    "K19a": AllocationCategory.DISTRIBUTIONS,
}

# K-lines that are allocated by pro-rata (not special allocation)
K_LINES_PRO_RATA = [
    "K1", "K2", "K3c",
    "K5", "K6a", "K6b", "K7",
    "K8", "K9a", "K9b", "K9c", "K10",
    "K11", "K12", "K13a", "K13d",
    "K15a", "K16a",
    "K17a",
    "K18a", "K18b", "K18c",
    "K20a", "K20b",
]


def _get_k_decimal(k_values: dict[str, str], line: str) -> Decimal:
    """Get a Schedule K value as Decimal, defaulting to 0."""
    raw = k_values.get(line, "")
    if not raw:
        return ZERO
    try:
        return Decimal(raw)
    except InvalidOperation:
        return ZERO


def get_allocation_pct(
    partner: Partner,
    category: str | None,
    k_value: Decimal,
    alloc_map: dict[str, Decimal],
) -> Decimal:
    """
    Determine the allocation percentage for a partner and category.

    Priority:
    1. PartnerAllocation override (if exists for this category)
    2. profit_pct (if k_value >= 0, i.e. income/gain)
    3. loss_pct (if k_value < 0, i.e. loss)

    Returns percentage as decimal (e.g., 0.50 for 50%).
    """
    # Check for special allocation override
    if category and category in alloc_map:
        return alloc_map[category] / HUNDRED

    # Default: profit % for income, loss % for losses
    if k_value >= 0:
        return partner.profit_pct / HUNDRED
    else:
        return partner.loss_pct / HUNDRED


def allocate_k1(
    tax_return,
    partner: Partner,
    k_values: dict[str, str],
) -> dict[str, Decimal]:
    """
    Allocate entity-level Schedule K values to a single partner.

    Returns a dict of K-1 box number → allocated Decimal amount.

    K-1 Box mapping for 1065:
        Box 1: Ordinary business income/loss (K1)
        Box 2: Net rental real estate income/loss (K2)
        Box 3: Other net rental income/loss (K3c)
        Box 4a: Guaranteed payments for services (per-partner)
        Box 4b: Guaranteed payments for capital (per-partner)
        Box 4c: Total guaranteed payments (per-partner)
        Box 5: Interest income (K5)
        Box 6a: Ordinary dividends (K6a)
        Box 6b: Qualified dividends (K6b)
        Box 7: Royalties (K7)
        Box 8: Net ST capital gain/loss (K8)
        Box 9a: Net LT capital gain/loss (K9a)
        Box 9b: Collectibles (28%) gain/loss (K9b)
        Box 9c: Unrecaptured section 1250 gain (K9c)
        Box 10: Net section 1231 gain/loss (K10)
        Box 11: Other income/loss (K11)
        Box 12: Section 179 deduction (K12)
        Box 13a: Charitable contributions (K13a)
        Box 13d: Investment interest expense (K13d)
        Box 14a: Net earnings from self-employment
        Box 14b: Gross farming income (K14b)
        Box 14c: Gross nonfarm income (K14c)
        Box 15a: Low-income housing credit (K15a)
        Box 16a: Foreign taxes paid (K16a)
        Box 17a: Post-1986 depreciation adjustment (K17a)
        Box 18a: Tax-exempt interest income (K18a)
        Box 18b: Other tax-exempt income (K18b)
        Box 18c: Nondeductible expenses (K18c)
        Box 19a: Distributions (per-partner)
        Box 20a: Investment income (K20a)
        Box 20b: Investment expenses (K20b)
    """
    # Load this partner's special allocation overrides
    allocs = PartnerAllocation.objects.filter(
        partner=partner, tax_return=tax_return,
    ).values_list("category", "percentage")
    alloc_map: dict[str, Decimal] = {cat: pct for cat, pct in allocs}

    result: dict[str, Decimal] = {}

    # ---------- Pro-rata allocated lines ----------
    k_to_box: dict[str, str] = {
        "K1": "1", "K2": "2", "K3c": "3",
        "K5": "5", "K6a": "6a", "K6b": "6b", "K7": "7",
        "K8": "8", "K9a": "9a", "K9b": "9b", "K9c": "9c",
        "K10": "10", "K11": "11", "K12": "12",
        "K13a": "13a", "K13d": "13d",
        "K15a": "15a", "K16a": "16a",
        "K17a": "17a",
        "K18a": "18a", "K18b": "18b", "K18c": "18c",
        "K20a": "20a", "K20b": "20b",
    }

    for k_line, box in k_to_box.items():
        entity_amount = _get_k_decimal(k_values, k_line)
        if entity_amount == 0:
            continue

        category = K_LINE_CATEGORY.get(k_line)
        pct = get_allocation_pct(partner, category, entity_amount, alloc_map)
        share = (entity_amount * pct).quantize(Decimal("1"))
        if share != 0:
            result[box] = share

    # ---------- Guaranteed payments (per-partner, not allocated) ----------
    gp_svc = partner.gp_services
    gp_cap = partner.gp_capital
    gp_total = gp_svc + gp_cap

    if gp_svc:
        result["4a"] = gp_svc.quantize(Decimal("1"))
    if gp_cap:
        result["4b"] = gp_cap.quantize(Decimal("1"))
    if gp_total:
        result["4c"] = gp_total.quantize(Decimal("1"))

    # ---------- Distributions (per-partner, not allocated) ----------
    if partner.distributions:
        result["19a"] = partner.distributions.quantize(Decimal("1"))

    # ---------- Self-employment earnings (Box 14) ----------
    se = compute_self_employment(partner, result)
    if se["14a"]:
        result["14a"] = se["14a"]
    if se["14b"]:
        result["14b"] = se["14b"]
    if se["14c"]:
        result["14c"] = se["14c"]

    return result


def compute_self_employment(
    partner: Partner,
    k1_data: dict[str, Decimal],
) -> dict[str, Decimal]:
    """
    Compute self-employment earnings per partner (K-1 Box 14).

    Rules:
    - General partner: ordinary income (Box 1) + guaranteed payments (Box 4c)
    - Limited partner: guaranteed payments for services ONLY
    - LLC member: treat as general unless partner_type == 'limited'

    Returns dict with keys 14a, 14b, 14c.
    """
    gp_services = partner.gp_services or ZERO
    gp_total = (partner.gp_services or ZERO) + (partner.gp_capital or ZERO)
    box1 = k1_data.get("1", ZERO)

    if partner.partner_type == "limited":
        # Limited partners: only GP for services is SE income
        se_earnings = gp_services
    else:
        # General partners and LLC members: ordinary income + all GP
        se_earnings = box1 + gp_total

    # 14b: gross farming income (partner's share of entity-level K14b)
    # For SE, we use the partner's share — but this is informational
    box_14b = k1_data.get("14b", ZERO)
    # 14c: gross nonfarm income (partner's share of entity-level K14c)
    box_14c = k1_data.get("14c", ZERO)

    return {
        "14a": se_earnings.quantize(Decimal("1")) if se_earnings else ZERO,
        "14b": box_14b.quantize(Decimal("1")) if box_14b else ZERO,
        "14c": box_14c.quantize(Decimal("1")) if box_14c else ZERO,
    }


def allocate_all_k1s(tax_return) -> list[dict]:
    """
    Allocate K-1 data for ALL partners on a partnership return.

    Returns a list of dicts, each with:
        - partner: Partner instance
        - k1_data: dict of box → Decimal (from allocate_k1)

    Used by render_all_k1s (PDF rendering) and potentially by the frontend.
    """
    from .models import FormFieldValue

    if tax_return.form_definition.code != "1065":
        return []

    partners = Partner.objects.filter(
        tax_return=tax_return, is_active=True,
    ).order_by("sort_order", "name").prefetch_related("allocations")

    if not partners.exists():
        return []

    # Load entity-level Schedule K values
    fvs = FormFieldValue.objects.filter(
        tax_return=tax_return,
    ).select_related("form_line")

    k_values: dict[str, str] = {}
    for fv in fvs:
        ln = fv.form_line.line_number
        if ln.startswith("K"):
            k_values[ln] = fv.value

    results = []
    for partner in partners:
        k1_data = allocate_k1(tax_return, partner, k_values)
        results.append({
            "partner": partner,
            "k1_data": k1_data,
        })

    return results
