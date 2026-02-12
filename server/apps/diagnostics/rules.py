"""
Built-in diagnostic rules.

Each rule function receives a TaxYear instance and returns a list of
finding dicts: [{"severity": "...", "message": "...", "details": {...}}]

An empty list means the check passed.
"""

from __future__ import annotations

from decimal import Decimal

from apps.clients.models import TaxYear
from apps.imports.models import TrialBalanceUpload, UploadStatus


def tb_exists_check(tax_year: TaxYear) -> list[dict]:
    """Check that at least one parsed Trial Balance exists."""
    uploads = TrialBalanceUpload.objects.filter(
        tax_year=tax_year, status=UploadStatus.PARSED
    )
    if not uploads.exists():
        return [
            {
                "severity": "error",
                "message": "No parsed Trial Balance found for this tax year.",
                "details": {"tax_year_id": str(tax_year.id), "year": tax_year.year},
            }
        ]
    return []


def tb_balance_check(tax_year: TaxYear) -> list[dict]:
    """Check that total debits equal total credits in the latest TB upload."""
    upload = (
        TrialBalanceUpload.objects.filter(
            tax_year=tax_year, status=UploadStatus.PARSED
        )
        .order_by("-created_at")
        .first()
    )
    if not upload:
        return []  # tb_exists_check will catch this

    rows = upload.rows.all()
    total_debit = sum(r.debit for r in rows)
    total_credit = sum(r.credit for r in rows)

    if total_debit != total_credit:
        diff = total_debit - total_credit
        return [
            {
                "severity": "error",
                "message": (
                    f"Trial Balance is out of balance. "
                    f"Debits: {total_debit:,.2f}, Credits: {total_credit:,.2f}, "
                    f"Difference: {abs(diff):,.2f}"
                ),
                "details": {
                    "upload_id": str(upload.id),
                    "total_debit": str(total_debit),
                    "total_credit": str(total_credit),
                    "difference": str(diff),
                },
            }
        ]
    return []


def tb_zero_rows_check(tax_year: TaxYear) -> list[dict]:
    """Flag TB rows where both debit and credit are zero."""
    upload = (
        TrialBalanceUpload.objects.filter(
            tax_year=tax_year, status=UploadStatus.PARSED
        )
        .order_by("-created_at")
        .first()
    )
    if not upload:
        return []

    zero_rows = upload.rows.filter(debit=Decimal("0"), credit=Decimal("0"))
    findings = []
    for row in zero_rows:
        findings.append(
            {
                "severity": "info",
                "message": (
                    f"Row {row.row_number} ({row.account_number} {row.account_name}) "
                    f"has zero debit and zero credit."
                ),
                "details": {
                    "row_id": str(row.id),
                    "row_number": row.row_number,
                    "account_number": row.account_number,
                },
            }
        )
    return findings


# Registry of built-in rules for seeding the database
BUILTIN_RULES = [
    {
        "code": "TB_EXISTS",
        "name": "Trial Balance Exists",
        "description": "Checks that at least one parsed Trial Balance has been uploaded.",
        "severity": "error",
        "rule_function": "apps.diagnostics.rules.tb_exists_check",
    },
    {
        "code": "TB_BALANCE",
        "name": "Trial Balance In Balance",
        "description": "Checks that total debits equal total credits.",
        "severity": "error",
        "rule_function": "apps.diagnostics.rules.tb_balance_check",
    },
    {
        "code": "TB_ZERO_ROWS",
        "name": "Zero-Amount Rows",
        "description": "Flags rows where both debit and credit are zero.",
        "severity": "info",
        "rule_function": "apps.diagnostics.rules.tb_zero_rows_check",
    },
]
