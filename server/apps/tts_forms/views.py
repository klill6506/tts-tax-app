"""
API views for IRS form PDF generation.

Endpoints:
    POST /api/v1/tax-returns/{id}/render-pdf/
        Generate a PDF for a tax return using the official IRS template.

    POST /api/v1/tax-returns/{id}/render-pdf/
        Body (optional): {"statements": {"19": [{"description": "...", "amount": "..."}]}}
"""

import io

from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.firms.permissions import IsFirmMember
from apps.returns.models import TaxReturn

from .renderer import render_tax_return


class PDFRenderMixin:
    """
    Mixin that adds a `render_pdf` action to TaxReturnViewSet.

    Add this mixin to the TaxReturnViewSet class to enable PDF generation:

        class TaxReturnViewSet(PDFRenderMixin, AuditViewSetMixin, ...):
            ...
    """

    @action(detail=True, methods=["post"], url_path="render-pdf")
    def render_pdf(self, request, pk=None):
        """Generate a PDF for this tax return using the official IRS template."""
        tax_return = self.get_object()

        # Optional statement detail items from request body
        statement_items = None
        if request.data and "statements" in request.data:
            statement_items = request.data["statements"]
            if not isinstance(statement_items, dict):
                return Response(
                    {"error": "statements must be a dict mapping line_number to items list."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            pdf_bytes = render_tax_return(
                tax_return,
                statement_items=statement_items,
            )
        except FileNotFoundError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Build a meaningful filename
        entity_name = (
            tax_return.tax_year.entity.name
            .replace(" ", "_")
            .replace("/", "-")
        )
        year = tax_return.tax_year.year
        form_code = tax_return.form_definition.code
        filename = f"{form_code}_{entity_name}_{year}.pdf"

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
