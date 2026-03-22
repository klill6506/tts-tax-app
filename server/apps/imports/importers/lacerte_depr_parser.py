"""
Lacerte Depreciation Schedule TXT parser.

Parses the Lacerte fixed-width depreciation schedule export and returns
structured asset dicts ready for DepreciationAsset creation.

The Lacerte format has columns:
  No. | Description | Acquired | Sold | Cost/Basis | Bus.Pct | 179/SDA | Prior Depr | Method Life | Current Depr

Group headers appear as standalone lines (e.g., "Auto / Transport Equipment").
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

# Date pattern for sold date (appears between acquired date and cost)
_SOLD_DATE_RE = re.compile(r"(\d{1,2}/\d{2}/\d{2})")

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
    # Fields in order: Cost/Basis, Bus.Pct, 179/SDA, Prior Depr, [Method Life CurrDepr]
    # Extract all numbers from remainder
    tokens = remainder.split()

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


def parse_lacerte_txt(file_content: str) -> list[dict]:
    """
    Parse Lacerte depreciation schedule TXT export.

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
