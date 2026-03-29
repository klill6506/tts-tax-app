from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from apps.audit.mixins import AuditViewSetMixin
from apps.firms.permissions import IsFirmMember

from .models import (
    Client,
    ClientEntityLink,
    Entity,
    EntityType,
    LinkRole,
    TaxYear,
)
from .serializers import (
    ClientEntityLinkCreateSerializer,
    ClientEntityLinkSerializer,
    ClientListSerializer,
    ClientReturnSerializer,
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

        # Auto-create an Individual entity + taxpayer link for new clients
        entity = Entity.objects.create(
            client=instance,
            name=instance.name,
            entity_type=EntityType.INDIVIDUAL,
            legal_name=instance.name,
        )
        ClientEntityLink.objects.create(
            client=instance,
            entity=entity,
            role=LinkRole.TAXPAYER,
            is_primary=True,
        )

        from apps.audit.service import log_create

        log_create(self.request, instance)
        return instance

    @action(detail=True, methods=["get"], url_path="returns")
    def client_returns(self, request, pk=None):
        """Return all tax returns/years for a client across all entities."""
        client = self.get_object()

        # 1. Direct entities (Entity.client = this client)
        direct_entity_ids = set(
            Entity.objects.filter(client=client).values_list("id", flat=True)
        )

        # 2. Linked entities (via ClientEntityLink)
        links = ClientEntityLink.objects.filter(
            client=client,
        ).exclude(
            entity_id__in=direct_entity_ids,  # avoid duplicates
        ).select_related("entity")

        linked_map = {}  # entity_id → (role, ownership_percentage)
        for link in links:
            linked_map[link.entity_id] = (
                link.role,
                link.ownership_percentage,
            )

        all_entity_ids = direct_entity_ids | set(linked_map.keys())

        # Fetch entities with their tax years + returns
        entities = Entity.objects.filter(
            id__in=all_entity_ids,
        ).prefetch_related(
            "tax_years__tax_returns__form_definition",
        ).order_by("name")

        rows = []
        for entity in entities:
            is_direct = entity.id in direct_entity_ids
            relationship = "direct"
            ownership = None
            if not is_direct and entity.id in linked_map:
                relationship = linked_map[entity.id][0]  # role name
                ownership = linked_map[entity.id][1]

            tax_years = entity.tax_years.all()
            if tax_years:
                for ty in tax_years:
                    # Get the federal return (the one without a federal_return parent)
                    federal = None
                    for tr in ty.tax_returns.all():
                        if tr.federal_return_id is None:
                            federal = tr
                            break
                    tax_return = federal
                    rows.append({
                        "entity_id": entity.id,
                        "entity_name": entity.name,
                        "entity_type": entity.entity_type,
                        "tax_year_id": ty.id,
                        "year": ty.year,
                        "tax_year_status": ty.status,
                        "return_id": tax_return.id if tax_return else None,
                        "form_code": (
                            tax_return.form_definition.code
                            if tax_return else None
                        ),
                        "return_status": (
                            tax_return.status if tax_return else None
                        ),
                        "relationship": relationship,
                        "ownership_percentage": ownership,
                    })
            else:
                # Entity with no tax years yet — still show it
                rows.append({
                    "entity_id": entity.id,
                    "entity_name": entity.name,
                    "entity_type": entity.entity_type,
                    "tax_year_id": None,
                    "year": None,
                    "tax_year_status": None,
                    "return_id": None,
                    "form_code": None,
                    "return_status": None,
                    "relationship": relationship,
                    "ownership_percentage": ownership,
                })

        serializer = ClientReturnSerializer(rows, many=True)
        return Response(serializer.data)


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
                | Q(tax_years__tax_returns__shareholders__linked_client_id=client_id)
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
        ).select_related("entity", "created_by").prefetch_related("tax_returns")
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
        # Default filing_states from entity's address state if not provided
        filing_states = serializer.validated_data.get("filing_states")
        if not filing_states:
            entity = serializer.validated_data["entity"]
            if entity.state:
                serializer.validated_data["filing_states"] = [entity.state.upper()]

        instance = serializer.save(created_by=self.request.user)
        from apps.audit.service import log_create

        log_create(self.request, instance)
        return instance
