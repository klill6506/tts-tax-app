import logging
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
from .models import (
    FormDefinition,
    FormFieldValue,
    FormLine,
    Officer,
    OtherDeduction,
    PreparerInfo,
    PriorYearReturn,
    RentalProperty,
    Shareholder,
    ShareholderLoan,
    TaxReturn,
)
from .serializers import (
    CreateReturnSerializer,
    FormDefinitionListSerializer,
    FormDefinitionSerializer,
    OfficerSerializer,
    OtherDeductionSerializer,
    PreparerInfoSerializer,
    PriorYearReturnSerializer,
    RentalPropertySerializer,
    ShareholderLoanSerializer,
    ShareholderSerializer,
    TaxReturnListSerializer,
    TaxReturnSerializer,
    UpdateFieldsSerializer,
)

logger = logging.getLogger(__name__)

# Maps entity_type → FormDefinition.code
ENTITY_FORM_MAP = {
    "scorp": "1120-S",
    "partnership": "1065",
    "ccorp": "1120",
}

# Maps FormDefinition.code → the "Other deductions" FormLine mapping_key
OTHER_DED_LINE_KEY = {
    "1120-S": "1120S_L19",
    "1065": "1065_L20",
    "1120": "1120_L26",
}

# Standard deduction categories for the Other Deductions dropdown
STANDARD_DEDUCTION_CATEGORIES = [
    "Amortization",
    "Accounting",
    "Answering Service",
    "Auto and Truck Expense",
    "Bank Charges",
    "Commissions",
    "Delivery and Freight",
    "Dues and Subscriptions",
    "Gifts",
    "Janitorial",
    "Laundry and Cleaning",
    "Legal and Professional",
    "Miscellaneous",
    "Office Expense",
    "Organizational Expenditures",
    "Outside Services",
    "Parking and Tolls",
    "Postage",
    "Printing",
    "Security",
    "Start-up Costs",
    "Supplies",
    "Telephone",
    "Tools",
    "Travel",
    "Uniforms",
    "Utilities",
    "Operating Expenses (O&G)",
    "Allocated Overhead (O&G)",
    "Other Expenses (O&G)",
    "Total Farm Expenses",
    "Pension Start-up Credit Reduction",
    "Credit Reduction",
    "Other Deductions",
]


def _rollup_other_deductions(tax_return):
    """Sum all OtherDeduction rows and write to the 'Other deductions' FormLine."""
    form_code = tax_return.form_definition.code
    mapping_key = OTHER_DED_LINE_KEY.get(form_code)
    if not mapping_key:
        return

    total = (
        OtherDeduction.objects.filter(tax_return=tax_return)
        .aggregate(total=models_Sum("amount"))["total"]
    ) or Decimal("0.00")

    try:
        fl = FormLine.objects.get(
            section__form=tax_return.form_definition,
            mapping_key=mapping_key,
        )
        fv, _ = FormFieldValue.objects.get_or_create(
            tax_return=tax_return,
            form_line=fl,
        )
        fv.value = str(total.quantize(Decimal("0.01")))
        fv.is_overridden = False
        fv.save(update_fields=["value", "is_overridden", "updated_at"])
    except FormLine.DoesNotExist:
        pass

    compute_return(tax_return)


