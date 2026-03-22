"""
Lacerte Depreciation Schedule TXT parser.

Parses the Lacerte fixed-width depreciation schedule export and returns
structured asset dicts ready for DepreciationAsset creation.

Handles TWO formats:
1. Multi-line: one asset per line, all columns on the same row (proper TXT export)
2. Single-line: PDF text dump where left columns and right columns (method/life/current)
   are in separate blocks, often all on 1-2 lines

The Lacerte format has columns:
  No. | Description | Acquired | Sold | Cost/Basis | Bus.Pct | 179/SDA | Prior Depr | Method Life | Current Depr

Group headers appear as standalone text (e.g., "Auto / Transport Equipment").
Total and Grand Total lines are skipped.

Usage:
    from apps.imports.importers.lacerte_depr_parser import parse_lacerte_txt
    assets = parse_lacerte_txt(file_content)
"""

import re
from datetime import date

# Regex for an asset row: starts with optional whitespace + number
_ASSET_ROW_RE = re.compile(
    r"^\s*(\d{1,4})\s+"  # asset number
    r"(.+?)\s+"           # description (greedy-ish, stopped by date)
    r"(\d{1,2}/\d{2}/\d{2})"  # date acquired (M/DD/YY or MM/DD/YY)
)

# Regex for method/life at the end of a line: e.g., "200DB HY  5     288"
_METHOD_RE = re.compile(
    r"(200DB|150DB|SL|AMT)\s+"   # method
    r"(HY|MQ|MM|S/L)\s+"        # convention
    r"(\d+)\s+"                  # life (years)
    r"([\d,]+)\s*$"              # current depreciation
)

# Alternate method regex when current depr is 0 at end of line
_METHOD_ZERO_RE = re.compile(
    r"(200DB|150DB|SL|AMT)\s+"
    r"(HY|MQ|MM|S/L)\s+"
    r"(\d+)\s+"
    r"([\d,]+|0)\s*$"
)

# Lines to skip
_SKIP_PATTERNS = [
    re.compile(r"^\s*$"),                          # blank
    re.compile(r"^\s*_{3,}"),                       # underscores (separators)
    re.compile(r"^\s*Total\s", re.IGNORECASE),     # subtotals
    re.compile(r"^\s*Grand\s+Total", re.IGNORECASE),  # grand total
    re.compile(r"^\s*No\.\s+Description", re.IGNORECASE),  # column header
    re.compile(r"^\s*Prior\s+Cur", re.IGNORECASE),  # column sub-header
    re.compile(r"^\s*Date\s+Date\s+Cost", re.IGNORECASE),
    re.compile(r"^\s*Form\s+\d{4}", re.IGNORECASE),  # "Form 1120S"
    re.compile(r"^\s*Current\s*$", re.IGNORECASE),
    re.compile(r"^\s*Method\s+Life\s+Depr", re.IGNORECASE),
    re.compile(r"^\d{1,2}/\d{2}/\d{2}\s+\d{4}\s+Federal"),  # header line 1
    re.compile(r"^\s*Page\s+\d", re.IGNORECASE),
    re.compile(r"^\s*\d{2}-\d{7}\s*$"),            # standalone EIN
    re.compile(r"^\s*\d{2}:\d{2}[AP]M\s*$", re.IGNORECASE),  # timestamp
    re.compile(r"^\s*Total\s+Depreciation", re.IGNORECASE),
]

# Group name mapping: Lacerte group header → our asset_group value
GROUP_MAP: dict[str, str] = {
    "auto": "vehicles",
    "auto / transport equipment": "vehicles",
    "auto/transport equipment": "vehicles",
    "transport": "vehicles",
    "vehicles": "vehicles",
    "machinery and equipment": "machinery_equipment",
    "machinery & equipment": "machinery_equipment",
    "machinery": "machinery_equipment",
    "furniture and fixtures": "furniture_fixtures",
    "furniture & fixtures": "furniture_fixtures",
    "furniture": "furniture_fixtures",
    "buildings": "buildings",
    "building": "buildings",
    "land": "land",
    "land improvements": "improvements",
    "improvements": "improvements",
    "leasehold improvements": "improvements",
    "intangible assets": "intangibles",
    "intangibles": "intangibles",
    "other depreciation": "machinery_equipment",
    "other": "machinery_equipment",
}

