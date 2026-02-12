import uuid

from django.conf import settings
from django.db import models


class UploadStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PARSED = "parsed", "Parsed"
    FAILED = "failed", "Failed"


class TrialBalanceUpload(models.Model):
    """A single TB file upload linked to a tax-year return."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tax_year = models.ForeignKey(
        "clients.TaxYear",
        on_delete=models.CASCADE,
        related_name="tb_uploads",
    )
    original_filename = models.CharField(max_length=255)
    file = models.FileField(upload_to="tb_uploads/%Y/%m/")
    status = models.CharField(
        max_length=20,
        choices=UploadStatus.choices,
        default=UploadStatus.PENDING,
    )
    row_count = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, default="")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="tb_uploads",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.original_filename} → {self.tax_year}"


class TrialBalanceRow(models.Model):
    """A single parsed row from a TB upload."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    upload = models.ForeignKey(
        TrialBalanceUpload,
        on_delete=models.CASCADE,
        related_name="rows",
    )
    row_number = models.IntegerField()
    account_number = models.CharField(max_length=50, blank=True, default="")
    account_name = models.CharField(max_length=255, blank=True, default="")
    debit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    raw_data = models.JSONField(
        default=dict,
        help_text="Full row as parsed from the file, for re-mapping later.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["row_number"]

    def __str__(self):
        return f"Row {self.row_number}: {self.account_number} {self.account_name}"
