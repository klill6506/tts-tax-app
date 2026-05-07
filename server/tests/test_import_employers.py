"""Integration tests for `manage.py import_employers`.

Synthetic CSV fixtures are built per-test via tempfile.NamedTemporaryFile —
no committed CSV files. UTF-8 BOM is included to mirror the real source.
"""
from __future__ import annotations

import tempfile
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.employers.models import Employer


# Header row with leading whitespace (matches real TaxWise export).
CSV_HEADER = "     EIN,                  NAME ,           ADDRESS,           CITY"


def _write_csv(rows: list[str]) -> Path:
    """Write a UTF-8-BOM CSV file to a tempfile and return its path."""
    handle = tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8-sig", newline="",
    )
    handle.write(CSV_HEADER + "\r\n")
    for r in rows:
        handle.write(r + "\r\n")
    handle.close()
    return Path(handle.name)


# Five fixture rows covering the test surface:
#   1. Clean MFJ-style row, valid EIN, parseable city
#   2. Another clean row with ZIP+4
#   3. Invalid EIN — should be logged as error, not crash
#   4. Address contains a line-2 fragment ("SUITE 800") — parse_warning expected
#   5. Missing zip in city column — parse_warning expected
SAMPLE_ROWS = [
    "11-1111111,ACME CORP,123 MAIN ST,DALLAS TX 75001-",
    "22-2222222,BETA LLC,456 OAK AVE,\"AUSTIN, TX 78701-1234\"",
    "1234,GAMMA INC,789 PINE RD,HOUSTON TX 77002-",
    "33-3333333,DELTA HOLDINGS,SUITE 800,\"PHOENIX, AZ 85001\"",
    "44-4444444,EPSILON GROUP,2500 BROAD ST,BOSTON MA",
]


@pytest.fixture
def csv_path(db):
    p = _write_csv(SAMPLE_ROWS)
    yield p
    p.unlink(missing_ok=True)


@pytest.mark.django_db
class TestDryRun:
    def test_dry_run_writes_nothing(self, csv_path):
        out = StringIO()
        call_command(
            "import_employers", "--csv-file", str(csv_path), stdout=out,
        )
        assert "DRY-RUN" in out.getvalue()
        assert Employer.objects.count() == 0

    def test_dry_run_reports_per_row_categories(self, csv_path):
        out = StringIO()
        call_command(
            "import_employers", "--csv-file", str(csv_path), stdout=out,
        )
        text = out.getvalue()
        # 5 total, 1 invalid EIN, 4 valid
        assert "total=5" in text
        assert "would create=4" in text
        assert "errors=1" in text
        # parse_warning categories are reported even on dry-run
        assert "address line 2 detected" in text
        assert "missing zip" in text


@pytest.mark.django_db
class TestCommit:
    def test_commit_creates_expected_rows(self, csv_path):
        out = StringIO()
        call_command(
            "import_employers", "--csv-file", str(csv_path),
            "--commit", stdout=out,
        )
        # 4 valid EINs persisted; 1 malformed row counted as error
        assert Employer.objects.count() == 4
        # Spot-check one upserted EIN structurally — no name/address echoed
        e = Employer.objects.get(ein="11-1111111")
        assert e.source == "taxwise_import"
        assert e.verified is False
        assert e.state == "TX"
        assert e.zip == "75001"

    def test_commit_zip_plus_four_kept(self, csv_path):
        call_command(
            "import_employers", "--csv-file", str(csv_path),
            "--commit", stdout=StringIO(),
        )
        e = Employer.objects.get(ein="22-2222222")
        assert e.zip == "78701-1234"

    def test_parse_warning_for_address_line_2(self, csv_path):
        call_command(
            "import_employers", "--csv-file", str(csv_path),
            "--commit", stdout=StringIO(),
        )
        e = Employer.objects.get(ein="33-3333333")
        assert "address line 2 detected" in e.parse_warning

    def test_parse_warning_for_missing_zip(self, csv_path):
        call_command(
            "import_employers", "--csv-file", str(csv_path),
            "--commit", stdout=StringIO(),
        )
        e = Employer.objects.get(ein="44-4444444")
        assert "missing zip" in e.parse_warning

    def test_no_employer_created_for_malformed_ein(self, csv_path):
        call_command(
            "import_employers", "--csv-file", str(csv_path),
            "--commit", stdout=StringIO(),
        )
        # GAMMA had EIN "1234" (rejected). Confirm structurally — no PII.
        assert not Employer.objects.filter(name="GAMMA INC").exists()

    def test_source_flag_respected(self, csv_path):
        call_command(
            "import_employers", "--csv-file", str(csv_path),
            "--commit", "--source", "user_entered", stdout=StringIO(),
        )
        # All newly-created rows tagged with the requested source.
        assert (
            Employer.objects.filter(source="user_entered").count() == 4
        )


