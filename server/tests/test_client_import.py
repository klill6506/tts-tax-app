"""Tests for the import_clients management command."""

import os
import tempfile

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.clients.models import Client, Entity, EntityType
from apps.firms.models import Firm


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def firm(db):
    return Firm.objects.create(name="Test Firm")


@pytest.fixture
def lacerte_csv():
    """Lacerte-style CSV with split TP/SP name columns."""
    content = (
        "TP Last Name,TP First Name,TP SSN,SP Last Name,SP First Name,SP SSN,"
        "Street Address,City,State,Zip,Email\n"
        "Smith,John,123-45-6789,Smith,Jane,987-65-4321,"
        "100 Main St,Athens,GA,30601,john@example.com\n"
        "Doe,Jane,111-22-3333,,,,"
        "200 Oak Ave,Atlanta,GA,30301,\n"
        "Johnson,Bob,444-55-6666,Johnson,Mary,777-88-9999,"
        "300 Pine Rd,Savannah,GA,31401,bob@test.com\n"
    )
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as f:
        f.write(content)
        path = f.name
    yield path
    os.unlink(path)


@pytest.fixture
def single_name_csv():
    """CSV with a single 'Name' column (pre-combined)."""
    content = (
        "Name,SSN,Address,City,State,Zip,Phone\n"
        '"Williams, Roger",555-66-7777,400 Elm St,Macon,GA,31201,555-1234\n'
        '"Brown, Alice",888-99-0000,500 Birch Ln,Augusta,GA,30901,\n'
    )
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as f:
        f.write(content)
        path = f.name
    yield path
    os.unlink(path)


@pytest.fixture
def csv_name_only():
    """CSV with only a name column."""
    content = "Name\nAlpha Client\nBeta Client\n"
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as f:
        f.write(content)
        path = f.name
    yield path
    os.unlink(path)


@pytest.fixture
def csv_no_name_col():
    """CSV missing a recognizable name column."""
    content = "ID,Value\n1,100\n2,200\n"
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as f:
        f.write(content)
        path = f.name
    yield path
    os.unlink(path)


@pytest.fixture
def csv_with_blanks():
    """Lacerte-style CSV with blank rows mixed in."""
    content = (
        "TP Last Name,TP First Name,TP SSN,Street Address,City,State,Zip\n"
        "Good,Row,111-11-1111,1 St,City,GA,30000\n"
        ",,,,,,\n"
        "  ,  ,  ,  ,  ,  ,  \n"
        "Another,Good,222-22-2222,2 St,Town,GA,30001\n"
    )
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as f:
        f.write(content)
        path = f.name
    yield path
    os.unlink(path)


