"""Employer database — federal EIN-keyed records for W-2 autofill.

Universal across firms (one row per EIN). Sources:
  - Bulk import from a TaxWise CSV export (initial seed)
  - User-entered during W-2 entry (learning loop)

State withholding accounts (state_id_number) are tracked separately in
EmployerStateAccount, since one employer often has accounts in multiple
states. State IDs accumulate via the learning loop only — the bulk
import has no state-ID column.
"""
import uuid

from django.db import models


class Employer(models.Model):
    """Federal employer record. One row per EIN. Universal across firms."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ein = models.CharField(
        max_length=10, unique=True, db_index=True,
        help_text="Federal EIN, format XX-XXXXXXX",
    )
    name = models.CharField(max_length=255)
    street = models.CharField(max_length=255, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    state = models.CharField(max_length=2, blank=True, default="")
    zip = models.CharField(
        max_length=10, blank=True, default="",
        help_text="5-digit or ZIP+4 format",
    )

    SOURCE_CHOICES = [
        ("taxwise_import", "TaxWise bulk import"),
        ("user_entered", "User entered during W-2 entry"),
    ]
    source = models.CharField(
        max_length=20, choices=SOURCE_CHOICES, default="user_entered",
    )
    verified = models.BooleanField(
        default=False,
        help_text="Preparer confirmed employer details are correct",
    )
    parse_warning = models.TextField(
        blank=True, default="",
        help_text="Populated for rows that needed cleanup during import",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.ein})"


class EmployerStateAccount(models.Model):
    """A single state withholding account for an employer.

    Many states possible per employer (Acme has GA + SC + TN accounts).
    Lookup key: (employer, state) -> state_id_number.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey(
        Employer, on_delete=models.CASCADE, related_name="state_accounts",
    )
    state = models.CharField(max_length=2)
    state_id_number = models.CharField(
        max_length=30,
        help_text="State-issued withholding account number",
    )
    source = models.CharField(max_length=20, default="user_entered")
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("employer", "state")]
        ordering = ["state"]

    def __str__(self):
        return f"{self.employer.ein} / {self.state}"
