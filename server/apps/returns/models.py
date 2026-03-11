import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models


# ---------------------------------------------------------------------------
# Form structure (reference data — seeded once)
# ---------------------------------------------------------------------------


class FormDefinition(models.Model):
    """A type of tax form, e.g. '1120-S'."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=30)  # e.g. "1120-S"
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    tax_year_applicable = models.IntegerField(
        help_text="The IRS tax year this definition covers.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["code"]
        unique_together = [("code", "tax_year_applicable")]

    def __str__(self):
        return f"{self.code} ({self.tax_year_applicable})"


class FormSection(models.Model):
    """A logical section of a form, e.g. 'Page 1 Income' or 'Schedule K'."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    form = models.ForeignKey(
        FormDefinition,
        on_delete=models.CASCADE,
        related_name="sections",
    )
    code = models.CharField(max_length=50)  # e.g. "page1_income"
    title = models.CharField(max_length=200)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]
        unique_together = [("form", "code")]

    def __str__(self):
        return f"{self.form.code} — {self.title}"


class FieldType(models.TextChoices):
    CURRENCY = "currency", "Currency"
    INTEGER = "integer", "Integer"
    TEXT = "text", "Text"
    BOOLEAN = "boolean", "Yes/No"
    PERCENTAGE = "percentage", "Percentage"


class NormalBalance(models.TextChoices):
    DEBIT = "debit", "Debit"
    CREDIT = "credit", "Credit"


