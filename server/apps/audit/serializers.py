from rest_framework import serializers

from .models import AuditEntry


class AuditEntrySerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(
        source="actor.username", read_only=True, default=None
    )

    class Meta:
        model = AuditEntry
        fields = (
            "id",
            "actor_username",
            "action",
            "model_name",
            "record_id",
            "changes",
            "timestamp",
        )