# Known group header patterns for detecting in single-line format
_GROUP_PATTERNS = [
    (re.compile(r"Auto\s*/?\s*Transport\s+Equipment", re.IGNORECASE), "vehicles"),
    (re.compile(r"Machinery\s+(?:and|&)\s+Equipment", re.IGNORECASE), "machinery_equipment"),
    (re.compile(r"Furniture\s+(?:and|&)\s+Fixtures", re.IGNORECASE), "furniture_fixtures"),
    (re.compile(r"Land\s+Improvements?", re.IGNORECASE), "improvements"),
    (re.compile(r"Leasehold\s+Improvements?", re.IGNORECASE), "improvements"),
    (re.compile(r"Intangible\s+Assets?", re.IGNORECASE), "intangibles"),
    (re.compile(r"Intangibles?(?:\s*/\s*Amortization)?", re.IGNORECASE), "intangibles"),
    (re.compile(r"Buildings?", re.IGNORECASE), "buildings"),
    (re.compile(r"(?<!\w)Land(?!\s+Imp)", re.IGNORECASE), "land"),
    (re.compile(r"Other\s+Depreciation", re.IGNORECASE), "machinery_equipment"),
]


def _parse_date(date_str: str) -> str | None:
    """Convert M/DD/YY or MM/DD/YY to YYYY-MM-DD string.

    Year pivot: 00-30 → 2000-2030, 31-99 → 1931-1999.
    """
    if not date_str:
        return None
    parts = date_str.split("/")
    if len(parts) != 3:
        return None
    try:
        month = int(parts[0])
        day = int(parts[1])
        year_2d = int(parts[2])
    except ValueError:
        return None
    year = 2000 + year_2d if year_2d <= 30 else 1900 + year_2d
    try:
        d = date(year, month, day)
        return d.isoformat()
    except ValueError:
        return None


def _parse_amount(amount_str: str) -> int:
    """Parse a dollar amount string like '18,000' or '89,642' to int."""
    if not amount_str:
        return 0
    clean = amount_str.replace(",", "").replace("$", "").strip()
    if not clean:
        return 0
    try:
        return int(clean)
    except ValueError:
        try:
            return int(float(clean))
        except ValueError:
            return 0


def _classify_group(header_text: str) -> str:
    """Map a Lacerte group header to our asset_group value."""
    normalized = header_text.strip().lower()
    # Try exact match first
    if normalized in GROUP_MAP:
        return GROUP_MAP[normalized]
    # Try substring match
    for key, value in GROUP_MAP.items():
        if key in normalized:
            return value
    return "machinery_equipment"  # default fallback


def _should_skip(line: str) -> bool:
    """Check if a line should be skipped."""
    for pattern in _SKIP_PATTERNS:
        if pattern.search(line):
            return True
    return False


def _is_group_header(line: str) -> bool:
    """Detect group headers: alphabetic text without leading numbers, not a skip line."""
    stripped = line.strip()
    if not stripped:
        return False
    if _should_skip(line):
        return False
    # Group headers don't start with a digit and contain mostly letters
    if stripped[0].isdigit():
        return False
    # Must have at least some letters
    alpha_chars = sum(1 for c in stripped if c.isalpha())
    if alpha_chars < 3:
        return False
    # Should not contain date patterns
    if re.search(r"\d{1,2}/\d{2}/\d{2}", stripped):
        return False
    # Should not contain large numbers (amounts)
    if re.search(r"\d{2,},\d{3}", stripped):
        return False
    return True


def _parse_asset_line(line: str, current_group: str) -> dict | None:
    """Parse a single asset row into a dict.

    Returns None if the line doesn't match the expected asset pattern.
    """
    match = _ASSET_ROW_RE.match(line)
    if not match:
        return None

    asset_number = int(match.group(1))
    description = match.group(2).strip()
    date_acquired_raw = match.group(3)

    # Everything after the acquired date
    remainder = line[match.end():]

    # Check for a sold date (another date pattern right after acquired)
    date_sold_raw = None
    sold_match = re.match(r"\s*(\d{1,2}/\d{2}/\d{2})\s*", remainder)
    if sold_match:
        date_sold_raw = sold_match.group(1)
        remainder = remainder[sold_match.end():]

    # Parse remaining numeric fields from the remainder
    cost_basis = 0
    business_pct = 100.0
    section_179 = 0
    prior_depreciation = 0
    current_depreciation = 0
    method = ""
    convention = ""
    life = 0

    # Parse method/life/current_depr from end if present
    method_match = _METHOD_RE.search(remainder) or _METHOD_ZERO_RE.search(remainder)
    if method_match:
        method = method_match.group(1)
        convention = method_match.group(2)
        life = int(method_match.group(3))
        current_depreciation = _parse_amount(method_match.group(4))
        # Get the part before method for numeric parsing
        before_method = remainder[:method_match.start()]
        tokens = before_method.split()
    else:
        tokens = remainder.split()

    # Parse numeric tokens left-to-right
    numeric_values = []
    for tok in tokens:
        clean = tok.replace(",", "").strip()
        if not clean:
            continue
        try:
            val = float(clean)
            numeric_values.append((val, tok))
        except ValueError:
            continue

    if len(numeric_values) >= 1:
        cost_basis = _parse_amount(numeric_values[0][1])
    if len(numeric_values) >= 2:
        # Determine if second value is Bus.Pct or goes to another field
        val, tok = numeric_values[1]
        if 0 < val <= 100 and "." in tok:
            business_pct = val
            remaining = numeric_values[2:]
        else:
            remaining = numeric_values[1:]

        # Remaining values are [179/SDA, Prior Depr] or just [Prior Depr]
        if len(remaining) == 1:
            # Only one value → it's prior depreciation (179/SDA was blank)
            prior_depreciation = _parse_amount(remaining[0][1])
        elif len(remaining) >= 2:
            # Two values → 179/SDA, then prior depreciation
            section_179 = _parse_amount(remaining[0][1])
            prior_depreciation = _parse_amount(remaining[1][1])

    return {
        "asset_number": asset_number,
        "description": description,
        "date_acquired": _parse_date(date_acquired_raw),
        "date_sold": _parse_date(date_sold_raw) if date_sold_raw else None,
        "cost_basis": cost_basis,
        "business_pct": business_pct,
        "section_179": section_179,
        "prior_depreciation": prior_depreciation,
        "current_depreciation": current_depreciation,
        "method": method,
        "convention": convention,
        "life": life,
        "asset_group": current_group,
        "raw_line": line.rstrip(),
    }


