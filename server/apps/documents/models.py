import uuid

from django.conf import settings
from django.db import models


class DocumentCategory(models.TextChoices):
    W2 = "w2", "W-2"
    FORM_1099 = "1099", "1099"
    RECEIPT = "receipt", "Receipt"
    BANK_STATEMENT = "bank_statement", "Bank Statement"
    K1 = "k1", "K-1"
    ENGAGEMENT_LETTER = "engagement_letter", "Engagement Letter"
    TAX_RETURN = "tax_return", "Completed Tax Return"
    EXTENSION = "extension", "Extension (7004)"
    ORGANIZER = "organizer", "Tax Organizer"
    CORRESPONDENCE = "correspondence", "IRS/State Correspondence"
    OTHER = "other", "Other"


def document_upload_path(instance, filename):
    year = instance.tax_year or "general"
    return f"documents/{instance.firm_id}/{instance.entity_id}/{year}/{filename}"


class ClientDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firm = models.ForeignKey(
        "firms.Firm", on_delete=models.CASCADE, related_name="documents",
    )
    client = models.ForeignKey(
        "clients.Client", on_delete=models.CASCADE, related_name="documents",
    )
    entity = models.ForeignKey(
        "clients.Entity", on_delete=models.CASCADE, related_name="documents",
    )
    file = models.FileField(upload_to=document_upload_path)
    filename = models.CharField(max_length=255)
    file_size = models.BigIntegerField(default=0)
    content_type = models.CharField(max_length=100, blank=True, default="")
    category = models.CharField(
        max_length=30, choices=DocumentCategory.choices,
        default=DocumentCategory.OTHER,
    )
    tax_year = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name="uploaded_documents",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["entity", "-created_at"]),
            models.Index(fields=["firm", "-created_at"]),
            models.Index(fields=["category"]),
        ]

    def __str__(self):
        return f"{self.filename} ({self.get_category_display()})"
