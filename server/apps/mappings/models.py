import uuid

from django.db import models


class MatchMode(models.TextChoices):
    EXACT = "exact", "Exact match on account number"
    PREFIX = "prefix", "Account number starts with"
    CONTAINS = "contains", "Account name contains"


class MappingTemplate(models.Model):
    """
    A reusable set of rules that maps QB chart-of-accounts lines to
    1120S (or other form) tax lines.

    Hierarchy:
    - firm-level default (client=NULL) — applies to all clients in the firm
    - client-level override (client set) — takes priority over firm default
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firm = models.ForeignKey(
        "firms.Firm",
        on_delete=models.CASCADE,
        related_name="mapping_templates",
    )
    client = models.ForeignKey(
        "clients.Client",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="mapping_templates",
        help_text="If set, this template overrides the firm default for this client.",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    is_default = models.BooleanField(
        default=False,
        help_text="If true, this is the firm's default template (client must be null).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["firm"],
                condition=models.Q(is_default=True, client__isnull=True),
                name="one_default_per_firm",
            ),
        ]

    def __str__(self):
        scope = f"client: {self.client.name}" if self.client else "firm default"
        return f"{self.name} ({scope})"


class MappingRule(models.Model):
    """
    A single mapping rule: matches a TB account and assigns it to a tax line.

    Example:
      match_mode=prefix, match_value="1000" → target_line="Line 1a"
      (all accounts starting with 1000 go to Line 1a - Gross Receipts)
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(
        MappingTemplate,
        on_delete=models.CASCADE,
        related_name="rules",
    )
    match_mode = models.CharField(
        max_length=20,
        choices=MatchMode.choices,
        default=MatchMode.EXACT,
    )
    match_value = models.CharField(
        max_length=255,
        help_text="The value to match against (account number or name fragment).",
    )
    target_line = models.CharField(
        max_length=100,
        help_text="Tax form line identifier, e.g. '1120S_L1a' or 'Line 1a'.",
    )
    target_description = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Human-readable label, e.g. 'Gross receipts or sales'.",
    )
    priority = models.IntegerField(
        default=0,
        help_text="Higher priority rules match first when multiple rules match.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-priority", "match_value"]

    def __str__(self):
        return f"{self.get_match_mode_display()}: '{self.match_value}' → {self.target_line}"

    def matches(self, account_number: str, account_name: str) -> bool:
        """Test whether this rule matches a given TB row."""
        if self.match_mode == MatchMode.EXACT:
            return account_number.strip() == self.match_value.strip()
        elif self.match_mode == MatchMode.PREFIX:
            return account_number.strip().startswith(self.match_value.strip())
        elif self.match_mode == MatchMode.CONTAINS:
            return self.match_value.strip().lower() in account_name.strip().lower()
        return False
