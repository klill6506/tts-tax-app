from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response

from apps.clients.models import TaxYear
from apps.firms.permissions import IsFirmMember

from .models import DiagnosticRule, DiagnosticRun
from .runner import run_diagnostics
from .serializers import (
    DiagnosticRuleSerializer,
    DiagnosticRunSerializer,
    RunDiagnosticsSerializer,
)


class DiagnosticRuleViewSet(
    ListModelMixin, RetrieveModelMixin, viewsets.GenericViewSet
):
    """Read-only list of available diagnostic rules."""

    permission_classes = [IsFirmMember]
    serializer_class = DiagnosticRuleSerializer
    queryset = DiagnosticRule.objects.filter(is_active=True)


class DiagnosticRunViewSet(
    ListModelMixin, RetrieveModelMixin, viewsets.GenericViewSet
):
    """View past diagnostic runs. Use the 'run' action to start a new one."""

    permission_classes = [IsFirmMember]
    serializer_class = DiagnosticRunSerializer

    def get_queryset(self):
        qs = DiagnosticRun.objects.filter(
            tax_year__entity__client__firm=self.request.firm
        ).select_related("run_by").prefetch_related("findings__rule")
        tax_year_id = self.request.query_params.get("tax_year")
        if tax_year_id:
            qs = qs.filter(tax_year_id=tax_year_id)
        return qs

    @action(detail=False, methods=["post"], url_path="run")
    def run(self, request):
        """Run all active diagnostic rules against a tax year."""
        ser = RunDiagnosticsSerializer(data=request.data)
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

        diagnostic_run = run_diagnostics(tax_year, run_by=request.user)

        return Response(
            DiagnosticRunSerializer(diagnostic_run).data,
            status=status.HTTP_201_CREATED,
        )
