"""
Mixin for DRF viewsets to automatically audit create/update/delete.

Usage:
    class ClientViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
        ...
"""

from apps.audit.service import log_create, log_delete, log_update, snapshot


class AuditViewSetMixin:
    """Drop into any ModelViewSet to get automatic audit logging."""

    def perform_create(self, serializer):
        instance = serializer.save()
        log_create(self.request, instance)
        return instance

    def perform_update(self, serializer):
        old_snap = snapshot(serializer.instance)
        instance = serializer.save()
        log_update(self.request, instance, old_snap)
        return instance

    def perform_destroy(self, instance):
        log_delete(self.request, instance)
        instance.delete()