@pytest.mark.django_db
class TestUpsertBehavior:
    def test_rerun_updates_not_duplicates(self, csv_path):
        # First commit
        call_command(
            "import_employers", "--csv-file", str(csv_path),
            "--commit", stdout=StringIO(),
        )
        first_count = Employer.objects.count()
        assert first_count == 4

        # Second commit — same data
        out = StringIO()
        call_command(
            "import_employers", "--csv-file", str(csv_path),
            "--commit", stdout=out,
        )
        # Count unchanged; updated counter should reflect 4
        assert Employer.objects.count() == first_count
        assert "updated=4" in out.getvalue()
        assert "created=0" in out.getvalue()

    def test_verified_records_skipped_on_update(self, csv_path):
        # Pre-create one of the EINs as verified, with deliberately stale data.
        e = Employer.objects.create(
            ein="11-1111111",
            name="STALE NAME",
            street="STALE ADDR",
            city="STALE CITY",
            state="ZZ",
            zip="00000",
            source="user_entered",
            verified=True,
        )
        out = StringIO()
        call_command(
            "import_employers", "--csv-file", str(csv_path),
            "--commit", stdout=out,
        )
        # The verified row was NOT overwritten
        e.refresh_from_db()
        assert e.name == "STALE NAME"
        assert e.state == "ZZ"
        # Counters reflect the skip
        assert "skipped_verified=1" in out.getvalue()
        # Other 3 valid rows still got created
        assert Employer.objects.count() == 4


@pytest.mark.django_db
class TestErrors:
    def test_missing_csv_file(self, db):
        with pytest.raises(CommandError):
            call_command(
                "import_employers", "--csv-file", "/nonexistent/x.csv",
                stdout=StringIO(),
            )

    def test_missing_required_header(self, db):
        bad = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False,
            encoding="utf-8-sig", newline="",
        )
        bad.write("EIN,NAME\r\n11-1111111,FOO\r\n")
        bad.close()
        try:
            with pytest.raises(CommandError):
                call_command(
                    "import_employers", "--csv-file", bad.name,
                    stdout=StringIO(),
                )
        finally:
            Path(bad.name).unlink(missing_ok=True)

    def test_malformed_ein_does_not_crash(self, csv_path):
        # The fixture has 1 malformed EIN — command must complete cleanly.
        out = StringIO()
        call_command(
            "import_employers", "--csv-file", str(csv_path),
            "--commit", stdout=out,
        )
        assert "errors=1" in out.getvalue()
        assert "malformed EIN" in out.getvalue()


@pytest.mark.django_db
class TestLimit:
    def test_limit_caps_processed_count(self, csv_path):
        out = StringIO()
        call_command(
            "import_employers", "--csv-file", str(csv_path),
            "--commit", "--limit", "2", stdout=out,
        )
        # Only 2 rows processed total → 2 created (both clean), 0 errors.
        assert "total=2" in out.getvalue()
        assert Employer.objects.count() == 2
