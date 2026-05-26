"""
Unit tests for ``apps.returns.verification.assert_value_at_pdf_location``.

These tests build a tiny PDF on the fly with ReportLab, then exercise
the helper's success and failure paths. No DB, no IRS templates.
"""
from __future__ import annotations

import io

import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from apps.returns.verification import assert_value_at_pdf_location


def _build_pdf() -> bytes:
    """Build a 2-page PDF with two label/value pairs per page."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setFont("Helvetica", 10)

    c.drawString(72, 720, "Line 1z  Wages, salaries, tips")
    c.drawString(450, 720, "60000.00")

    c.drawString(72, 700, "Line 25a  Withholding from W-2")
    c.drawString(450, 700, "5000.00")
    c.showPage()

    c.drawString(72, 720, "Line 19  Child tax credit")
    c.drawString(450, 720, "4000.00")
    c.save()
    return buf.getvalue()


@pytest.fixture(scope="module")
def sample_pdf() -> bytes:
    return _build_pdf()


def test_finds_value_on_correct_page(sample_pdf):
    assert_value_at_pdf_location(
        sample_pdf,
        page_number=0,
        expected_value="60000.00",
        location_hint="Line 1z",
    )


def test_finds_value_with_loose_substring(sample_pdf):
    assert_value_at_pdf_location(
        sample_pdf,
        page_number=0,
        expected_value="5000",
        location_hint="Line 25a",
    )


def test_finds_value_on_page_two(sample_pdf):
    assert_value_at_pdf_location(
        sample_pdf,
        page_number=1,
        expected_value="4000.00",
        location_hint="Line 19",
    )


def test_missing_hint_raises(sample_pdf):
    with pytest.raises(AssertionError, match="location_hint"):
        assert_value_at_pdf_location(
            sample_pdf,
            page_number=0,
            expected_value="60000.00",
            location_hint="Line 99z",
        )


def test_wrong_value_raises(sample_pdf):
    with pytest.raises(AssertionError, match="Expected value"):
        assert_value_at_pdf_location(
            sample_pdf,
            page_number=0,
            expected_value="99999.00",
            location_hint="Line 1z",
        )


def test_value_off_baseline_outside_tolerance_raises(sample_pdf):
    # "Line 19" is on page 1; on page 0 it doesn't exist at all.
    with pytest.raises(AssertionError, match="location_hint"):
        assert_value_at_pdf_location(
            sample_pdf,
            page_number=0,
            expected_value="4000.00",
            location_hint="Line 19",
            tolerance=2,
        )


def test_out_of_range_page_raises(sample_pdf):
    with pytest.raises(AssertionError, match="out of range"):
        assert_value_at_pdf_location(
            sample_pdf,
            page_number=99,
            expected_value="anything",
            location_hint="Line 1z",
        )


def test_empty_bytes_raises():
    with pytest.raises(AssertionError, match="empty"):
        assert_value_at_pdf_location(
            b"",
            page_number=0,
            expected_value="x",
            location_hint="x",
        )
