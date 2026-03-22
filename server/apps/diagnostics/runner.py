"""
Diagnostic runner: executes all active rules against a tax year.
"""

from __future__ import annotations

import importlib

from django.utils import timezone

from apps.clients.models import TaxYear

from .models import DiagnosticFinding, DiagnosticRule, DiagnosticRun, RunStatus


def _import_function(dotted_path: str):
    """Import a function from a dotted module path."""
    module_path, func_name = dotted_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, func_name)


def run_diagnostics(tax_year: TaxYear, run_by=None) -> DiagnosticRun:
    """
    Run all active diagnostic rules against a tax year.
    Returns a DiagnosticRun with all findings attached.
    """
    run = DiagnosticRun.objects.create(
        tax_year=tax_year,
        run_by=run_by,
        status=RunStatus.RUNNING,
    )

    active_rules = DiagnosticRule.objects.filter(is_active=True)
    all_findings = []

    for rule in active_rules:
        try:
            check_fn = _import_function(rule.rule_function)
            results = check_fn(tax_year)
        except Exception as e:
            results = [
                {
                    "severity": "error",
                    "message": f"Rule {rule.code} failed to execute: {e}",
                    "details": {"rule_code": rule.code, "error": str(e)},
                }
            ]

        for result in results:
            all_findings.append(
                DiagnosticFinding(
                    run=run,
                    rule=rule,
                    severity=result.get("severity", rule.severity),
                    message=result["message"],
                    details=result.get("details", {}),
                )
            )

    if all_findings:
        DiagnosticFinding.objects.bulk_create(all_findings)

    run.status = RunStatus.COMPLETED
    run.finding_count = len(all_findings)
    run.completed_at = timezone.now()
    run.save()

    return run


def seed_builtin_rules():
    """Create or update the built-in diagnostic rules."""
    from .rules import BUILTIN_RULES

    for rule_data in BUILTIN_RULES:
        DiagnosticRule.objects.update_or_create(
            code=rule_data["code"],
            defaults={
                "name": rule_data["name"],
                "description": rule_data["description"],
                "severity": rule_data["severity"],
                "category": rule_data.get("category", "preparer"),
                "rule_function": rule_data["rule_function"],
                "is_active": True,
            },
        )
