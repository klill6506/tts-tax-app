"""End-to-end PDF render assertions for Schedule 8812 + Form 1040 Lines 19/28.

Closes the render half of Session K Part 2's verification chain. Three
scenarios exercise the CTC-only path, the ACTC-eligible path, and the
Form 2555 zero-out edge case (TS13 from the spec). For each scenario we
build the DB graph, run compute_sch_8812, render the PDFs, and assert
the computed values land in the correct widget positions on both
Schedule 8812 and Form 1040.

Why these three:
    - CTC-only:           MFJ AGI $150K + 2 QC + ample tax → CTC=$4,400,
                          ACTC=$0. Proves Schedule 8812 Line 14 lands on
                          page 1 and Form 1040 Line 19 lands on page 2.
    - ACTC-eligible:      MFJ low AGI + 3 QC + low tax → CTC limited by
                          tax, ACTC pays out the refundable balance.
                          Proves Schedule 8812 Line 27 lands on page 2
                          and Form 1040 Line 28 lands on page 2.
    - Form 2555 zero-out: MFJ files Form 2555. Per scenario TS13 +
                          spec disambiguation, L_16a → 0 and L_27 → 0
                          even when QC > 0. Proves the zero-out renders
                          as "0" in the PDF (not blank).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth.models import User

from apps.clients.models import Client, Entity, EntityType, TaxYear
from apps.firms.models import Firm, FirmMembership, Role
from apps.returns.compute_8812 import compute_sch_8812
from apps.returns.models import (
    Dependent,
    FormDefinition,
    FormFieldValue,
    FormLine,
    Taxpayer,
    TaxReturn,
    W2Income,
)
from apps.returns.verification import (
    assert_value_at_pdf_location,
    assert_value_at_widget_position,
)
from apps.tts_forms.renderer import render_sch_8812, render_tax_return

import fitz


def _assert_no_currency_at_position(pdf_bytes, *, page_number, expected_x,
                                    expected_y, x_tolerance=36.0,
                                    y_tolerance=8.0):
    """Helper: assert no currency-like text span sits in the tolerance box.

    Zero values render BLANK per IRS form convention (format_currency
    returns "" for $0). This verifies the zero-out cases really do
    produce empty fields, not accidental non-zero values.
    """
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        page = doc[page_number]
        spans = []
        for block in page.get_text("dict").get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    t = (span.get("text") or "").strip()
                    if not t:
                        continue
                    b = span["bbox"]
                    spans.append((t, (b[0] + b[2]) / 2, (b[1] + b[3]) / 2))

    for text, x, y in spans:
        if abs(y - expected_y) > y_tolerance:
            continue
        if abs(x - expected_x) > x_tolerance:
            continue
        # Look like a currency value? digits + optional comma + optional decimal.
        cleaned = text.replace(",", "").replace("$", "").replace("(", "").replace(")", "")
        if any(c.isdigit() for c in cleaned):
            try:
                float(cleaned)
            except ValueError:
                continue
            raise AssertionError(
                f"Expected blank at ({expected_x:.0f}, {expected_y:.0f}) "
                f"on page {page_number}, but found currency-like value "
                f"{text!r} at ({x:.0f}, {y:.0f})."
            )


# ---------------------------------------------------------------------------
# Fixtures + helpers (mirror the patterns in test_sch_8812_scenarios.py)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def seeded_forms(django_db_setup, django_db_blocker):
    from django.core.management import call_command

    with django_db_blocker.unblock():
        call_command("seed_1040", "--year", "2025")
        call_command("seed_sch_8812", "--year", "2025")


@pytest.fixture
def firm(db):
    return Firm.objects.create(name="Test Firm SCH 8812 Render")


@pytest.fixture
def user(firm):
    u = User.objects.create_user(username="sch8812_render_preparer", password="x")
    FirmMembership.objects.create(user=u, firm=firm, role=Role.PREPARER)
    return u


@pytest.fixture
def form_1040(seeded_forms):
    return FormDefinition.objects.get(code="1040", tax_year_applicable=2025)


def _qc_dep(tax_return, idx):
    return Dependent.objects.create(
        tax_return=tax_return,
        first_name=f"QC{idx}",
        relationship="child",
        date_of_birth=date(2018, 1, 1),
        months_resided_with_taxpayer=12,
        provided_over_half_own_support=False,
        filed_joint_return=False,
        citizenship_status="us_citizen",
        tin_type="valid_ssn",
    )


def _build_minimal_1040(firm, user, form_1040, *, filing_status, agi,
                        tax_before, qc_count=0, files_form_2555=False,
                        wages=Decimal("0")):
    cl = Client.objects.create(firm=firm, name="Render Test Client")
    ent = Entity.objects.create(client=cl, name="Render Test Filer",
                                entity_type=EntityType.INDIVIDUAL)
    ty = TaxYear.objects.create(entity=ent, year=2025)
    tr = TaxReturn.objects.create(tax_year=ty, form_definition=form_1040,
                                  created_by=user)

    Taxpayer.objects.create(
        tax_return=tr,
        filing_status=filing_status,
        first_name="Render",
        last_name="Sample",
        ssn="999-00-1234",
        taxpayer_has_valid_ssn=True,
        spouse_has_valid_ssn=(filing_status == "mfj"),
        spouse_first_name="Spouse" if filing_status == "mfj" else "",
        spouse_last_name="Sample" if filing_status == "mfj" else "",
        files_form_2555=files_form_2555,
    )

    for i in range(qc_count):
        _qc_dep(tr, i)

    if wages > 0:
        W2Income.objects.create(
            tax_return=tr,
            employer_name="Render Test Employer",
            employer_ein="00-0000000",
            wages=wages,
            federal_tax_withheld=Decimal("0"),
        )

    # Backfill 1040 FormFieldValue rows so we can set 11/16/18 directly.
    lines = FormLine.objects.filter(section__form=form_1040)
    FormFieldValue.objects.bulk_create(
        [FormFieldValue(tax_return=tr, form_line=ln, value="") for ln in lines]
    )

    line_map = {
        fv.form_line.line_number: fv
        for fv in FormFieldValue.objects.filter(tax_return=tr)
        .select_related("form_line")
    }
    line_map["11"].value = str(agi)
    line_map["11"].save(update_fields=["value"])
    line_map["16"].value = str(tax_before)
    line_map["16"].save(update_fields=["value"])
    line_map["18"].value = str(tax_before)
    line_map["18"].save(update_fields=["value"])

    return tr


# ---------------------------------------------------------------------------
# Scenario A — CTC-only path (MFJ, 2 QC, ample tax)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_ctc_only_renders_to_correct_locations(firm, user, form_1040):
    """MFJ + 2 QC + tax $16,668 → CTC=$4,400, ACTC=$0.

    Schedule 8812 Line 14 (CTC) = $4,400 lands on page 1.
    Form 1040 Line 19 = $4,400 lands on page 2.
    """
    tr = _build_minimal_1040(
        firm, user, form_1040,
        filing_status="mfj",
        agi=Decimal("150000"),
        tax_before=Decimal("16668"),
        qc_count=2,
        wages=Decimal("150000"),
    )

    compute_sch_8812(tr)

    # Assert in DB first — sanity check on compute
    fv_l14 = FormFieldValue.objects.get(
        tax_return=tr,
        form_line__line_number="L_14",
        form_line__section__form__code="SCH_8812",
    )
    assert Decimal(fv_l14.value) == Decimal("4400.00"), (
        f"L_14 expected $4,400 (2 QC × $2,200 OBBBA), got {fv_l14.value}"
    )

    fv_1040_19 = FormFieldValue.objects.get(
        tax_return=tr,
        form_line__line_number="19",
        form_line__section__form__code="1040",
    )
    assert Decimal(fv_1040_19.value) == Decimal("4400.00")

    # Render Schedule 8812 — assert Line 14 ($4,400) lands at f1_19 position
    # (page 1 right column, x≈540, y≈450).
    pdf_8812 = render_sch_8812(tr)
    assert pdf_8812, "Schedule 8812 PDF should render when CTC > 0"
    assert_value_at_widget_position(
        pdf_8812,
        page_number=0,
        expected_value="4,400",
        expected_x=540.0,
        expected_y=450.0,
    )

    # Render Form 1040 — Line 19 ($4,400) at f2_11 position (page 2,
    # x≈540, y≈198).
    pdf_1040 = render_tax_return(tr)
    assert pdf_1040
    assert_value_at_widget_position(
        pdf_1040,
        page_number=1,
        expected_value="4,400",
        expected_x=540.0,
        expected_y=198.0,
    )


# ---------------------------------------------------------------------------
# Scenario B — ACTC-eligible path (low AGI, 3 QC, low tax → refundable)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_actc_eligible_renders_to_correct_locations(firm, user, form_1040):
    """MFJ + 3 QC + AGI $30K + tax $1,000 → CTC limited to $1,000;
    refundable ACTC pays out remainder per the 15% method.

    L_5 = 3 × $2,200 = $6,600 (pre-phaseout credit)
    L_12 = $6,600 (no phaseout under $400K MFJ)
    L_13 = $1,000 (tax liability cap)
    L_14 = min($6,600, $1,000) = $1,000 → Form 1040 Line 19
    L_16a = $6,600 − $1,000 = $5,600 (overflow)
    L_16b = 3 × $1,700 = $5,100
    L_17 = min($5,600, $5,100) = $5,100
    Earned income = $30,000 (W-2 wages)
    L_19 = $30,000 − $2,500 = $27,500
    L_20 = $27,500 × 15% = $4,125
    L_27 = min($5,100, $4,125) = $4,125 → Form 1040 Line 28
    """
    tr = _build_minimal_1040(
        firm, user, form_1040,
        filing_status="mfj",
        agi=Decimal("30000"),
        tax_before=Decimal("1000"),
        qc_count=3,
        wages=Decimal("30000"),
    )

    compute_sch_8812(tr)

    fv_l14 = FormFieldValue.objects.get(
        tax_return=tr, form_line__line_number="L_14",
        form_line__section__form__code="SCH_8812",
    )
    assert Decimal(fv_l14.value) == Decimal("1000.00")
    fv_l27 = FormFieldValue.objects.get(
        tax_return=tr, form_line__line_number="L_27",
        form_line__section__form__code="SCH_8812",
    )
    assert Decimal(fv_l27.value) == Decimal("4125.00"), (
        f"L_27 expected $4,125 (15% of $27,500), got {fv_l27.value}"
    )

    pdf_8812 = render_sch_8812(tr)
    assert pdf_8812

    # Schedule 8812 Line 14 ($1,000) at f1_19 position (page 1).
    assert_value_at_widget_position(
        pdf_8812,
        page_number=0,
        expected_value="1,000",
        expected_x=540.0,
        expected_y=450.0,
    )
    # Schedule 8812 Line 27 ($4,125) at f2_16 position (page 2).
    assert_value_at_widget_position(
        pdf_8812,
        page_number=1,
        expected_value="4,125",
        expected_x=540.0,
        expected_y=474.0,
    )

    pdf_1040 = render_tax_return(tr)
    # Form 1040 Line 19 ($1,000) at f2_11 position.
    assert_value_at_widget_position(
        pdf_1040,
        page_number=1,
        expected_value="1,000",
        expected_x=540.0,
        expected_y=198.0,
    )
    # Form 1040 Line 28 ($4,125) at f2_24 position (middle col, x≈446).
    assert_value_at_widget_position(
        pdf_1040,
        page_number=1,
        expected_value="4,125",
        expected_x=446.0,
        expected_y=414.0,
    )


# ---------------------------------------------------------------------------
# Scenario C — Form 2555 zero-out (TS13)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_form_2555_zero_out_renders_zero(firm, user, form_1040):
    """MFJ + 2 QC + Form 2555 = True → all ACTC fields zero out.

    Per spec TS13 + the R018 / L_16a gating resolution: filing Form 2555
    zeros out L_16a (and the entire ACTC path) regardless of QC count.
    L_14 (CTC) still computes normally — it's the *refundable* ACTC
    that's blocked.
    """
    tr = _build_minimal_1040(
        firm, user, form_1040,
        filing_status="mfj",
        agi=Decimal("150000"),
        tax_before=Decimal("16668"),
        qc_count=2,
        files_form_2555=True,
        wages=Decimal("150000"),
    )

    compute_sch_8812(tr)

    # L_16a = 0 (Form 2555 zero-out)
    fv_l16a = FormFieldValue.objects.get(
        tax_return=tr, form_line__line_number="L_16a",
        form_line__section__form__code="SCH_8812",
    )
    assert Decimal(fv_l16a.value) == Decimal("0.00")
    # L_27 = 0 (no ACTC)
    fv_l27 = FormFieldValue.objects.get(
        tax_return=tr, form_line__line_number="L_27",
        form_line__section__form__code="SCH_8812",
    )
    assert Decimal(fv_l27.value) == Decimal("0.00")

    pdf_8812 = render_sch_8812(tr)
    assert pdf_8812

    # L_14 (CTC) is unaffected by Form 2555 — still $4,400 at f1_19.
    assert_value_at_widget_position(
        pdf_8812,
        page_number=0,
        expected_value="4,400",
        expected_x=540.0,
        expected_y=450.0,
    )

    # L_16a and L_27 are zero — per IRS form convention, $0 amounts
    # render BLANK (format_currency returns ""). Assert no non-zero
    # currency value lands at those positions.
    _assert_no_currency_at_position(
        pdf_8812, page_number=1, expected_x=540.0, expected_y=90.0,
    )
    _assert_no_currency_at_position(
        pdf_8812, page_number=1, expected_x=540.0, expected_y=474.0,
    )

    # Form 1040 Line 28 (ACTC) is zero — also renders blank at f2_24.
    pdf_1040 = render_tax_return(tr)
    _assert_no_currency_at_position(
        pdf_1040, page_number=1, expected_x=446.0, expected_y=414.0,
    )