class FormLine(models.Model):
    """An individual line on a tax form that can hold a value."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    section = models.ForeignKey(
        FormSection,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    line_number = models.CharField(max_length=20)  # e.g. "1a", "7", "22a"
    label = models.CharField(max_length=500)
    field_type = models.CharField(
        max_length=20,
        choices=FieldType.choices,
        default=FieldType.CURRENCY,
    )
    mapping_key = models.CharField(
        max_length=60,
        blank=True,
        default="",
        help_text=(
            "Key that bridges MappingRule.target_line → this form line. "
            "E.g. '1120S_L1a'. Leave blank for lines that are always manual."
        ),
    )
    is_computed = models.BooleanField(
        default=False,
        help_text="True if this line is auto-calculated from other lines.",
    )
    normal_balance = models.CharField(
        max_length=6,
        choices=NormalBalance.choices,
        default=NormalBalance.DEBIT,
        help_text=(
            "Debit for expenses/assets; Credit for revenue/liabilities/equity. "
            "Controls sign when importing from trial balance."
        ),
    )
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]
        unique_together = [("section", "line_number")]

    def __str__(self):
        return f"Line {self.line_number}: {self.label}"


# ---------------------------------------------------------------------------
# Per-return data
# ---------------------------------------------------------------------------


class ReturnStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    IN_PROGRESS = "in_progress", "In Progress"
    IN_REVIEW = "in_review", "In Review"
    APPROVED = "approved", "Approved"
    FILED = "filed", "Filed"


class AccountingMethod(models.TextChoices):
    CASH = "cash", "Cash"
    ACCRUAL = "accrual", "Accrual"
    OTHER = "other", "Other"


class TaxReturn(models.Model):
    """A single tax return for a tax year, linked to a form definition."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tax_year = models.ForeignKey(
        "clients.TaxYear",
        on_delete=models.CASCADE,
        related_name="tax_returns",
    )
    form_definition = models.ForeignKey(
        FormDefinition,
        on_delete=models.PROTECT,
        related_name="returns",
    )
    federal_return = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="state_returns",
        help_text="Links a state return to its federal return.",
    )
    status = models.CharField(
        max_length=20,
        choices=ReturnStatus.choices,
        default=ReturnStatus.DRAFT,
    )
    # Return-level header fields
    accounting_method = models.CharField(
        max_length=10,
        choices=AccountingMethod.choices,
        default=AccountingMethod.CASH,
    )
    tax_year_start = models.DateField(null=True, blank=True)
    tax_year_end = models.DateField(null=True, blank=True)

    # Page 1 header checkboxes
    is_initial_return = models.BooleanField(default=False)
    is_final_return = models.BooleanField(default=False)
    is_name_change = models.BooleanField(default=False)
    is_address_change = models.BooleanField(default=False)
    is_amended_return = models.BooleanField(default=False)

    # Extension tracking (Form 7004)
    extension_filed = models.BooleanField(
        default=False,
        help_text="Whether Form 7004 extension was filed for this return.",
    )
    extension_date = models.DateField(
        null=True, blank=True,
        help_text="Date the Form 7004 extension was filed.",
    )
    tentative_tax = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Form 7004 Line 6: Tentative total tax.",
    )
    total_payments = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Form 7004 Line 7: Total payments and credits.",
    )
    balance_due = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Form 7004 Line 8: Balance due (Line 6 minus Line 7).",
    )

    # Banking info (for payments/refunds)
    bank_routing_number = models.CharField(
        max_length=9, blank=True, default="",
        help_text="9-digit ABA routing number.",
    )
    bank_account_number = models.CharField(
        max_length=17, blank=True, default="",
        help_text="Bank account number.",
    )
    bank_account_type = models.CharField(
        max_length=10, blank=True, default="checking",
        choices=[("checking", "Checking"), ("savings", "Savings")],
        help_text="Checking or Savings.",
    )

    s_election_date = models.DateField(
        null=True, blank=True,
        help_text="Date S-Corp election was effective.",
    )
    number_of_shareholders = models.IntegerField(
        null=True, blank=True,
        help_text="Number of shareholders during any part of the tax year.",
    )
    product_or_service = models.CharField(
        max_length=255, blank=True, default="",
        help_text="Principal product or service (IRS line F).",
    )
    business_activity_code = models.CharField(
        max_length=10, blank=True, default="",
        help_text="Business activity code (IRS line I).",
    )

    # Preparer assignment (firm-level)
    preparer = models.ForeignKey(
        "firms.Preparer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tax_returns",
        help_text="Assigned preparer from the firm's preparer list.",
    )
    staff_preparer = models.ForeignKey(
        "firms.Preparer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="staff_returns",
        help_text="Staff preparer who entered the data (not the signer).",
    )
    signature_date = models.DateField(
        null=True, blank=True,
        help_text="Date the preparer signed the return.",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_returns",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.form_definition.code} — {self.tax_year}"


class FormFieldValue(models.Model):
    """A single field value on a tax return."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tax_return = models.ForeignKey(
        TaxReturn,
        on_delete=models.CASCADE,
        related_name="field_values",
    )
    form_line = models.ForeignKey(
        FormLine,
        on_delete=models.PROTECT,
        related_name="values",
    )
    value = models.TextField(
        blank=True,
        default="",
        help_text="Stored as text; interpreted per form_line.field_type.",
    )
    is_overridden = models.BooleanField(
        default=False,
        help_text="True if a user manually overrode the mapped/computed value.",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("tax_return", "form_line")]
        ordering = ["form_line__sort_order"]

    def __str__(self):
        return f"{self.form_line.line_number} = {self.value}"


# ---------------------------------------------------------------------------
# Other Deductions detail schedule
# ---------------------------------------------------------------------------


class DeductionSource(models.TextChoices):
    MANUAL = "manual", "Manual"
    TB_IMPORT = "tb_import", "TB Import"
    STANDARD = "standard", "Standard"


class OtherDeduction(models.Model):
    """A single line-item in the Other Deductions detail schedule."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tax_return = models.ForeignKey(
        TaxReturn,
        on_delete=models.CASCADE,
        related_name="other_deductions",
    )
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    category = models.CharField(max_length=100, blank=True, default="")
    sort_order = models.IntegerField(default=0)
    source = models.CharField(
        max_length=10,
        choices=DeductionSource.choices,
        default=DeductionSource.MANUAL,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "description"]

    def __str__(self):
        return f"{self.description}: {self.amount}"


