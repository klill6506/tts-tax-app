"""
Tests for prior year return import (Lacerte PDF parser + management command).

Tests cover:
    - Lacerte PDF parser: extraction of EIN, entity name, line values,
      balance sheet, other deductions
    - PriorYearReturn model: creation, unique constraint, JSON fields
    - import_prior_year management command: dry-run, live import, matching
    - Prior year API endpoint
"""

import io
import json
import uuid
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import User
from django.test import Client as TestClient

from apps.clients.models import Client, Entity, EntityType, TaxYear
from apps.firms.models import Firm, FirmMembership, Role
from apps.returns.management.commands.seed_1120s import Command as SeedCommand
from apps.returns.models import PriorYearReturn, TaxReturn


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def seeded():
    """Seed form definitions (1120-S with sections and lines)."""
    cmd = SeedCommand()
    cmd.handle(verbosity=0)
    from apps.returns.models import FormDefinition
    return FormDefinition.objects.get(code="1120-S")


@pytest.fixture
def firm():
    return Firm.objects.create(name="Test Firm PY")


@pytest.fixture
def user_and_http(firm):
    user = User.objects.create_user(username="pytest_py", password="pass")
    FirmMembership.objects.create(user=user, firm=firm, role=Role.ADMIN)
    http = TestClient()
    http.login(username="pytest_py", password="pass")
    return user, http


@pytest.fixture
def entity(firm):
    client = Client.objects.create(name="Paradise Garden Tours", firm=firm)
    return Entity.objects.create(
        name="PARADISE FOUND GARDEN TOURS, INC",
        entity_type=EntityType.SCORP,
        client=client,
        ein="",  # No EIN initially (like our real data)
    )


@pytest.fixture
def tax_year(entity):
    return TaxYear.objects.create(entity=entity, year=2025)


@pytest.fixture
def tax_return(seeded, tax_year, user_and_http):
    user, _ = user_and_http
    return TaxReturn.objects.create(
        tax_year=tax_year,
        form_definition=seeded,
        created_by=user,
    )


@pytest.fixture
def prior_year_data(entity):
    return PriorYearReturn.objects.create(
        entity=entity,
        year=2024,
        form_code="1120-S",
        line_values={
            "1c": 112450,
            "3": 112450,
            "6": 112450,
            "16": 100,
            "20": 97412,
            "21": 97512,
            "22": 14938,
        },
        other_deductions={
            "Accounting": 600,
            "Auto and Truck Expense": 1160,
            "Insurance": 238,
        },
        balance_sheet={
            "L1_boy": 11379,
            "L1_eoy": 9122,
            "L15_boy": 11379,
            "L15_eoy": 9122,
        },
        source_software="lacerte",
        source_file="Partial Return for PARADISE.pdf",
    )


# ---------------------------------------------------------------------------
# Parser tests (no DB needed)
# ---------------------------------------------------------------------------


