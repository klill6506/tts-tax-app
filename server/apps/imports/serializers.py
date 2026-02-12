from rest_framework import serializers

from .models import TrialBalanceRow, TrialBalanceUpload


class TrialBalanceRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrialBalanceRow
        fields = (
            "id",
            "row_number",
            "account_number",
            "account_name",
            "debit",
            "credit",
            "raw_data",
        )


class TrialBalanceUploadSerializer(serializers.ModelSerializer):
    uploaded_by_username = serializers.CharField(
        source="uploaded_by.username", read_only=True, default=None
    )
    tax_year_id = serializers.UUIDField(source="tax_year.id", read_only=True)

    class Meta:
        model = TrialBalanceUpload
        fields = (
            "id",
            "tax_year_id",
            "original_filename",
            "status",
            "row_count",
            "error_message",
            "uploaded_by_username",
            "created_at",
        )


class TrialBalanceUploadCreateSerializer(serializers.Serializer):
    """Handles multipart file upload for a specific tax year."""

    tax_year = serializers.UUIDField()
    file = serializers.FileField()

    def validate_file(self, value):
        from .parsers import ALLOWED_EXTENSIONS, MAX_FILE_SIZE

        name = value.name.lower()
        if not any(name.endswith(ext) for ext in ALLOWED_EXTENSIONS):
            raise serializers.ValidationError(
                f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        if value.size > MAX_FILE_SIZE:
            raise serializers.ValidationError(
                f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)} MB."
            )
        return value
