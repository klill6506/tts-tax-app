from rest_framework import serializers

from .models import ClientDocument, DocumentCategory


class ClientDocumentSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True)
    entity_name = serializers.CharField(source="entity.name", read_only=True)
    entity_type = serializers.CharField(source="entity.entity_type", read_only=True)
    uploaded_by_name = serializers.SerializerMethodField()
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = ClientDocument
        fields = (
            "id", "client", "client_name", "entity", "entity_name",
            "entity_type", "filename", "file_size", "content_type",
            "category", "category_display", "tax_year", "notes",
            "uploaded_by", "uploaded_by_name", "download_url",
            "created_at", "updated_at",
        )

    def get_uploaded_by_name(self, obj):
        if obj.uploaded_by:
            name = obj.uploaded_by.get_full_name()
            return name if name.strip() else obj.uploaded_by.username
        return ""

    def get_download_url(self, obj):
        if obj.file:
            try:
                return obj.file.url
            except Exception:
                return None
        return None


class ClientDocumentUploadSerializer(serializers.Serializer):
    entity = serializers.UUIDField()
    file = serializers.FileField()
    category = serializers.ChoiceField(
        choices=DocumentCategory.choices, default="other",
    )
    tax_year = serializers.IntegerField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, default="", allow_blank=True)

    def validate_file(self, value):
        if value.size > 25 * 1024 * 1024:
            raise serializers.ValidationError("File size exceeds 25 MB limit.")
        return value


class EntityDocumentSummarySerializer(serializers.Serializer):
    entity_id = serializers.UUIDField()
    entity_name = serializers.CharField()
    entity_type = serializers.CharField()
    ein = serializers.CharField()
    client_id = serializers.UUIDField()
    client_name = serializers.CharField()
    document_count = serializers.IntegerField()
    last_upload = serializers.DateTimeField(allow_null=True)
    total_size = serializers.IntegerField()
