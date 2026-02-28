"""
Lacerte PDF parser for prior year return data.

Parses Lacerte-printed 1120-S PDF returns and extracts:
- Entity info (name, EIN, S election date, business activity code)
- Form line values (Lines 1-28 from page 1)
- Other deduction detail (from statement pages)
- Balance sheet (Schedule L: BOY and EOY)
- Schedule M-2 ending balances
- Shareholders (from K-1 pages: name, SSN, address, ownership, shares)
- Officers (from Form 1125-E: name, SSN, ownership, compensation)

Usage:
    from apps.imports.lacerte_parser import parse_lacerte_1120s
    result = parse_lacerte_1120s("path/to/return.pdf")
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber


@dataclass
class LacerteParseResult:
    """Structured result from parsing a Lacerte PDF."""

    entity_name: str = ""
    ein: str = ""
    form_code: str = ""
    tax_year: int = 0
    s_election_date: str = ""
    business_activity_code: str = ""
    number_of_shareholders: int = 0
    date_incorporated: str = ""

    # Form line values: line_number → amount (as int, dollars)
    line_values: dict[str, int] = field(default_factory=dict)

    # Other deductions detail: description → amount
    other_deductions: dict[str, int] = field(default_factory=dict)

    # Balance sheet: "L{line}_{boy|eoy}" → amount
    balance_sheet: dict[str, int] = field(default_factory=dict)

    # Schedule M-2 ending balances: "M2_{line}_{col}" → amount
    m2_balances: dict[str, int] = field(default_factory=dict)

    # Shareholders from K-1 pages
    shareholders: list[dict] = field(default_factory=list)

    # Officers from Form 1125-E
    officers: list[dict] = field(default_factory=list)

    # Import metadata
    source_file: str = ""
    page_count: int = 0
    warnings: list[str] = field(default_factory=list)


def _clean_amount(text: str) -> int | None:
    """Parse a Lacerte amount string to int (whole dollars). Returns None if not a number."""
    text = text.strip().rstrip(".")
    text = text.replace(",", "")
    # Handle parentheses for negatives
    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1]
    try:
        return int(text)
    except ValueError:
        return None


def _extract_ein(text: str) -> str:
    """Extract EIN (XX-XXXXXXX) from page text."""
    match = re.search(r"(\d{2}-\d{7})", text)
    return match.group(1) if match else ""


def _extract_tax_year(text: str) -> int:
    """Extract tax year from form header."""
    # Look for "calendar year YYYY" or "or YYYY"
    match = re.search(r"calendar year (\d{4})|or\s+(\d{4})", text)
    if match:
        return int(match.group(1) or match.group(2))
    return 0


def _detect_form_code(text: str) -> str:
    """Detect which IRS form this is from the header."""
    if "1120-S" in text[:500]:
        return "1120-S"
    if "1065" in text[:500]:
        return "1065"
    if "1120" in text[:500]:
        return "1120"
    return ""


def _extract_page1_lines(page) -> dict[str, int]:
    """
    Extract form line values from page 1 of the 1120-S.

    Uses word positions: line numbers at x~473-490, amounts at x~520-580.
    Matches by y-coordinate proximity.
    """
    words = page.extract_words(keep_blank_chars=True, x_tolerance=2, y_tolerance=2)

    # Line numbers on the right margin (x ~ 473-490)
    line_nums = [
        w for w in words
        if 470 <= w["x0"] <= 490 and w["top"] > 220
    ]
    # Amounts in the amount column (x ~ 520-580)
    amounts = [
        w for w in words
        if 520 <= w["x0"] <= 580 and w["top"] > 220
    ]

    result: dict[str, int] = {}
    for ln_word in line_nums:
        ln = ln_word["text"].strip()
        if not re.match(r"^\d+[a-z]?$", ln):
            continue

        # Find closest amount within 5 points of y
        closest = None
        min_dist = 999.0
        for a_word in amounts:
            dist = abs(a_word["top"] - ln_word["top"])
            if dist < min_dist and dist < 5:
                min_dist = dist
                closest = a_word

        if closest:
            amount = _clean_amount(closest["text"])
            if amount is not None:
                result[ln] = amount

    return result


def _extract_entity_name(words: list[dict], text: str) -> str:
    """
    Extract entity name from the TYPE/PRINT block on page 1.

    The entity name appears between the EIN area and the address,
    typically at y ~ 113-130, x < 400.
    """
    # Strategy: look for all-caps text in the name area
    name_words = [
        w for w in words
        if 110 < w["top"] < 140 and 60 < w["x0"] < 400
    ]
    name_words.sort(key=lambda w: (w["top"], w["x0"]))

    if not name_words:
        return ""

    # Group by y proximity (same line)
    lines: dict[int, list[str]] = {}
    for w in name_words:
        bucket = round(w["top"] / 11) * 11
        lines.setdefault(bucket, []).append(w["text"])

    # Take the first line that looks like a name (skip "TYPE", "OR", "PRINT")
    skip_words = {"TYPE", "OR", "PRINT"}
    for bucket in sorted(lines.keys()):
        parts = [p for p in lines[bucket] if p.strip() not in skip_words]
        if parts:
            name = " ".join(parts).strip()
            # Remove leading "TYPE" if it snuck in
            name = re.sub(r"^TYPE\s+", "", name)
            if len(name) > 3:
                return name

    return ""


def _extract_balance_sheet(text: str) -> dict[str, int]:
    """
    Extract Schedule L balance sheet values.

    Returns dict with keys like "L1_boy", "L1_eoy", etc.
    BOY = beginning of year, EOY = end of year.
    """
    result: dict[str, int] = {}

    sched_l_start = text.find("Schedule L")
    if sched_l_start < 0:
        return result

    bs_text = text[sched_l_start:]

    # Schedule L line patterns: number followed by description, then amounts
    # BOY amounts come first, EOY amounts second
    for line in bs_text.split("\n"):
        # Skip header/label lines
        if "Beginning of tax year" in line or "End of tax year" in line:
            continue
        if line.strip().startswith("Form "):
            break

        # Find line number at start
        ln_match = re.match(r"\s*(\d+[a-z]?)\s+", line)
        if not ln_match:
            continue
        ln = ln_match.group(1)

        # Find all amounts in the line
        amounts = re.findall(r"(\d{1,3}(?:,\d{3})*)\.", line)
        if not amounts:
            continue

        # Handle parenthetical negatives too
        neg_amounts = re.findall(r"\(\s*(\d{1,3}(?:,\d{3})*)\.\)", line)

        amounts_int = []
        for a in amounts:
            val = int(a.replace(",", ""))
            # Check if this amount appears inside parens
            if a in neg_amounts:
                val = -val
            amounts_int.append(val)

        if len(amounts_int) >= 2:
            result[f"L{ln}_boy"] = amounts_int[0]
            result[f"L{ln}_eoy"] = amounts_int[1]
        elif len(amounts_int) == 1:
            # Single amount — could be EOY only
            result[f"L{ln}_eoy"] = amounts_int[0]

    return result


def _extract_other_deductions(text: str) -> dict[str, int]:
    """
    Extract other deduction detail from statement pages.

    Looks for "Other Deductions" statement section and parses
    description + amount pairs.
    """
    result: dict[str, int] = {}

    # Find the "Other Deductions" statement section
    od_start = text.find("Other Deductions")
    if od_start < 0:
        return result

    od_text = text[od_start:]

    for line in od_text.split("\n"):
        line = line.strip()
        if not line or "Other Deductions" in line:
            continue
        # Stop at the Total line — everything after is a different statement
        if line.startswith("Total"):
            break
        # Stop if we hit a new statement section
        if line.startswith("Statement"):
            break

        # Pattern: description followed by dots/spaces then optional $ and amount
        match = re.search(
            r"^(.+?)\s*[.\s]{3,}\$?\s*(\d{1,3}(?:,\d{3})*)\.\s*$", line
        )
        if match:
            desc = match.group(1).strip().rstrip(". ")
            amount = int(match.group(2).replace(",", ""))
            if desc and amount > 0:
                result[desc] = amount

    return result


def _extract_schedule_k(text: str) -> dict[str, int]:
    """Extract Schedule K line values if present."""
    result: dict[str, int] = {}

    # Look for Schedule K section
    k_start = text.find("Schedule K")
    if k_start < 0:
        return result

    k_text = text[k_start:]

    # Line 18 reconciliation is the most reliable K value
    k18_match = re.search(r"18\s+(\d{1,3}(?:,\d{3})*)\.\s*$", k_text, re.MULTILINE)
    if k18_match:
        result["K18"] = int(k18_match.group(1).replace(",", ""))

    return result


def _extract_k1_shareholder(page) -> dict | None:
    """
    Extract shareholder info from a Schedule K-1 page.

    K-1 layout (Lacerte):
        Part I  (Corporation): EIN at (57, 183), name at (57, 207)
        Part II (Shareholder):
            SSN at (57, 375), name at (57, 399), address at (57, 409),
            city/state/zip at (57, 419), entity type at (201, 500),
            allocation % at (273, 519), BOY shares at (263-275, 548),
            EOY shares at (275, 561)
    """
    words = page.extract_words(keep_blank_chars=True, x_tolerance=2, y_tolerance=2)
    text = page.extract_text() or ""

    # Must be an actual K-1 page (not supplemental info page)
    if "Schedule K-1" not in text[:200]:
        return None
    # Skip supplemental/statement pages
    if "Supplemental Information" in text[:300]:
        return None
    if "Statement A" in text[:200]:
        return None

    def words_in_region(x_min, x_max, y_min, y_max):
        return sorted(
            [w for w in words if x_min <= w["x0"] <= x_max and y_min <= w["top"] <= y_max],
            key=lambda w: w["x0"],
        )

    def join_words(ws):
        return " ".join(w["text"] for w in ws).strip()

    # SSN (Part II line E) — at y~375
    ssn_words = words_in_region(50, 200, 370, 390)
    ssn = ""
    for w in ssn_words:
        if re.match(r"\d{3}-\d{2}-\d{4}", w["text"]):
            ssn = w["text"]
            break

    # Name (Part II line F) — at y~399, tighter range to avoid address bleed
    name_words = words_in_region(50, 290, 395, 408)
    name = join_words(name_words)

    # Address — at y~409
    addr_words = words_in_region(50, 290, 408, 420)
    address = join_words(addr_words)

    # City/State/Zip — at y~419
    csz_words = words_in_region(50, 290, 418, 435)
    csz = join_words(csz_words)
    city, state, zip_code = "", "", ""
    csz_match = re.match(r"(.+?),\s*([A-Z]{2})\s+(\d{5}(?:-\d{4})?)", csz)
    if csz_match:
        city = csz_match.group(1).strip()
        state = csz_match.group(2)
        zip_code = csz_match.group(3)

    # Entity type (Part II line F checkbox area)
    type_words = words_in_region(190, 300, 495, 515)
    entity_type = join_words(type_words) if type_words else ""

    # Ownership percentage (Part II line G)
    pct_words = words_in_region(260, 310, 515, 535)
    ownership = 0.0
    for w in pct_words:
        pct_match = re.match(r"(\d+\.?\d*)%?", w["text"])
        if pct_match:
            ownership = float(pct_match.group(1))
            break

    # Shares (Part II line H — BOY and EOY)
    boy_share_words = words_in_region(260, 300, 543, 560)
    eoy_share_words = words_in_region(260, 300, 556, 575)
    boy_shares = 0
    eoy_shares = 0
    for w in boy_share_words:
        val = _clean_amount(w["text"])
        if val is not None:
            boy_shares = val
            break
    for w in eoy_share_words:
        val = _clean_amount(w["text"])
        if val is not None:
            eoy_shares = val
            break

    if not name:
        return None

    # Clean address: strip city/state/zip if it leaked onto the address line
    if city and address.endswith(csz):
        address = address[: -len(csz)].rstrip(" ,")

    return {
        "name": name,
        "ssn": ssn,
        "address_line1": address,
        "city": city,
        "state": state,
        "zip_code": zip_code,
        "entity_type": entity_type.lower() if entity_type else "",
        "ownership_percentage": ownership,
        "beginning_shares": boy_shares,
        "ending_shares": eoy_shares,
    }


def _extract_officers(page) -> list[dict]:
    """
    Extract officer data from Form 1125-E page.

    1125-E layout (Lacerte):
        Officer rows start at top=171, ~24pt spacing, up to 20 rows.
        Columns: name (x 38-195), SSN (x 195-270), % time (x 270-340),
                 common % (x 340-410), preferred % (x 410-482),
                 compensation (x 482-575)
    """
    words = page.extract_words(keep_blank_chars=True, x_tolerance=2, y_tolerance=2)
    text = page.extract_text() or ""

    if "1125-E" not in text[:200]:
        return []

    officers = []
    # Officer rows at top ~ 171 + n*24 (n=0..19)
    for row_idx in range(20):
        row_top = 165 + row_idx * 24
        row_bot = row_top + 16

        row_words = [
            w for w in words
            if row_top <= w["top"] <= row_bot and w["text"] != "%"
        ]
        if not row_words:
            continue

        # Classify by x position
        name_parts = sorted(
            [w for w in row_words if w["x0"] < 195],
            key=lambda w: w["x0"],
        )
        ssn_parts = [w for w in row_words if 195 <= w["x0"] < 270]
        time_parts = [w for w in row_words if 270 <= w["x0"] < 340]
        common_parts = [w for w in row_words if 340 <= w["x0"] < 410]
        comp_parts = [w for w in row_words if w["x0"] >= 482]

        name = " ".join(w["text"] for w in name_parts).strip()
        if not name:
            continue

        ssn = ssn_parts[0]["text"] if ssn_parts else ""
        time_pct = 0.0
        if time_parts:
            try:
                time_pct = float(time_parts[0]["text"])
            except ValueError:
                pass
        common_pct = 0.0
        if common_parts:
            try:
                common_pct = float(common_parts[0]["text"])
            except ValueError:
                pass
        compensation = 0
        if comp_parts:
            val = _clean_amount(comp_parts[0]["text"])
            compensation = val if val is not None else 0

        officers.append({
            "name": name,
            "ssn": ssn,
            "percent_time": time_pct,
            "percent_ownership": common_pct,
            "compensation": compensation,
        })

    return officers


def _extract_m2_balances(text: str) -> dict[str, int]:
    """
    Extract Schedule M-2 ending balances from page 5.

    The M-2 ending balance (line 8) becomes the next year's beginning balance.
    """
    result: dict[str, int] = {}

    m2_start = text.find("Schedule M-2")
    if m2_start < 0:
        return result

    m2_text = text[m2_start:]

    for line in m2_text.split("\n"):
        # Match lines starting with a single digit line number
        ln_match = re.match(r"\s*(\d)\s+\D", line)
        if not ln_match:
            continue
        ln = ln_match.group(1)

        # Stop if we hit the form footer
        if "Form 1120" in line:
            break

        # Find amounts near end of line: "amount." pattern
        # Must be preceded by dots/spaces (leader dots) to avoid picking up
        # numbers embedded in the description text
        # Look for the last amount(s) on the line
        amounts_with_sign = re.findall(
            r"(?:^|[.\s])\s*(-?\d{1,3}(?:,\d{3})*)\.\s*$", line
        )
        if not amounts_with_sign:
            # Try with parens for negatives
            amounts_with_sign = re.findall(
                r"(?:^|[.\s])\s*\(\s*(\d{1,3}(?:,\d{3})*)\.\)\s*$", line
            )
            if amounts_with_sign:
                amounts_with_sign = ["-" + a for a in amounts_with_sign]

        if not amounts_with_sign:
            continue

        # Take the last amount on the line (column (a) — AAA)
        raw = amounts_with_sign[-1].replace(",", "")
        try:
            result[f"M2_{ln}"] = int(raw)
        except ValueError:
            pass

    return result


def parse_lacerte_1120s(pdf_path: str | Path) -> LacerteParseResult:
    """
    Parse a Lacerte-printed 1120-S return PDF.

    Args:
        pdf_path: Path to the Lacerte PDF file.

    Returns:
        LacerteParseResult with all extracted data.
    """
    pdf_path = Path(pdf_path)
    result = LacerteParseResult(
        source_file=pdf_path.name,
    )

    with pdfplumber.open(str(pdf_path)) as pdf:
        result.page_count = len(pdf.pages)

        if len(pdf.pages) == 0:
            result.warnings.append("PDF has no pages")
            return result

        # ---- Page 1: Header + Income/Deductions ----
        page1 = pdf.pages[0]
        text1 = page1.extract_text() or ""
        words1 = page1.extract_words(
            keep_blank_chars=True, x_tolerance=2, y_tolerance=2
        )

        result.form_code = _detect_form_code(text1)
        result.tax_year = _extract_tax_year(text1)
        result.ein = _extract_ein(text1)
        result.entity_name = _extract_entity_name(words1, text1)

        # S election date
        selec_match = re.search(r"(\d{1,2}/\d{2}/\d{4})", text1[:500])
        if selec_match:
            result.s_election_date = selec_match.group(1)

        # Business activity code
        bac_idx = text1.find("Business activity")
        if bac_idx >= 0:
            bac_match = re.search(r"(\d{6})", text1[bac_idx : bac_idx + 100])
            if bac_match:
                result.business_activity_code = bac_match.group(1)

        # Date incorporated (Line E on page 1 header)
        # Appears after S election date — look for a second date pattern
        # or look for "Date incorporated" label nearby
        date_inc_match = re.search(
            r"(?:date\s+incorporated|incorporated)\s*[:\-]?\s*(\d{1,2}/\d{2}/\d{4})",
            text1[:600],
            re.IGNORECASE,
        )
        if date_inc_match:
            result.date_incorporated = date_inc_match.group(1)
        else:
            # On Lacerte PDFs, dates appear in sequence: S election date, then
            # date incorporated. Look for a second date after the first one.
            all_dates = re.findall(r"(\d{1,2}/\d{2}/\d{4})", text1[:600])
            if len(all_dates) >= 2:
                # First date = S election date (Line A), second = date incorporated (Line E)
                result.date_incorporated = all_dates[1]

        # Number of shareholders
        sh_match = re.search(
            r"number of shareholders.*?(\d+)\s*$",
            text1,
            re.MULTILINE | re.IGNORECASE,
        )
        if sh_match:
            result.number_of_shareholders = int(sh_match.group(1))

        # Form line values
        result.line_values = _extract_page1_lines(page1)

        # ---- Remaining pages: Schedule K, L, Statements, K-1s, 1125-E ----
        full_text = text1
        for i in range(1, len(pdf.pages)):
            page = pdf.pages[i]
            page_text = page.extract_text() or ""
            full_text += "\n" + page_text

            # K-1 shareholder extraction
            if "Schedule K-1" in page_text[:200]:
                sh = _extract_k1_shareholder(page)
                if sh:
                    result.shareholders.append(sh)

            # 1125-E officer extraction
            if "1125-E" in page_text[:200]:
                officers = _extract_officers(page)
                if officers:
                    result.officers = officers

        result.balance_sheet = _extract_balance_sheet(full_text)
        result.other_deductions = _extract_other_deductions(full_text)

        # Schedule K (if present)
        k_values = _extract_schedule_k(full_text)
        if k_values:
            result.line_values.update(k_values)

        # Schedule M-2 ending balances
        result.m2_balances = _extract_m2_balances(full_text)

        # Validation
        if not result.ein:
            result.warnings.append("Could not extract EIN")
        if not result.entity_name:
            result.warnings.append("Could not extract entity name")
        if not result.line_values:
            result.warnings.append("No form line values extracted")

    return result
