"""
Field coordinate mappings for Form 7206 — Self-Employed Health Insurance Deduction (2025).

Coordinates are in PDF points (1 point = 1/72 inch).
Origin (0, 0) is the bottom-left corner of the page.
Page size: ~612 x 792 points.

Single-page form. For S-Corp >2% shareholders, lines 4-10 are skipped.
The S-Corp preparer fills lines 1, 3, and optionally 11-14.

Coordinates calibrated via pdfplumber extraction from the official 2025 PDF.
"""

from .f1120s import FieldCoord

# ---------------------------------------------------------------------------
# Header fields
# ---------------------------------------------------------------------------
HEADER_FIELDS: dict[str, FieldCoord] = {
    # Name(s) shown on return
    "taxpayer_name": FieldCoord(
        page=0, x=36, y=693, width=420, alignment="left", font_size=10
    ),
    # Taxpayer identification number (SSN)
    "taxpayer_ssn": FieldCoord(
        page=0, x=458, y=693, width=118, alignment="left", font_size=10
    ),
}

# ---------------------------------------------------------------------------
# Form fields — amounts are right-aligned in the right column
# The amount column is approximately x=495 to x=570
# ---------------------------------------------------------------------------
FIELD_MAP: dict[str, FieldCoord] = {
    # Line 1: Total health insurance premiums paid
    "1": FieldCoord(page=0, x=495, y=645, width=72, alignment="right", font_size=9),
    # Line 2: Qualified long-term care premiums
    "2": FieldCoord(page=0, x=495, y=399, width=72, alignment="right", font_size=9),
    # Line 3: Add lines 1 and 2
    "3": FieldCoord(page=0, x=495, y=387, width=72, alignment="right", font_size=9),
    # Line 4: Net profit (skip for S-Corp — "skip to line 11")
    "4": FieldCoord(page=0, x=495, y=351, width=72, alignment="right", font_size=9),
    # Line 11: S-Corp shareholder wages (W-2)
    "11": FieldCoord(page=0, x=495, y=189, width=72, alignment="right", font_size=9),
    # Line 12: Form 2555 amount
    "12": FieldCoord(page=0, x=495, y=177, width=72, alignment="right", font_size=9),
    # Line 13: Subtract line 12 from line 10 or 11
    "13": FieldCoord(page=0, x=495, y=165, width=72, alignment="right", font_size=9),
    # Line 14: Self-employed health insurance deduction (smaller of line 3 or 13)
    "14": FieldCoord(page=0, x=495, y=129, width=72, alignment="right", font_size=9),
}
