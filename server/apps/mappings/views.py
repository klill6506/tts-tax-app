from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.audit.mixins import AuditViewSetMixin
from apps.firms.permissions import IsFirmMember
from apps.imports.models import TrialBalanceUpload

from .engine import apply_template, resolve_template
from .models import MappingRule, MappingTemplate
from .serializers import (
    ApplyMappingSerializer,
    MappedRowSerializer,
    MappingRuleCreateSerializer,
    MappingRuleSerializer,
    MappingTemplateCreateSerializer,
    MappingTemplateSerializer,
)


class MappingTemplateViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    permission_classes = [IsFirmMember]

    def get_queryset(self):
        return MappingTemplate.objects.filter(
            firm=self.request.firm
        ).select_related("client").prefetch_related("rules")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return MappingTemplateCreateSerializer
        return MappingTemplateSerializer

    def perform_create(self, serializer):
        client = serializer.validated_data.pop("client", None)
        instance = serializer.save(firm=self.request.firm, client=client)
        from apps.audit.service import log_create
        log_create(self.request, instance)
        return instance

    @action(detail=False, methods=["post"], url_path="apply")
    def apply_mapping(self, request):
        """Apply a mapping template to a TB upload and return classified rows."""
        ser = ApplyMappingSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        # Validate upload belongs to firm
        try:
            upload = TrialBalanceUpload.objects.get(
                id=ser.validated_data["upload"],
                tax_year__entity__client__firm=request.firm,
            )
        except TrialBalanceUpload.DoesNotExist:
            return Response(
                {"error": "Upload not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Resolve template
        template_id = ser.validated_data.get("template")
        if template_id:
            try:
                template = MappingTemplate.objects.get(
                    id=template_id, firm=request.firm
                )
            except MappingTemplate.DoesNotExist:
                return Response(
                    {"error": "Template not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            # Auto-resolve: client-specific > firm default
            client = upload.tax_year.entity.client
            template = resolve_template(request.firm, client)
            if not template:
                return Response(
                    {"error": "No mapping template found for this client or firm."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        mapped = apply_template(template, upload)
        out = MappedRowSerializer(mapped, many=True)
        return Response({
            "template_id": str(template.id),
            "template_name": template.name,
            "total_rows": len(mapped),
            "mapped_rows": sum(1 for r in mapped if r.target_line),
            "unmapped_rows": sum(1 for r in mapped if not r.target_line),
            "rows": out.data,
        })


class MappingRuleViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    permission_classes = [IsFirmMember]

    def get_queryset(self):
        qs = MappingRule.objects.filter(
            template__firm=self.request.firm
        ).select_related("template")
        template_id = self.request.query_params.get("template")
        if template_id:
            qs = qs.filter(template_id=template_id)
        return qs

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return MappingRuleCreateSerializer
        return MappingRuleSerializer
