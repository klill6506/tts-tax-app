from django.contrib.auth import authenticate, login, logout
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
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


def _user_payload(user):
    """Build the standard user+memberships response dict."""
    user.active_memberships = user.firm_memberships.filter(
        is_active=True
    ).select_related("firm")
    return MeSerializer(user).data


@api_view(["POST"])
@permission_classes([AllowAny])
def auth_login(request):
    """Authenticate and start a session. Returns user profile on success."""
    username = request.data.get("username", "")
    password = request.data.get("password", "")

    if not username or not password:
        return Response(
            {"error": "Username and password are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = authenticate(request, username=username, password=password)
    if user is None:
        return Response(
            {"error": "Invalid credentials."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    login(request, user)
    return Response({"data": _user_payload(user)})


@api_view(["POST"])
def auth_logout(request):
    """End the current session."""
    logout(request)
    return Response({"data": "Logged out."})
