"""
Tests for the Lacerte Client List PDF parser.

Uses ReportLab to synthesize a fake-layout PDF that mirrors the real
report's geometry, then verifies parse output. No real PII in fixtures.
"""

from __future__ import annotations

import io
from datetime import date

import pytest
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, letter

from apps.imports.lacerte_clientlist_parser import (
    LEFT_COLUMNS,
    RIGHT_COLUMNS,
    LacerteDemographic,
    _parse_name_lnf,
    parse_lacerte_clientlist,
)


# ---------------------------------------------------------------------------
# Synthetic PDF generator — mirrors the real report's column geometry
# ---------------------------------------------------------------------------

PAGE_W, PAGE_H = landscape(letter)  # 792 x 612


def _draw_row(c: canvas.Canvas, y_from_top: float, cells: dict[str, str]):
    """Draw cells at the x-centers of specified columns, at y_from_top."""
    y = PAGE_H - y_from_top
    for col_name, value in cells.items():
        ranges = LEFT_COLUMNS if col_name in LEFT_COLUMNS else RIGHT_COLUMNS
        x_min, _ = ranges[col_name]
        c.drawString(x_min + 2, y, value)


def _make_left_page(c: canvas.Canvas, rows: list[dict]):
    c.setFont("Helvetica", 8)
    # Header at y~96 from top
    _draw_row(c, 96, {
        "name": "Full Name (LNF)",
        "tp_ssn": "TP SSN",
        "tp_dob": "TP DOB",
        "tp_email": "TP E-Mail Addr.",
        "sp_first": "SP F. Name",
        "sp_last": "SP L. Name",
        "sp_dob": "SP DOB",
    })
    # Data rows start at y=120, 12 pts apart
    for i, row in enumerate(rows):
        y = 120 + i * 12
        _draw_row(c, y, {
            "name": row["name"],
            "tp_ssn": row.get("tp_ssn", ""),
            "tp_dob": row.get("tp_dob", ""),
            "tp_email": row.get("tp_email", ""),
            "sp_first": row.get("sp_first", ""),
            "sp_last": row.get("sp_last", ""),
            "sp_dob": row.get("sp_dob", ""),
        })
    c.showPage()


def _make_right_page(c: canvas.Canvas, rows: list[dict]):
    c.setFont("Helvetica", 8)
    _draw_row(c, 96, {
        "sp_phone_label": "Sp. Day Phone",
        "sp_email": "Sp Email Addr.",
        "sp_ssn": "SP SSN",
        "street": "Street Address",
        "city": "City",
        "state": "State",
        "zip": "Zip",
        "preparer": "Preparer",
    })
    for i, row in enumerate(rows):
        y = 120 + i * 12
        _draw_row(c, y, {
            "sp_phone_label": row.get("sp_phone_label", ""),
            "sp_email": row.get("sp_email", ""),
            "sp_ssn": row.get("sp_ssn", ""),
            "street": row.get("street", ""),
            "city": row.get("city", ""),
            "state": row.get("state", ""),
            "zip": row.get("zip", ""),
            "preparer": row.get("preparer", ""),
        })
    c.showPage()