# ---------------------------------------------------------------------------
# Single-line (PDF text dump) format parser
# ---------------------------------------------------------------------------


def _is_single_line_format(content: str) -> bool:
    """Detect if the content is a single-line PDF text dump rather than
    a properly formatted multi-line file."""
    meaningful = [ln for ln in content.splitlines() if ln.strip()]
    if len(meaningful) <= 4:
        return True
    # Also check if most content is on one very long line
    if meaningful and max(len(ln) for ln in meaningful) > 500:
        return True
    return False


def _parse_single_line_format(text: str) -> list[dict]:
    """Parse the single-line PDF text dump format from Lacerte.

    In this format, left-side columns (No, Desc, Date, Cost, Prior) and
    right-side columns (Method, Life, Current) are in separate blocks —
    the method block appears at the end after all asset data.
    """
    # --- Step 1: Split left block (asset data) from right block (method data) ---
    # The method block is signaled by "Method Life Depr" or "Current Method Life Depr"
    method_marker = re.search(
        r"(?:\d{2}:\d{2}[AP]M\s+)?(?:Current\s+)?Method\s+Life\s+Depr",
        text, re.IGNORECASE,
    )
    if method_marker:
        left = text[:method_marker.start()]
        right = text[method_marker.end():]
    else:
        left = text
        right = ""

    # --- Step 2: Extract method/convention/life/current from right block ---
    # In the PDF text dump, entries are often concatenated without spaces:
    #   "288200DB MQ 5 2,266" = current_depr=288 then method=200DB...
    # Insert a space before each method code to separate them.
    right = re.sub(r"(\d)(200DB|150DB|SL|AMT)", r"\1 \2", right)
    method_entries = re.findall(
        r"(200DB|150DB|SL|AMT)\s+(HY|MQ|MM|S/L)\s+(\d+)\s+([\d,]+)",
        right,
    )

    # --- Step 3: Clean up left block by stripping noise inline ---
    # Strip everything before first group header (header/metadata)
    first_group_pos = None
    for pattern, _ in _GROUP_PATTERNS:
        m = pattern.search(left)
        if m and (first_group_pos is None or m.start() < first_group_pos):
            first_group_pos = m.start()
    if first_group_pos is not None:
        left = left[first_group_pos:]

    # Strip total lines: "Total <group> <amounts>" and "Grand Total..."
    left = re.sub(r"Total\s+Depreciation[\d,.\s]*", " ", left, flags=re.IGNORECASE)
    left = re.sub(r"Grand\s+Total[\d,.\s]*", " ", left, flags=re.IGNORECASE)
    left = re.sub(r"Total\s+[\w\s&/]+?[\d,]+[\d,.\s]*", " ", left, flags=re.IGNORECASE)

    # Replace underscore runs with spaces (they're just visual separators)
    left = re.sub(r"_{3,}", " ", left)

    # Collapse whitespace
    left = re.sub(r"\s+", " ", left)

    # --- Step 4: Find group header positions in cleaned left block ---
    group_positions: list[tuple[int, str]] = []
    for pattern, group in _GROUP_PATTERNS:
        for m in pattern.finditer(left):
            group_positions.append((m.start(), group))
    group_positions.sort()

    # --- Step 5: Find all asset entries in cleaned left block ---
    asset_re = re.compile(
        r"(?<![,.\d])"          # not preceded by comma, dot, or digit
        r"(\d{1,3})"            # asset number
        r"\s+"
        r"(.*?)"                # description (non-greedy)
        r"\s+"
        r"(\d{1,2}/\d{2}/\d{2})"  # date acquired
    )

    raw_assets: list[dict] = []
    matches = list(asset_re.finditer(left))

    for idx, m in enumerate(matches):
        asset_num = int(m.group(1))
        desc = m.group(2).strip()

        # Skip asset number 0
        if asset_num == 0:
            continue

        # Skip if description looks like noise
        if re.search(r"Federal|Summary|Schedule|Client\s+\w|Page\s+\d", desc, re.IGNORECASE):
            continue

        date_acq_raw = m.group(3)

        # Determine which group this asset belongs to
        asset_pos = m.start()
        current_group = "machinery_equipment"
        for gpos, group in group_positions:
            if gpos < asset_pos:
                current_group = group

        # Get the amount text between this date and the next match
        after_date_start = m.end()
        if idx + 1 < len(matches):
            after_date_end = matches[idx + 1].start()
        else:
            after_date_end = len(left)

        amount_text = left[after_date_start:after_date_end]

        # Check for sold date right after acquired date
        date_sold_raw = None
        sold_match = re.match(r"\s*(\d{1,2}/\d{2}/\d{2})", amount_text)
        if sold_match:
            date_sold_raw = sold_match.group(1)
            amount_text = amount_text[sold_match.end():]

        # Parse numeric tokens
        numeric_values = []
        for tok in amount_text.split():
            clean = tok.replace(",", "").strip()
            if not clean:
                continue
            try:
                val = float(clean)
                numeric_values.append((val, tok))
            except ValueError:
                continue

        cost_basis = 0
        business_pct = 100.0
        section_179 = 0
        prior_depreciation = 0

        if len(numeric_values) >= 1:
            cost_basis = _parse_amount(numeric_values[0][1])
        if len(numeric_values) >= 2:
            val, tok = numeric_values[1]
            if 0 < val <= 100 and "." in tok:
                business_pct = val
                remaining = numeric_values[2:]
            else:
                remaining = numeric_values[1:]

            if len(remaining) == 1:
                prior_depreciation = _parse_amount(remaining[0][1])
            elif len(remaining) >= 2:
                section_179 = _parse_amount(remaining[0][1])
                prior_depreciation = _parse_amount(remaining[1][1])

        raw_assets.append({
            "asset_number": asset_num,
            "description": desc,
            "date_acquired": _parse_date(date_acq_raw),
            "date_sold": _parse_date(date_sold_raw) if date_sold_raw else None,
            "cost_basis": cost_basis,
            "business_pct": business_pct,
            "section_179": section_179,
            "prior_depreciation": prior_depreciation,
            "current_depreciation": 0,
            "method": "",
            "convention": "",
            "life": 0,
            "asset_group": current_group,
            "raw_line": "",
        })

    # --- Step 5: Merge method data (right block) into assets by position ---
    method_idx = 0
    for asset in raw_assets:
        if method_idx < len(method_entries):
            meth, conv, life_str, curr = method_entries[method_idx]
            asset["method"] = meth
            asset["convention"] = conv
            asset["life"] = int(life_str)
            asset["current_depreciation"] = _parse_amount(curr)
            method_idx += 1

    return raw_assets


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_lacerte_txt(file_content: str) -> list[dict]:
    """
    Parse Lacerte depreciation schedule TXT export.

    Auto-detects format: multi-line (proper TXT) or single-line (PDF text dump).

    Returns list of dicts, each representing one asset:
    {
        "asset_number": 8,
        "description": "2008 Chevy Truck",
        "date_acquired": "2020-08-12",
        "date_sold": None,
        "cost_basis": 18000,
        "business_pct": 100.0,
        "section_179": 0,
        "prior_depreciation": 17712,
        "current_depreciation": 288,
        "method": "200DB",
        "convention": "HY",
        "life": 5,
        "asset_group": "vehicles",
        "raw_line": "...",
    }
    """
    if not file_content or not file_content.strip():
        return []

    # Auto-detect format
    if _is_single_line_format(file_content):
        return _parse_single_line_format(file_content)

    # Multi-line format: parse line by line
    lines = file_content.splitlines()
    assets: list[dict] = []
    current_group = "machinery_equipment"  # default

    for line in lines:
        # Skip blank, header, total, and separator lines
        if _should_skip(line):
            continue

        # Check for group header
        if _is_group_header(line):
            current_group = _classify_group(line)
            continue

        # Try to parse as an asset row
        asset = _parse_asset_line(line, current_group)
        if asset:
            assets.append(asset)

    return assets
