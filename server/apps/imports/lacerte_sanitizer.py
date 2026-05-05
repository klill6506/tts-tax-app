"""
Sanitizer for LacerteDemographic records.

Replaces PII (name, SSN, DOB, address, email, phone-label) with synthetic
values from Faker while preserving structural fields the tax app may use
for real analysis (filing status, state).

A stable `seed` per record keeps sanitization deterministic across runs:
the same input produces the same fake output, so re-imports don't churn
the DB. Seed is derived from the real TP SSN (hashed) so fake identities
stay consistent for a given taxpayer.
"""

from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import date, timedelta

from faker import Faker

from apps.imports.lacerte_clientlist_parser import LacerteDemographic


def _seed_from_ssn(ssn: str) -> int:
    """Deterministic int seed from an SSN string (or any stable key)."""
    digest = hashlib.sha256(ssn.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def _fake_ssn(fake: Faker) -> str:
    """Faker.ssn() returns 'XXX-XX-XXXX' — already in our format."""
    return fake.ssn()


def _jitter_dob(real: date | None, fake: Faker) -> date | None:
    """Shift the DOB by a random ±365 days so age-band is roughly preserved."""
    if real is None:
        return None
    delta_days = fake.random_int(min=-365, max=365)
    return real + timedelta(days=delta_days)


def sanitize(record: LacerteDemographic) -> LacerteDemographic:
    """Return a copy of `record` with PII replaced by synthetic values.

    Preserved: filing_status, state, source_page, warnings, sp_phone_label
               (which is just "Home"/"Work", not an actual number).
    Replaced:  names, SSNs, DOBs, emails, street, city, zip, preparer.
    """
    # Deterministic seed per record — use TP SSN if present, else full name.
    seed_key = record.tp_ssn or record.full_name_lnf or "UNKNOWN"
    fake = Faker("en_US")
    fake.seed_instance(_seed_from_ssn(seed_key))

    tp_first = fake.first_name().upper()
    tp_last = fake.last_name().upper()
    tp_mid = fake.random_uppercase_letter() if record.tp_middle_initial else ""

    has_spouse = record.filing_status == "mfj" or bool(record.sp_first_name)
    if has_spouse:
        sp_first = fake.first_name().upper()
        sp_mid = fake.random_uppercase_letter() if record.sp_middle_initial else ""
        # Preserve "separate last name" structure: if the real spouse had a
        # different surname from TP, give the fake one a different surname too.
        if record.sp_last_name and record.sp_last_name != record.tp_last_name:
            sp_last = fake.last_name().upper()
        else:
            sp_last = tp_last
    else:
        sp_first = sp_mid = sp_last = ""

    # Rebuild the LNF string so it stays consistent with name parts.
    lnf = f"{tp_last}, {tp_first}"
    if tp_mid:
        lnf += f" {tp_mid}"
    if record.tp_suffix:
        lnf += f" {record.tp_suffix}"
    if has_spouse and sp_first:
        lnf += f" AND {sp_first}"
        if sp_mid:
            lnf += f" {sp_mid}"
        if sp_last and sp_last != tp_last:
            lnf += f" {sp_last}"

    # Keep the original state so downstream state-filing logic is unchanged.
    street = fake.street_address().upper()
    city = fake.city().upper()
    zip_code = fake.zipcode()

    return replace(
        record,
        full_name_lnf=lnf,
        tp_first_name=tp_first,
        tp_last_name=tp_last,
        tp_middle_initial=tp_mid,
        # tp_suffix preserved (structural, not identifying on its own)
        sp_first_name=sp_first,
        sp_middle_initial=sp_mid,
        sp_last_name=sp_last,
        tp_ssn=_fake_ssn(fake) if record.tp_ssn else "",
        sp_ssn=_fake_ssn(fake) if record.sp_ssn else "",
        tp_dob=_jitter_dob(record.tp_dob, fake),
        sp_dob=_jitter_dob(record.sp_dob, fake),
        tp_email=fake.email() if record.tp_email else "",
        sp_email=fake.email() if record.sp_email else "",
        street=street,
        city=city,
        # state preserved
        zip_code=zip_code,
        preparer=record.preparer,  # keep preparer — not PII about the client
    )


def sanitize_all(records: list[LacerteDemographic]) -> list[LacerteDemographic]:
    return [sanitize(r) for r in records]