# ---------------------------------------------------------------------------
# Line Item Detail — generic sub-schedule for M-1, Schedule L, etc.
# ---------------------------------------------------------------------------


class LineItemDetail(models.Model):
    """
    A detail row for any form line that needs a sub-schedule breakdown.

    Used for:
    - M-1 lines (M1_2, M1_3c, M1_5b, M1_6b): description + amount
    - Schedule L lines (L6, L9, L14, L18, L21): description + amount_boy + amount_eoy

    The total of all detail items rolls up into the parent form line value.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tax_return = models.ForeignKey(
        TaxReturn,
        on_delete=models.CASCADE,
        related_name="line_item_details",
    )
    line_number = models.CharField(
        max_length=20,
        help_text="Parent form line (e.g., 'M1_2', 'L6').",
    )
    description = models.CharField(max_length=255)
    amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Amount (for single-column lines like M-1).",
    )
    amount_boy = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Beginning of year amount (for Schedule L lines).",
    )
    amount_eoy = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="End of year amount (for Schedule L lines).",
    )
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["line_number", "sort_order", "description"]

    def __str__(self):
        return f"{self.line_number}: {self.description}"


# ---------------------------------------------------------------------------
# Officer (per return)
# ---------------------------------------------------------------------------


class Officer(models.Model):
    """An officer listed on a tax return."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tax_return = models.ForeignKey(
        TaxReturn,
        on_delete=models.CASCADE,
        related_name="officers",
    )
    name = models.CharField(max_length=255)
    title = models.CharField(max_length=100, blank=True, default="")
    ssn = models.CharField(max_length=11, blank=True, default="")
    percent_time = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Percent of time devoted to business.",
    )
    percent_ownership = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
    )
    compensation = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
    )
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return f"{self.name} ({self.title})"


# ---------------------------------------------------------------------------
# Shareholder (per return — drives K-1 generation)
# ---------------------------------------------------------------------------


