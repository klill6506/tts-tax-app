from rest_framework import viewsets
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin

from apps.firms.permissions import IsFirmMember

from .models import AuditEntry
from .serializers import AuditEntrySerializer


class AuditEntryViewSet(
    ListModelMixin, RetrieveModelMixin, viewsets.GenericViewSet
):
    """Read-only audit log, scoped to the requesting user's firm."""

    permission_classes = [IsFirmMember]
    serializer_class = AuditEntrySerializer

    def get_queryset(self):
        qs = AuditEntry.objects.filter(
            firm=self.request.firm
        ).select_related("actor")
        # Optional filters
        model_name = self.request.query_params.get("model")
        if model_name:
            qs = qs.filter(model_name__icontains=model_name)
        record_id = self.request.query_params.get("record")
        if record_id:
            qs = qs.filter(record_id=record_id)
        action = self.request.query_params.get("action")
        if action:
            qs = qs.filter(action=action)
        return qs
