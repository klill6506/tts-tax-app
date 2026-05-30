"""End-to-end render assertions locking in the Form 1040 (2025) field map.

The 2025 IRS Form 1040 was substantially redesigned for OBBBA: AGI is
labeled "11a", standard deduction is "12e", QBI is "13a", Lines 14-15
moved from page 1 to page 2, and the page-2 widget IDs that used to
hold Lines 24/33/34/37 in earlier renderer drafts now hold different
lines entirely.

This test renders a 1040 PDF with a unique non-zero value on every
line in FIELD_MAP, then asserts each value lands at the field map's
declared widget position. If the widget mapping drifts or the PDF
template is replaced with a different layout, these assertions fail.

Values are deliberately distinct (1a=100001, 1z=100002, 2a=203, …) so
that mis-mapped fields surface as the wrong value at the wrong
position rather than passing silently.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth.models import User

from apps.clients.models import Client, Entity, EntityType, TaxYear
from apps.firms.models import Firm, FirmMembership, Role
from apps.returns.models import (
    FormDefinition,
    FormFieldValue,
    FormLine,
    Taxpayer,
    TaxReturn,
)
from apps.returns.verification import assert_value_at_widget_position
from apps.tts_forms.field_maps.f1040_2025 import FIELD_MAP as F1040_FIELD_MAP
from apps.tts_forms.renderer import render_tax_return


# Distinct value per line — picked so the formatted decimal is unique
# across the whole table (so a mis-routed value lands somewhere
# unexpected and fails the assertion instead of silently passing).
LINE_VALUES: dict[str, str] = {
    "1a":  "100001",
    "1z":  "100002",
    "2a":  "203",
    "2b":  "204",
    "8":   "805",
    "9":   "906",
    "10":  "1007",
    "11":  "1108",
    "12":  "1209",
    "13":  "1310",
    "14":  "1411",
    "15":  "1512",
    "16":  "1613",
    "19":  "1914",   # NOT touched this session; verified Part 2.
    "24":  "2415",
    "25a": "2516",
    "25d": "2517",
    "28":  "2818",   # NOT touched this session; verified Part 2.
    "33":  "3319",
    "34":  "3420",
    "37":  "3721",
}

# Expected widget position per line, derived from the field map's
# acro_name and looked up against the 2025 PDF. (page, x_center, y_center).
# Values match the rects dumped by scripts/inspect_1040_full.py.
EXPECTED_POSITIONS: dict[str, tuple[int, float, float]] = {
    "1a":  (0, 540.0, 456.0),
    "1z":  (0, 540.0, 564.0),
    "2a":  (0, 288.0, 576.0),
    "2b":  (0, 540.0, 576.0),
    "8":   (0, 540.0, 720.0),
    "9":   (0, 540.0, 732.0),
    "10":  (0, 540.0, 744.0),
    "11":  (0, 540.0, 756.0),
    "12":  (1, 540.0, 102.0),
    "13":  (1, 540.0, 114.0),
    "14":  (1, 540.0, 138.0),
    "15":  (1, 540.0, 150.0),
    "16":  (1, 540.0, 162.0),
    "19":  (1, 540.0, 198.0),
    "24":  (1, 540.0, 258.0),
    "25a": (1, 446.0, 282.0),
    "25d": (1, 540.0, 318.0),
    "28":  (1, 446.0, 414.0),
    "33":  (1, 540.0, 474.0),
    "34":  (1, 540.0, 486.0),
    "37":  (1, 540.0, 552.0),
}

# Sanity: every line in FIELD_MAP must be covered by both tables.
assert set(LINE_VALUES) == set(F1040_FIELD_MAP.keys()), (
    f"LINE_VALUES drift: {set(LINE_VALUES) ^ set(F1040_FIELD_MAP.keys())}"
)
assert set(EXPECTED_POSITIONS) == set(F1040_FIELD_MAP.keys()), (
    f"EXPECTED_POSITIONS drift: "
    f"{set(EXPECTED_POSITIONS) ^ set(F1040_FIELD_MAP.keys())}"
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def seeded_forms(django_db_setup, django_db_blocker):
    from django.core.management import call_command

    with django_db_blocker.unblock():
        call_command("seed_1040", "--year", "2025")


@pytest.fixture
def firm(db):
    return Firm.objects.create(name="Test Firm 1040 Audit")


@pytest.fixture
def user(firm):
    u = User.objects.create_user(username="f1040_audit_preparer", password="x")
    FirmMembership.objects.create(user=u, firm=firm, role=Role.PREPARER)
    return u


@pytest.fixture
def form_1040(seeded_forms):
    return FormDefinition.objects.get(code="1040", tax_year_applicable=2025)


@pytest.fixture
def populated_1040_pdf(firm, user, form_1040):
    """Render a 1040 PDF with every FIELD_MAP line set to its distinct value.

    Sets values directly on FormFieldValue rows (no compute pass) — the
    audit's purpose is to verify *render position*, not the compute
    chain. Compute correctness is gated by separate scenario + flow
    assertion tests.
    """
    cl = Client.objects.create(firm=firm, name="Field Map Audit Client")
    ent = Entity.objects.create(client=cl, name="Audit Filer",
                                entity_type=EntityType.INDIVIDUAL)
    ty = TaxYear.objects.create(entity=ent, year=2025)
    tr = TaxReturn.objects.create(tax_year=ty, form_definition=form_1040,
                                  created_by=user)
    Taxpayer.objects.create(
        tax_return=tr,
        filing_status="single",
        first_name="Audit",
        last_name="Filer",
        ssn="999-00-9001",
    )

    # Backfill blank FormFieldValue rows for every 1040 line.
    lines = FormLine.objects.filter(section__form=form_1040)
    FormFieldValue.objects.bulk_create(
        [FormFieldValue(tax_return=tr, form_line=ln, value="") for ln in lines]
    )

    # Set each line in LINE_VALUES.
    for line_number, value in LINE_VALUES.items():
        fv = FormFieldValue.objects.filter(
            tax_return=tr,
            form_line__line_number=line_number,
            form_line__section__form=form_1040,
        ).first()
        if fv is None:
            pytest.skip(
                f"seed_1040 missing line {line_number!r} — audit cannot "
                f"verify render position without a FormFieldValue to write."
            )
        fv.value = value
        fv.save(update_fields=["value"])

    return render_tax_return(tr)


# ---------------------------------------------------------------------------
# Parametrized assertion: one test case per line in FIELD_MAP
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@pytest.mark.parametrize("line_number", sorted(LINE_VALUES.keys()))
def test_field_lands_at_expected_widget_position(populated_1040_pdf, line_number):
    """For each FIELD_MAP line, assert its distinct value lands at the
    declared widget position on the rendered PDF."""
    value = LINE_VALUES[line_number]
    formatted = f"{Decimal(value):,.0f}"  # match renderer's currency formatter
    page, x_center, y_center = EXPECTED_POSITIONS[line_number]
    assert_value_at_widget_position(
        populated_1040_pdf,
        page_number=page,
        expected_value=formatted,
        expected_x=x_center,
        expected_y=y_center,
    )
