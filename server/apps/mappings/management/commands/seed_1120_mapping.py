"""
Seed a default mapping template for 1120 (C-Corp) with rules matching
common QuickBooks account names to form lines.

Run: poetry run python manage.py seed_1120_mapping
"""

from django.core.management.base import BaseCommand

from apps.firms.models import Firm
from apps.mappings.models import MappingRule, MappingTemplate

# ---------------------------------------------------------------------------
# Mapping rules: (match_mode, match_value, target_line, description, priority)
# target_line must match FormLine.mapping_key from seed_1120.py
# ---------------------------------------------------------------------------

RULES = [
    # === INCOME ===
    ("contains", "Sales & Service", "1120_L1a", "Gross receipts", 100),
    ("contains", "Sales Revenue", "1120_L1a", "Gross receipts", 99),
    ("contains", "Gross Receipts", "1120_L1a", "Gross receipts", 98),
    ("contains", "Service Revenue", "1120_L1a", "Gross receipts", 97),
    ("contains", "Returns and Allowances", "1120_L1b", "Returns & allowances", 100),
    ("contains", "Cost of Goods", "1120_L2", "COGS", 100),
    ("contains", "Dividend Income", "1120_L4", "Dividends", 90),
    ("contains", "Interest Income", "1120_L5", "Interest", 90),
    ("contains", "Rent Income", "1120_L6", "Gross rents", 90),
    ("contains", "Other Income", "1120_L10", "Other income", 80),

    # === DEDUCTIONS ===
    ("contains", "Officer Compensation", "1120_L12", "Compensation of officers", 100),
    ("contains", "Payroll Expense", "1120_L13", "Salaries and wages", 100),
    ("contains", "Salaries", "1120_L13", "Salaries and wages", 95),
    ("contains", "Contract Labor", "1120_L13", "Salaries and wages (contract)", 90),
    ("contains", "Repairs & Maintenance", "1120_L14", "Repairs and maintenance", 100),
    ("contains", "Repairs and Maintenance", "1120_L14", "Repairs and maintenance", 99),
    ("contains", "Bad Debt", "1120_L15", "Bad debts", 100),
    ("contains", "Rent", "1120_L16", "Rents", 100),
    ("contains", "Taxes", "1120_L17", "Taxes and licenses", 80),
    ("contains", "Licenses & Permits", "1120_L17", "Taxes and licenses", 90),
    ("contains", "Interest Expense", "1120_L18", "Interest", 100),
    ("contains", "Credit Card Interest", "1120_L18", "Interest - CC", 95),
    ("contains", "Charitable", "1120_L19", "Charitable contributions", 100),
    ("contains", "Donations", "1120_L19", "Charitable contributions", 99),
    ("contains", "Depreciation Expense", "1120_L20", "Depreciation", 100),
    ("contains", "Depletion", "1120_L21", "Depletion", 100),
    ("contains", "Advertising", "1120_L22", "Advertising", 100),
    ("contains", "Pension", "1120_L23", "Pension/profit-sharing", 100),
    ("contains", "Employee Benefit", "1120_L24", "Employee benefit programs", 100),
    ("contains", "Insurance Expense", "1120_L24", "Employee benefit programs", 90),

    # Other deductions (Line 26)
    ("contains", "Accounting Fees", "1120_L26", "Other deductions", 80),
    ("contains", "Automobile Expense", "1120_L26", "Other deductions", 80),
    ("contains", "Bank Service Charges", "1120_L26", "Other deductions", 80),
    ("contains", "Computer and Internet", "1120_L26", "Other deductions", 80),
    ("contains", "Credit Card Fees", "1120_L26", "Other deductions", 80),
    ("contains", "Dues and Subscriptions", "1120_L26", "Other deductions", 80),
    ("contains", "Postage", "1120_L26", "Other deductions", 80),
    ("contains", "Supplies", "1120_L26", "Other deductions", 80),
    ("contains", "Meals", "1120_L26", "Other deductions", 80),
    ("contains", "Office Expense", "1120_L26", "Other deductions", 80),
    ("contains", "Utilities", "1120_L26", "Other deductions", 80),

    # === SCHEDULE L — BALANCE SHEET ===
    ("contains", "Cash", "1120_L1d_eoy", "Cash — end", 85),
    ("contains", "Bank", "1120_L1d_eoy", "Cash — end", 80),
    ("contains", "Accounts Receivable", "1120_L2d_eoy", "Trade notes/AR — end", 90),
    ("contains", "Due from", "1120_L2d_eoy", "Trade notes/AR — end", 85),
    ("contains", "Inventory", "1120_L3d_eoy", "Inventories — end", 90),
    ("contains", "Furniture and Equipment", "1120_L10d_eoy", "Buildings/depreciable — end", 90),
    ("contains", "Accumulated Depreciation", "1120_L10e_eoy", "Less accum depr — end", 90),
    ("contains", "Land", "1120_L12d_eoy", "Land — end", 90),
    ("contains", "Accounts Payable", "1120_L16d_eoy", "AP — end", 90),
    ("contains", "Notes Payable", "1120_L17d_eoy", "Short-term notes — end", 85),
    ("contains", "Payroll Liabilities", "1120_L18d_eoy", "Other current liabilities — end", 83),
    ("contains", "Capital Stock", "1120_L22d_com_eoy", "Capital stock: common — end", 90),
    ("contains", "Paid-In Capital", "1120_L23d_eoy", "Additional paid-in capital — end", 89),
    ("contains", "Retained Earnings", "1120_L25d_eoy", "Retained earnings — end", 90),
]


class Command(BaseCommand):
    help = "Seed a default mapping template for 1120 (C-Corp)."

    def handle(self, *args, **options):
        firm = Firm.objects.first()
        if not firm:
            self.stderr.write(self.style.ERROR("No firms found. Create one first."))
            return

        template, created = MappingTemplate.objects.get_or_create(
            firm=firm,
            name="Default 1120 Mapping",
            defaults={"is_default": False, "client": None},
        )
        action = "Created" if created else "Updated"
        self.stdout.write(f"{action} template: {template.name}")

        # Remove old rules and recreate
        template.rules.all().delete()

        for mode, value, target, desc, priority in RULES:
            MappingRule.objects.create(
                template=template,
                match_mode=mode,
                match_value=value,
                target_line=target,
                target_description=desc,
                priority=priority,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(RULES)} mapping rules for 1120 ({firm.name})."
            )
        )
