from rest_framework import serializers

from apps.firms.models import FirmMembership


class FirmMembershipSerializer(serializers.ModelSerializer):
    firm_id = serializers.UUIDField(source="firm.id")
    firm_name = serializers.CharField(source="firm.name")

    class Meta:
        model = FirmMembership
        fields = ("firm_id", "firm_name", "role")


class MeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    memberships = FirmMembershipSerializer(many=True, source="active_memberships")
