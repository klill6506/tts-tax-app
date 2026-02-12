from rest_framework import viewsets

from apps.audit.mixins import AuditViewSetMixin
from apps.firms.permissions import IsFirmMember

from .models import Client, Entity, TaxYear
from .serializers import (
    ClientSerializer,
    EntityCreateSerializer,
    EntitySerializer,
    TaxYearCreateSerializer,
    TaxYearSerializer,
)


class ClientViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    """CRUD for clients, scoped to the requesting user's firm."""

    permission_classes = [IsFirmMember]
    serializer_class = ClientSerializer

    def get_queryset(self):
        return Client.objects.filter(firm=self.request.firm)

    def perform_create(self, serializer):
        instance = serializer.save(firm=self.request.firm)
        from apps.audit.service import log_create

        log_create(self.request, instance)
        return instance


class EntityViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    """CRUD for entities, scoped to the requesting user's firm."""

    permission_classes = [IsFirmMember]

    def get_queryset(self):
        qs = Entity.objects.filter(
            client__firm=self.request.firm
        ).select_related("client")
        # Optional filter by client
        client_id = self.request.query_params.get("client")
        if client_id:
            qs = qs.filter(client_id=client_id)
        return qs

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return EntityCreateSerializer
        return EntitySerializer


class TaxYearViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    """CRUD for tax year containers, scoped to the requesting user's firm."""

    permission_classes = [IsFirmMember]

    def get_queryset(self):
        qs = TaxYear.objects.filter(
            entity__client__firm=self.request.firm
        ).select_related("entity", "created_by")
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