class Shareholder(models.Model):
    """A shareholder listed on a tax return, used for K-1 generation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tax_return = models.ForeignKey(
        TaxReturn,
        on_delete=models.CASCADE,
        related_name="shareholders",
    )

    # Identity
    name = models.CharField(max_length=255)
    ssn = models.CharField(
        max_length=11, blank=True, default="",
        help_text="SSN or TIN (formatted XXX-XX-XXXX)",
    )

    # Address (for K-1 delivery)
    address_line1 = models.CharField(max_length=255, blank=True, default="")
    address_line2 = models.CharField(max_length=255, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    state = models.CharField(max_length=2, blank=True, default="")
    zip_code = models.CharField(max_length=10, blank=True, default="")

    # Ownership
    ownership_percentage = models.DecimalField(
        max_digits=7, decimal_places=4, default=0,
        help_text="Percentage of stock ownership for the tax year.",
    )
    beginning_shares = models.IntegerField(
        default=0,
        help_text="Number of shares owned at beginning of tax year.",
    )
    ending_shares = models.IntegerField(
        default=0,
        help_text="Number of shares owned at end of tax year.",
    )

    # Financial data (drives K-1 and Form 7206)
    distributions = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Cash and property distributions to this shareholder (K-1 line 16d).",
    )
    health_insurance_premium = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Health insurance premiums paid by S-Corp for >2%% shareholder. Drives Form 7206.",
    )

    # Form 7203 — Stock Basis (Part I)
    stock_basis_boy = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Line 1: Stock basis at beginning of tax year.",
    )
    capital_contributions = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Line 2: Stock purchases and capital contributions during year.",
    )
    depletion = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Line 10: Depletion (entered by preparer).",
    )

    # Form 7203 — Prior Year Suspended Losses (Part III carry-forward)
    suspended_ordinary_loss = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Prior year suspended ordinary business loss.",
    )
    suspended_rental_re_loss = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Prior year suspended net rental real estate loss.",
    )
    suspended_other_rental_loss = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Prior year suspended other net rental loss.",
    )
    suspended_st_capital_loss = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Prior year suspended net short-term capital loss.",
    )
    suspended_lt_capital_loss = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Prior year suspended net long-term capital loss.",
    )
    suspended_1231_loss = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Prior year suspended net section 1231 loss.",
    )
    suspended_other_loss = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Prior year suspended other loss/deduction items.",
    )

    # Client linking (shared entity support)
    linked_client = models.ForeignKey(
        "clients.Client",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shareholder_links",
        help_text="Link to a client record if this shareholder is also a client.",
    )

    # Flags
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the shareholder was active during the tax year.",
    )

    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return f"{self.name} ({self.ownership_percentage}%)"


# ---------------------------------------------------------------------------
# Shareholder Loan — Form 7203 Part II (per shareholder, per loan)
# ---------------------------------------------------------------------------


class ShareholderLoan(models.Model):
    """A loan from a shareholder to the S-Corp, tracked for Form 7203 Part II."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shareholder = models.ForeignKey(
        Shareholder,
        on_delete=models.CASCADE,
        related_name="loans",
    )

    description = models.CharField(
        max_length=255,
        help_text="Description of the loan (e.g., 'Operating line of credit').",
    )

    # Section A: Loan Balance
    loan_balance_boy = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Line 16: Beginning of year loan balance.",
    )
    additional_loans = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Line 17: Additional loans made during year.",
    )
    # Line 18 = 16 + 17 (computed)
    loan_repayments = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Line 19: Loan repayments during year.",
    )
    # Line 20 = 18 - 19 (computed)

    # Section B: Debt Basis
    debt_basis_boy = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Line 21: Debt basis at beginning of year.",
    )
    new_loans_increasing_basis = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Line 22: Portion of new loans that increase debt basis.",
    )
    # Lines 23-25 are computed at render time

    # Loan detail fields (informational — for note generation)
    original_loan_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Original principal amount of the loan.",
    )
    interest_rate = models.DecimalField(
        max_digits=6, decimal_places=4, default=0,
        help_text="Annual interest rate (e.g. 5.24 for 5.24%).",
    )
    payment_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Regular payment amount.",
    )
    maturity_date = models.DateField(
        null=True, blank=True,
        help_text="Loan maturity date.",
    )

    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "description"]

    def __str__(self):
        return f"{self.description} ({self.shareholder.name})"


# ---------------------------------------------------------------------------
# Rental Property — Form 8825 (per return)
# ---------------------------------------------------------------------------


class PropertyType(models.TextChoices):
    SINGLE_FAMILY = "1", "Single family residence"
    MULTI_FAMILY = "2", "Multi-family residence"
    VACATION = "3", "Vacation/short-term rental"
    COMMERCIAL = "4", "Commercial"
    LAND = "5", "Land"
    OTHER = "6", "Other"


