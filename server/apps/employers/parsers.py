"""
EIN / CSV parsing utilities for the employer database.

Spec
----
This module is the parsing surface for raw rows coming out of the TaxWise
"Employer" CSV export and similar one-off employer lists. It does NOT touch
the database — it just normalizes/validates a single field at a time so the
import command can decide what to do with each row.

Functions
~~~~~~~~~

parse_ein(raw) -> str | None
    Normalize a federal EIN to canonical "XX-XXXXXXX" form.
    Accepts:  "12-3456789", "123456789", whitespace-padded variants.
    Rejects:  fewer/more than 9 digits, any non-digit beyond a single optional
              hyphen between the 2nd and 3rd digit, multiple hyphens.
    Returns:  the canonical "XX-XXXXXXX" string, or None on failure.
    Note:     does not validate IRS prefix codes — accepts any 9 digits.

parse_city_state_zip(raw) -> (city, state, zip, warnings)
    Split a single mashed CITY-column string into its three parts. The
    TaxWise export packs city + state + zip into one column with several
    inconsistent formats:

        "ADDISON TX 75001-"           — space-separated, trailing hyphen on zip
        "ADDISON, TX 75001-"          — comma + space after city
        "AKRON, OH 44316"             — clean comma-separated
        "ALBANY GA 31702-1867"        — space-separated, ZIP+4
        "AHTENS, GA 30608"            — typo in city — preserved verbatim
        "ADDISON TX"                  — missing zip            (warning emitted)
        "SOME WEIRD FORMAT"           — no recognizable state  (warning emitted)
        '"ADDISON, TX 75001-"'        — surrounding quotes from CSV escaping

    Strategy:
      1. Strip surrounding quotes and surrounding whitespace.
      2. Match against:
             ^(?P<city>.+?)\\s*,?\\s+(?P<state>[A-Z]{2})
              (?:\\s+(?P<zip>\\d{5}(?:-\\d{4})?))?\\s*-?\\s*$
      3. If the regex fails, return empty fields + warning ["unparseable: <raw>"].
      4. If the regex matches but no zip group was captured, return the city/state
         and an empty zip + warning ["missing zip"].

    Returns: tuple of (city: str, state: str, zip: str, warnings: list[str]).
             Fields are empty strings when not extractable. The function never
             raises — malformed input is reported via the warnings list.

validate_zip(raw) -> (zip, warnings)
    Normalize a ZIP/ZIP+4 string. Accepts:
        "75001"        -> ("75001", [])
        "75001-1234"   -> ("75001-1234", [])
        "75001-"       -> ("75001", [])               (trailing-hyphen tolerance)
    Rejects (returns ("", ["invalid zip"])):
        empty string, non-numeric, fewer/more than 5 digits, partial +4
        like "75001-12".
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# EIN
# ---------------------------------------------------------------------------

_EIN_RE = re.compile(r"^(\d{2})-?(\d{7})$")


def parse_ein(raw: str | None) -> str | None:
    """Normalize EIN to canonical XX-XXXXXXX form, or None if invalid."""
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    m = _EIN_RE.match(raw)
    if m is None:
        return None
    return f"{m.group(1)}-{m.group(2)}"


# ---------------------------------------------------------------------------
# City / state / zip
# ---------------------------------------------------------------------------

# Single regex covering the four mashed-format variants documented above.
# - .+?       non-greedy city (allows multi-word like "NEW YORK")
# - \s*,?\s+  optional comma + whitespace separator before the state
# - [A-Z]{2}  2-letter state abbreviation
# - optional zip group: 5 digits optionally followed by -NNNN
# - \s*-?\s*$ tolerates a trailing hyphen after the zip
_CSZ_RE = re.compile(
    r"^(?P<city>.+?)\s*,?\s+(?P<state>[A-Z]{2})"
    r"(?:\s+(?P<zip>\d{5}(?:-\d{4})?))?\s*-?\s*$"
)


def parse_city_state_zip(raw: str | None) -> tuple[str, str, str, list[str]]:
    """Split a mashed 'CITY' column into (city, state, zip, warnings)."""
    if raw is None or not raw.strip():
        return ("", "", "", ["empty"])

    cleaned = raw.strip()
    # Strip surrounding double or single quotes, then re-strip whitespace.
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in ('"', "'"):
        cleaned = cleaned[1:-1].strip()

    m = _CSZ_RE.match(cleaned)
    if m is None:
        return ("", "", "", [f"unparseable: {raw}"])

    city = m.group("city").strip().rstrip(",").strip()
    state = m.group("state")
    zip_raw = m.group("zip") or ""

    warnings: list[str] = []
    if not zip_raw:
        warnings.append("missing zip")

    return (city, state, zip_raw, warnings)


# ---------------------------------------------------------------------------
# Zip
# ---------------------------------------------------------------------------

# 5 digits, optional -NNNN extension, tolerate a trailing dash.
_ZIP_RE = re.compile(r"^(\d{5})(?:-(\d{4}))?-?$")


def validate_zip(raw: str | None) -> tuple[str, list[str]]:
    """Normalize a ZIP. Returns (canonical_zip, warnings)."""
    raw = (raw or "").strip()
    if not raw:
        return ("", ["invalid zip"])
    m = _ZIP_RE.match(raw)
    if m is None:
        return ("", ["invalid zip"])
    base, plus4 = m.group(1), m.group(2)
    return (f"{base}-{plus4}" if plus4 else base, [])
