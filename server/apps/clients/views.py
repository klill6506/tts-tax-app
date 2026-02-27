from rest_framework import filters, viewsets
from rest_framework.pagination import PageNumberPagination

from apps.audit.mixins import AuditViewSetMixin
from apps.firms.permissions import IsFirmMember

from .models import Client, ClientEntityLink, Entity, TaxYear
from .serializers import (
    ClientEntityLinkCreateSerializer,
    ClientEntityLinkSerializer,
    ClientListSerializer,
    ClientSerializer,
    EntityCreateSerializer,
    EntitySerializer,
    TaxYearCreateSerializer,
    TaxYearSerializer,
)


class ClientPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


class ClientViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    """CRUD for clients, scoped to the requesting user's firm."""

    permission_classes = [IsFirmMember]
    pagination_class = ClientPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name", "status", "created_at"]
    ordering = ["name"]

    def get_serializer_class(self):
        if self.action == "list":
            return ClientListSerializer
        return ClientSerializer

    def get_queryset(self):
        from django.db.models import Count
        from django.db.models.functions import Coalesce

        qs = Client.objects.filter(firm=self.request.firm)

        # Annotate entity_count so the list view doesn't need N+1 queries
        if self.action == "list":
            qs = qs.annotate(
                entity_count=Coalesce(Count("entities", distinct=True), 0),
            )

        return qs

    def perform_create(self, serializer):
        instance = serializer.save(firm=self.request.firm)
        from apps.audit.service import log_create

        log_create(self.request, instance)
        return instance


class EntityViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    """CRUD for entities, scoped to the requesting user's firm."""

    permission_classes = [IsFirmMember]

    def get_queryset(self):
        from django.db.models import Q

        qs = Entity.objects.filter(
            client__firm=self.request.firm
        ).select_related("client")
        # Optional filter by client — include directly-owned AND shareholder-linked
        client_id = self.request.query_params.get("client")
        if client_id:
            qs = qs.filter(
                Q(client_id=client_id)
                | Q(tax_years__tax_return__shareholders__linked_client_id=client_id)
            ).distinct()
        return qs

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return EntityCreateSerializer
        return EntitySerializer


class ClientEntityLinkViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    """CRUD for client↔entity associations, scoped to the requesting user's firm."""

    permission_classes = [IsFirmMember]

    def get_queryset(self):
        qs = ClientEntityLink.objects.filter(
            client__firm=self.request.firm
        ).select_related("client", "entity")
        # Filter by client or entity
        client_id = self.request.query_params.get("client")
        if client_id:
            qs = qs.filter(client_id=client_id)
        entity_id = self.request.query_params.get("entity")
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ClientEntityLinkCreateSerializer
        return ClientEntityLinkSerializer


class TaxYearViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    """CRUD for tax year containers, scoped to the requesting user's firm."""

    permission_classes = [IsFirmMember]

    def get_queryset(self):
        qs = TaxYear.objects.filter(
            entity__client__firm=self.request.firm
        ).select_related("entity", "created_by", "tax_return")
        # Optional filters
        entity_id = self.request.query_params.get("entity")
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        year = self.request.query_params.get("year")
        if year:
            qs = qs.filter(year=year)
        return qs

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return TaxYearCreateSerializer
        return TaxYearSerializer

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        from apps.audit.service import log_create

        log_create(self.request, instance)
        return instance