# Need this import for the aggregate
from django.db.models import Sum as models_Sum


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
        from django.db.models import Q

        qs = TaxReturn.objects.filter(
            tax_year__entity__client__firm=self.request.firm
        ).select_related(
            "form_definition",
            "tax_year__entity__client",
            "created_by",
            "preparer",
        ).prefetch_related(
            "field_values__form_line__section",
            "other_deductions",
            "officers",
            "shareholders",
            "rental_properties",
            "preparer_info",
        )
        # Filter by tax year UUID (existing)
        tax_year_id = self.request.query_params.get("tax_year")
        if tax_year_id:
            qs = qs.filter(tax_year_id=tax_year_id)
        # Filter by calendar year
        year = self.request.query_params.get("year")
        if year:
            qs = qs.filter(tax_year__year=year)
        # Filter by return status
        ret_status = self.request.query_params.get("status")
        if ret_status:
            qs = qs.filter(status=ret_status)
        # Filter by form code (e.g. "1120-S")
        form_code = self.request.query_params.get("form_code")
        if form_code:
            qs = qs.filter(form_definition__code=form_code)
        # Search across client name and entity name
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(tax_year__entity__name__icontains=search)
                | Q(tax_year__entity__client__name__icontains=search)
            )
        return qs

    # ------------------------------------------------------------------
    # Create return (form-aware by entity type)
    # ------------------------------------------------------------------

    @action(detail=False, methods=["post"], url_path="create")
    def create_return(self, request):
        """Create a new tax return for a tax year."""
        ser = CreateReturnSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            tax_year = TaxYear.objects.select_related("entity").get(
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

        # Select form based on entity type
        entity_type = tax_year.entity.entity_type
        form_code = ENTITY_FORM_MAP.get(entity_type)
        if not form_code:
            return Response(
                {"error": f"Form not yet supported for entity type '{entity_type}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        form_def = FormDefinition.objects.filter(code=form_code).first()
        if not form_def:
            return Response(
                {"error": f"Form {form_code} definition not found. Run the seed command."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Default tax year dates to calendar year for S-Corps and Partnerships
        import datetime
        year = tax_year.year
        default_start = datetime.date(year, 1, 1)
        default_end = datetime.date(year, 12, 31)

        tax_return = TaxReturn.objects.create(
            tax_year=tax_year,
            form_definition=form_def,
            created_by=request.user,
            tax_year_start=default_start,
            tax_year_end=default_end,
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

    # ------------------------------------------------------------------
    # Update return info (accounting method, tax year dates)
    # ------------------------------------------------------------------

    @action(detail=True, methods=["patch"], url_path="info")
    def update_info(self, request, pk=None):
        """Update return-level header fields."""
        tax_return = self.get_object()
        allowed = {
            "accounting_method", "tax_year_start", "tax_year_end", "status",
            # Page 1 header flags
            "is_initial_return", "is_final_return", "is_name_change",
            "is_address_change", "is_amended_return",
            "s_election_date", "number_of_shareholders",
            "product_or_service", "business_activity_code",
            # Preparer
            "preparer", "signature_date",
        }
        nullable_fields = {
            "s_election_date", "number_of_shareholders",
            "preparer", "signature_date",
        }
        updated = 0
        for field in allowed:
            if field in request.data:
                val = request.data[field]
                # Handle null/blank for nullable fields
                if val == "" and field in nullable_fields:
                    val = None
                # For FK fields, convert UUID string to _id
                if field == "preparer":
                    setattr(tax_return, "preparer_id", val)
                else:
                    setattr(tax_return, field, val)
                updated += 1
        if updated:
            tax_return.save()
        return Response(TaxReturnSerializer(tax_return).data)

    # ------------------------------------------------------------------
    # Bulk update field values
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------

    @action(detail=True, methods=["post"], url_path="compute")
    def compute(self, request, pk=None):
        """Recompute all calculated fields on a return."""
        tax_return = self.get_object()
        computed = compute_return(tax_return)
        return Response({"computed": computed})

    # ------------------------------------------------------------------
    # Other Deductions CRUD
    # ------------------------------------------------------------------

    @action(detail=True, methods=["get", "post"], url_path="other-deductions")
    def other_deductions(self, request, pk=None):
        """List or create Other Deduction rows."""
        tax_return = self.get_object()

        if request.method == "GET":
            qs = OtherDeduction.objects.filter(tax_return=tax_return)
            return Response(OtherDeductionSerializer(qs, many=True).data)

        # POST — create
        ser = OtherDeductionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save(tax_return=tax_return)
        _rollup_other_deductions(tax_return)
        return Response(ser.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["patch", "delete"],
        url_path="other-deductions/(?P<ded_id>[^/.]+)",
    )
    def other_deduction_detail(self, request, pk=None, ded_id=None):
        """Update or delete a single Other Deduction row."""
        tax_return = self.get_object()
        try:
            ded = OtherDeduction.objects.get(id=ded_id, tax_return=tax_return)
        except OtherDeduction.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if request.method == "DELETE":
            ded.delete()
            _rollup_other_deductions(tax_return)
            return Response(status=status.HTTP_204_NO_CONTENT)

        # PATCH
        ser = OtherDeductionSerializer(ded, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        _rollup_other_deductions(tax_return)
        return Response(ser.data)

    # ------------------------------------------------------------------
    # Officers CRUD
    # ------------------------------------------------------------------

    @action(detail=True, methods=["get", "post"], url_path="officers")
    def officers(self, request, pk=None):
        """List or create Officer rows."""
        tax_return = self.get_object()

        if request.method == "GET":
            qs = Officer.objects.filter(tax_return=tax_return)
            return Response(OfficerSerializer(qs, many=True).data)

        # POST
        ser = OfficerSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save(tax_return=tax_return)
        return Response(ser.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["patch", "delete"],
        url_path="officers/(?P<officer_id>[^/.]+)",
    )
    def officer_detail(self, request, pk=None, officer_id=None):
        """Update or delete a single Officer row."""
        tax_return = self.get_object()
        try:
            officer = Officer.objects.get(id=officer_id, tax_return=tax_return)
        except Officer.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if request.method == "DELETE":
            officer.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        # PATCH
        ser = OfficerSerializer(officer, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)

    # ------------------------------------------------------------------
    # Shareholders CRUD
    # ------------------------------------------------------------------

    @action(detail=True, methods=["get", "post"], url_path="shareholders")
    def shareholders(self, request, pk=None):
        """List or create Shareholder rows."""
        tax_return = self.get_object()

        if request.method == "GET":
            qs = Shareholder.objects.filter(
                tax_return=tax_return
            ).select_related("linked_client")
            return Response(ShareholderSerializer(qs, many=True).data)

        # POST
        ser = ShareholderSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save(tax_return=tax_return)
        self._rollup_distributions(tax_return)
        return Response(ser.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["patch", "delete"],
        url_path="shareholders/(?P<sh_id>[^/.]+)",
    )
    def shareholder_detail(self, request, pk=None, sh_id=None):
        """Update or delete a single Shareholder row."""
        tax_return = self.get_object()
        try:
            sh = Shareholder.objects.select_related("linked_client").get(
                id=sh_id, tax_return=tax_return
            )
        except Shareholder.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if request.method == "DELETE":
            sh.delete()
            self._rollup_distributions(tax_return)
            return Response(status=status.HTTP_204_NO_CONTENT)

        # PATCH
        ser = ShareholderSerializer(sh, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        self._rollup_distributions(tax_return)
        return Response(ser.data)

    # ------------------------------------------------------------------
    # Shareholder Loans CRUD (Form 7203 Part II)
    # ------------------------------------------------------------------

    @action(
        detail=True,
        methods=["get", "post"],
        url_path="shareholders/(?P<sh_id>[^/.]+)/loans",
    )
    def shareholder_loans(self, request, pk=None, sh_id=None):
        """List or create loans for a shareholder."""
        tax_return = self.get_object()
        try:
            sh = Shareholder.objects.get(id=sh_id, tax_return=tax_return)
        except Shareholder.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if request.method == "GET":
            qs = ShareholderLoan.objects.filter(shareholder=sh)
            return Response(ShareholderLoanSerializer(qs, many=True).data)

        ser = ShareholderLoanSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save(shareholder=sh)
        return Response(ser.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["patch", "delete"],
        url_path="shareholders/(?P<sh_id>[^/.]+)/loans/(?P<loan_id>[^/.]+)",
    )
    def shareholder_loan_detail(self, request, pk=None, sh_id=None, loan_id=None):
        """Update or delete a shareholder loan."""
        tax_return = self.get_object()
        try:
            sh = Shareholder.objects.get(id=sh_id, tax_return=tax_return)
        except Shareholder.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            loan = ShareholderLoan.objects.get(id=loan_id, shareholder=sh)
        except ShareholderLoan.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if request.method == "DELETE":
            loan.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        ser = ShareholderLoanSerializer(loan, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)

    # ------------------------------------------------------------------
    # Rental Properties CRUD (Form 8825)
    # ------------------------------------------------------------------

    @action(detail=True, methods=["get", "post"], url_path="rental-properties")
    def rental_properties(self, request, pk=None):
        """List or create Rental Property rows."""
        tax_return = self.get_object()

        if request.method == "GET":
            qs = RentalProperty.objects.filter(tax_return=tax_return)
            return Response(RentalPropertySerializer(qs, many=True).data)

        # POST
        ser = RentalPropertySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save(tax_return=tax_return)
        self._rollup_rental_to_k2(tax_return)
        return Response(ser.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["patch", "delete"],
        url_path="rental-properties/(?P<rp_id>[^/.]+)",
    )
    def rental_property_detail(self, request, pk=None, rp_id=None):
        """Update or delete a single Rental Property row."""
        tax_return = self.get_object()
        try:
            rp = RentalProperty.objects.get(id=rp_id, tax_return=tax_return)
        except RentalProperty.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if request.method == "DELETE":
            rp.delete()
            self._rollup_rental_to_k2(tax_return)
            return Response(status=status.HTTP_204_NO_CONTENT)

        # PATCH
        ser = RentalPropertySerializer(rp, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        self._rollup_rental_to_k2(tax_return)
        return Response(ser.data)

    def _rollup_rental_to_k2(self, tax_return):
        """Sum net rental income from all properties into Schedule K line 2."""
        from decimal import Decimal

        total = Decimal("0")
        for rp in RentalProperty.objects.filter(tax_return=tax_return):
            total += rp.net_rent

        # Map to Schedule K line 2 (1120S_K2)
        form_code = tax_return.form_definition.code
        k2_key = {
            "1120-S": "1120S_K2",
            "1065": "1065_K2",
        }.get(form_code)
        if not k2_key:
            return

        try:
            fl = FormLine.objects.get(
                section__form=tax_return.form_definition,
                mapping_key=k2_key,
            )
            fv, _ = FormFieldValue.objects.get_or_create(
                tax_return=tax_return,
                form_line=fl,
            )
            fv.value = str(total.quantize(Decimal("0.01")))
            fv.is_overridden = False
            fv.save(update_fields=["value", "is_overridden", "updated_at"])
        except FormLine.DoesNotExist:
            pass

        compute_return(tax_return)

    def _rollup_distributions(self, tax_return):
        """Sum all shareholder distributions into Schedule K line 16d."""
        from decimal import Decimal
        from django.db.models import Sum

        total = (
            Shareholder.objects.filter(tax_return=tax_return)
            .aggregate(total=Sum("distributions"))["total"]
        ) or Decimal("0")

        form_code = tax_return.form_definition.code
        k16d_key = {
            "1120-S": "1120S_K16d",
            "1065": "1065_K16d",
        }.get(form_code)
        if not k16d_key:
            return

        try:
            fl = FormLine.objects.get(
                section__form=tax_return.form_definition,
                mapping_key=k16d_key,
            )
            fv, _ = FormFieldValue.objects.get_or_create(
                tax_return=tax_return,
                form_line=fl,
            )
            fv.value = str(total.quantize(Decimal("0.01")))
            fv.is_overridden = False
            fv.save(update_fields=["value", "is_overridden", "updated_at"])
        except FormLine.DoesNotExist:
            pass

        compute_return(tax_return)

    # ------------------------------------------------------------------
    # Preparer Info (get-or-create + patch)
    # ------------------------------------------------------------------

    @action(detail=True, methods=["get", "patch"], url_path="preparer")
    def preparer(self, request, pk=None):
        """Get or update preparer info for a return."""
        tax_return = self.get_object()

        if request.method == "GET":
            info, _ = PreparerInfo.objects.get_or_create(
                tax_return=tax_return,
            )
            return Response(PreparerInfoSerializer(info).data)

        # PATCH
        info, _ = PreparerInfo.objects.get_or_create(
            tax_return=tax_return,
        )
        ser = PreparerInfoSerializer(info, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)

    # ------------------------------------------------------------------
    # Standard deduction categories (static list)
    # ------------------------------------------------------------------

    @action(detail=False, methods=["get"], url_path="deduction-categories")
    def deduction_categories(self, request):
        """Return the standard list of Other Deduction categories."""
        return Response(STANDARD_DEDUCTION_CATEGORIES)

    # ------------------------------------------------------------------
    # Trial Balance import (enhanced with OtherDeduction routing)
    # ------------------------------------------------------------------

    @action(detail=True, methods=["post"], url_path="import-tb")
    def import_tb(self, request, pk=None):
        """Import trial balance data into form fields via the mapping engine."""
        tax_return = self.get_object()
        tax_year = tax_return.tax_year
        form_code = tax_return.form_definition.code

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

        # Build a lookup of form lines by mapping_key
        form_lines = {
            fl.mapping_key: fl
            for fl in FormLine.objects.filter(
                section__form=tax_return.form_definition,
                mapping_key__gt="",
            )
        }

        # The "Other deductions" line key for this form
        other_ded_key = OTHER_DED_LINE_KEY.get(form_code)

        # Aggregate amounts by target_line, respecting normal balance
        amounts: dict[str, Decimal] = defaultdict(Decimal)
        mapped_count = 0
        other_ded_rows = []  # rows going to Other Deductions detail
        unmapped_rows = []

        total_debit = Decimal("0")
        total_credit = Decimal("0")

        for row in mapped_rows:
            total_debit += row.debit
            total_credit += row.credit

            if row.target_line:
                # Route to Other Deductions detail if targeting the other ded line
                if other_ded_key and row.target_line == other_ded_key:
                    net = row.debit - row.credit  # expenses are debit-normal
                    other_ded_rows.append((row.account_name, net))
                else:
                    fl = form_lines.get(row.target_line)
                    if fl and fl.normal_balance == "credit":
                        amounts[row.target_line] += row.credit - row.debit
                    else:
                        amounts[row.target_line] += row.debit - row.credit
                mapped_count += 1
            else:
                # Unmapped row — route expenses to Other Deductions
                net = row.debit - row.credit
                if net > 0:  # only if it looks like an expense (positive debit net)
                    other_ded_rows.append((row.account_name, net))
                unmapped_rows.append({
                    "account_number": row.account_number,
                    "account_name": row.account_name,
                    "debit": str(row.debit),
                    "credit": str(row.credit),
                })

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

        # Create OtherDeduction rows (clear previous TB imports first)
        OtherDeduction.objects.filter(
            tax_return=tax_return, source="tb_import"
        ).delete()

        other_ded_created = 0
        for idx, (desc, amt) in enumerate(other_ded_rows):
            if amt:  # skip zero amounts
                OtherDeduction.objects.create(
                    tax_return=tax_return,
                    description=desc,
                    amount=amt.quantize(Decimal("0.01")),
                    source="tb_import",
                    sort_order=idx,
                )
                other_ded_created += 1

        # Roll up Other Deductions total into the form line
        _rollup_other_deductions(tax_return)

        # Log import summary
        logger.info(
            "TB Import: return=%s form=%s total_rows=%d mapped=%d "
            "other_ded=%d unmapped=%d debit_total=%s credit_total=%s",
            tax_return.id, form_code, len(mapped_rows), mapped_count,
            other_ded_created, len(unmapped_rows),
            total_debit, total_credit,
        )

        return Response({
            "imported": updated,
            "computed": 0,  # compute ran inside _rollup
            "total_rows": len(mapped_rows),
            "mapped_rows": mapped_count,
            "unmapped_rows": len(unmapped_rows),
            "other_deductions_created": other_ded_created,
        })

    # ------------------------------------------------------------------
    # Prior Year Data
    # ------------------------------------------------------------------

    @action(detail=True, methods=["get"], url_path="prior-year")
    def prior_year(self, request, pk=None):
        """
        Get prior year return data for comparison display.

        Returns the PriorYearReturn for this return's entity and
        the year before this return's tax year.
        """
        tax_return = self.get_object()
        entity = tax_return.tax_year.entity
        prior_year = tax_return.tax_year.year - 1

        try:
            pyr = PriorYearReturn.objects.get(
                entity=entity,
                year=prior_year,
            )
        except PriorYearReturn.DoesNotExist:
            return Response(
                {"error": f"No prior year data for {entity.name} ({prior_year})."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = PriorYearReturnSerializer(pyr)
        return Response(serializer.data)
