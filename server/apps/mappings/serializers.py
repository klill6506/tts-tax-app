from rest_framework import serializers

from .models import MappingRule, MappingTemplate


class MappingRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = MappingRule
        fields = (
            "id",
            "match_mode",
            "match_value",
            "target_line",
            "target_description",
            "priority",
        )
        read_only_fields = ("id",)


class MappingTemplateSerializer(serializers.ModelSerializer):
    rules = MappingRuleSerializer(many=True, read_only=True)
    client_id = serializers.UUIDField(source="client.id", read_only=True, default=None)
    client_name = serializers.CharField(
        source="client.name", read_only=True, default=None
    )

    class Meta:
        model = MappingTemplate
        fields = (
            "id",
            "name",
            "description",
            "is_default",
            "client_id",
            "client_name",
            "rules",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class MappingTemplateCreateSerializer(serializers.ModelSerializer):
    client = serializers.UUIDField(required=False, allow_null=True, default=None)

    class Meta:
        model = MappingTemplate
        fields = ("id", "name", "description", "is_default", "client")
        read_only_fields = ("id",)

    def validate_client(self, value):
        if value is None:
            return None
        from apps.clients.models import Client

        request = self.context.get("request")
        try:
            return Client.objects.get(id=value, firm=request.firm)
        except Client.DoesNotExist:
            raise serializers.ValidationError("Client not found in your firm.")


class MappingRuleCreateSerializer(serializers.ModelSerializer):
    template = serializers.PrimaryKeyRelatedField(
        queryset=MappingTemplate.objects.none()
    )

    class Meta:
        model = MappingRule
        fields = (
            "id",
            "template",
            "match_mode",
            "match_value",
            "target_line",
            "target_description",
            "priority",
        )
        read_only_fields = ("id",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and hasattr(request, "firm") and request.firm:
            self.fields["template"].queryset = MappingTemplate.objects.filter(
                firm=request.firm
            )


class ApplyMappingSerializer(serializers.Serializer):
    upload = serializers.UUIDField()
    template = serializers.UUIDField(required=False, allow_null=True, default=None)


class MappedRowSerializer(serializers.Serializer):
    tb_row_id = serializers.CharField()
    row_number = serializers.IntegerField()
    account_number = serializers.CharField()
    account_name = serializers.CharField()
    debit = serializers.DecimalField(max_digits=15, decimal_places=2)
    credit = serializers.DecimalField(max_digits=15, decimal_places=2)
    target_line = serializers.CharField(allow_null=True)
    target_description = serializers.CharField()
    matched_rule_id = serializers.CharField(allow_null=True)
