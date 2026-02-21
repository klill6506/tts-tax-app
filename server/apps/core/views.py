from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    """Unauthenticated health check for monitoring / load balancers."""
    return Response({"status": "ok"})


@api_view(["GET"])
@permission_classes([AllowAny])
def version(request):
    """Return the current app version. Unauthenticated so the client can
    display it in the About dialog before/without login."""
    return Response({"version": settings.APP_VERSION})