class RentalProperty(models.Model):
    """A rental property listed on Form 8825."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tax_return = models.ForeignKey(
        TaxReturn,
        on_delete=models.CASCADE,
        related_name="rental_properties",
    )

    # Property info
    description = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Property address or description.",
    )
    property_type = models.CharField(
        max_length=1,
        choices=PropertyType.choices,
        default=PropertyType.OTHER,
    )
    fair_rental_days = models.IntegerField(default=365)
    personal_use_days = models.IntegerField(default=0)

    # Income
    rents_received = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Expenses (each maps to a line on Form 8825)
    advertising = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    auto_and_travel = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    cleaning_and_maintenance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    commissions = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    insurance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    legal_and_professional = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    interest_mortgage = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    interest_other = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    repairs = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    taxes = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    utilities = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    depreciation = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    other_expenses = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "description"]

    @property
    def total_expenses(self):
        from decimal import Decimal
        return sum([
            self.advertising, self.auto_and_travel,
            self.cleaning_and_maintenance, self.commissions,
            self.insurance, self.legal_and_professional,
            self.interest_mortgage, self.interest_other,
            self.repairs, self.taxes, self.utilities,
            self.depreciation, self.other_expenses,
        ], Decimal("0"))

    @property
    def net_rent(self):
        return self.rents_received - self.total_expenses

    def __str__(self):
        return f"{self.description} (net: {self.net_rent})"


# ---------------------------------------------------------------------------
# Preparer Info (per return)
# ---------------------------------------------------------------------------


class PreparerInfo(models.Model):
    """Paid preparer information for a tax return (page 5 / signature block)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tax_return = models.OneToOneField(
        TaxReturn,
        on_delete=models.CASCADE,
        related_name="preparer_info",
    )

    # Preparer
    preparer_name = models.CharField(max_length=255, blank=True, default="")
    ptin = models.CharField(
        max_length=20, blank=True, default="",
        help_text="Preparer Tax Identification Number.",
    )
    signature_date = models.DateField(null=True, blank=True)
    is_self_employed = models.BooleanField(default=False)

    # Firm
    firm_name = models.CharField(max_length=255, blank=True, default="")
    firm_ein = models.CharField(max_length=20, blank=True, default="")
    firm_phone = models.CharField(max_length=20, blank=True, default="")
    firm_address = models.CharField(max_length=255, blank=True, default="")
    firm_city = models.CharField(max_length=100, blank=True, default="")
    firm_state = models.CharField(max_length=2, blank=True, default="")
    firm_zip = models.CharField(max_length=10, blank=True, default="")

    # Third-party designee
    designee_name = models.CharField(max_length=255, blank=True, default="")
    designee_phone = models.CharField(max_length=20, blank=True, default="")
    designee_pin = models.CharField(max_length=10, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Preparer: {self.preparer_name or '(blank)'}"


class PriorYearReturn(models.Model):
    """
    Imported prior year return data for year-over-year comparison.

    Stores form line values, balance sheet, and other deduction detail
    as JSON — this is read-only reference data displayed alongside the
    current year return. One record per entity per year per form type.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity = models.ForeignKey(
        "clients.Entity",
        on_delete=models.CASCADE,
        related_name="prior_year_returns",
    )
    year = models.IntegerField(help_text="Tax year (e.g., 2024).")
    form_code = models.CharField(
        max_length=20, help_text="IRS form code (e.g., '1120-S')."
    )

    # All data stored as JSON — flexible, read-only reference
    line_values = models.JSONField(
        default=dict,
        help_text="Form line number → amount (e.g., {'1c': 112450, '22': 14938}).",
    )
    other_deductions = models.JSONField(
        default=dict,
        help_text="Other deduction detail: description → amount.",
    )
    balance_sheet = models.JSONField(
        default=dict,
        help_text="Balance sheet: 'L{line}_{boy|eoy}' → amount.",
    )
    m2_balances = models.JSONField(
        default=dict,
        help_text="Schedule M-2 balances: 'M2_{line}' → amount.",
    )
    shareholders = models.JSONField(
        default=list,
        help_text="Shareholders from K-1 pages (list of dicts).",
    )
    officers = models.JSONField(
        default=list,
        help_text="Officers from Form 1125-E (list of dicts).",
    )

    # Import metadata
    source_software = models.CharField(
        max_length=50, default="lacerte",
        help_text="Software the data was imported from.",
    )
    source_file = models.CharField(
        max_length=255, blank=True, default="",
        help_text="Original filename (for audit trail).",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("entity", "year", "form_code")]
        ordering = ["-year"]

    def __str__(self):
        return f"PY {self.year} {self.form_code} — {self.entity.name}"


# ---------------------------------------------------------------------------
# Dispositions (Schedule D / Form 4797)
# ---------------------------------------------------------------------------


class TermType(models.TextChoices):
    SHORT = "short", "Short-term"
    LONG = "long", "Long-term"


class Disposition(models.Model):
    """
    A single asset disposition (sale/exchange) on a tax return.

    Stores data that will eventually flow to Schedule D and Form 4797.
    Supports multiple dispositions per return.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tax_return = models.ForeignKey(
        TaxReturn,
        on_delete=models.CASCADE,
        related_name="dispositions",
    )

    # Property identification
    description = models.CharField(
        max_length=255, blank=True, default="",
        help_text="Description of property sold or exchanged.",
    )

    # Dates — support "various" via null + various flag
    date_acquired = models.DateField(
        null=True, blank=True,
        help_text="Date property was acquired (null if various).",
    )
    date_acquired_various = models.BooleanField(
        default=False,
        help_text="True if acquired on various dates.",
    )
    date_sold = models.DateField(
        null=True, blank=True,
        help_text="Date property was sold (null if various).",
    )
    date_sold_various = models.BooleanField(
        default=False,
        help_text="True if sold on various dates.",
    )

    # Amounts
    sales_price = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Gross sales price.",
    )
    cost_basis = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Cost or other basis (do not reduce by depreciation).",
    )
    amt_cost_basis = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        help_text="AMT cost or other basis. Null = same as regular.",
    )
    state_cost_basis = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        help_text="State cost or other basis. Null = same as regular.",
    )
    state_amt_cost_basis = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        help_text="State AMT cost or other basis.",
    )
    expenses_of_sale = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Expenses of sale or exchange.",
    )

    # Classification
    term = models.CharField(
        max_length=5,
        choices=TermType.choices,
        default=TermType.LONG,
        help_text="Short-term or long-term.",
    )

    # Flags
    nontaxable_federal = models.BooleanField(
        default=False,
        help_text="Nontaxable to federal.",
    )
    nontaxable_state = models.BooleanField(
        default=False,
        help_text="Nontaxable to state.",
    )
    related_party_loss = models.BooleanField(
        default=False,
        help_text="Related party loss.",
    )
    securities_trader = models.BooleanField(
        default=False,
        help_text="Securities trader transaction.",
    )
    is_4797 = models.BooleanField(
        default=False,
        help_text="True = Form 4797 (investment property). "
                  "False = Schedule D (noninvestment).",
    )
    inherited_property = models.BooleanField(
        default=False,
        help_text="Inherited property with stepped-up basis.",
    )
    net_investment_income_tax = models.CharField(
        max_length=3,
        choices=[("yes", "Yes"), ("no", "No")],
        default="yes",
        help_text="Subject to net investment income tax.",
    )

    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "description"]

    @property
    def gain_loss(self):
        """Calculate gain or loss: sales price - cost basis - expenses."""
        return self.sales_price - self.cost_basis - self.expenses_of_sale

    def __str__(self):
        return f"{self.description} ({self.term}: {self.gain_loss})"


