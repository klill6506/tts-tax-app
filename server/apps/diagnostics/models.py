import uuid

from django.conf import settings
from django.db import models


class Severity(models.TextChoices):
    ERROR = "error", "Error"
    WARNING = "warning", "Warning"
    INFO = "info", "Info"


class Category(models.TextChoices):
    PREPARER = "preparer", "Preparer"
    INTERNAL = "internal", "Internal"


class RunStatus(models.TextChoices):
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class DiagnosticRule(models.Model):
    """
    A registered diagnostic check that can be run against a tax year.

    Rules are identified by a unique `code` (e.g. "TB_BALANCE_CHECK").
    The `rule_function` field stores the dotted Python path to the
    callable that implements the check.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    severity = models.CharField(
        max_length=10,
        choices=Severity.choices,
        default=Severity.WARNING,
    )
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.PREPARER,
    )
    rule_function = models.CharField(
        max_length=255,
        help_text="Dotted path to the check function, e.g. 'apps.diagnostics.rules.tb_balance_check'.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"[{self.code}] {self.name}"


class DiagnosticRun(models.Model):
    """A single execution of all active rules against a tax year."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tax_year = models.ForeignKey(
        "clients.TaxYear",
        on_delete=models.CASCADE,
        related_name="diagnostic_runs",
    )
    run_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    status = models.CharField(
        max_length=20,
        choices=RunStatus.choices,
        default=RunStatus.RUNNING,
    )
    finding_count = models.IntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"Run {self.id} on {self.tax_year} ({self.status})"


class DiagnosticFinding(models.Model):
    """A single finding produced by a rule during a diagnostic run."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(
        DiagnosticRun,
        on_delete=models.CASCADE,
        related_name="findings",
    )
    rule = models.ForeignKey(
        DiagnosticRule,
        on_delete=models.CASCADE,
        related_name="findings",
    )
    severity = models.CharField(max_length=10, choices=Severity.choices)
    message = models.TextField()
    details = models.JSONField(default=dict, blank=True)
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["severity", "-created_at"]

    def __str__(self):
        return f"[{self.severity}] {self.message[:80]}"