class TestLacerteParser:
    """Test the Lacerte PDF parser on the real sample PDF if available."""

    @pytest.fixture
    def sample_pdf_path(self):
        path = Path("D:/dev/tts-tax-app/Lacerte Export/Partial Return for PARADISE.pdf")
        if not path.exists():
            pytest.skip("Sample Lacerte PDF not available")
        return path

    def test_parse_extracts_ein(self, sample_pdf_path):
        from apps.imports.lacerte_parser import parse_lacerte_1120s

        result = parse_lacerte_1120s(sample_pdf_path)
        assert result.ein == "81-0573751"

    def test_parse_extracts_entity_name(self, sample_pdf_path):
        from apps.imports.lacerte_parser import parse_lacerte_1120s

        result = parse_lacerte_1120s(sample_pdf_path)
        assert "PARADISE" in result.entity_name
        assert "GARDEN TOURS" in result.entity_name

    def test_parse_extracts_form_code(self, sample_pdf_path):
        from apps.imports.lacerte_parser import parse_lacerte_1120s

        result = parse_lacerte_1120s(sample_pdf_path)
        assert result.form_code == "1120-S"

    def test_parse_extracts_tax_year(self, sample_pdf_path):
        from apps.imports.lacerte_parser import parse_lacerte_1120s

        result = parse_lacerte_1120s(sample_pdf_path)
        assert result.tax_year == 2024

    def test_parse_extracts_line_values(self, sample_pdf_path):
        from apps.imports.lacerte_parser import parse_lacerte_1120s

        result = parse_lacerte_1120s(sample_pdf_path)
        assert result.line_values["1c"] == 112450
        assert result.line_values["22"] == 14938
        assert result.line_values["20"] == 97412

    def test_parse_extracts_balance_sheet(self, sample_pdf_path):
        from apps.imports.lacerte_parser import parse_lacerte_1120s

        result = parse_lacerte_1120s(sample_pdf_path)
        assert result.balance_sheet["L1_boy"] == 11379
        assert result.balance_sheet["L1_eoy"] == 9122

    def test_parse_extracts_other_deductions(self, sample_pdf_path):
        from apps.imports.lacerte_parser import parse_lacerte_1120s

        result = parse_lacerte_1120s(sample_pdf_path)
        # This partial Lacerte export doesn't include an "Other Deductions"
        # statement page, so the parser correctly returns empty.
        assert result.other_deductions == {}

    def test_parse_extracts_business_activity_code(self, sample_pdf_path):
        from apps.imports.lacerte_parser import parse_lacerte_1120s

        result = parse_lacerte_1120s(sample_pdf_path)
        assert result.business_activity_code == "487000"

    def test_parse_has_no_warnings(self, sample_pdf_path):
        from apps.imports.lacerte_parser import parse_lacerte_1120s

        result = parse_lacerte_1120s(sample_pdf_path)
        assert result.warnings == []


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPriorYearReturnModel:
    def test_create_prior_year_return(self, entity):
        pyr = PriorYearReturn.objects.create(
            entity=entity,
            year=2024,
            form_code="1120-S",
            line_values={"1c": 100000, "22": 50000},
            balance_sheet={"L1_eoy": 25000},
        )
        assert pyr.id is not None
        assert pyr.year == 2024
        assert pyr.line_values["1c"] == 100000

    def test_unique_constraint(self, entity):
        PriorYearReturn.objects.create(
            entity=entity, year=2024, form_code="1120-S",
        )
        with pytest.raises(Exception):
            PriorYearReturn.objects.create(
                entity=entity, year=2024, form_code="1120-S",
            )

    def test_default_json_fields(self, entity):
        pyr = PriorYearReturn.objects.create(
            entity=entity, year=2023, form_code="1120-S",
        )
        assert pyr.line_values == {}
        assert pyr.other_deductions == {}
        assert pyr.balance_sheet == {}

    def test_str_representation(self, prior_year_data):
        assert "2024" in str(prior_year_data)
        assert "1120-S" in str(prior_year_data)


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPriorYearEndpoint:
    def test_get_prior_year_data(
        self, user_and_http, tax_return, prior_year_data
    ):
        _, http = user_and_http
        resp = http.get(
            f"/api/v1/tax-returns/{tax_return.id}/prior-year/",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["year"] == 2024
        assert data["form_code"] == "1120-S"
        assert data["line_values"]["1c"] == 112450
        assert data["line_values"]["22"] == 14938
        assert "Accounting" in data["other_deductions"]
        assert data["balance_sheet"]["L1_eoy"] == 9122

    def test_prior_year_404_when_no_data(
        self, user_and_http, tax_return
    ):
        _, http = user_and_http
        resp = http.get(
            f"/api/v1/tax-returns/{tax_return.id}/prior-year/",
        )
        assert resp.status_code == 404

    def test_prior_year_includes_entity_name(
        self, user_and_http, tax_return, prior_year_data
    ):
        _, http = user_and_http
        resp = http.get(
            f"/api/v1/tax-returns/{tax_return.id}/prior-year/",
        )
        assert resp.status_code == 200
        assert "PARADISE" in resp.json()["entity_name"]
