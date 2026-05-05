"""Tests for the Lacerte demographic sanitizer."""

from datetime import date

from apps.imports.lacerte_clientlist_parser import LacerteDemographic
from apps.imports.lacerte_sanitizer import sanitize, sanitize_all


def _sample_record() -> LacerteDemographic:
    return LacerteDemographic(
        full_name_lnf="TESTERSON, ALPHA F AND BETA G",
        tp_first_name="ALPHA",
        tp_middle_initial="F",
        tp_last_name="TESTERSON",
        tp_suffix="",
        sp_first_name="BETA",
        sp_middle_initial="G",
        sp_last_name="TESTERSON",
        tp_ssn="111-11-1111",
        tp_dob=date(1980, 1, 15),
        sp_ssn="222-22-2222",
        sp_dob=date(1982, 2, 20),
        tp_email="alpha@example.com",
        sp_email="beta@example.com",
        sp_phone_label="Home",
        street="123 FAKE ST",
        city="NOWHERE",
        state="GA",
        zip_code="30000",
        preparer="1. Tester",
        filing_status="mfj",
    )


class TestSanitizerReplaces:
    """Sanitizer must replace every identifying field."""

    def test_ssn_replaced(self):
        s = sanitize(_sample_record())
        assert s.tp_ssn != "111-11-1111"
        assert s.sp_ssn != "222-22-2222"
        # Still looks like an SSN
        assert len(s.tp_ssn) == 11 and s.tp_ssn[3] == "-" and s.tp_ssn[6] == "-"

    def test_name_replaced(self):
        s = sanitize(_sample_record())
        assert s.tp_first_name != "ALPHA"
        assert s.tp_last_name != "TESTERSON"
        assert s.sp_first_name != "BETA"
        assert s.full_name_lnf != "TESTERSON, ALPHA F AND BETA G"

    def test_dob_replaced(self):
        s = sanitize(_sample_record())
        assert s.tp_dob != date(1980, 1, 15)
        assert s.sp_dob != date(1982, 2, 20)
        # Still roughly in the same age band (+/- 1 year)
        assert abs((s.tp_dob - date(1980, 1, 15)).days) <= 365
        assert abs((s.sp_dob - date(1982, 2, 20)).days) <= 365

    def test_address_replaced(self):
        s = sanitize(_sample_record())
        assert s.street != "123 FAKE ST"
        assert s.city != "NOWHERE"
        assert s.zip_code != "30000"

    def test_email_replaced(self):
        s = sanitize(_sample_record())
        assert s.tp_email != "alpha@example.com"
        assert "@" in s.tp_email
        assert s.sp_email != "beta@example.com"


class TestSanitizerPreserves:
    """Structural fields must remain intact for downstream logic."""

    def test_state_preserved(self):
        s = sanitize(_sample_record())
        assert s.state == "GA"

    def test_filing_status_preserved(self):
        s = sanitize(_sample_record())
        assert s.filing_status == "mfj"

    def test_has_spouse_preserved(self):
        s = sanitize(_sample_record())
        assert s.sp_first_name  # still has spouse
        assert s.sp_ssn

    def test_single_stays_single(self):
        rec = _sample_record()
        rec.filing_status = "single"
        rec.sp_first_name = rec.sp_last_name = rec.sp_middle_initial = ""
        rec.sp_ssn = ""
        rec.sp_dob = None
        rec.sp_email = ""
        s = sanitize(rec)
        assert s.filing_status == "single"
        assert s.sp_first_name == ""
        assert s.sp_ssn == ""
        assert s.sp_dob is None

    def test_empty_email_stays_empty(self):
        rec = _sample_record()
        rec.tp_email = ""
        s = sanitize(rec)
        assert s.tp_email == ""


class TestSanitizerDeterministic:
    """Same input SSN should produce the same fake output — enables safe re-imports."""

    def test_deterministic_by_ssn(self):
        a = sanitize(_sample_record())
        b = sanitize(_sample_record())
        assert a.tp_ssn == b.tp_ssn
        assert a.tp_first_name == b.tp_first_name
        assert a.street == b.street

    def test_different_ssn_different_output(self):
        r1 = _sample_record()
        r2 = _sample_record()
        r2.tp_ssn = "999-99-9999"
        s1 = sanitize(r1)
        s2 = sanitize(r2)
        assert s1.tp_ssn != s2.tp_ssn
        assert s1.tp_first_name != s2.tp_first_name or s1.tp_last_name != s2.tp_last_name


def test_sanitize_all():
    records = [_sample_record(), _sample_record()]
    records[1].tp_ssn = "888-88-8888"
    out = sanitize_all(records)
    assert len(out) == 2
    assert out[0].tp_ssn != out[1].tp_ssn
