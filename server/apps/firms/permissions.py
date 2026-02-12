from rest_framework.permissions import BasePermission


class IsFirmMember(BasePermission):
    """
    Allow access only to authenticated users who have an active firm membership.
    The FirmMiddleware must run first to set request.firm.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request, "firm", None) is not None
        )
