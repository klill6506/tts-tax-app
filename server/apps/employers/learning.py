"""
Learning loop — promote W-2 entry data into the employer database.

Called from the W-2 viewset after each create/update. The contract:

  1. If the W-2 row carries an EIN that doesn't yet exist in the Employer
     table, create a new Employer row using the snapshot fields the
     preparer just typed (or autofilled and accepted). Mark it
     source="user_entered", verified=False — preparer can review later.

  2. If the W-2 row carries Box 15 state + state_id_number, and that
     (employer, state) pair has no EmployerStateAccount yet, create one.
     This is how state withholding IDs accumulate over time.

The function never raises — failures here must not roll back the W-2 save.
Any exceptions are swallowed and logged; the W-2 row stays in place.
"""
from __future__ import annotations

import logging

from django.db import transaction

from apps.employers.models import Employer, EmployerStateAccount
from apps.employers.parsers import parse_ein

logger = logging.getLogger(__name__)


def sync_w2_to_employer_db(w2_income) -> None:
    """Promote a W-2 row's snapshot fields into the employer database.

    Idempotent: if the Employer / EmployerStateAccount already exists,
    nothing changes. Existing rows are NEVER modified (so a verified
    Employer row stays untouched).
    """
    raw_ein = (getattr(w2_income, "employer_ein", "") or "").strip()
    if not raw_ein:
        return
    canonical_ein = parse_ein(raw_ein)
    if canonical_ein is None:
        return

    try:
        with transaction.atomic():
            employer, created = Employer.objects.get_or_create(
                ein=canonical_ein,
                defaults={
                    "name": (w2_income.employer_name or "").strip() or "(unknown)",
                    "street": w2_income.employer_street or "",
                    "city": w2_income.employer_city or "",
                    "state": w2_income.employer_state or "",
                    "zip": w2_income.employer_zip or "",
                    "source": "user_entered",
                    "verified": False,
                },
            )
            # Box-15 state account
            box15_state = (w2_income.state_box15 or "").strip().upper()
            state_id = (w2_income.state_id_number or "").strip()
            if box15_state and state_id and len(box15_state) == 2:
                EmployerStateAccount.objects.get_or_create(
                    employer=employer,
                    state=box15_state,
                    defaults={
                        "state_id_number": state_id,
                        "source": "user_entered",
                        "verified": False,
                    },
                )
    except Exception:  # noqa: BLE001
        # Never let employer-DB failures roll back the W-2 save.
        logger.exception("sync_w2_to_employer_db failed for w2_income=%s", w2_income.pk)
