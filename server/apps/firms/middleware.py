from apps.firms.models import FirmMembership


class FirmMiddleware:
    """
    Attach the current user's active firm to request.firm.

    Phase 1: users belong to one firm, so we pick their first active
    membership. If no membership exists, request.firm is None.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.firm = None
        request.firm_membership = None

        if hasattr(request, "user") and request.user.is_authenticated:
            membership = (
                FirmMembership.objects.filter(
                    user=request.user,
                    is_active=True,
                )
                .select_related("firm")
                .first()
            )
            if membership:
                request.firm = membership.firm
                request.firm_membership = membership

        return self.get_response(request)
