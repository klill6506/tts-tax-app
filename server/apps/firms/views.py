from rest_framework import viewsets, status
from rest_framework.response import Response

from .models import Preparer
from .permissions import IsFirmMember
from .serializers import PreparerSerializer, PreparerListSerializer


class PreparerViewSet(viewsets.ModelViewSet):
    """CRUD for firm-level preparers."""

    permission_classes = [IsFirmMember]

    def get_serializer_class(self):
        if self.action == "list":
            return PreparerListSerializer
        return PreparerSerializer

    def get_queryset(self):
        return Preparer.objects.filter(firm=self.request.firm)

    def perform_create(self, serializer):
        serializer.save(firm=self.request.firm)
