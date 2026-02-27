"""Tests for the import_scorps management command."""

import csv
import os
import tempfile

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.clients.models import (
    Client,
    ClientEntityLink,
    Entity,
    EntityType,
    LinkRole,
)
from apps.firms.models import Firm, FirmMembership, Role


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_csv(path, headers, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row)


CORP_HEADERS = ["client_no", "corp_name", "corp_address", "corp_city_state_zip", "prep_no"]
SH_HEADERS = [
    "client_no", "shareholder_name", "shareholder_address",
    "shareholder_city_state_zip", "phone", "fax", "email",
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def firm(db):
    return Firm.objects.create(name="Test Tax Firm")


@pytest.fixture
def tmpdir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def corps_csv(tmpdir):
    path = os.path.join(tmpdir, "corps.csv")
    _write_csv(path, CORP_HEADERS, [
        ["101", "ACME CORP", "123 MAIN ST", "ATHENS, GA 30606", "1"],
        ["102", "BETA LLC", "456 OAK AVE", "ATLANTA, GA 30329", "2"],
    ])
    return path


@pytest.fixture
def shareholders_csv(tmpdir):
    path = os.path.join(tmpdir, "shareholders.csv")
    _write_csv(path, SH_HEADERS, [
        ["101", "JOHN SMITH", "789 ELM ST", "ATHENS, GA 30606", "(706) 555-1234", "", "john@acme.com"],
        ["101", "JANE DOE", "100 PINE RD", "ATLANTA, GA 30329", "", "", ""],
        ["102", "BOB JONES", "200 MAPLE DR", "DECATUR, GA 30030", "(404) 555-9999", "", "bob@beta.com"],
    ])
    return path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestImportScorps:

    def test_basic_import(self, firm, corps_csv, shareholders_csv):
        call_command(
            "import_scorps",
            f"--corps={corps_csv}",
            f"--shareholders={shareholders_csv}",
            f"--firm={firm.id}",
        )
        # 2 S-Corp clients + 3 shareholder individuals = 5
        assert Client.objects.filter(firm=firm).count() == 5
        # 2 S-Corp entities
        scorps = Entity.objects.filter(entity_type=EntityType.SCORP)
        assert scorps.count() == 2
        # 3 shareholders created as individual clients + entities
        individuals = Entity.objects.filter(entity_type=EntityType.INDIVIDUAL)
        assert individuals.count() == 3
        # 3 shareholder links
        links = ClientEntityLink.objects.filter(role=LinkRole.SHAREHOLDER)
        assert links.count() == 3
        # 3 taxpayer self-links for the new individuals
        taxpayer_links = ClientEntityLink.objects.filter(role=LinkRole.TAXPAYER)
        assert taxpayer_links.count() == 3

    def test_scorp_entity_fields(self, firm, corps_csv, shareholders_csv):
        call_command(
            "import_scorps",
            f"--corps={corps_csv}",
            f"--shareholders={shareholders_csv}",
            f"--firm={firm.id}",
        )
        entity = Entity.objects.get(name="ACME CORP")
        assert entity.entity_type == EntityType.SCORP
        assert entity.address_line1 == "123 MAIN ST"
        assert entity.city == "ATHENS"
        assert entity.state == "GA"
        assert entity.zip_code == "30606"
        assert entity.legal_name == "ACME CORP"

    def test_shareholder_name_conversion(self, firm, corps_csv, shareholders_csv):
        call_command(
            "import_scorps",
            f"--corps={corps_csv}",
            f"--shareholders={shareholders_csv}",
            f"--firm={firm.id}",
        )
        # "JOHN SMITH" should become "SMITH, JOHN"
        assert Client.objects.filter(firm=firm, name="SMITH, JOHN").exists()
        assert Client.objects.filter(firm=firm, name="DOE, JANE").exists()
        assert Client.objects.filter(firm=firm, name="JONES, BOB").exists()

    def test_shareholder_individual_entity_created(self, firm, corps_csv, shareholders_csv):
        call_command(
            "import_scorps",
            f"--corps={corps_csv}",
            f"--shareholders={shareholders_csv}",
            f"--firm={firm.id}",
        )
        john = Client.objects.get(firm=firm, name="SMITH, JOHN")
        entity = Entity.objects.get(client=john)
        assert entity.entity_type == EntityType.INDIVIDUAL
        assert entity.address_line1 == "789 ELM ST"
        assert entity.phone == "(706) 555-1234"
        assert entity.email == "john@acme.com"

    def test_first_shareholder_is_primary(self, firm, corps_csv, shareholders_csv):
        call_command(
            "import_scorps",
            f"--corps={corps_csv}",
            f"--shareholders={shareholders_csv}",
            f"--firm={firm.id}",
        )
        acme = Entity.objects.get(name="ACME CORP")
        john = Client.objects.get(name="SMITH, JOHN")
        jane = Client.objects.get(name="DOE, JANE")
        link_john = ClientEntityLink.objects.get(
            client=john, entity=acme, role=LinkRole.SHAREHOLDER
        )
        link_jane = ClientEntityLink.objects.get(
            client=jane, entity=acme, role=LinkRole.SHAREHOLDER
        )
        assert link_john.is_primary is True
        assert link_jane.is_primary is False

    def test_matches_existing_individual(self, firm, corps_csv, shareholders_csv):
        # Pre-create an individual that should match shareholder "JOHN SMITH"
        existing = Client.objects.create(firm=firm, name="SMITH, JOHN")
        Entity.objects.create(
            client=existing,
            name="SMITH, JOHN",
            entity_type=EntityType.INDIVIDUAL,
        )
        call_command(
            "import_scorps",
            f"--corps={corps_csv}",
            f"--shareholders={shareholders_csv}",
            f"--firm={firm.id}",
        )
        # Should NOT create a duplicate "SMITH, JOHN"
        assert Client.objects.filter(firm=firm, name="SMITH, JOHN").count() == 1
        # But should create shareholder link to the existing client
        acme = Entity.objects.get(name="ACME CORP")
        assert ClientEntityLink.objects.filter(
            client=existing, entity=acme, role=LinkRole.SHAREHOLDER
        ).exists()

    def test_skip_zz_prefix(self, firm, tmpdir, shareholders_csv):
        corps = os.path.join(tmpdir, "corps.csv")
        _write_csv(corps, CORP_HEADERS, [
            ["101", "ACME CORP", "123 MAIN ST", "ATHENS, GA 30606", "1"],
            ["ZZ1", "ZZ - INACTIVE CORP", "456 OAK", "ATLANTA, GA 30329", "7"],
            ["ZZ2", "zzOther Closed LLC", "789 ELM", "DECATUR, GA 30030", "7"],
        ])
        call_command(
            "import_scorps",
            f"--corps={corps}",
            f"--shareholders={shareholders_csv}",
            f"--firm={firm.id}",
        )
        # 1 corp + 2 shareholders for corp 101 (BOB JONES for 102 is skipped — no corp 102)
        assert Client.objects.filter(firm=firm).count() == 3
        assert Entity.objects.filter(entity_type=EntityType.SCORP).count() == 1

    def test_include_zz_flag(self, firm, tmpdir, shareholders_csv):
        corps = os.path.join(tmpdir, "corps.csv")
        _write_csv(corps, CORP_HEADERS, [
            ["101", "ACME CORP", "123 MAIN ST", "ATHENS, GA 30606", "1"],
            ["ZZ1", "ZZ - INACTIVE CORP", "456 OAK", "ATLANTA, GA 30329", "7"],
        ])
        call_command(
            "import_scorps",
            f"--corps={corps}",
            f"--shareholders={shareholders_csv}",
            f"--firm={firm.id}",
            "--include-zz",
        )
        assert Entity.objects.filter(entity_type=EntityType.SCORP).count() == 2

    def test_idempotent(self, firm, corps_csv, shareholders_csv):
        call_command(
            "import_scorps",
            f"--corps={corps_csv}",
            f"--shareholders={shareholders_csv}",
            f"--firm={firm.id}",
        )
        count_before = Client.objects.count()
        links_before = ClientEntityLink.objects.count()

        # Run again — should create nothing new
        call_command(
            "import_scorps",
            f"--corps={corps_csv}",
            f"--shareholders={shareholders_csv}",
            f"--firm={firm.id}",
        )
        assert Client.objects.count() == count_before
        assert ClientEntityLink.objects.count() == links_before

    def test_dry_run_creates_nothing(self, firm, corps_csv, shareholders_csv):
        call_command(
            "import_scorps",
            f"--corps={corps_csv}",
            f"--shareholders={shareholders_csv}",
            f"--firm={firm.id}",
            "--dry-run",
        )
        assert Client.objects.filter(firm=firm).count() == 0
        assert Entity.objects.count() == 0
        assert ClientEntityLink.objects.count() == 0

    def test_embedded_address_parsing(self, firm, tmpdir, shareholders_csv):
        corps = os.path.join(tmpdir, "corps.csv")
        _write_csv(corps, CORP_HEADERS, [
            ["101", "EMBEDDED ADDR CORP", "1592 MARS HILL RD STE A WATKINSVILLE, GA 30677", "", "1"],
        ])
        call_command(
            "import_scorps",
            f"--corps={corps}",
            f"--shareholders={shareholders_csv}",
            f"--firm={firm.id}",
        )
        entity = Entity.objects.get(name="EMBEDDED ADDR CORP")
        assert entity.city == "WATKINSVILLE"
        assert entity.state == "GA"
        assert entity.zip_code == "30677"
        assert entity.address_line1 == "1592 MARS HILL RD STE A"

    def test_name_with_suffix(self, firm, tmpdir):
        corps = os.path.join(tmpdir, "corps.csv")
        _write_csv(corps, CORP_HEADERS, [
            ["101", "SUFFIX TEST CORP", "123 MAIN", "ATHENS, GA 30606", "1"],
        ])
        sh = os.path.join(tmpdir, "sh.csv")
        _write_csv(sh, SH_HEADERS, [
            ["101", "TOMMY MARTIN JR", "100 ELM", "ATHENS, GA 30606", "", "", ""],
        ])
        call_command(
            "import_scorps",
            f"--corps={corps}",
            f"--shareholders={sh}",
            f"--firm={firm.id}",
        )
        assert Client.objects.filter(name="MARTIN JR, TOMMY").exists()

    def test_missing_file_raises_error(self, firm, tmpdir):
        with pytest.raises(CommandError, match="File not found"):
            call_command(
                "import_scorps",
                "--corps=/nonexistent/corps.csv",
                f"--shareholders={tmpdir}/sh.csv",
                f"--firm={firm.id}",
            )

    def test_bad_firm_raises_error(self, firm, corps_csv, shareholders_csv):
        with pytest.raises(CommandError, match="not found"):
            call_command(
                "import_scorps",
                f"--corps={corps_csv}",
                f"--shareholders={shareholders_csv}",
                "--firm=00000000-0000-0000-0000-000000000000",
            )

    def test_duplicate_corp_names_handled(self, firm, tmpdir, shareholders_csv):
        """Two client_nos with the same corp_name should create only one Client."""
        corps = os.path.join(tmpdir, "corps.csv")
        _write_csv(corps, CORP_HEADERS, [
            ["A1", "SAME NAME LLC", "123 MAIN", "ATHENS, GA 30606", "1"],
            ["A2", "SAME NAME LLC", "456 OAK", "ATLANTA, GA 30329", "2"],
        ])
        call_command(
            "import_scorps",
            f"--corps={corps}",
            f"--shareholders={shareholders_csv}",
            f"--firm={firm.id}",
        )
        assert Client.objects.filter(firm=firm, name="SAME NAME LLC").count() == 1

    def test_shareholders_for_skipped_zz_not_imported(self, firm, tmpdir):
        corps = os.path.join(tmpdir, "corps.csv")
        _write_csv(corps, CORP_HEADERS, [
            ["ZZ1", "zzINACTIVE CORP", "123 MAIN", "ATHENS, GA 30606", "7"],
        ])
        sh = os.path.join(tmpdir, "sh.csv")
        _write_csv(sh, SH_HEADERS, [
            ["ZZ1", "JOHN SMITH", "100 ELM", "ATHENS, GA 30606", "", "", ""],
        ])
        call_command(
            "import_scorps",
            f"--corps={corps}",
            f"--shareholders={sh}",
            f"--firm={firm.id}",
        )
        assert Client.objects.filter(firm=firm).count() == 0
        assert ClientEntityLink.objects.count() == 0
