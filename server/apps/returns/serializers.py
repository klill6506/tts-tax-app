from rest_framework import serializers

from .models import (
    FormDefinition,
    FormFieldValue,
    FormLine,
    FormSection,
    Officer,
    OtherDeduction,
    PreparerInfo,
    RentalProperty,
    Shareholder,
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
# Other Deductions & Officers
# ---------------------------------------------------------------------------


class OtherDeductionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OtherDeduction
        fields = (
            "id",
            "description",
            "amount",
            "category",
            "sort_order",
            "source",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class OfficerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Officer
        fields = (
            "id",
            "name",
            "title",
            "ssn",
            "percent_ownership",
            "compensation",
            "sort_order",
        )
        read_only_fields = ("id",)


class RentalPropertySerializer(serializers.ModelSerializer):
    total_expenses = serializers.DecimalField(
        max_digits=15, decimal_places=2, read_only=True
    )
    net_rent = serializers.DecimalField(
        max_digits=15, decimal_places=2, read_only=True
    )

    class Meta:
        model = RentalProperty
        fields = (
            "id",
            "description",
            "property_type",
            "fair_rental_days",
            "personal_use_days",
            "rents_received",
            "advertising",
            "auto_and_travel",
            "cleaning_and_maintenance",
            "commissions",
            "insurance",
            "legal_and_professional",
            "interest_mortgage",
            "interest_other",
            "repairs",
            "taxes",
            "utilities",
            "depreciation",
            "other_expenses",
            "total_expenses",
            "net_rent",
            "sort_order",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class PreparerInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PreparerInfo
        fields = (
            "id",
            "preparer_name",
            "ptin",
            "signature_date",
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
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class ShareholderSerializer(serializers.ModelSerializer):
    linked_client_name = serializers.CharField(
        source="linked_client.name", read_only=True, default=None
    )

    class Meta:
        model = Shareholder
        fields = (
            "id",
            "name",
            "ssn",
            "address_line1",
            "address_line2",
            "city",
            "state",
            "zip_code",
            "ownership_percentage",
            "beginning_shares",
            "ending_shares",
            "distributions",
            "health_insurance_premium",
            "linked_client",
            "linked_client_name",
            "is_active",
            "sort_order",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


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
    other_deductions = OtherDeductionSerializer(many=True, read_only=True)
    officers = OfficerSerializer(many=True, read_only=True)
    shareholders = ShareholderSerializer(many=True, read_only=True)
    rental_properties = RentalPropertySerializer(many=True, read_only=True)
    preparer_info = PreparerInfoSerializer(read_only=True)
    form_code = serializers.CharField(source="form_definition.code", read_only=True)
    tax_year_id = serializers.UUIDField(source="tax_year.id", read_only=True)
    year = serializers.IntegerField(source="tax_year.year", read_only=True)
    entity_name = serializers.CharField(
        source="tax_year.entity.name", read_only=True
    )
    entity_id = serializers.UUIDField(
        source="tax_year.entity.id", read_only=True
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
            "entity_id",
            "entity_name",
            "client_name",
            "form_code",
            "status",
            "accounting_method",
            "tax_year_start",
            "tax_year_end",
            # Page 1 header flags
            "is_initial_return",
            "is_final_return",
            "is_name_change",
            "is_address_change",
            "is_amended_return",
            "s_election_date",
            "number_of_shareholders",
            "product_or_service",
            "business_activity_code",
            # Nested data
            "field_values",
            "other_deductions",
            "officers",
            "shareholders",
            "rental_properties",
            "preparer_info",
            "created_at",
            "updated_at",
        )


class TaxReturnListSerializer(serializers.ModelSerializer):
    form_code = serializers.CharField(source="form_definition.code", read_only=True)
    year = serializers.IntegerField(source="tax_year.year", read_only=True)
    entity_name = serializers.CharField(
        source="tax_year.entity.name", read_only=True
    )
    entity_type = serializers.CharField(
        source="tax_year.entity.entity_type", read_only=True
    )
    entity_id = serializers.UUIDField(
        source="tax_year.entity.id", read_only=True
    )
    client_name = serializers.CharField(
        source="tax_year.entity.client.name", read_only=True
    )
    client_id = serializers.UUIDField(
        source="tax_year.entity.client.id", read_only=True
    )

    class Meta:
        model = TaxReturn
        fields = (
            "id",
            "tax_year_id",
            "year",
            "entity_name",
            "entity_type",
            "entity_id",
            "client_name",
            "client_id",
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
