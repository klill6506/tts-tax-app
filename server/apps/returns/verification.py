"""
PDF render verification helpers.

Used by the Input/Compute/Render Verification harness (see CLAUDE.md
"Input/Compute/Render Verification — MANDATORY" and DECISIONS.md
2026-05-26 entry).

Today's only export is `assert_value_at_pdf_location`, which lets a
test assert that an expected value appears near a label on a specific
page of a rendered PDF. The 1040 module has no Rule Studio spec yet —
once it does, this helper is what closes step 4 ("render") of the
verification chain.
"""
from __future__ import annotations

from dataclasses import dataclass

import fitz  # pymupdf


@dataclass
class _Span:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def y_center(self) -> float:
        return (self.y0 + self.y1) / 2

    @property
    def x_center(self) -> float:
        return (self.x0 + self.x1) / 2


def _iter_spans(page: fitz.Page) -> list[_Span]:
    """Flatten a page into per-span records with bounding boxes."""
    spans: list[_Span] = []
    raw = page.get_text("dict")
    for block in raw.get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = (span.get("text") or "").strip()
                if not text:
                    continue
                bbox = span.get("bbox") or [0, 0, 0, 0]
                spans.append(_Span(text, bbox[0], bbox[1], bbox[2], bbox[3]))
    return spans


def assert_value_at_pdf_location(
    pdf_bytes: bytes,
    page_number: int,
    expected_value: str,
    location_hint: str,
    *,
    tolerance: int = 5,
) -> None:
    """Assert ``expected_value`` appears near ``location_hint`` on the given page.

    Opens the PDF with pymupdf, finds a text span on ``page_number``
    that contains ``location_hint``, then looks for ``expected_value``
    on the same vertical band (y-center within ``tolerance`` pixels)
    and to the right of the hint. Raises AssertionError if no match.

    Args:
        pdf_bytes: Rendered PDF as bytes.
        page_number: 0-indexed page number.
        expected_value: Value to look for (substring match against
            extracted text spans).
        location_hint: Substring identifying the line label (e.g.,
            ``"Line 1z"`` or ``"Wages, salaries"``).
        tolerance: Vertical alignment tolerance in PDF user-space
            pixels. Default 5px is right for IRS form lines where
            label and value sit on the same baseline.
    """
    if not pdf_bytes:
        raise AssertionError("pdf_bytes is empty")

    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        if page_number < 0 or page_number >= doc.page_count:
            raise AssertionError(
                f"page_number={page_number} out of range "
                f"(doc has {doc.page_count} pages)"
            )
        page = doc[page_number]
        spans = _iter_spans(page)

    if not spans:
        raise AssertionError(
            f"No text spans found on page {page_number}. "
            f"Expected to find '{expected_value}' near '{location_hint}'."
        )

    hint_spans = [s for s in spans if location_hint in s.text]
    if not hint_spans:
        raise AssertionError(
            f"location_hint '{location_hint}' not found on page {page_number}. "
            f"Sample of {len(spans)} spans: "
            f"{[s.text for s in spans[:5]]}..."
        )

    for hint in hint_spans:
        for candidate in spans:
            if candidate is hint:
                continue
            if expected_value not in candidate.text:
                continue
            if abs(candidate.y_center - hint.y_center) > tolerance:
                continue
            if candidate.x_center < hint.x_center:
                continue
            return

    near_hint_texts = sorted(
        (
            (abs(s.y_center - hint_spans[0].y_center), s.text)
            for s in spans
        ),
    )[:8]
    raise AssertionError(
        f"Expected value '{expected_value}' not found near "
        f"'{location_hint}' (within {tolerance}px vertically, to the "
        f"right) on page {page_number}. Closest spans by y-distance: "
        f"{[t for _, t in near_hint_texts]}"
    )


def assert_value_at_widget_position(
    pdf_bytes: bytes,
    page_number: int,
    expected_value: str,
    expected_x: float,
    expected_y: float,
    *,
    x_tolerance: float = 80.0,
    y_tolerance: float = 8.0,
) -> None:
    """Assert ``expected_value`` appears at the given PDF position.

    Sibling to ``assert_value_at_pdf_location``. The renderer flattens
    AcroForm widgets into text spans, so post-render PDFs don't have
    widgets to look up — they have positioned text. This helper checks
    that an expected value (substring match) lands inside the rectangle
    centered on ``(expected_x, expected_y)`` with the given tolerances.

    The expected position comes from the field map's AcroForm rect. The
    typical IRS form line widget is ~72px wide and 12px tall, so the
    default tolerances (80px / 8px) cover normal field width plus the
    small rendering offset (~1-2px).

    Args:
        pdf_bytes: Rendered PDF bytes.
        page_number: 0-indexed page number.
        expected_value: Substring expected to appear (e.g., ``"4,400"``).
        expected_x: X-coordinate near where the value should land
            (typically the widget's rect.x0 or x_center).
        expected_y: Y-coordinate near where the value should land
            (typically the widget's rect.y_center).
        x_tolerance: Horizontal box half-width in PDF user-space pixels.
        y_tolerance: Vertical box half-height in PDF user-space pixels.

    Raises:
        AssertionError: if no text span containing ``expected_value`` is
            found inside the tolerance box.
    """
    if not pdf_bytes:
        raise AssertionError("pdf_bytes is empty")

    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        if page_number < 0 or page_number >= doc.page_count:
            page_count = doc.page_count
            raise AssertionError(
                f"page_number={page_number} out of range (doc has "
                f"{page_count} pages)"
            )
        page = doc[page_number]
        spans = _iter_spans(page)

    for s in spans:
        if expected_value not in s.text:
            continue
        if abs(s.y_center - expected_y) > y_tolerance:
            continue
        if abs(s.x_center - expected_x) > x_tolerance:
            continue
        return

    near_spans = sorted(
        (
            (
                (s.x_center - expected_x) ** 2 + (s.y_center - expected_y) ** 2,
                s.text,
                s.x_center,
                s.y_center,
            )
            for s in spans
        ),
    )[:8]
    raise AssertionError(
        f"Expected '{expected_value}' near ({expected_x:.0f}, "
        f"{expected_y:.0f}) on page {page_number}. Closest spans: "
        f"{[(t, f'({x:.0f}, {y:.0f})') for _, t, x, y in near_spans]}"
    )
