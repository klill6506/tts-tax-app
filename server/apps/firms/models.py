import uuid

from django.conf import settings
from django.db import models


class Firm(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Role(models.TextChoices):
    ADMIN = "admin", "Admin"
    PREPARER = "preparer", "Preparer"
    REVIEWER = "reviewer", "Reviewer"


class FirmMembership(models.Model):
    """Links a Django user to a firm with a specific role."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="firm_memberships",
    )
    firm = models.ForeignKey(
        Firm,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.PREPARER,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "firm"],
                name="unique_user_per_firm",
            ),
        ]
        ordering = ["firm__name", "user__username"]

    def __str__(self):
        return f"{self.user.username} @ {self.firm.name} ({self.role})"


class Preparer(models.Model):
    """A preparer at the firm level — reusable across all returns."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firm = models.ForeignKey(
        Firm,
        on_delete=models.CASCADE,
        related_name="preparers",
    )

    # Preparer identity
    name = models.CharField(max_length=255)
    ptin = models.CharField(
        max_length=20, blank=True, default="",
        help_text="Preparer Tax Identification Number.",
    )
    is_self_employed = models.BooleanField(default=False)

    # Firm info (for IRS signature block)
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

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} (PTIN: {self.ptin or 'N/A'})"


class PrintPackage(models.Model):
    """A print package definition that controls which forms appear in the
    print dropdown and what label to show.  The actual form assembly is
    handled by the renderer using the ``code`` value."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firm = models.ForeignKey(
        Firm,
        on_delete=models.CASCADE,
        related_name="print_packages",
    )
    name = models.CharField(max_length=100)
    code = models.CharField(
        max_length=30,
        help_text="Internal code used by the renderer (e.g. 'client', 'filing').",
    )
    description = models.CharField(max_length=500, blank=True, default="")
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["firm", "code"],
                name="unique_package_code_per_firm",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"
