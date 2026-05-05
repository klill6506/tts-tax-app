from django.db.models import Count, Max, Q, Sum
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from apps.audit.mixins import AuditViewSetMixin
from apps.audit.service import log_create, log_delete
from apps.clients.models import Entity
from apps.firms.permissions import IsFirmMember

from .models import ClientDocument
from .serializers import (
    ClientDocumentSerializer,
    ClientDocumentUploadSerializer,
    EntityDocumentSummarySerializer,
)


class DocumentPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


class ClientDocumentViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    permission_classes = [IsFirmMember]
    pagination_class = DocumentPagination
    serializer_class = ClientDocumentSerializer

    def get_queryset(self):
        qs = ClientDocument.objects.filter(
            firm=self.request.firm
        ).select_related("client", "entity", "uploaded_by")

        entity_id = self.request.query_params.get("entity")
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        client_id = self.request.query_params.get("client")
        if client_id:
            qs = qs.filter(client_id=client_id)
        entity_type = self.request.query_params.get("entity_type")
        if entity_type:
            qs = qs.filter(entity__entity_type=entity_type)
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)
        tax_year = self.request.query_params.get("tax_year")
        if tax_year:
            qs = qs.filter(tax_year=tax_year)
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(filename__icontains=search)
                | Q(entity__name__icontains=search)
                | Q(client__name__icontains=search)
                | Q(notes__icontains=search)
            )
        ordering = self.request.query_params.get("ordering", "-created_at")
        allowed = {"created_at", "-created_at", "filename", "-filename", "category", "-category"}
        if ordering in allowed:
            qs = qs.order_by(ordering)
        return qs

    @action(detail=False, methods=["post"], url_path="upload")
    def upload(self, request):
        ser = ClientDocumentUploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            entity = Entity.objects.select_related("client").get(
                id=ser.validated_data["entity"],
                client__firm=request.firm,
            )
        except Entity.DoesNotExist:
            return Response(
                {"error": "Entity not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        uploaded_file = ser.validated_data["file"]

        doc = ClientDocument.objects.create(
            firm=request.firm,
            client=entity.client,
            entity=entity,
            file=uploaded_file,
            filename=uploaded_file.name,
            file_size=uploaded_file.size,
            content_type=getattr(uploaded_file, "content_type", ""),
            category=ser.validated_data.get("category", "other"),
            tax_year=ser.validated_data.get("tax_year"),
            notes=ser.validated_data.get("notes", ""),
            uploaded_by=request.user,
        )
        log_create(request, doc)

        return Response(
            ClientDocumentSerializer(doc).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"], url_path="folders")
    def folders(self, request):
        """Entity-level folder summaries with document counts."""
        base_qs = Entity.objects.filter(
            client__firm=request.firm
        ).select_related("client")

        search = request.query_params.get("search")
        if search:
            base_qs = base_qs.filter(
                Q(name__icontains=search)
                | Q(client__name__icontains=search)
                | Q(ein__icontains=search)
            )

        # Entity type counts (before type filter, after search)
        counts = {"all": base_qs.count()}
        for et in ["scorp", "partnership", "ccorp", "trust", "individual"]:
            counts[et] = base_qs.filter(entity_type=et).count()

        # Apply entity_type filter after counts
        entity_type = request.query_params.get("entity_type")
        if entity_type:
            base_qs = base_qs.filter(entity_type=entity_type)

        # Annotate with document stats
        qs = base_qs.annotate(
            document_count=Count("documents"),
            last_upload=Max("documents__created_at"),
            total_size=Sum("documents__file_size"),
        )

        ordering = request.query_params.get("ordering", "name")
        allowed = {"name", "-name", "-document_count", "document_count", "-last_upload"}
        if ordering in allowed:
            qs = qs.order_by(ordering)
        else:
            qs = qs.order_by("name")

        paginator = DocumentPagination()
        page = paginator.paginate_queryset(qs, request)

        rows = [
            {
                "entity_id": e.id,
                "entity_name": e.name,
                "entity_type": e.entity_type,
                "ein": e.ein or "",
                "client_id": e.client_id,
                "client_name": e.client.name,
                "document_count": e.document_count,
                "last_upload": e.last_upload,
                "total_size": e.total_size or 0,
            }
            for e in page
        ]

        ser = EntityDocumentSummarySerializer(rows, many=True)
        response = paginator.get_paginated_response(ser.data)
        response.data["counts"] = counts
        return response

    def perform_destroy(self, instance):
        log_delete(self.request, instance)
        instance.file.delete(save=False)
        instance.delete()
