"""One-off script to run diagnostics on the imported TB."""

import os
import sys
from pathlib import Path

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
django.setup()

from apps.clients.models import TaxYear
from apps.diagnostics.runner import run_diagnostics, seed_builtin_rules

# Make sure built-in rules are seeded
seed_builtin_rules()

ty = TaxYear.objects.select_related("entity__client").first()
print(f"Running diagnostics for: {ty.entity.client.name} > {ty.entity.name} | {ty.year}")

run = run_diagnostics(ty)
print(f"Run status: {run.status}")
print(f"Finding count: {run.finding_count}")

for f in run.findings.select_related("rule").all():
    print(f"  [{f.severity}] ({f.rule.code}) {f.message}")

if run.finding_count == 0:
    print("\nAll checks passed - clean bill of health!")
else:
    errors = run.findings.filter(severity="error").count()
    warnings = run.findings.filter(severity="warning").count()
    infos = run.findings.filter(severity="info").count()
    print(f"\nSummary: {errors} errors, {warnings} warnings, {infos} info")
