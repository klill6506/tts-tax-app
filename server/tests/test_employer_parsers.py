"""Tests for apps.employers.parsers — EIN / address-column parsing helpers."""
import pytest

from apps.employers.parsers import (
    parse_city_state_zip,
    parse_ein,
    validate_zip,
)


# ---------------------------------------------------------------------------
# parse_ein
# ---------------------------------------------------------------------------

class TestParseEIN:
    def test_canonical_with_hyphen(self):
        assert parse_ein("12-3456789") == "12-3456789"

    def test_no_hyphen_normalized(self):
        assert parse_ein("123456789") == "12-3456789"

    def test_strips_whitespace(self):
        assert parse_ein("  12-3456789  ") == "12-3456789"
        assert parse_ein("\t123456789\n") == "12-3456789"

    def test_low_prefix_kept(self):
        # Don't validate IRS prefix codes — accept anything 9 digits.
        assert parse_ein("00-0000001") == "00-0000001"

    def test_too_few_digits(self):
        assert parse_ein("12345") is None
        assert parse_ein("12-345678") is None

    def test_too_many_digits(self):
        assert parse_ein("1234567890") is None
        assert parse_ein("12-34567890") is None

    def test_letter_in_digits(self):
        assert parse_ein("12-345678a") is None

    def test_two_hyphens(self):
        assert parse_ein("12-3456-789") is None

    def test_hyphen_in_wrong_place(self):
        assert parse_ein("123-456789") is None

    def test_empty_string(self):
        assert parse_ein("") is None
        assert parse_ein("   ") is None

    def test_none(self):
        assert parse_ein(None) is None


# ---------------------------------------------------------------------------
# parse_city_state_zip
# ---------------------------------------------------------------------------

class TestParseCityStateZip:
    def test_space_separated_with_trailing_hyphen(self):
        assert parse_city_state_zip("ADDISON TX 75001-") == ("ADDISON", "TX", "75001", [])

    def test_comma_separated_with_trailing_hyphen(self):
        # Quotes will be stripped first, then comma-separated form parses.
        assert parse_city_state_zip('"ADDISON, TX 75001-"') == ("ADDISON", "TX", "75001", [])

    def test_clean_comma_separated(self):
        assert parse_city_state_zip('"AKRON, OH 44316"') == ("AKRON", "OH", "44316", [])

    def test_zip_plus_four(self):
        assert parse_city_state_zip("ALBANY GA 31702-1867") == ("ALBANY", "GA", "31702-1867", [])

    def test_missing_zip(self):
        city, state, zip_code, warnings = parse_city_state_zip("ADDISON TX")
        assert (city, state, zip_code) == ("ADDISON", "TX", "")
        assert "missing zip" in warnings

    def test_completely_unparseable(self):
        city, state, zip_code, warnings = parse_city_state_zip("SOME WEIRD FORMAT")
        assert (city, state, zip_code) == ("", "", "")
        assert any(w.startswith("unparseable") for w in warnings)

    def test_empty_string(self):
        city, state, zip_code, warnings = parse_city_state_zip("")
        assert (city, state, zip_code) == ("", "", "")
        assert warnings == ["empty"]

    def test_none(self):
        city, state, zip_code, warnings = parse_city_state_zip(None)
        assert (city, state, zip_code) == ("", "", "")
        assert warnings == ["empty"]

    def test_typo_in_city_preserved(self):
        # Don't validate spelling — preserve city verbatim.
        assert parse_city_state_zip("AHTENS, GA 30608") == ("AHTENS", "GA", "30608", [])

    def test_multi_word_city(self):
        assert parse_city_state_zip("NEW YORK, NY 10001") == ("NEW YORK", "NY", "10001", [])
        assert parse_city_state_zip("LOS ANGELES CA 90001") == ("LOS ANGELES", "CA", "90001", [])

    def test_only_state_no_city_no_zip(self):
        # "GA" alone has nothing in front of the state — should be unparseable.
        city, state, zip_code, warnings = parse_city_state_zip("GA")
        assert (city, state, zip_code) == ("", "", "")
        assert any(w.startswith("unparseable") for w in warnings)

    def test_single_quoted_input(self):
        assert parse_city_state_zip("'ATLANTA, GA 30303'") == ("ATLANTA", "GA", "30303", [])


# ---------------------------------------------------------------------------
# validate_zip
# ---------------------------------------------------------------------------

class TestValidateZip:
    def test_five_digits(self):
        assert validate_zip("75001") == ("75001", [])

    def test_zip_plus_four(self):
        assert validate_zip("75001-1234") == ("75001-1234", [])

    def test_trailing_hyphen_tolerated(self):
        assert validate_zip("75001-") == ("75001", [])

    def test_strips_whitespace(self):
        assert validate_zip("  75001  ") == ("75001", [])

    def test_too_short(self):
        z, w = validate_zip("7500")
        assert z == ""
        assert w == ["invalid zip"]

    def test_letters(self):
        z, w = validate_zip("ABCDE")
        assert z == ""
        assert w == ["invalid zip"]

    def test_partial_plus_four(self):
        # 5 digits + dash + only 2 of the +4 = invalid
        z, w = validate_zip("75001-12")
        assert z == ""
        assert w == ["invalid zip"]

    def test_empty(self):
        z, w = validate_zip("")
        assert z == ""
        assert w == ["invalid zip"]

    def test_none(self):
        z, w = validate_zip(None)
        assert z == ""
        assert w == ["invalid zip"]
