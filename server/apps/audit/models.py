import uuid

from django.conf import settings
from django.db import models


class AuditAction(models.TextChoices):
    CREATE = "create", "Create"
    UPDATE = "update", "Update"
    DELETE = "delete", "Delete"


class AuditEntry(models.Model):
    """
    Immutable log of every create/update/delete on domain models.

    Security rules:
    - Never store raw PII (SSN, EIN, etc.) in `changes`.
    - Store record UUIDs; look up details via admin if needed.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
    )
    firm = models.ForeignKey(
        "firms.Firm",
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
    )
    action = models.CharField(max_length=10, choices=AuditAction.choices)
    model_name = models.CharField(max_length=100)
    record_id = models.CharField(max_length=100)
    changes = models.JSONField(
        default=dict,
        blank=True,
        help_text="Field-level changes: {field: {old, new}}. Never include PII.",
    )
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name_plural = "audit entries"

    def __str__(self):
        return (
            f"{self.get_action_display()} {self.model_name} "
            f"{self.record_id} by {self.actor}"
        )
