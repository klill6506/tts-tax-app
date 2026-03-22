"""
Tests for Lacerte depreciation TXT import parser.

Uses the MWELDING fixture: tests/fixtures/lacerte_mwelding.txt
"""

from pathlib import Path

import pytest

from apps.imports.importers.lacerte_depr_parser import (
    _classify_group,
    _parse_date,
    _parse_amount,
    parse_lacerte_txt,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures"
MWELDING_PATH = FIXTURE_DIR / "lacerte_mwelding.txt"


@pytest.fixture
def mwelding_content():
    return MWELDING_PATH.read_text(encoding="utf-8")


@pytest.fixture
def parsed_assets(mwelding_content):
    return parse_lacerte_txt(mwelding_content)


# ---------------------------------------------------------------------------
# Parser integration tests (full file)
# ---------------------------------------------------------------------------

class TestParseLacerteTxt:
    def test_parses_correct_asset_count(self, parsed_assets):
        assert len(parsed_assets) == 12

    def test_all_assets_have_required_fields(self, parsed_assets):
        required = [
            "asset_number", "description", "date_acquired",
            "cost_basis", "method", "convention", "life",
            "asset_group", "prior_depreciation", "current_depreciation",
        ]
        for asset in parsed_assets:
            for field in required:
                assert field in asset, f"Missing field '{field}' in asset {asset.get('asset_number')}"

    def test_first_asset_chevy_truck(self, parsed_assets):
        a = parsed_assets[0]
        assert a["asset_number"] == 8
        assert a["description"] == "2008 Chevy Truck"
        assert a["date_acquired"] == "2020-08-12"
        assert a["date_sold"] is None
        assert a["cost_basis"] == 18000
        assert a["business_pct"] == 100.0
        assert a["prior_depreciation"] == 17712
        assert a["current_depreciation"] == 288
        assert a["method"] == "200DB"
        assert a["convention"] == "HY"
        assert a["life"] == 5
        assert a["asset_group"] == "vehicles"

    def test_business_pct_parsed(self, parsed_assets):
        """Asset #9 (Dodge Ram) has 51% business use."""
        dodge = next(a for a in parsed_assets if a["asset_number"] == 9)
        assert dodge["business_pct"] == 51.0
        assert dodge["cost_basis"] == 89642
        assert dodge["prior_depreciation"] == 41465

    def test_fully_depreciated_asset(self, parsed_assets):
        """Assets 1-7 are fully depreciated (current_depreciation = 0)."""
        forklift = next(a for a in parsed_assets if a["asset_number"] == 1)
        assert forklift["current_depreciation"] == 0
        assert forklift["prior_depreciation"] == 4815
        assert forklift["cost_basis"] == 4815

    def test_no_sold_dates(self, parsed_assets):
        """MWELDING fixture has no disposed assets."""
        for a in parsed_assets:
            assert a["date_sold"] is None

    def test_total_cost_basis(self, parsed_assets):
        """Total cost should match Lacerte grand total: 150,628."""
        total = sum(a["cost_basis"] for a in parsed_assets)
        assert total == 150628

    def test_total_prior_depreciation(self, parsed_assets):
        """Total prior depr should match: 102,163."""
        total = sum(a["prior_depreciation"] for a in parsed_assets)
        assert total == 102163

    def test_total_current_depreciation(self, parsed_assets):
        """Total current depr should match: 2,554."""
        total = sum(a["current_depreciation"] for a in parsed_assets)
        assert total == 2554

    def test_totals_and_headers_skipped(self, parsed_assets):
        """No asset should have description starting with 'Total' or 'Grand'."""
        for a in parsed_assets:
            assert not a["description"].startswith("Total")
            assert not a["description"].startswith("Grand")


# ---------------------------------------------------------------------------
# Group detection
# ---------------------------------------------------------------------------

class TestGroupDetection:
    def test_vehicles_group(self, parsed_assets):
        vehicle_assets = [a for a in parsed_assets if a["asset_group"] == "vehicles"]
        assert len(vehicle_assets) == 2
        assert all(a["asset_number"] in (8, 9) for a in vehicle_assets)

    def test_machinery_group(self, parsed_assets):
        mach_assets = [a for a in parsed_assets if a["asset_group"] == "machinery_equipment"]
        assert len(mach_assets) == 10

    def test_classify_group_auto_transport(self):
        assert _classify_group("Auto / Transport Equipment") == "vehicles"
        assert _classify_group("auto / transport equipment") == "vehicles"

    def test_classify_group_machinery(self):
        assert _classify_group("Machinery and Equipment") == "machinery_equipment"
        assert _classify_group("Machinery & Equipment") == "machinery_equipment"

    def test_classify_group_furniture(self):
        assert _classify_group("Furniture and Fixtures") == "furniture_fixtures"

    def test_classify_group_buildings(self):
        assert _classify_group("Buildings") == "buildings"

    def test_classify_group_land(self):
        assert _classify_group("Land") == "land"

    def test_classify_group_improvements(self):
        assert _classify_group("Land Improvements") == "improvements"
        assert _classify_group("Leasehold Improvements") == "improvements"

    def test_classify_group_intangibles(self):
        assert _classify_group("Intangible Assets") == "intangibles"

    def test_classify_group_unknown_defaults(self):
        assert _classify_group("Something Else Entirely") == "machinery_equipment"


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

class TestDateParsing:
    def test_standard_date(self):
        assert _parse_date("8/12/20") == "2020-08-12"

    def test_two_digit_month(self):
        assert _parse_date("10/25/21") == "2021-10-25"

    def test_year_pivot_2000s(self):
        assert _parse_date("1/01/16") == "2016-01-01"
        assert _parse_date("6/15/00") == "2000-06-15"
        assert _parse_date("12/31/30") == "2030-12-31"

    def test_year_pivot_1900s(self):
        assert _parse_date("3/15/99") == "1999-03-15"
        assert _parse_date("7/04/85") == "1985-07-04"
        assert _parse_date("1/01/31") == "1931-01-01"

    def test_empty_date(self):
        assert _parse_date("") is None
        assert _parse_date(None) is None

    def test_invalid_date(self):
        assert _parse_date("not-a-date") is None


# ---------------------------------------------------------------------------
# Amount parsing
# ---------------------------------------------------------------------------

class TestAmountParsing:
    def test_whole_number(self):
        assert _parse_amount("18,000") == 18000

    def test_no_commas(self):
        assert _parse_amount("4815") == 4815

    def test_with_dollar_sign(self):
        assert _parse_amount("$89,642") == 89642

    def test_empty(self):
        assert _parse_amount("") == 0
        assert _parse_amount(None) == 0

    def test_zero(self):
        assert _parse_amount("0") == 0


# ---------------------------------------------------------------------------
# Method parsing
# ---------------------------------------------------------------------------

class TestMethodParsing:
    def test_200db_hy(self, parsed_assets):
        a = next(a for a in parsed_assets if a["asset_number"] == 8)
        assert a["method"] == "200DB"
        assert a["convention"] == "HY"
        assert a["life"] == 5

    def test_200db_mq(self, parsed_assets):
        a = next(a for a in parsed_assets if a["asset_number"] == 9)
        assert a["method"] == "200DB"
        assert a["convention"] == "MQ"
        assert a["life"] == 5

    def test_7yr_life(self, parsed_assets):
        a = next(a for a in parsed_assets if a["asset_number"] == 1)
        assert a["method"] == "200DB"
        assert a["convention"] == "HY"
        assert a["life"] == 7


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_content(self):
        assert parse_lacerte_txt("") == []

    def test_headers_only(self):
        content = """12/31/25 2025 Federal Summary Depreciation Schedule
No. Description Acquired Sold Basis Pct. SDA Depr.
Form 1120S
Total Depreciation 0 0 0
Grand Total Depreciation 0 0 0
"""
        assert parse_lacerte_txt(content) == []

    def test_disposed_asset(self):
        """Test an asset with a sold date."""
        content = """Machinery and Equipment
  1  Sold Machine  6/15/18  3/01/25  25,000  20,000  200DB HY  7  1,500
"""
        assets = parse_lacerte_txt(content)
        assert len(assets) == 1
        a = assets[0]
        assert a["description"] == "Sold Machine"
        assert a["date_acquired"] == "2018-06-15"
        assert a["date_sold"] == "2025-03-01"
        assert a["cost_basis"] == 25000

    def test_section_179_asset(self):
        """Test an asset with Section 179 and prior depreciation."""
        content = """Furniture and Fixtures
  1  Office Desk  1/15/25  5,000  5,000  0  200DB HY  7  0
"""
        assets = parse_lacerte_txt(content)
        assert len(assets) == 1


# ---------------------------------------------------------------------------
# Single-line (PDF text dump) format
# ---------------------------------------------------------------------------

class TestSingleLineFormat:
    """Tests for the single-line PDF text dump format (Lacerte 'Single Page')."""

    @pytest.fixture
    def mwelding_raw(self):
        """The actual raw file from Lacerte (single-line dump)."""
        raw_path = Path(__file__).parent.parent.parent / "Single Page Form for MWELDING.txt"
        if not raw_path.exists():
            pytest.skip("Raw MWELDING file not available")
        return raw_path.read_text(encoding="utf-8")

    def test_parses_all_12_assets(self, mwelding_raw):
        assets = parse_lacerte_txt(mwelding_raw)
        assert len(assets) == 12

    def test_totals_match_lacerte(self, mwelding_raw):
        """Grand totals must match Lacerte: cost=150,628 prior=102,163 current=2,554."""
        assets = parse_lacerte_txt(mwelding_raw)
        assert sum(a["cost_basis"] for a in assets) == 150628
        assert sum(a["prior_depreciation"] for a in assets) == 102163
        assert sum(a["current_depreciation"] for a in assets) == 2554

    def test_business_pct_in_single_line(self, mwelding_raw):
        """Asset #9 (Dodge Ram) should have 51% business use and correct prior."""
        assets = parse_lacerte_txt(mwelding_raw)
        dodge = next(a for a in assets if a["asset_number"] == 9)
        assert dodge["business_pct"] == 51.0
        assert dodge["prior_depreciation"] == 41465

    def test_forklift_not_lost(self, mwelding_raw):
        """Asset #1 (FORKLIFT) must be found despite tricky text boundaries."""
        assets = parse_lacerte_txt(mwelding_raw)
        forklift = next((a for a in assets if a["asset_number"] == 1), None)
        assert forklift is not None
        assert forklift["description"] == "FORKLIFT"
        assert forklift["cost_basis"] == 4815

    def test_methods_aligned_correctly(self, mwelding_raw):
        """Method/convention/life from right block must match assets in order."""
        assets = parse_lacerte_txt(mwelding_raw)
        chevy = next(a for a in assets if a["asset_number"] == 8)
        assert chevy["method"] == "200DB"
        assert chevy["convention"] == "HY"
        assert chevy["life"] == 5
        assert chevy["current_depreciation"] == 288

    def test_groups_detected_in_single_line(self, mwelding_raw):
        assets = parse_lacerte_txt(mwelding_raw)
        vehicle_nums = {a["asset_number"] for a in assets if a["asset_group"] == "vehicles"}
        mach_nums = {a["asset_number"] for a in assets if a["asset_group"] == "machinery_equipment"}
        assert vehicle_nums == {8, 9}
        assert mach_nums == {1, 2, 3, 4, 5, 6, 7, 10, 11, 12}
