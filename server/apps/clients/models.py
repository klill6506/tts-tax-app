import uuid

from django.conf import settings
from django.db import models


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ClientStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"


class EntityType(models.TextChoices):
    SCORP = "scorp", "S-Corp (1120S)"
    PARTNERSHIP = "partnership", "Partnership (1065)"
    CCORP = "ccorp", "C-Corp (1120)"
    TRUST = "trust", "Trust (1041)"
    INDIVIDUAL = "individual", "Individual (1040)"


class LinkRole(models.TextChoices):
    TAXPAYER = "taxpayer", "Taxpayer"
    SHAREHOLDER = "shareholder", "Shareholder"
    PARTNER = "partner", "Partner"
    OFFICER = "officer", "Officer"


class ReturnStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    IN_PROGRESS = "in_progress", "In Progress"
    IN_REVIEW = "in_review", "In Review"
    APPROVED = "approved", "Approved"
    FILED = "filed", "Filed"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Client(models.Model):
    """A client of the firm (e.g. a business or individual)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firm = models.ForeignKey(
        "firms.Firm",
        on_delete=models.CASCADE,
        related_name="clients",
    )
    name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=ClientStatus.choices,
        default=ClientStatus.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Entity(models.Model):
    """A tax entity belonging to a client (e.g. an S-Corp)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="entities",
    )
    name = models.CharField(max_length=255)
    entity_type = models.CharField(
        max_length=20,
        choices=EntityType.choices,
        default=EntityType.SCORP,
    )
    # Identity
    legal_name = models.CharField(max_length=255, blank=True, default="")
    ein = models.CharField(
        max_length=20, blank=True, default="",
        help_text="EIN in XX-XXXXXXX format",
    )
    # Address
    address_line1 = models.CharField(max_length=255, blank=True, default="")
    address_line2 = models.CharField(max_length=255, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    state = models.CharField(max_length=2, blank=True, default="")
    zip_code = models.CharField(max_length=10, blank=True, default="")
    # Contact
    phone = models.CharField(
        max_length=20, blank=True, default="",
        help_text="Business phone number.",
    )
    email = models.EmailField(blank=True, default="")
    # Spouse (individual returns)
    spouse_first_name = models.CharField(max_length=255, blank=True, default="")
    spouse_last_name = models.CharField(max_length=255, blank=True, default="")
    spouse_ssn = models.CharField(
        max_length=20, blank=True, default="",
        help_text="Spouse SSN in XXX-XX-XXXX format",
    )
    # Business info
    date_incorporated = models.DateField(null=True, blank=True)
    state_incorporated = models.CharField(max_length=2, blank=True, default="")
    business_activity = models.CharField(max_length=255, blank=True, default="")
    naics_code = models.CharField(max_length=10, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "entities"
        constraints = [
            models.UniqueConstraint(
                fields=["client", "name", "entity_type"],
                name="unique_client_entity_name_type",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_entity_type_display()})"


class ClientEntityLink(models.Model):
    """Links a client to an entity they are associated with.

    For individuals: role=taxpayer links them to their own 1040 entity.
    For business owners: role=shareholder/partner/officer links them to
    the business entity they have an interest in.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="entity_links",
    )
    entity = models.ForeignKey(
        Entity,
        on_delete=models.CASCADE,
        related_name="client_links",
    )
    role = models.CharField(
        max_length=20,
        choices=LinkRole.choices,
        default=LinkRole.TAXPAYER,
    )
    ownership_percentage = models.DecimalField(
        max_digits=7, decimal_places=4, null=True, blank=True,
        help_text="Ownership percentage (e.g. 60.0000 for 60%)",
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="Primary owner/taxpayer for this entity.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_primary", "client__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["client", "entity", "role"],
                name="unique_client_entity_role",
            ),
        ]

    def __str__(self):
        return f"{self.client.name} -> {self.entity.name} ({self.get_role_display()})"


class TaxYear(models.Model):
    """A single tax-year return container for an entity."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity = models.ForeignKey(
        Entity,
        on_delete=models.CASCADE,
        related_name="tax_years",
    )
    year = models.IntegerField()
    status = models.CharField(
        max_length=20,
        choices=ReturnStatus.choices,
        default=ReturnStatus.DRAFT,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_tax_years",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-year"]
        constraints = [
            models.UniqueConstraint(
                fields=["entity", "year"],
                name="unique_entity_year",
            ),
        ]

    def __str__(self):
        return f"{self.entity.name} — {self.year} ({self.get_status_display()})"
