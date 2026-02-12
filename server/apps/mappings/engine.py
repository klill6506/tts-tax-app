"""
Mapping engine: applies a MappingTemplate to a TrialBalanceUpload.

Returns a list of MappedRow dicts with the original TB data plus the
resolved target_line. Rows that don't match any rule get target_line=None.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from apps.imports.models import TrialBalanceRow, TrialBalanceUpload

from .models import MappingRule, MappingTemplate


@dataclass
class MappedRow:
    tb_row_id: str
    row_number: int
    account_number: str
    account_name: str
    debit: Decimal
    credit: Decimal
    target_line: str | None
    target_description: str
    matched_rule_id: str | None


def resolve_template(firm, client=None) -> MappingTemplate | None:
    """
    Find the best mapping template for a given firm/client.
    Priority: client-specific > firm default > None.
    """
    if client:
        client_template = MappingTemplate.objects.filter(
            firm=firm, client=client
        ).first()
        if client_template:
            return client_template

    return MappingTemplate.objects.filter(
        firm=firm, is_default=True, client__isnull=True
    ).first()


def apply_template(
    template: MappingTemplate, upload: TrialBalanceUpload
) -> list[MappedRow]:
    """
    Apply a mapping template to all rows in a TB upload.
    Rules are evaluated in priority order (highest first).
    """
    rules = list(template.rules.all().order_by("-priority"))
    tb_rows = upload.rows.all().order_by("row_number")

    results = []
    for row in tb_rows:
        matched_rule = None
        for rule in rules:
            if rule.matches(row.account_number, row.account_name):
                matched_rule = rule
                break

        results.append(
            MappedRow(
                tb_row_id=str(row.id),
                row_number=row.row_number,
                account_number=row.account_number,
                account_name=row.account_name,
                debit=row.debit,
                credit=row.credit,
                target_line=matched_rule.target_line if matched_rule else None,
                target_description=(
                    matched_rule.target_description if matched_rule else ""
                ),
                matched_rule_id=(
                    str(matched_rule.id) if matched_rule else None
                ),
            )
        )

    return results
