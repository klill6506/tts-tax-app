"""
Seed a default mapping template for 1065 (Partnership) with rules matching
common QuickBooks account names to form lines.

Run: poetry run python manage.py seed_1065_mapping
"""

from django.core.management.base import BaseCommand

from apps.firms.models import Firm
from apps.mappings.models import MappingRule, MappingTemplate

# ---------------------------------------------------------------------------
# Mapping rules: (match_mode, match_value, target_line, description, priority)
# target_line must match FormLine.mapping_key from seed_1065.py
# ---------------------------------------------------------------------------

RULES = [
    # === INCOME ===
    ("contains", "Sales & Service", "1065_L1a", "Gross receipts", 100),
    ("contains", "Sales Revenue", "1065_L1a", "Gross receipts", 99),
    ("contains", "Gross Receipts", "1065_L1a", "Gross receipts", 98),
    ("contains", "Service Revenue", "1065_L1a", "Gross receipts", 97),
    ("contains", "Returns and Allowances", "1065_L1b", "Returns & allowances", 100),
    ("contains", "Cost of Goods", "1065_L2", "COGS", 100),
    ("contains", "Other Income", "1065_L7", "Other income", 80),

    # === DEDUCTIONS ===
    ("contains", "Payroll Expense", "1065_L9", "Salaries and wages", 100),
    ("contains", "Salaries", "1065_L9", "Salaries and wages", 95),
    ("contains", "Contract Labor", "1065_L9", "Salaries and wages (contract)", 90),
    ("contains", "Guaranteed Payment", "1065_L10", "Guaranteed payments to partners", 100),
    ("contains", "Repairs & Maintenance", "1065_L11", "Repairs and maintenance", 100),
    ("contains", "Repairs and Maintenance", "1065_L11", "Repairs and maintenance", 99),
    ("contains", "Bad Debt", "1065_L12", "Bad debts", 100),
    ("contains", "Rent", "1065_L13", "Rent", 100),
    ("contains", "Taxes", "1065_L14", "Taxes and licenses", 80),
    ("contains", "Licenses & Permits", "1065_L14", "Taxes and licenses", 90),
    ("contains", "Interest Expense", "1065_L15", "Interest", 100),
    ("contains", "Credit Card Interest", "1065_L15", "Interest - CC", 95),
    ("contains", "Depreciation Expense", "1065_L16", "Depreciation", 100),
    ("contains", "Depletion", "1065_L17", "Depletion", 100),
    ("contains", "Pension", "1065_L18", "Retirement plans", 100),
    ("contains", "Employee Benefit", "1065_L19", "Employee benefit programs", 100),
    ("contains", "Insurance Expense", "1065_L19", "Employee benefit programs", 90),

    # Other deductions (Line 20)
    ("contains", "Accounting Fees", "1065_L20", "Other deductions", 80),
    ("contains", "Automobile Expense", "1065_L20", "Other deductions", 80),
    ("contains", "Bank Service Charges", "1065_L20", "Other deductions", 80),
    ("contains", "Computer and Internet", "1065_L20", "Other deductions", 80),
    ("contains", "Credit Card Fees", "1065_L20", "Other deductions", 80),
    ("contains", "Dues and Subscriptions", "1065_L20", "Other deductions", 80),
    ("contains", "Postage", "1065_L20", "Other deductions", 80),
    ("contains", "Supplies", "1065_L20", "Other deductions", 80),
    ("contains", "Advertising", "1065_L20", "Other deductions", 80),
    ("contains", "Meals", "1065_L20", "Other deductions", 80),
    ("contains", "Office Expense", "1065_L20", "Other deductions", 80),
    ("contains", "Utilities", "1065_L20", "Other deductions", 80),

    # === SCHEDULE K ===
    ("contains", "Donations", "1065_K13a", "Charitable contributions", 100),
    ("contains", "Charitable", "1065_K13a", "Charitable contributions", 99),

    # === SCHEDULE L — BALANCE SHEET ===
    ("contains", "Cash", "1065_L1d_eoy", "Cash — end", 85),
    ("contains", "Bank", "1065_L1d_eoy", "Cash — end", 80),
    ("contains", "Accounts Receivable", "1065_L2d_eoy", "Trade notes/AR — end", 90),
    ("contains", "Due from", "1065_L2d_eoy", "Trade notes/AR — end", 85),
    ("contains", "Inventory", "1065_L3d_eoy", "Inventories — end", 90),
    ("contains", "Furniture and Equipment", "1065_L9d_eoy", "Buildings/depreciable — end", 90),
    ("contains", "Accumulated Depreciation", "1065_L9e_eoy", "Less accum depr — end", 90),
    ("contains", "Land", "1065_L11d_eoy", "Land — end", 90),
    ("contains", "Accounts Payable", "1065_L15d_eoy", "AP — end", 90),
    ("contains", "Notes Payable", "1065_L16d_eoy", "Short-term notes — end", 85),
    ("contains", "Payroll Liabilities", "1065_L17d_eoy", "Other current liabilities — end", 83),
    ("contains", "Partners' Capital", "1065_L22d_eoy", "Partners' capital — end", 90),
    ("contains", "Partner Capital", "1065_L22d_eoy", "Partners' capital — end", 89),
    ("contains", "Retained Earnings", "1065_L22d_eoy", "Partners' capital — end", 88),
]


class Command(BaseCommand):
    help = "Seed a default mapping template for 1065 (Partnership)."

    def handle(self, *args, **options):
        firm = Firm.objects.first()
        if not firm:
            self.stderr.write(self.style.ERROR("No firms found. Create one first."))
            return

        template, created = MappingTemplate.objects.get_or_create(
            firm=firm,
            name="Default 1065 Mapping",
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
                f"Seeded {len(RULES)} mapping rules for 1065 ({firm.name})."
            )
        )
