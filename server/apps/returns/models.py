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
