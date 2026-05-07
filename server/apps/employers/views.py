"""DRF views for the employer database — autofill lookup."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.firms.permissions import IsFirmMember

from .models import Employer
from .parsers import parse_ein
from .serializers import EmployerSerializer


class EmployerLookupView(APIView):
    """GET /api/v1/employers/lookup/?ein=XX-XXXXXXX

    Backs the W-2 entry autofill flow. The frontend calls this on EIN-blur;
    a 200 response populates name + address fields (yellow / "imported"
    color per the data-entry color convention), 404 lets the preparer
    enter a fresh record, and 400 surfaces a malformed-EIN validation
    error on the EIN field itself.

    Returned payload (200):
        {
          "id": "<uuid>",
          "ein": "XX-XXXXXXX",
          "name": "...",
          "street": "...",
          "city": "...",
          "state": "GA",
          "zip": "30303",
          "source": "taxwise_import" | "user_entered",
          "verified": false,
          "parse_warning": "...",
          "state_accounts": [
            {"id": "...", "state": "GA", "state_id_number": "...", "verified": false},
            ...
          ]
        }
    """

    permission_classes = [IsFirmMember]

    def get(self, request):
        raw_ein = request.query_params.get("ein", "")
        canonical_ein = parse_ein(raw_ein)
        if canonical_ein is None:
            return Response(
                {"error": "Invalid EIN format. Expected XX-XXXXXXX or 9 digits."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            employer = (
                Employer.objects
                .prefetch_related("state_accounts")
                .get(ein=canonical_ein)
            )
        except Employer.DoesNotExist:
            return Response(
                {"error": f"Employer with EIN {canonical_ein} not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(EmployerSerializer(employer).data)
