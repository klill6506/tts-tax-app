from rest_framework import serializers

from .models import Employer, EmployerStateAccount


class EmployerStateAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployerStateAccount
        fields = ("id", "state", "state_id_number", "verified")


class EmployerSerializer(serializers.ModelSerializer):
    """Employer payload returned by the autofill lookup endpoint.

    Includes a nested list of state withholding accounts (one row per state
    the employer has an account in). Empty list is the common case for
    bulk-imported employers; the list grows via the W-2 entry learning loop.
    """

    state_accounts = EmployerStateAccountSerializer(many=True, read_only=True)

    class Meta:
        model = Employer
        fields = (
            "id", "ein", "name", "street", "city", "state", "zip",
            "source", "verified", "parse_warning",
            "state_accounts",
        )
