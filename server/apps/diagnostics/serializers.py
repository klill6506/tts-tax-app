from rest_framework import serializers

from .models import DiagnosticFinding, DiagnosticRule, DiagnosticRun


class DiagnosticRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiagnosticRule
        fields = ("id", "code", "name", "description", "severity", "is_active")


class DiagnosticFindingSerializer(serializers.ModelSerializer):
    rule_code = serializers.CharField(source="rule.code", read_only=True)
    rule_name = serializers.CharField(source="rule.name", read_only=True)

    class Meta:
        model = DiagnosticFinding
        fields = (
            "id",
            "rule_code",
            "rule_name",
            "severity",
            "message",
            "details",
            "is_resolved",
            "created_at",
        )


class DiagnosticRunSerializer(serializers.ModelSerializer):
    findings = DiagnosticFindingSerializer(many=True, read_only=True)
    run_by_username = serializers.CharField(
        source="run_by.username", read_only=True, default=None
    )

    class Meta:
        model = DiagnosticRun
        fields = (
            "id",
            "tax_year_id",
            "run_by_username",
            "status",
            "finding_count",
            "started_at",
            "completed_at",
            "findings",
        )


class RunDiagnosticsSerializer(serializers.Serializer):
    tax_year = serializers.UUIDField()
