from rest_framework import serializers

from apps.returns.models import TaxReturn

from .models import Client, ClientEntityLink, Entity, TaxYear


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ("id", "name", "status", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class ClientListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for the paginated client list.

    Includes entity_count from the annotated queryset so the Dashboard
    doesn't need N+1 queries to fetch entities per client.
    """

    entity_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Client
        fields = ("id", "name", "status", "entity_count", "created_at")
        read_only_fields = fields


class EntitySerializer(serializers.ModelSerializer):
    client_id = serializers.UUIDField(source="client.id", read_only=True)
    client_name = serializers.CharField(source="client.name", read_only=True)

    class Meta:
        model = Entity
        fields = (
            "id",
            "client_id",
            "client_name",
            "name",
            "entity_type",
            "legal_name",
            "ein",
            "phone",
            "address_line1",
            "address_line2",
            "city",
            "state",
            "zip_code",
            "date_incorporated",
            "state_incorporated",
            "business_activity",
            "naics_code",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class EntityCreateSerializer(serializers.ModelSerializer):
    """Used for create/update — accepts client as a UUID."""

    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.none())

    class Meta:
        model = Entity
        fields = (
            "id", "client", "name", "entity_type",
            "legal_name", "ein", "phone",
            "address_line1", "address_line2", "city", "state", "zip_code",
            "date_incorporated", "state_incorporated",
            "business_activity", "naics_code",
        )
        read_only_fields = ("id",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Scope the client choices to the current firm
        request = self.context.get("request")
        if request and hasattr(request, "firm") and request.firm:
            self.fields["client"].queryset = Client.objects.filter(
                firm=request.firm
            )

    def validate(self, attrs):
        client = attrs.get("client")
        name = attrs.get("name")
        entity_type = attrs.get("entity_type")

        if client and name and entity_type:
            # On update, exclude the current instance
            instance_id = self.instance.id if self.instance else None

            qs = Entity.objects.filter(
                client=client,
                name__iexact=name,
                entity_type=entity_type,
            )
            if instance_id:
                qs = qs.exclude(id=instance_id)

            if qs.exists():
                raise serializers.ValidationError(
                    f"An entity named '{name}' of type "
                    f"'{entity_type}' already exists for this client."
                )
        return attrs


class ClientEntityLinkSerializer(serializers.ModelSerializer):
    """Read serializer — returns denormalized names for display."""

    client_name = serializers.CharField(source="client.name", read_only=True)
    entity_name = serializers.CharField(source="entity.name", read_only=True)
    entity_type = serializers.CharField(source="entity.entity_type", read_only=True)

    class Meta:
        model = ClientEntityLink
        fields = (
            "id",
            "client",
            "client_name",
            "entity",
            "entity_name",
            "entity_type",
            "role",
            "ownership_percentage",
            "is_primary",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class ClientEntityLinkCreateSerializer(serializers.ModelSerializer):
    """Write serializer — accepts client/entity as UUIDs, scoped to firm."""

    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.none())
    entity = serializers.PrimaryKeyRelatedField(queryset=Entity.objects.none())

    class Meta:
        model = ClientEntityLink
        fields = (
            "id", "client", "entity", "role",
            "ownership_percentage", "is_primary",
        )
        read_only_fields = ("id",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and hasattr(request, "firm") and request.firm:
            self.fields["client"].queryset = Client.objects.filter(
                firm=request.firm
            )
            self.fields["entity"].queryset = Entity.objects.filter(
                client__firm=request.firm
            )


class ClientReturnSerializer(serializers.Serializer):
    """Flat serializer for the client returns endpoint.

    Combines entity, tax year, and return data into a single row.
    """

    # Entity info
    entity_id = serializers.UUIDField()
    entity_name = serializers.CharField()
    entity_type = serializers.CharField()
    # Tax year info
    tax_year_id = serializers.UUIDField(allow_null=True)
    year = serializers.IntegerField(allow_null=True)
    tax_year_status = serializers.CharField(allow_null=True)
    # Return info
    return_id = serializers.UUIDField(allow_null=True)
    form_code = serializers.CharField(allow_null=True)
    return_status = serializers.CharField(allow_null=True)
    # Relationship info
    relationship = serializers.CharField()  # "direct" or "shareholder" / "partner" etc.
    ownership_percentage = serializers.DecimalField(
        max_digits=7, decimal_places=4, allow_null=True,
    )


class TaxYearSerializer(serializers.ModelSerializer):
    entity_id = serializers.UUIDField(source="entity.id", read_only=True)
    entity_name = serializers.CharField(source="entity.name", read_only=True)
    created_by_username = serializers.CharField(
        source="created_by.username", read_only=True, default=None
    )
    tax_return_id = serializers.SerializerMethodField()

    class Meta:
        model = TaxYear
        fields = (
            "id",
            "entity_id",
            "entity_name",
            "year",
            "status",
            "created_by_username",
            "tax_return_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_tax_return_id(self, obj):
        """Return the UUID of the linked TaxReturn, or None."""
        try:
            return str(obj.tax_return.id)
        except TaxReturn.DoesNotExist:
            return None


class TaxYearCreateSerializer(serializers.ModelSerializer):
    """Used for create/update — accepts entity as a UUID."""

    entity = serializers.PrimaryKeyRelatedField(queryset=Entity.objects.none())

    class Meta:
        model = TaxYear
        fields = ("id", "entity", "year", "status")
        read_only_fields = ("id",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and hasattr(request, "firm") and request.firm:
            self.fields["entity"].queryset = Entity.objects.filter(
                client__firm=request.firm
            )
