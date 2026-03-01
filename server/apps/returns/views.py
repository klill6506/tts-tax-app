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


def _populate_boy_from_prior_year(tax_return):
    """
    Auto-populate Balance Sheet BOY (beginning of year) values from
    the prior year's EOY (end of year) values.

    Prior year's ending balance IS this year's beginning balance.
    Skips fields that have been manually overridden.
    """
    entity = tax_return.tax_year.entity
    prior_year_num = tax_return.tax_year.year - 1

    try:
        pyr = PriorYearReturn.objects.get(entity=entity, year=prior_year_num)
    except PriorYearReturn.DoesNotExist:
        return 0

    bs = pyr.balance_sheet or {}
    if not bs:
        return 0

    # Get all BOY FormFieldValues for this return's Schedule L
    boy_fvs = FormFieldValue.objects.filter(
        tax_return=tax_return,
        form_line__section__code="sched_l",
        form_line__mapping_key__endswith="_boy",
    ).select_related("form_line")

    updated = 0
    for fv in boy_fvs:
        if fv.is_overridden:
            continue

        line_num = fv.form_line.line_number  # e.g., "L1a", "L9b"
        ln = line_num[1:]  # strip 'L' → "1a", "9b"

        # Build candidate PY keys to try
        # "L1a" → try "L1" (strip trailing 'a' column letter)
        # "L9b" → try "L9b" (sub-line, keep as-is)
        py_keys = []
        if ln.endswith("a"):
            base = ln[:-1]  # "1" from "1a"
            py_keys = [f"L{base}", f"L{ln}"]
        elif ln.endswith("b"):
            py_keys = [f"L{ln}"]
        else:
            py_keys = [f"L{ln}"]

        # Look up the PY EOY value using candidate keys
        amount = None
        for key in py_keys:
            eoy_key = f"{key}_eoy"
            if eoy_key in bs:
                amount = bs[eoy_key]
                break

        if amount is not None and amount != 0:
            fv.value = str(Decimal(str(amount)).quantize(Decimal("0.01")))
            fv.save(update_fields=["value", "updated_at"])
            updated += 1

    if updated:
        compute_return(tax_return)

    return updated


def _populate_m2_boy_from_prior_year(tax_return):
    """
    Auto-populate Schedule M-2 beginning balance (line 1) from
    the prior year's ending balance (line 8).
    """
    entity = tax_return.tax_year.entity
    prior_year_num = tax_return.tax_year.year - 1

    try:
        pyr = PriorYearReturn.objects.get(entity=entity, year=prior_year_num)
    except PriorYearReturn.DoesNotExist:
        return 0

    m2 = pyr.m2_balances or {}
    if not m2:
        return 0

    # M2_8 is the ending balance on the 1120-S M-2
    # (1065 uses M2_9, 1120 uses M2_8 as well)
    ending_key = "M2_8"
    if pyr.form_code == "1065":
        ending_key = "M2_9"
    ending_balance = m2.get(ending_key)
    if ending_balance is None:
        return 0

    # Set M2_1 (beginning balance) on the current year return
    try:
        m2_1_fv = FormFieldValue.objects.get(
            tax_return=tax_return,
            form_line__line_number="M2_1",
            form_line__section__code="sched_m2",
        )
    except FormFieldValue.DoesNotExist:
        return 0

    if m2_1_fv.is_overridden:
        return 0

    m2_1_fv.value = str(Decimal(str(ending_balance)).quantize(Decimal("0.01")))
    m2_1_fv.save(update_fields=["value", "updated_at"])
    compute_return(tax_return)
    return 1


