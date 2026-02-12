from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializers import MeSerializer


@api_view(["GET"])
def me(request):
    """Return the current user's profile, firm(s), and role(s)."""
    user = request.user
    # Attach active memberships for the serializer
    user.active_memberships = user.firm_memberships.filter(
        is_active=True
    ).select_related("firm")
    serializer = MeSerializer(user)
    return Response({"data": serializer.data})
