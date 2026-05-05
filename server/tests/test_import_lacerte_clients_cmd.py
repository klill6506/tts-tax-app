"""Integration tests for `manage.py import_lacerte_clients`."""

from __future__ import annotations

from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.clients.models import Client, Entity, EntityType, TaxYear
from apps.firms.models import Firm
from apps.returns.models import FormDefinition, Taxpayer, TaxReturn

from tests.test_lacerte_clientlist_parser import SAMPLE_ROWS, build_synthetic_pdf


@pytest.fixture
def firm(db):
    return Firm.objects.create(name="Import Test Firm")


@pytest.fixture
def form_1040(db):
    return FormDefinition.objects.create(
        code="1040", name="Form 1040", tax_year_applicable=2025,
    )


@pytest.fixture
def synthetic_pdf(tmp_path):
    path = tmp_path / "clientlist.pdf"
    path.write_bytes(build_synthetic_pdf(SAMPLE_ROWS))
    return path


class TestDryRun:
    def test_dry_run_writes_nothing(self, firm, form_1040, synthetic_pdf):
        out = StringIO()
        call_command(
            "import_lacerte_clients",
            "--pdf-file", str(synthetic_pdf),
            "--tax-year", "2025",
            "--firm", str(firm.id),
            stdout=out,
        )
        text = out.getvalue()
        assert "DRY-RUN" in text
        assert f"Would import" in text
        # Nothing persisted.
        assert Client.objects.filter(firm=firm).count() == 0
        assert Entity.objects.count() == 0
        assert Taxpayer.objects.count() == 0

    def test_dry_run_reports_all_rows(self, firm, form_1040, synthetic_pdf):
        out = StringIO()
        call_command(
            "import_lacerte_clients",
            "--pdf-file", str(synthetic_pdf),
            "--tax-year", "2025",
            "--firm", str(firm.id),
            stdout=out,
        )
        text = out.getvalue()
        assert f"created={len(SAMPLE_ROWS)}" in text


class TestCommit:
    def test_commit_creates_full_chain(self, firm, form_1040, synthetic_pdf):
        out = StringIO()
        call_command(
            "import_lacerte_clients",
            "--pdf-file", str(synthetic_pdf),
            "--tax-year", "2025",
            "--firm", str(firm.id),
            "--commit",
            stdout=out,
        )
        # Sanitized by default — fake SSNs, fake names. We just check counts +
        # that the chain was wired up correctly.
        assert Client.objects.filter(firm=firm).count() == len(SAMPLE_ROWS)
        assert Entity.objects.filter(
            client__firm=firm, entity_type=EntityType.INDIVIDUAL
        ).count() == len(SAMPLE_ROWS)
        assert TaxYear.objects.filter(entity__client__firm=firm, year=2025).count() == len(SAMPLE_ROWS)
        assert TaxReturn.objects.filter(
            tax_year__entity__client__firm=firm, form_definition=form_1040
        ).count() == len(SAMPLE_ROWS)
        assert Taxpayer.objects.filter(
            tax_return__tax_year__entity__client__firm=firm
        ).count() == len(SAMPLE_ROWS)

    def test_commit_is_idempotent(self, firm, form_1040, synthetic_pdf):
        """Running twice doesn't create duplicates — second run is all 'nochange'."""
        out = StringIO()
        call_command(
            "import_lacerte_clients",
            "--pdf-file", str(synthetic_pdf),
            "--tax-year", "2025",
            "--firm", str(firm.id),
            "--commit",
            stdout=out,
        )
        first_count = Client.objects.filter(firm=firm).count()

        out2 = StringIO()
        call_command(
            "import_lacerte_clients",
            "--pdf-file", str(synthetic_pdf),
            "--tax-year", "2025",
            "--firm", str(firm.id),
            "--commit",
            stdout=out2,
        )
        assert Client.objects.filter(firm=firm).count() == first_count
        # Second run should report nochange for every record.
        assert f"nochange={len(SAMPLE_ROWS)}" in out2.getvalue()

    def test_commit_infers_filing_status(self, firm, form_1040, synthetic_pdf):
        call_command(
            "import_lacerte_clients",
            "--pdf-file", str(synthetic_pdf),
            "--tax-year", "2025",
            "--firm", str(firm.id),
            "--commit",
            stdout=StringIO(),
        )
        statuses = set(
            Taxpayer.objects.filter(
                tax_return__tax_year__entity__client__firm=firm
            ).values_list("filing_status", flat=True)
        )
        assert "mfj" in statuses
        assert "single" in statuses


class TestErrors:
    def test_missing_pdf(self, firm, form_1040):
        with pytest.raises(CommandError):
            call_command(
                "import_lacerte_clients",
                "--pdf-file", "/nonexistent/path.pdf",
                "--firm", str(firm.id),
                stdout=StringIO(),
            )

    def test_missing_form_definition(self, firm, synthetic_pdf):
        # No FormDefinition for code=1040 in this DB.
        with pytest.raises(CommandError):
            call_command(
                "import_lacerte_clients",
                "--pdf-file", str(synthetic_pdf),
                "--firm", str(firm.id),
                stdout=StringIO(),
            )
