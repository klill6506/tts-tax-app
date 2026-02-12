from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response

from apps.audit.service import log_create
from apps.clients.models import TaxYear
from apps.firms.permissions import IsFirmMember

from .models import TrialBalanceRow, TrialBalanceUpload, UploadStatus
from .parsers import ParseError, parse_file
from .serializers import (
    TrialBalanceRowSerializer,
    TrialBalanceUploadCreateSerializer,
    TrialBalanceUploadSerializer,
)


class TrialBalanceUploadViewSet(
    ListModelMixin, RetrieveModelMixin, viewsets.GenericViewSet
):
    """List and view TB uploads. Use the upload action to add new ones."""

    permission_classes = [IsFirmMember]
    serializer_class = TrialBalanceUploadSerializer

    def get_queryset(self):
        qs = TrialBalanceUpload.objects.filter(
            tax_year__entity__client__firm=self.request.firm
        ).select_related("uploaded_by", "tax_year")
        tax_year_id = self.request.query_params.get("tax_year")
        if tax_year_id:
            qs = qs.filter(tax_year_id=tax_year_id)
        return qs

    @action(detail=False, methods=["post"], url_path="upload")
    def upload(self, request):
        """Upload and parse a Trial Balance file (CSV or XLSX)."""
        serializer = TrialBalanceUploadCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Validate tax year belongs to the user's firm
        tax_year_id = serializer.validated_data["tax_year"]
        try:
            tax_year = TaxYear.objects.get(
                id=tax_year_id,
                entity__client__firm=request.firm,
            )
        except TaxYear.DoesNotExist:
            return Response(
                {"error": "Tax year not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        uploaded_file = serializer.validated_data["file"]

        # Create the upload record
        upload = TrialBalanceUpload.objects.create(
            tax_year=tax_year,
            original_filename=uploaded_file.name,
            file=uploaded_file,
            uploaded_by=request.user,
            status=UploadStatus.PENDING,
        )

        # Parse the file
        try:
            uploaded_file.seek(0)
            parsed_rows = parse_file(uploaded_file)
        except ParseError as e:
            upload.status = UploadStatus.FAILED
            upload.error_message = str(e)
            upload.save()
            return Response(
                TrialBalanceUploadSerializer(upload).data,
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        # Store parsed rows
        row_objects = [
            TrialBalanceRow(
                upload=upload,
                row_number=idx + 1,
                account_number=row["account_number"],
                account_name=row["account_name"],
                debit=row["debit"],
                credit=row["credit"],
                raw_data=row["raw_data"],
            )
            for idx, row in enumerate(parsed_rows)
        ]
        TrialBalanceRow.objects.bulk_create(row_objects)

        upload.status = UploadStatus.PARSED
        upload.row_count = len(row_objects)
        upload.save()

        log_create(request, upload)

        return Response(
            TrialBalanceUploadSerializer(upload).data,
            status=status.HTTP_201_CREATED,
        )


class TrialBalanceRowViewSet(
    ListModelMixin, RetrieveModelMixin, viewsets.GenericViewSet
):
    """Read-only access to parsed TB rows."""

    permission_classes = [IsFirmMember]
    serializer_class = TrialBalanceRowSerializer

    def get_queryset(self):
        qs = TrialBalanceRow.objects.filter(
            upload__tax_year__entity__client__firm=self.request.firm
        )
        upload_id = self.request.query_params.get("upload")
        if upload_id:
            qs = qs.filter(upload_id=upload_id)
        return qs
