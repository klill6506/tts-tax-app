from rest_framework import serializers

from .models import (
    FormDefinition,
    FormFieldValue,
    FormLine,
    FormSection,
    TaxReturn,
)


# ---------------------------------------------------------------------------
# Read serializers (nested for full form view)
# ---------------------------------------------------------------------------


class FormLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormLine
        fields = (
            "id",
            "line_number",
            "label",
            "field_type",
            "mapping_key",
            "is_computed",
            "sort_order",
        )


class FormSectionSerializer(serializers.ModelSerializer):
    lines = FormLineSerializer(many=True, read_only=True)

    class Meta:
        model = FormSection
        fields = ("id", "code", "title", "sort_order", "lines")


class FormDefinitionSerializer(serializers.ModelSerializer):
    sections = FormSectionSerializer(many=True, read_only=True)

    class Meta:
        model = FormDefinition
        fields = ("id", "code", "name", "description", "tax_year_applicable", "sections")


class FormDefinitionListSerializer(serializers.ModelSerializer):
    """Lightweight — no nested sections (for list view)."""

    class Meta:
        model = FormDefinition
        fields = ("id", "code", "name", "tax_year_applicable")


# ---------------------------------------------------------------------------
# Tax Return
# ---------------------------------------------------------------------------


class FieldValueSerializer(serializers.ModelSerializer):
    line_number = serializers.CharField(source="form_line.line_number", read_only=True)
    label = serializers.CharField(source="form_line.label", read_only=True)
    field_type = serializers.CharField(source="form_line.field_type", read_only=True)
    section_code = serializers.CharField(source="form_line.section.code", read_only=True)
    is_computed = serializers.BooleanField(source="form_line.is_computed", read_only=True)

    class Meta:
        model = FormFieldValue
        fields = (
            "id",
            "form_line",
            "line_number",
            "label",
            "field_type",
            "section_code",
            "value",
            "is_overridden",
            "is_computed",
        )


class TaxReturnSerializer(serializers.ModelSerializer):
    field_values = FieldValueSerializer(many=True, read_only=True)
    form_code = serializers.CharField(source="form_definition.code", read_only=True)
    tax_year_id = serializers.UUIDField(source="tax_year.id", read_only=True)
    year = serializers.IntegerField(source="tax_year.year", read_only=True)
    entity_name = serializers.CharField(
        source="tax_year.entity.name", read_only=True
    )
    client_name = serializers.CharField(
        source="tax_year.entity.client.name", read_only=True
    )

    class Meta:
        model = TaxReturn
        fields = (
            "id",
            "tax_year_id",
            "year",
            "entity_name",
            "client_name",
            "form_code",
            "status",
            "field_values",
            "created_at",
            "updated_at",
        )


class TaxReturnListSerializer(serializers.ModelSerializer):
    form_code = serializers.CharField(source="form_definition.code", read_only=True)
    year = serializers.IntegerField(source="tax_year.year", read_only=True)
    entity_name = serializers.CharField(
        source="tax_year.entity.name", read_only=True
    )
    client_name = serializers.CharField(
        source="tax_year.entity.client.name", read_only=True
    )

    class Meta:
        model = TaxReturn
        fields = (
            "id",
            "tax_year_id",
            "year",
            "entity_name",
            "client_name",
            "form_code",
            "status",
            "created_at",
        )


# ---------------------------------------------------------------------------
# Write serializers
# ---------------------------------------------------------------------------


class CreateReturnSerializer(serializers.Serializer):
    tax_year = serializers.UUIDField()


class UpdateFieldsSerializer(serializers.Serializer):
    """Bulk update field values. Expects a list of {form_line, value}."""

    fields = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False,
    )