# ---------------------------------------------------------------------------
# Depreciation Assets (internal depreciation module)
# ---------------------------------------------------------------------------


class DepreciationAsset(models.Model):
    """A single depreciable asset on a tax return."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tax_return = models.ForeignKey(
        TaxReturn,
        on_delete=models.CASCADE,
        related_name="depreciation_assets",
    )
    asset_number = models.IntegerField(
        help_text="Auto-assigned per return, display only.",
    )
    description = models.CharField(max_length=200, blank=True, default="")

    GROUP_CHOICES = [
        ("Buildings", "Buildings"),
        ("Machinery and Equipment", "Machinery and Equipment"),
        ("Furniture and Fixtures", "Furniture and Fixtures"),
        ("Land", "Land"),
        ("Improvements", "Improvements"),
        ("Vehicles", "Vehicles"),
        ("Intangibles/Amortization", "Intangibles/Amortization"),
    ]
    group_label = models.CharField(max_length=100, choices=GROUP_CHOICES)
    property_label = models.CharField(
        max_length=200, blank=True, default="",
        help_text="Location/property name for grouping (e.g. '821 Hillside Drive'). "
                  "Blank for page 1 business assets.",
    )

    # Dates
    date_acquired = models.DateField(null=True, blank=True)
    date_sold = models.DateField(null=True, blank=True)

    # Basis
    cost_basis = models.DecimalField(max_digits=12, decimal_places=2)
    business_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("100.00"),
    )

    # Method
    METHOD_CHOICES = [
        ("200DB", "200DB"),
        ("150DB", "150DB"),
        ("SL", "S/L"),
        ("NONE", "None"),
    ]
    CONVENTION_CHOICES = [
        ("HY", "HY"),
        ("MQ", "MQ"),
        ("MM", "MM"),
    ]
    method = models.CharField(max_length=10, choices=METHOD_CHOICES)
    convention = models.CharField(max_length=5, choices=CONVENTION_CHOICES)
    life = models.DecimalField(
        max_digits=4, decimal_places=1, null=True, blank=True,
        help_text="Common lives: 3, 5, 7, 10, 15, 20, 27.5, 39",
    )

    # Section 179
    sec_179_elected = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0"),
    )
    sec_179_prior = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0"),
    )

    # Bonus / SDA
    bonus_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0"),
        help_text="Auto-suggested based on date_acquired per OBBBA rules, user can override.",
    )
    bonus_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0"),
    )

    # Regular depreciation
    prior_depreciation = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0"),
    )
    current_depreciation = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0"),
    )

    # AMT depreciation
    amt_method = models.CharField(max_length=10, blank=True, default="")
    amt_life = models.DecimalField(
        max_digits=4, decimal_places=1, null=True, blank=True,
    )
    amt_prior_depreciation = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0"),
    )
    amt_current_depreciation = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0"),
    )

    # State depreciation (Georgia)
    state_method = models.CharField(max_length=10, blank=True, default="")
    state_life = models.DecimalField(
        max_digits=4, decimal_places=1, null=True, blank=True,
    )
    state_prior_depreciation = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0"),
    )
    state_current_depreciation = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0"),
    )
    state_bonus_disallowed = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0"),
        help_text="Federal bonus taken that state does not allow. "
                  "Flows to GA-600S Schedule 1 as an addition.",
    )

    # Flow destination
    FLOW_CHOICES = [
        ("page1", "Page 1 (Line 14)"),
        ("8825", "Form 8825"),
        ("sched_f", "Schedule F"),
    ]
    flow_to = models.CharField(
        max_length=10, choices=FLOW_CHOICES, default="page1",
    )
    rental_property = models.ForeignKey(
        RentalProperty,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="depreciation_assets",
        help_text="Only used when flow_to = '8825'.",
    )

    # Vehicles / Listed Property
    is_listed_property = models.BooleanField(default=False)
    vehicle_miles_total = models.IntegerField(null=True, blank=True)
    vehicle_miles_business = models.IntegerField(null=True, blank=True)

    # Amortization
    is_amortization = models.BooleanField(default=False)
    amort_code = models.CharField(
        max_length=20, blank=True, default="",
        help_text="Common codes: '197' (Section 197 intangibles), '195' (startup costs).",
    )
    amort_months = models.IntegerField(null=True, blank=True)

    # Disposal information (populated when asset is sold)
    sales_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
    )
    expenses_of_sale = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
    )
    # Regular disposal computed fields
    depreciation_recapture = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Ordinary income recapture (Section 1245/1250).",
    )
    capital_gain = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Computed: total_gain - depreciation_recapture.",
    )
    gain_loss_on_sale = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Computed: sales_price - adjusted_basis - expenses_of_sale.",
    )
    # AMT disposal computed fields
    amt_gain_loss_on_sale = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
    )
    amt_depreciation_recapture = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
    )
    amt_capital_gain = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
    )

    # Import tracking
    imported_from_lacerte = models.BooleanField(default=False)
    lacerte_asset_no = models.IntegerField(null=True, blank=True)

    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "asset_number"]

    def __str__(self):
        return f"#{self.asset_number}: {self.description} ({self.group_label})"
