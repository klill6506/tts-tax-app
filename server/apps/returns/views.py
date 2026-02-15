from collections import defaultdict
from decimal import Decimal

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.mixins import DestroyModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response

from apps.audit.mixins import AuditViewSetMixin
from apps.clients.models import TaxYear
from apps.firms.permissions import IsFirmMember
from apps.imports.models import TrialBalanceUpload
from apps.mappings.engine import apply_template, resolve_template
from apps.tts_forms.views import PDFRenderMixin

from .compute import compute_return
from .models import FormDefinition, FormFieldValue, FormLine, TaxReturn
from .serializers import (
    CreateReturnSerializer,
    FormDefinitionListSerializer,
    FormDefinitionSerializer,
    TaxReturnListSerializer,
    TaxReturnSerializer,
    UpdateFieldsSerializer,
)


class FormDefinitionViewSet(
    ListModelMixin, RetrieveModelMixin, viewsets.GenericViewSet
):
    """Read-only list of available form definitions."""

    permission_classes = [IsFirmMember]
    queryset = FormDefinition.objects.prefetch_related(
        "sections__lines"
    )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return FormDefinitionSerializer
        return FormDefinitionListSerializer


class TaxReturnViewSet(
    PDFRenderMixin,
    AuditViewSetMixin,
    ListModelMixin,
    RetrieveModelMixin,
    DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """List, retrieve, create, and edit tax returns."""

    permission_classes = [IsFirmMember]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return TaxReturnSerializer
        return TaxReturnListSerializer

    def get_queryset(self):
        qs = TaxReturn.objects.filter(
            tax_year__entity__client__firm=self.request.firm
        ).select_related(
            "form_definition",
            "tax_year__entity__client",
            "created_by",
        ).prefetch_related(
            "field_values__form_line__section",
        )
        tax_year_id = self.request.query_params.get("tax_year")
        if tax_year_id:
            qs = qs.filter(tax_year_id=tax_year_id)
        return qs

    @action(detail=False, methods=["post"], url_path="create")
    def create_return(self, request):
        """Create a new tax return for a tax year."""
        ser = CreateReturnSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            tax_year = TaxYear.objects.get(
                id=ser.validated_data["tax_year"],
                entity__client__firm=request.firm,
            )
        except TaxYear.DoesNotExist:
            return Response(
                {"error": "Tax year not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if return already exists
        if TaxReturn.objects.filter(tax_year=tax_year).exists():
            return Response(
                {"error": "A return already exists for this tax year."},
                status=status.HTTP_409_CONFLICT,
            )

        # Use 1120-S by default
        form_def = FormDefinition.objects.filter(code="1120-S").first()
        if not form_def:
            return Response(
                {"error": "Form 1120-S definition not found. Run seed_1120s."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        tax_return = TaxReturn.objects.create(
            tax_year=tax_year,
            form_definition=form_def,
            created_by=request.user,
        )

        # Pre-populate all form lines with empty values
        lines = FormLine.objects.filter(
            section__form=form_def
        ).select_related("section")
        FormFieldValue.objects.bulk_create([
            FormFieldValue(
                tax_return=tax_return,
                form_line=line,
                value="",
            )
            for line in lines
        ])

        return Response(
            TaxReturnSerializer(tax_return).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["patch"], url_path="fields")
    def update_fields(self, request, pk=None):
        """Bulk update field values on a return."""
        tax_return = self.get_object()
        ser = UpdateFieldsSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        updated = 0
        for entry in ser.validated_data["fields"]:
            form_line_id = entry.get("form_line")
            value = entry.get("value", "")
            if not form_line_id:
                continue

            try:
                fv = FormFieldValue.objects.get(
                    tax_return=tax_return,
                    form_line_id=form_line_id,
                )
            except FormFieldValue.DoesNotExist:
                continue

            fv.value = str(value)
            fv.is_overridden = True
            fv.updated_by = request.user
            fv.save()
            updated += 1

        # Recompute calculated fields after manual edits
        computed = compute_return(tax_return)

        return Response({"updated": updated, "computed": computed})

    @action(detail=True, methods=["post"], url_path="compute")
    def compute(self, request, pk=None):
        """Recompute all calculated fields on a return."""
        tax_return = self.get_object()
        computed = compute_return(tax_return)
        return Response({"computed": computed})

    @action(detail=True, methods=["post"], url_path="import-tb")
    def import_tb(self, request, pk=None):
        """Import trial balance data into form fields via the mapping engine."""
        tax_return = self.get_object()
        tax_year = tax_return.tax_year

        # Find the most recent parsed TB upload for this tax year
        upload = (
            TrialBalanceUpload.objects.filter(tax_year=tax_year, status="parsed")
            .order_by("-created_at")
            .first()
        )
        if not upload:
            return Response(
                {"error": "No parsed trial balance found for this tax year."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Resolve mapping template (client-specific or firm default)
        client = tax_year.entity.client
        template = resolve_template(firm=request.firm, client=client)
        if not template:
            return Response(
                {"error": "No mapping template found. Create one first."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Apply mapping rules to TB rows
        mapped_rows = apply_template(template, upload)

        # Build a lookup of form lines by mapping_key so we know each
        # line's normal_balance (debit vs credit) for sign handling.
        form_lines = {
            fl.mapping_key: fl
            for fl in FormLine.objects.filter(
                section__form=tax_return.form_definition,
                mapping_key__gt="",
            )
        }

        # Aggregate amounts by target_line, respecting normal balance:
        #   debit-normal lines:  debit − credit  (expenses, assets)
        #   credit-normal lines: credit − debit   (revenue, liabilities, equity)
        amounts: dict[str, Decimal] = defaultdict(Decimal)
        mapped_count = 0
        for row in mapped_rows:
            if row.target_line:
                fl = form_lines.get(row.target_line)
                if fl and fl.normal_balance == "credit":
                    amounts[row.target_line] += row.credit - row.debit
                else:
                    amounts[row.target_line] += row.debit - row.credit
                mapped_count += 1

        # Update FormFieldValues with the aggregated amounts
        updated = 0
        for mapping_key, amount in amounts.items():
            fl = form_lines.get(mapping_key)
            if not fl:
                continue
            try:
                fv = FormFieldValue.objects.get(
                    tax_return=tax_return,
                    form_line=fl,
                )
                fv.value = str(amount.quantize(Decimal("0.01")))
                fv.is_overridden = False
                fv.updated_by = request.user
                fv.save()
                updated += 1
            except FormFieldValue.DoesNotExist:
                continue

        # Recompute calculated fields after import
        computed = compute_return(tax_return)

        return Response({
            "imported": updated,
            "computed": computed,
            "total_rows": len(mapped_rows),
            "mapped_rows": mapped_count,
            "unmapped_rows": len(mapped_rows) - mapped_count,
        })