def _populate_shareholders_from_prior_year(tax_return):
    """
    Pre-create Shareholder records from prior year K-1 data.

    Uses PriorYearReturn.shareholders (list of dicts from K-1 parsing).
    Only runs if no shareholders exist yet on this return.
    """
    if tax_return.shareholders.exists():
        return 0

    entity = tax_return.tax_year.entity
    prior_year_num = tax_return.tax_year.year - 1

    try:
        pyr = PriorYearReturn.objects.get(entity=entity, year=prior_year_num)
    except PriorYearReturn.DoesNotExist:
        return 0

    py_shareholders = pyr.shareholders or []
    if not py_shareholders:
        return 0

    shareholders = []
    for idx, sh in enumerate(py_shareholders):
        shareholders.append(
            Shareholder(
                tax_return=tax_return,
                name=sh.get("name", ""),
                ssn=sh.get("ssn", ""),
                address_line1=sh.get("address_line1", ""),
                city=sh.get("city", ""),
                state=sh.get("state", ""),
                zip_code=sh.get("zip_code", ""),
                ownership_percentage=Decimal(
                    str(sh.get("ownership_percentage", 0))
                ),
                # PY ending shares become this year's beginning shares
                beginning_shares=sh.get("ending_shares", 0),
                ending_shares=sh.get("ending_shares", 0),
                sort_order=(idx + 1) * 10,
                is_active=True,
            )
        )
    Shareholder.objects.bulk_create(shareholders)
    return len(shareholders)


def _populate_officers_from_prior_year(tax_return):
    """
    Pre-create Officer records from prior year 1125-E data.

    Uses PriorYearReturn.officers (list of dicts from 1125-E parsing).
    Only runs if no officers exist yet on this return.
    """
    if tax_return.officers.exists():
        return 0

    entity = tax_return.tax_year.entity
    prior_year_num = tax_return.tax_year.year - 1

    try:
        pyr = PriorYearReturn.objects.get(entity=entity, year=prior_year_num)
    except PriorYearReturn.DoesNotExist:
        return 0

    py_officers = pyr.officers or []
    if not py_officers:
        return 0

    officers = []
    for idx, off in enumerate(py_officers):
        officers.append(
            Officer(
                tax_return=tax_return,
                name=off.get("name", ""),
                ssn=off.get("ssn", ""),
                percent_time=Decimal(
                    str(off.get("percent_time", 0))
                ),
                percent_ownership=Decimal(
                    str(off.get("percent_ownership", 0))
                ),
                # Don't carry forward compensation — it changes every year
                compensation=Decimal("0"),
                sort_order=(idx + 1) * 10,
            )
        )
    Officer.objects.bulk_create(officers)
    return len(officers)


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

# ── Standard deduction presets ──────────────────────────────────────────
# These are pre-populated as OtherDeduction rows on every new return
# (Lacerte-style).  They do NOT have their own IRS form line — they
# all roll up into the "Other deductions" line (1120-S L19, 1065 L20,
# 1120 L26) and generate a supporting schedule on the printed return.
OTHER_DEDUCTION_PRESETS = [
    "Accounting",
    "Amortization",
    "Answering Service",
    "Auto and Truck Expense",
    "Bank Charges",
    "Charitable Contributions",
    "Commissions",
    "Computer and Internet",
    "Contract Labor",
    "Delivery and Freight",
    "Dues and Subscriptions",
    "Equipment Rental",
    "Gifts",
    "Insurance",
    "Janitorial",
    "Laundry and Cleaning",
    "Legal and Professional",
    "Licenses and Permits",
    "Meals",
    "Miscellaneous",
    "Non-Deductible Expenses",
    "Office Expense",
    "Organizational Expenditures",
    "Outside Services",
    "Parking and Tolls",
    "Payroll Processing",
    "Postage",
    "Printing",
    "Professional Development",
    "Security",
    "Software and Subscriptions",
    "Start-up Costs",
    "Storage",
    "Supplies",
    "Telephone",
    "Tools",
    "Training",
    "Travel",
    "Uniforms",
    "Utilities",
    "Waste Removal",
]

# Full list for the dropdown (includes presets + specialty categories)
STANDARD_DEDUCTION_CATEGORIES = sorted(
    set(OTHER_DEDUCTION_PRESETS) | {
        "Operating Expenses (O&G)",
        "Allocated Overhead (O&G)",
        "Other Expenses (O&G)",
        "Total Farm Expenses",
        "Pension Start-up Credit Reduction",
        "Credit Reduction",
        "Other Deductions",
    }
)


