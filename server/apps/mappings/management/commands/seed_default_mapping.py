"""
Seed a default mapping template for 1120-S with rules matching common
QuickBooks account names to form lines.

Run: poetry run python manage.py seed_default_mapping
"""

from django.core.management.base import BaseCommand

from apps.firms.models import Firm
from apps.mappings.models import MappingTemplate, MappingRule

# ---------------------------------------------------------------------------
# Mapping rules: (match_mode, match_value, target_line, description, priority)
# target_line must match FormLine.mapping_key from seed_1120s.py
# ---------------------------------------------------------------------------

RULES = [
    # === INCOME ===
    ("contains", "Sales & Service", "1120S_L1a", "Gross receipts", 100),
    ("contains", "Sales Revenue", "1120S_L1a", "Gross receipts", 99),
    ("contains", "Gross Receipts", "1120S_L1a", "Gross receipts", 98),
    ("contains", "Service Revenue", "1120S_L1a", "Gross receipts", 97),
    ("contains", "Returns and Allowances", "1120S_L1b", "Returns & allowances", 100),
    ("contains", "Cost of Goods", "1120S_A2", "COGS — Purchases", 100),

    # === DEDUCTIONS ===
    ("contains", "Officer Compensation", "1120S_L7", "Compensation of officers", 100),
    ("contains", "Payroll Expense", "1120S_L8", "Salaries and wages", 100),
    ("contains", "Contract Labor", "1120S_L8", "Salaries and wages (contract)", 90),
    ("contains", "Repairs & Maintenance", "1120S_L9", "Repairs and maintenance", 100),
    ("contains", "Repairs and Maintenance", "1120S_L9", "Repairs and maintenance", 99),
    ("contains", "Bad Debt", "1120S_L10", "Bad debts", 100),
    ("contains", "Rent", "1120S_L11", "Rents", 100),
    ("contains", "Taxes", "1120S_L12", "Taxes and licenses", 80),
    ("contains", "Licenses & Permits", "1120S_L12", "Taxes and licenses", 90),
    ("contains", "Tags & Titles", "1120S_L12", "Taxes and licenses", 85),
    ("contains", "Transportation Tax", "1120S_L12", "Taxes and licenses", 84),
    ("contains", "Interest Expense", "1120S_L13", "Interest", 100),
    ("contains", "Credit Card Interest", "1120S_L13", "Interest - CC", 95),
    ("contains", "Depreciation Expense", "1120S_L14", "Depreciation", 100),
    ("contains", "Depletion", "1120S_L15", "Depletion", 100),
    ("contains", "Advertising", "1120S_L16", "Advertising", 100),
    ("contains", "Pension", "1120S_L17", "Pension/profit-sharing", 100),
    ("contains", "Employee Benefit", "1120S_L18", "Employee benefit programs", 100),
    ("contains", "Insurance Expense", "1120S_L18", "Employee benefit programs", 90),

    # Other deductions (Line 19)
    ("contains", "Accounting Fees", "1120S_L19", "Other deductions", 80),
    ("contains", "Automobile Expense", "1120S_L19", "Other deductions", 80),
    ("contains", "Bank Service Charges", "1120S_L19", "Other deductions", 80),
    ("contains", "Computer and Internet", "1120S_L19", "Other deductions", 80),
    ("contains", "Credit Card Fees", "1120S_L19", "Other deductions", 80),
    ("contains", "Dues and Subscriptions", "1120S_L19", "Other deductions", 80),
    ("contains", "Postage", "1120S_L19", "Other deductions", 80),
    ("contains", "Supplies", "1120S_L19", "Other deductions", 80),
    ("contains", "Shareholder Meals", "1120S_L19", "Other deductions", 80),

    # === SCHEDULE K ===
    ("contains", "Donations", "1120S_K12a", "Charitable contributions", 100),
    ("contains", "Charitable", "1120S_K12a", "Charitable contributions", 99),

    # === SCHEDULE L — BALANCE SHEET ===
    # Assets — BOY/EOY (use same rules; TB only has one snapshot = EOY)
    ("contains", "Commercial Bank", "1120S_L1d_eoy", "Cash — end", 90),
    ("contains", "Oconee State Bank", "1120S_L1d_eoy", "Cash — end", 89),
    ("contains", "Customer Deposits", "1120S_L1d_eoy", "Cash — end", 88),
    ("contains", "Old Commercial Bank", "1120S_L1d_eoy", "Cash — end", 87),
    ("contains", "Due from", "1120S_L2d_eoy", "Trade notes/AR — end", 85),
    ("contains", "Shareholder Loan", "1120S_L5d_eoy", "Loans to shareholders — end", 90),
    ("contains", "Furniture and Equipment", "1120S_L9d_eoy", "Buildings/depreciable — end", 90),
    ("contains", "Bus ", "1120S_L9d_eoy", "Buildings/depreciable — end", 80),
    ("contains", "Freightliner", "1120S_L9d_eoy", "Buildings/depreciable — end", 80),
    ("contains", "IC Bus", "1120S_L9d_eoy", "Buildings/depreciable — end", 80),
    ("contains", "Trolley Bus", "1120S_L9d_eoy", "Buildings/depreciable — end", 80),
    ("contains", "Accumulated Depreciation", "1120S_L9e_eoy", "Less accum depr — end", 90),

    # Liabilities
    ("contains", "Accounts Payable", "1120S_L15d_eoy", "AP — end", 90),
    ("contains", "Amex", "1120S_L17d_eoy", "Other current liabilities — end", 85),
    ("contains", "Direct Deposit Liabilities", "1120S_L17d_eoy", "Other current liabilities — end", 84),
    ("contains", "Payroll Liabilities", "1120S_L17d_eoy", "Other current liabilities — end", 83),
    ("contains", "Sales Tax Payable", "1120S_L17d_eoy", "Other current liabilities — end", 82),
    ("contains", "Notes Payable", "1120S_L20d_eoy", "Other liabilities — end", 85),
    ("contains", "N/P", "1120S_L20d_eoy", "Other liabilities — end", 84),

    # Equity
    ("contains", "Capital Stock", "1120S_L21d_eoy", "Capital stock — end", 90),
    ("contains", "Paid-In-Capital", "1120S_L21d_eoy", "Capital stock — end", 89),
    ("contains", "Retained Earnings", "1120S_L23d_eoy", "Retained earnings — end", 90),
    ("contains", "Shareholder Distributions", "1120S_K16d", "Distributions", 90),

    # === NON-DEDUCTIBLE / SCHEDULE K line 16 ===
    ("contains", "Shareholder Income Taxes", "1120S_K16c", "Nondeductible expenses", 90),
]


class Command(BaseCommand):
    help = "Seed a default mapping template for the first firm."

    def handle(self, *args, **options):
        firm = Firm.objects.first()
        if not firm:
            self.stderr.write(self.style.ERROR("No firms found. Create one first."))
            return

        template = MappingTemplate.objects.filter(
            firm=firm, is_default=True, client__isnull=True
        ).first()
        if template:
            template.name = "Default 1120-S Mapping"
            template.save()
            created = False
        else:
            template = MappingTemplate.objects.create(
                firm=firm, is_default=True, client=None,
                name="Default 1120-S Mapping",
            )
            created = True
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
                f"Seeded {len(RULES)} mapping rules for {firm.name}."
            )
        )