@pytest.fixture
def txt_file():
    """Tab-delimited TXT file with Lacerte-style columns."""
    content = (
        "TP Last Name\tTP First Name\tTP SSN\tStreet Address\tCity\tState\tZip\n"
        "Tab\tClient\t333-33-3333\t99 Tab St\tTabCity\tGA\t30000\n"
    )
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        f.write(content)
        path = f.name
    yield path
    os.unlink(path)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestImportClientsCommand:

    def test_lacerte_csv_import(self, firm, lacerte_csv):
        """Lacerte-style split TP/SP columns produce 'Last, First' names."""
        call_command("import_clients", lacerte_csv, "--firm", str(firm.id))
        assert Client.objects.filter(firm=firm).count() == 3
        assert Entity.objects.count() == 3

        # Check first client — split name combined as "Last, First"
        john = Client.objects.get(name="Smith, John")
        entity = john.entities.first()
        assert entity.entity_type == EntityType.INDIVIDUAL
        assert entity.legal_name == "Smith, John"
        assert entity.ein == "123-45-6789"
        assert entity.address_line1 == "100 Main St"
        assert entity.city == "Athens"
        assert entity.state == "GA"
        assert entity.zip_code == "30601"
        assert entity.email == "john@example.com"

    def test_spouse_data_imported(self, firm, lacerte_csv):
        """Spouse fields are populated from SP columns."""
        call_command("import_clients", lacerte_csv, "--firm", str(firm.id))

        john_entity = Client.objects.get(name="Smith, John").entities.first()
        assert john_entity.spouse_first_name == "Jane"
        assert john_entity.spouse_last_name == "Smith"
        assert john_entity.spouse_ssn == "987-65-4321"

        # Jane Doe has no spouse
        jane_entity = Client.objects.get(name="Doe, Jane").entities.first()
        assert jane_entity.spouse_first_name == ""
        assert jane_entity.spouse_last_name == ""
        assert jane_entity.spouse_ssn == ""

    def test_single_name_column(self, firm, single_name_csv):
        """Falls back to single 'Name' column when no TP split columns."""
        call_command("import_clients", single_name_csv, "--firm", str(firm.id))
        assert Client.objects.filter(firm=firm).count() == 2
        roger = Client.objects.get(name="Williams, Roger")
        entity = roger.entities.first()
        assert entity.ein == "555-66-7777"
        assert entity.phone == "555-1234"

    def test_name_only_csv(self, firm, csv_name_only):
        call_command("import_clients", csv_name_only, "--firm", str(firm.id))
        assert Client.objects.filter(firm=firm).count() == 2
        alpha = Client.objects.get(name="Alpha Client")
        entity = alpha.entities.first()
        assert entity.entity_type == EntityType.INDIVIDUAL
        assert entity.ein == ""
        assert entity.address_line1 == ""

    def test_no_name_column_raises_error(self, firm, csv_no_name_col):
        with pytest.raises(CommandError, match="Could not detect a name column"):
            call_command("import_clients", csv_no_name_col, "--firm", str(firm.id))

    def test_missing_file_raises_error(self, firm):
        with pytest.raises(CommandError, match="File not found"):
            call_command(
                "import_clients", "/nonexistent/file.csv",
                "--firm", str(firm.id),
            )

    def test_bad_firm_raises_error(self, lacerte_csv):
        with pytest.raises(CommandError, match="Firm not found"):
            call_command(
                "import_clients", lacerte_csv,
                "--firm", "00000000-0000-0000-0000-000000000000",
            )

    def test_skips_blank_rows(self, firm, csv_with_blanks):
        call_command("import_clients", csv_with_blanks, "--firm", str(firm.id))
        # Two data rows, blank rows skipped
        assert Client.objects.filter(firm=firm).count() == 2

    def test_skips_duplicates(self, firm, lacerte_csv):
        # Pre-create one client with the combined name
        Client.objects.create(firm=firm, name="Smith, John")
        call_command("import_clients", lacerte_csv, "--firm", str(firm.id))
        # Smith skipped, Doe and Johnson created
        assert Client.objects.filter(firm=firm).count() == 3
        # Only 2 entities (the pre-existing John has no entity from import)
        assert Entity.objects.count() == 2

    def test_dry_run_creates_nothing(self, firm, lacerte_csv):
        call_command(
            "import_clients", lacerte_csv,
            "--firm", str(firm.id), "--dry-run",
        )
        assert Client.objects.filter(firm=firm).count() == 0
        assert Entity.objects.count() == 0

    def test_txt_tab_delimited(self, firm, txt_file):
        call_command("import_clients", txt_file, "--firm", str(firm.id))
        assert Client.objects.filter(firm=firm).count() == 1
        tab_client = Client.objects.get(name="Tab, Client")
        entity = tab_client.entities.first()
        assert entity.ein == "333-33-3333"
        assert entity.city == "TabCity"

    def test_all_entities_are_individual(self, firm, lacerte_csv):
        call_command("import_clients", lacerte_csv, "--firm", str(firm.id))
        for entity in Entity.objects.all():
            assert entity.entity_type == EntityType.INDIVIDUAL

    def test_legal_name_matches_client_name(self, firm, lacerte_csv):
        call_command("import_clients", lacerte_csv, "--firm", str(firm.id))
        for entity in Entity.objects.all():
            assert entity.legal_name == entity.client.name