def _populate_schedule_b_defaults(tax_return):
    """
    Auto-default all Schedule B Yes/No questions to "false" (Lacerte approach).

    Most S-Corp returns answer "No" to all Schedule B questions.
    B8 (built-in gain amount) defaults to "0".
    Preparers change only the ones that apply.
    """
    b_fields = FormFieldValue.objects.filter(
        tax_return=tax_return,
        form_line__section__code="sched_b",
    ).select_related("form_line")

    updated = 0
    for fv in b_fields:
        if fv.is_overridden:
            continue
        if fv.form_line.field_type == "boolean":
            fv.value = "false"
            fv.save(update_fields=["value", "updated_at"])
            updated += 1
        elif fv.form_line.field_type == "currency":
            # B8: net unrealized built-in gain — default 0
            fv.value = "0.00"
            fv.save(update_fields=["value", "updated_at"])
            updated += 1

    return updated


def _prepopulate_standard_deductions(tax_return):
    """
    Pre-populate a new return with standard deduction categories
    (Lacerte-style).  Each preset gets an OtherDeduction row with $0.

    If prior year data exists, match PY other_deductions descriptions
    to standard categories and fill in amounts.
    """
    # Look up prior year deductions for matching
    entity = tax_return.tax_year.entity
    prior_year_num = tax_return.tax_year.year - 1
    py_other = {}
    try:
        pyr = PriorYearReturn.objects.get(entity=entity, year=prior_year_num)
        py_other = pyr.other_deductions or {}
    except PriorYearReturn.DoesNotExist:
        pass

    # Build case-insensitive PY lookup
    py_lookup = {k.lower().strip(): v for k, v in py_other.items()}

    standard_deds = []
    for idx, cat in enumerate(OTHER_DEDUCTION_PRESETS):
        # Check if PY has a matching deduction
        py_amount = py_lookup.get(cat.lower(), 0)
        standard_deds.append(
            OtherDeduction(
                tax_return=tax_return,
                description=cat,
                amount=Decimal(str(py_amount)).quantize(Decimal("0.01")),
                category=cat,
                sort_order=(idx + 1) * 10,
                source="standard",
            )
        )
    OtherDeduction.objects.bulk_create(standard_deds)


def _rollup_other_deductions(tax_return):
    """Sum OtherDeduction rows: charity → K12a, non-deductible → K16c/K18c,
    everything else → Line 19."""
    form_code = tax_return.form_definition.code
    mapping_key = OTHER_DED_LINE_KEY.get(form_code)
    if not mapping_key:
        return

    deductions = OtherDeduction.objects.filter(tax_return=tax_return)

    # Separate special categories from ordinary deductions
    charity_total = (
        deductions.filter(description__iexact="Charitable Contributions")
        .aggregate(total=models_Sum("amount"))["total"]
    ) or Decimal("0.00")

    nonded_total = (
        deductions.filter(description__iexact="Non-Deductible Expenses")
        .aggregate(total=models_Sum("amount"))["total"]
    ) or Decimal("0.00")

    other_total = (
        deductions.exclude(description__iexact="Charitable Contributions")
        .exclude(description__iexact="Non-Deductible Expenses")
        .aggregate(total=models_Sum("amount"))["total"]
    ) or Decimal("0.00")

    # Write other deductions → Line 19 (or equivalent)
    try:
        fl = FormLine.objects.get(
            section__form=tax_return.form_definition,
            mapping_key=mapping_key,
        )
        fv, _ = FormFieldValue.objects.get_or_create(
            tax_return=tax_return,
            form_line=fl,
        )
        fv.value = str(other_total.quantize(Decimal("0.01")))
        fv.is_overridden = False
        fv.save(update_fields=["value", "is_overridden", "updated_at"])
    except FormLine.DoesNotExist:
        pass

    # Write charity → K12a (Schedule K, charitable contributions)
    CHARITY_LINE_KEY = {
        "1120-S": "1120S_K12a",
        "1065": "1065_K13a",
    }
    charity_key = CHARITY_LINE_KEY.get(form_code)
    if charity_key:
        _write_schedule_k_line(tax_return, charity_key, charity_total)

    # Write non-deductible → K16c (1120-S) or K18c (1065)
    NONDED_LINE_KEY = {
        "1120-S": "1120S_K16c",
        "1065": "1065_K18c",
    }
    nonded_key = NONDED_LINE_KEY.get(form_code)
    if nonded_key:
        _write_schedule_k_line(tax_return, nonded_key, nonded_total)

    compute_return(tax_return)


