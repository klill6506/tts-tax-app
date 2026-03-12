from rest_framework import serializers

from .models import Preparer, PrintPackage


class PreparerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Preparer
        fields = (
            "id",
            "name",
            "ptin",
            "is_self_employed",
            "firm_name",
            "firm_ein",
            "firm_phone",
            "firm_address",
            "firm_city",
            "firm_state",
            "firm_zip",
            "designee_name",
            "designee_phone",
            "designee_pin",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class PreparerListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for dropdown lists."""

    class Meta:
        model = Preparer
        fields = ("id", "name", "ptin", "is_active")


class PrintPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrintPackage
        fields = (
            "id",
            "name",
            "code",
            "description",
            "sort_order",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