def build_synthetic_pdf(rows: list[dict]) -> bytes:
    """Build a 2-page Lacerte-style client list PDF from the given rows."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=landscape(letter))
    _make_left_page(c, rows)
    _make_right_page(c, rows)
    c.save()
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Fixture data
# ---------------------------------------------------------------------------

SAMPLE_ROWS = [
    {
        # MFJ, same last name
        "name": "TESTERSON, ALPHA AND BETA",
        "tp_ssn": "111-11-1111", "tp_dob": "01/15/80",
        "tp_email": "alpha@example.com",
        "sp_first": "BETA", "sp_last": "TESTERSON", "sp_dob": "02/20/82",
        "sp_phone_label": "Home", "sp_email": "",
        "sp_ssn": "222-22-2222",
        "street": "123 FAKE ST", "city": "NOWHERE", "state": "GA",
        "zip": "30000", "preparer": "1. Tester",
    },
    {
        # Single
        "name": "SOLO, GAMMA",
        "tp_ssn": "333-33-3333", "tp_dob": "06/06/66",
        "tp_email": "", "sp_first": "", "sp_last": "", "sp_dob": "",
        "sp_phone_label": "", "sp_email": "", "sp_ssn": "",
        "street": "500 LONE RD", "city": "SOLITUDE", "state": "GA",
        "zip": "30001", "preparer": "1. Tester",
    },
    {
        # MFJ with suffix
        "name": "JUNIORSON, DELTA JR AND EPSILON",
        "tp_ssn": "444-44-4444", "tp_dob": "03/03/55",
        "tp_email": "",
        "sp_first": "EPSILON", "sp_last": "JUNIORSON", "sp_dob": "04/04/58",
        "sp_phone_label": "Work", "sp_email": "",
        "sp_ssn": "555-55-5555",
        "street": "99 SENIOR LN", "city": "AGEDVILLE", "state": "FL",
        "zip": "30002", "preparer": "1. Tester",
    },
    {
        # Spouse has different last name
        "name": "HUSBAND, ZETA AND ETA WIFE",
        "tp_ssn": "666-66-6666", "tp_dob": "07/07/77",
        "tp_email": "",
        "sp_first": "ETA", "sp_last": "WIFE", "sp_dob": "08/08/88",
        "sp_phone_label": "", "sp_email": "", "sp_ssn": "777-77-7777",
        "street": "1 COUPLE CT", "city": "LOVETOWN", "state": "GA",
        "zip": "30003", "preparer": "1. Tester",
    },
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestNameParser:
    """_parse_name_lnf covers edge cases seen in the real report."""

    def test_single_taxpayer(self):
        last, first, mid, suf, sf, sm, sl = _parse_name_lnf("BLACKWELL, EMILY")
        assert (last, first, mid, suf) == ("BLACKWELL", "EMILY", "", "")
        assert (sf, sm, sl) == ("", "", "")

    def test_mfj_same_last(self):
        last, first, mid, suf, sf, sm, sl = _parse_name_lnf(
            "ANDERSON, SCOTT AND TIFFANY"
        )
        assert (last, first) == ("ANDERSON", "SCOTT")
        assert (sf, sl) == ("TIFFANY", "ANDERSON")

    def test_middle_initials(self):
        last, first, mid, suf, sf, sm, sl = _parse_name_lnf(
            "BACH, KENNETH F AND LINDA A"
        )
        assert (first, mid) == ("KENNETH", "F")
        assert (sf, sm, sl) == ("LINDA", "A", "BACH")

    def test_suffix(self):
        last, first, mid, suf, sf, sm, sl = _parse_name_lnf(
            "CARTER, JARED JR AND RICHARD A"
        )
        assert (first, suf) == ("JARED", "JR")
        assert (sf, sm) == ("RICHARD", "A")

    def test_separate_spouse_surname(self):
        last, first, mid, suf, sf, sm, sl = _parse_name_lnf(
            "CLARK, HAILEY E AND JOHN M COURSON"
        )
        assert (last, first, mid) == ("CLARK", "HAILEY", "E")
        assert (sf, sm, sl) == ("JOHN", "M", "COURSON")


class TestParsePDF:
    """End-to-end parse against a synthetic Lacerte-layout PDF."""

    @pytest.fixture
    def pdf_bytes(self):
        return build_synthetic_pdf(SAMPLE_ROWS)

    @pytest.fixture
    def pdf_path(self, pdf_bytes, tmp_path):
        p = tmp_path / "synthetic_clientlist.pdf"
        p.write_bytes(pdf_bytes)
        return p

    def test_record_count(self, pdf_path):
        records = parse_lacerte_clientlist(pdf_path)
        assert len(records) == len(SAMPLE_ROWS)

    def test_mfj_record(self, pdf_path):
        records = parse_lacerte_clientlist(pdf_path)
        r = records[0]
        assert r.tp_last_name == "TESTERSON"
        assert r.tp_first_name == "ALPHA"
        assert r.sp_first_name == "BETA"
        assert r.sp_last_name == "TESTERSON"
        assert r.tp_ssn == "111-11-1111"
        assert r.sp_ssn == "222-22-2222"
        assert r.tp_dob == date(1980, 1, 15)
        assert r.sp_dob == date(1982, 2, 20)
        assert r.street == "123 FAKE ST"
        assert r.state == "GA"
        assert r.zip_code == "30000"
        assert r.filing_status == "mfj"
        assert r.warnings == []

    def test_single_record(self, pdf_path):
        records = parse_lacerte_clientlist(pdf_path)
        r = next(r for r in records if r.tp_last_name == "SOLO")
        assert r.filing_status == "single"
        assert r.sp_ssn == ""
        assert r.sp_dob is None
        assert r.sp_first_name == ""
        assert r.tp_dob == date(1966, 6, 6)

    def test_suffix_preserved(self, pdf_path):
        records = parse_lacerte_clientlist(pdf_path)
        r = next(r for r in records if r.tp_last_name == "JUNIORSON")
        assert r.tp_first_name == "DELTA"
        assert r.tp_suffix == "JR"

    def test_separate_spouse_surname(self, pdf_path):
        records = parse_lacerte_clientlist(pdf_path)
        r = next(r for r in records if r.tp_last_name == "HUSBAND")
        assert r.sp_last_name == "WIFE"
        assert r.sp_first_name == "ETA"

    def test_ssn_redaction_helper(self):
        r = LacerteDemographic(tp_ssn="123-45-6789")
        assert r.tp_ssn_last4() == "6789"
        r2 = LacerteDemographic()
        assert r2.tp_ssn_last4() == ""
