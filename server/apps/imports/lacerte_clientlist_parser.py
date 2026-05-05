"""
Lacerte "Client List" custom-report PDF parser.

Parses the tabular client-list report Lacerte exports (landscape, two-page
horizontal spread per group of clients):

    LEFT page columns:   Full Name (LNF) | TP SSN | TP DOB | TP Email |
                         SP F. Name | SP L. Name | SP DOB
    RIGHT page columns:  Sp. Day Phone | Sp Email Addr | SP SSN |
                         Street Address | City | State | Zip | Preparer

Pages 1-2 form one spread, 3-4 another, etc. Same client row has the same
y-coordinate on both pages.

Scope: taxpayer demographics only (name, SSN, DOB, address, spouse fields).
Filing status is *inferred* (spouse present -> mfj, else single) — this
report has no explicit filing status column and no dependents.

Usage:
    from apps.imports.lacerte_clientlist_parser import parse_lacerte_clientlist
    records = parse_lacerte_clientlist("path/to/report.pdf")
    for r in records:
        print(r.full_name_lnf, r.tp_ssn_last4())
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import pdfplumber

# Column x-range boundaries, derived from inspecting the real report layout.
# (Values are PDF user-space points; page is 792 wide = landscape letter.)
LEFT_COLUMNS = {
    "name":     (40, 235),
    "tp_ssn":   (235, 295),
    "tp_dob":   (295, 350),
    "tp_email": (350, 520),
    "sp_first": (520, 595),
    "sp_last":  (595, 665),
    "sp_dob":   (665, 760),
}

RIGHT_COLUMNS = {
    "sp_phone_label": (40, 120),
    "sp_email":       (120, 250),
    "sp_ssn":         (250, 315),
    "street":         (315, 459),
    "city":           (459, 545),
    "state":          (545, 580),
    "zip":            (580, 639),
    "preparer":       (639, 760),
}

# y-range that contains data rows (skip page header above, footer below if any).
DATA_Y_MIN = 110.0
DATA_Y_MAX = 600.0
# Each report row is ~12 points tall. Bucket y-positions so both pages align.
Y_BUCKET = 6


@dataclass
class LacerteDemographic:
    """One taxpayer record parsed from a Lacerte client-list report row."""

    # Raw LNF string as it appears in the report (e.g. "ANDERSON, SCOTT AND TIFFANY")
    full_name_lnf: str = ""

    # Parsed taxpayer name parts
    tp_last_name: str = ""
    tp_first_name: str = ""
    tp_middle_initial: str = ""
    tp_suffix: str = ""

    # Spouse name parts (empty if single filer)
    sp_first_name: str = ""
    sp_middle_initial: str = ""
    sp_last_name: str = ""

    # IDs and DOBs
    tp_ssn: str = ""
    tp_dob: date | None = None
    sp_ssn: str = ""
    sp_dob: date | None = None

    # Contact
    tp_email: str = ""
    sp_email: str = ""
    # "Home" / "Work" / "" — the report shows a label, not a number
    sp_phone_label: str = ""

    # Address
    street: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""

    preparer: str = ""

    # Inferred
    filing_status: str = "single"  # "single" | "mfj"

    # Parse metadata
    source_page: int = 0
    warnings: list[str] = field(default_factory=list)

    def tp_ssn_last4(self) -> str:
        return self.tp_ssn[-4:] if len(self.tp_ssn) >= 4 else ""

    def sp_ssn_last4(self) -> str:
        return self.sp_ssn[-4:] if len(self.sp_ssn) >= 4 else ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SUFFIXES = {"JR", "SR", "II", "III", "IV"}

# Two-digit-year DOB format used in the report (MM/DD/YY)
_DOB_RE = re.compile(r"^\d{1,2}/\d{1,2}/\d{2}$")
_SSN_RE = re.compile(r"^\d{3}-\d{2}-\d{4}$")


def _parse_dob(text: str) -> date | None:
    """Parse MM/DD/YY. Windows 1930-2029 for 2-digit years (reasonable for DOBs)."""
    text = text.strip()
    if not _DOB_RE.match(text):
        return None
    try:
        dt = datetime.strptime(text, "%m/%d/%y")
    except ValueError:
        return None
    # strptime assumes 2-digit < 69 => 2000s, >= 69 => 1900s. For DOBs we
    # want a different pivot: any future year (> current year) shifts back 100.
    today = date.today()
    if dt.year > today.year:
        dt = dt.replace(year=dt.year - 100)
    return dt.date()


def _column_text(words: list[dict], x_min: float, x_max: float) -> str:
    """Join words whose x-start falls within [x_min, x_max)."""
    parts = [w["text"] for w in words if x_min <= w["x0"] < x_max]
    return " ".join(parts).strip()


def _bucket_rows(words: list[dict]) -> dict[int, list[dict]]:
    """Group words into horizontal rows keyed by rounded y-bucket."""
    rows: dict[int, list[dict]] = {}
    for w in words:
        y = w["top"]
        if y < DATA_Y_MIN or y > DATA_Y_MAX:
            continue
        bucket = round(y / Y_BUCKET) * Y_BUCKET
        rows.setdefault(bucket, []).append(w)
    return rows


def _parse_name_lnf(raw: str) -> tuple[str, str, str, str, str, str, str]:
    """
    Parse 'LASTNAME, FIRST [M] [SUFFIX] [AND SP_FIRST [M] [SP_LAST]]'.

    Returns:
        (tp_last, tp_first, tp_mid, tp_suffix,
         sp_first, sp_mid, sp_last)

    Spouse fields are empty strings if no 'AND' is present.
    When spouse has no explicit last name, sp_last = tp_last (family surname).
    """
    raw = raw.strip()
    if "," not in raw:
        return (raw, "", "", "", "", "", "")

    last_part, rest = raw.split(",", 1)
    tp_last = last_part.strip()
    rest = rest.strip()

    # Split on " AND " for spouse
    if re.search(r"\s+AND\s+", rest):
        tp_part, sp_part = re.split(r"\s+AND\s+", rest, maxsplit=1)
    else:
        tp_part, sp_part = rest, ""

    tp_first, tp_mid, tp_suffix = _parse_person_tokens(tp_part)
    sp_first, sp_mid, sp_last = "", "", ""
    if sp_part:
        sp_first, sp_mid, sp_last_parsed = _parse_person_tokens(sp_part)
        # If the spouse block has extra trailing tokens after first+mid,
        # treat them as a separate last name (e.g. "JOHN M COURSON").
        sp_last = sp_last_parsed or tp_last

    return (tp_last, tp_first, tp_mid, tp_suffix, sp_first, sp_mid, sp_last)


def _parse_person_tokens(block: str) -> tuple[str, str, str]:
    """
    Parse a single person block like 'SCOTT', 'KENNETH F',
    'CHARLES JR', or 'JOHN M COURSON'.

    Returns (first, middle_initial, suffix_or_extra_surname).
    - 1 token: first
    - 2 tokens: first + (middle initial OR suffix)
    - 3+ tokens: first + middle + (suffix OR extra last name joined)
    """
    tokens = block.split()
    if not tokens:
        return ("", "", "")
    first = tokens[0]
    if len(tokens) == 1:
        return (first, "", "")

    rest = tokens[1:]
    middle = ""
    extra = ""

    # If second token is 1 char, it's a middle initial
    if len(rest[0]) == 1 and rest[0].isalpha():
        middle = rest[0]
        rest = rest[1:]

    if rest:
        # If the remainder is a suffix token, set as suffix (no extra last name)
        if len(rest) == 1 and rest[0].upper() in _SUFFIXES:
            return (first, middle, rest[0])
        # Otherwise join as extra last name (spouse w/ different surname case)
        # Strip trailing suffix if present
        if rest[-1].upper() in _SUFFIXES:
            return (first, middle, " ".join(rest[:-1]))
        extra = " ".join(rest)

    return (first, middle, extra)


def _extract_row(
    left_words: list[dict],
    right_words: list[dict] | None,
    source_page: int,
) -> LacerteDemographic | None:
    """Build one LacerteDemographic from a pair of aligned rows (left/right page)."""
    name_raw = _column_text(left_words, *LEFT_COLUMNS["name"])
    if not name_raw:
        return None
    # Header row guard — these show up if our y-range is too generous.
    if name_raw.startswith("Full Name") or "LNF" in name_raw:
        return None

    rec = LacerteDemographic(full_name_lnf=name_raw, source_page=source_page)
    (
        rec.tp_last_name,
        rec.tp_first_name,
        rec.tp_middle_initial,
        rec.tp_suffix,
        rec.sp_first_name,
        rec.sp_middle_initial,
        rec.sp_last_name,
    ) = _parse_name_lnf(name_raw)

    # TP SSN / DOB / email
    tp_ssn = _column_text(left_words, *LEFT_COLUMNS["tp_ssn"])
    if _SSN_RE.match(tp_ssn):
        rec.tp_ssn = tp_ssn
    elif tp_ssn:
        rec.warnings.append(f"TP SSN malformed: {tp_ssn!r}")

    tp_dob = _column_text(left_words, *LEFT_COLUMNS["tp_dob"])
    if tp_dob:
        parsed = _parse_dob(tp_dob)
        if parsed:
            rec.tp_dob = parsed
        else:
            rec.warnings.append(f"TP DOB unparseable: {tp_dob!r}")

    rec.tp_email = _column_text(left_words, *LEFT_COLUMNS["tp_email"])

    # Spouse data from left page (DOB only; names already parsed from LNF)
    sp_dob = _column_text(left_words, *LEFT_COLUMNS["sp_dob"])
    if sp_dob:
        parsed = _parse_dob(sp_dob)
        if parsed:
            rec.sp_dob = parsed
        else:
            rec.warnings.append(f"SP DOB unparseable: {sp_dob!r}")

    # Right page data (address / spouse SSN / etc.)
    if right_words is not None:
        rec.sp_phone_label = _column_text(right_words, *RIGHT_COLUMNS["sp_phone_label"])
        rec.sp_email = _column_text(right_words, *RIGHT_COLUMNS["sp_email"])

        sp_ssn = _column_text(right_words, *RIGHT_COLUMNS["sp_ssn"])
        if _SSN_RE.match(sp_ssn):
            rec.sp_ssn = sp_ssn
        elif sp_ssn:
            rec.warnings.append(f"SP SSN malformed: {sp_ssn!r}")

        rec.street = _column_text(right_words, *RIGHT_COLUMNS["street"])
        rec.city = _column_text(right_words, *RIGHT_COLUMNS["city"])
        rec.state = _column_text(right_words, *RIGHT_COLUMNS["state"])
        rec.zip_code = _column_text(right_words, *RIGHT_COLUMNS["zip"])
        rec.preparer = _column_text(right_words, *RIGHT_COLUMNS["preparer"])

    # Filing-status inference: any spouse signal present => MFJ
    has_spouse = bool(rec.sp_first_name or rec.sp_ssn or rec.sp_dob)
    rec.filing_status = "mfj" if has_spouse else "single"

    return rec


def parse_lacerte_clientlist(pdf_path: str | Path) -> list[LacerteDemographic]:
    """
    Parse a Lacerte "Client List" custom-report PDF.

    Returns a list of LacerteDemographic records, one per client row.
    Pages are processed in 2-page spreads (left columns + right columns).
    If the PDF has an odd page count, the last unpaired page is processed
    with left-only columns.
    """
    pdf_path = Path(pdf_path)
    records: list[LacerteDemographic] = []

    with pdfplumber.open(str(pdf_path)) as pdf:
        pages = pdf.pages
        i = 0
        while i < len(pages):
            left_page = pages[i]
            right_page = pages[i + 1] if i + 1 < len(pages) else None

            left_words = left_page.extract_words(
                keep_blank_chars=False, x_tolerance=1.5, y_tolerance=2
            )
            right_words = None
            if right_page is not None:
                right_words = right_page.extract_words(
                    keep_blank_chars=False, x_tolerance=1.5, y_tolerance=2
                )

            left_rows = _bucket_rows(left_words)
            right_rows = _bucket_rows(right_words or [])

            for y in sorted(left_rows.keys()):
                rec = _extract_row(
                    left_rows[y],
                    right_rows.get(y),
                    source_page=i + 1,
                )
                if rec is not None:
                    records.append(rec)

            i += 2  # advance to next spread

    return records