def _write_schedule_k_line(tax_return, mapping_key, total):
    """Write a total to a Schedule K line, respecting is_overridden."""
    try:
        fl = FormLine.objects.get(
            section__form=tax_return.form_definition,
            mapping_key=mapping_key,
        )
        fv, _ = FormFieldValue.objects.get_or_create(
            tax_return=tax_return,
            form_line=fl,
        )
        if not fv.is_overridden:
            fv.value = str(total.quantize(Decimal("0.01")))
            fv.save(update_fields=["value", "updated_at"])
    except FormLine.DoesNotExist:
        pass


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

        # Auto-populate return-level fields from the entity
        entity = tax_year.entity
        extra_fields = {}
        if entity.naics_code:
            extra_fields["business_activity_code"] = entity.naics_code
        if entity.business_activity:
            extra_fields["product_or_service"] = entity.business_activity
        if hasattr(entity, "date_incorporated") and entity.date_incorporated:
            # S election date often == date incorporated for small S-Corps
            pass  # s_election_date stays null unless PY data provides it
        # Pull s_election_date from PriorYearReturn metadata if available
        try:
            pyr = PriorYearReturn.objects.get(
                entity=entity, year=year - 1
            )
            if pyr.line_values and pyr.line_values.get("_s_election_date"):
                raw_date = pyr.line_values["_s_election_date"]
                # Convert MM/DD/YYYY → YYYY-MM-DD for Django DateField
                try:
                    dt = datetime.datetime.strptime(raw_date, "%m/%d/%Y")
                    extra_fields["s_election_date"] = dt.strftime("%Y-%m-%d")
                except ValueError:
                    extra_fields["s_election_date"] = raw_date
            if pyr.line_values and pyr.line_values.get("_number_of_shareholders"):
                extra_fields["number_of_shareholders"] = pyr.line_values["_number_of_shareholders"]
        except PriorYearReturn.DoesNotExist:
            pass

        tax_return = TaxReturn.objects.create(
            tax_year=tax_year,
            form_definition=form_def,
            created_by=request.user,
            tax_year_start=default_start,
            tax_year_end=default_end,
            **extra_fields,
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

        # Pre-populate standard deductions (Lacerte-style)
        _prepopulate_standard_deductions(tax_return)

        # Auto-default Schedule B answers (Lacerte-style — all "No")
        _populate_schedule_b_defaults(tax_return)

        # Auto-populate Balance Sheet BOY from prior year EOY
        _populate_boy_from_prior_year(tax_return)

        # Auto-populate M-2 beginning balance from prior year ending balance
        _populate_m2_boy_from_prior_year(tax_return)

        # Auto-populate shareholders from prior year K-1 data
        _populate_shareholders_from_prior_year(tax_return)

        # Auto-populate officers from prior year 1125-E data
        _populate_officers_from_prior_year(tax_return)

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
            # Extension (Form 7004)
            "extension_filed", "extension_date",
            "tentative_tax", "total_payments", "balance_due",
            # Banking
            "bank_routing_number", "bank_account_number", "bank_account_type",
            # Preparer
            "preparer", "staff_preparer", "signature_date",
        }
        nullable_fields = {
            "s_election_date", "number_of_shareholders",
            "extension_date",
            "preparer", "staff_preparer", "signature_date",
        }
        updated = 0
        for field in allowed:
            if field in request.data:
                val = request.data[field]
                # Handle null/blank for nullable fields
                if val == "" and field in nullable_fields:
                    val = None
                # For FK fields, convert UUID string to _id
                if field in ("preparer", "staff_preparer"):
                    setattr(tax_return, f"{field}_id", val)
                else:
                    setattr(tax_return, field, val)
                updated += 1
        if updated:
            tax_return.save()

        # Auto-sync PreparerInfo snapshot when preparer FK changes
        if "preparer" in request.data:
            self._sync_preparer_info(tax_return)

        return Response(TaxReturnSerializer(tax_return).data)

    # ------------------------------------------------------------------
    # Preparer → PreparerInfo sync
    # ------------------------------------------------------------------

    def _sync_preparer_info(self, tax_return):
        """Copy data from the firm-level Preparer into the per-return PreparerInfo snapshot."""
        prep = tax_return.preparer
        if prep is None:
            # Preparer was cleared — delete the snapshot
            PreparerInfo.objects.filter(tax_return=tax_return).delete()
            return

        info, _ = PreparerInfo.objects.get_or_create(tax_return=tax_return)
        info.preparer_name = prep.name
        info.ptin = prep.ptin
        info.is_self_employed = prep.is_self_employed
        info.signature_date = tax_return.signature_date
        info.firm_name = prep.firm_name
        info.firm_ein = prep.firm_ein
        info.firm_phone = prep.firm_phone
        info.firm_address = prep.firm_address
        info.firm_city = prep.firm_city
        info.firm_state = prep.firm_state
        info.firm_zip = prep.firm_zip
        info.designee_name = prep.designee_name
        info.designee_phone = prep.designee_phone
        info.designee_pin = prep.designee_pin
        info.save()

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
        self._rollup_officer_compensation(tax_return)
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
            self._rollup_officer_compensation(tax_return)
            return Response(status=status.HTTP_204_NO_CONTENT)

        # PATCH
        ser = OfficerSerializer(officer, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        self._rollup_officer_compensation(tax_return)
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

    def _rollup_officer_compensation(self, tax_return):
        """Sum all officer compensation into Page 1 Line 7."""
        from decimal import Decimal
        from django.db.models import Sum

        total = (
            Officer.objects.filter(tax_return=tax_return)
            .aggregate(total=Sum("compensation"))["total"]
        ) or Decimal("0")

        form_code = tax_return.form_definition.code
        line7_key = {
            "1120-S": "1120S_L7",
            "1065": "1065_L9",
        }.get(form_code)
        if not line7_key:
            return

        try:
            fl = FormLine.objects.get(
                section__form=tax_return.form_definition,
                mapping_key=line7_key,
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

        # Create/update OtherDeduction rows
        # First clear previous TB-only imports (not standard rows)
        OtherDeduction.objects.filter(
            tax_return=tax_return, source="tb_import"
        ).delete()

        # Reset standard deduction amounts before re-importing
        OtherDeduction.objects.filter(
            tax_return=tax_return, source="standard"
        ).update(amount=Decimal("0.00"))

        # Build lookup of existing standard deductions for matching
        existing_standard = {
            d.description.lower().strip(): d
            for d in OtherDeduction.objects.filter(
                tax_return=tax_return, source="standard"
            )
        }

        other_ded_created = 0
        for idx, (desc, amt) in enumerate(other_ded_rows):
            if not amt:  # skip zero amounts
                continue
            # Try to match to an existing standard deduction
            match = existing_standard.get(desc.lower().strip())
            if match:
                match.amount = match.amount + amt.quantize(Decimal("0.01"))
                match.save(update_fields=["amount", "updated_at"])
            else:
                OtherDeduction.objects.create(
                    tax_return=tax_return,
                    description=desc,
                    amount=amt.quantize(Decimal("0.01")),
                    source="tb_import",
                    sort_order=1000 + idx,
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

    @action(detail=True, methods=["post"], url_path="populate-boy")
    def populate_boy(self, request, pk=None):
        """
        Populate Balance Sheet BOY values from prior year EOY.

        Useful when prior year data is imported after the return was
        already created.
        """
        tax_return = self.get_object()
        updated = _populate_boy_from_prior_year(tax_return)
        if updated == 0:
            # Check if PY data exists at all
            entity = tax_return.tax_year.entity
            prior_year_num = tax_return.tax_year.year - 1
            if not PriorYearReturn.objects.filter(
                entity=entity, year=prior_year_num
            ).exists():
                return Response(
                    {"error": "No prior year data found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
        return Response({"updated": updated})
