import uuid

from django.conf import settings
from django.db import models


class HelpQuery(models.Model):
    """Audit trail for AI help questions asked by preparers."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="help_queries",
    )
    firm = models.ForeignKey(
        "firms.Firm",
        on_delete=models.CASCADE,
        related_name="help_queries",
    )
    form_code = models.CharField(max_length=30, blank=True, default="")
    section = models.CharField(max_length=100, blank=True, default="")
    question = models.TextField()
    response = models.TextField(blank=True, default="")
    mode = models.CharField(
        max_length=10,
        choices=[("grounded", "IRS-Grounded"), ("broad", "Broader Search")],
        default="grounded",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.form_code}] {self.question[:80]}"
