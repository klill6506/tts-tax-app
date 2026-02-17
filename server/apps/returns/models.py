import uuid

from django.conf import settings
from django.db import models


# ---------------------------------------------------------------------------
# Form structure (reference data — seeded once)
# ---------------------------------------------------------------------------


class FormDefinition(models.Model):
    """A type of tax form, e.g. '1120-S'."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=30, unique=True)  # e.g. "1120-S"
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    tax_year_applicable = models.IntegerField(
        help_text="The IRS tax year this definition covers.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["code"]

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
    label = models.CharField(max_length=300)
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
    tax_year = models.OneToOneField(
        "clients.TaxYear",
        on_delete=models.CASCADE,
        related_name="tax_return",
    )
    form_definition = models.ForeignKey(
        FormDefinition,
        on_delete=models.PROTECT,
        related_name="returns",
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
