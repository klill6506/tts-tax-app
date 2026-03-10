"""
API views for IRS form PDF generation.

Endpoints:
    POST /api/v1/tax-returns/{id}/render-pdf/
        Generate a PDF for a tax return using the official IRS template.

    POST /api/v1/tax-returns/{id}/render-k1s/
        Generate all Schedule K-1 PDFs concatenated into one document.

    POST /api/v1/tax-returns/{id}/render-k1/{sh_id}/
        Generate a single K-1 for one shareholder.

    POST /api/v1/tax-returns/{id}/render-7206/{sh_id}/
        Generate Form 7206 for one shareholder.

    POST /api/v1/tax-returns/{id}/render-1125a/
        Generate Form 1125-A (Cost of Goods Sold).

    POST /api/v1/tax-returns/{id}/render-8825/
        Generate Form 8825 (Rental Real Estate).

    POST /api/v1/tax-returns/{id}/render-7004/
        Generate Form 7004 (Extension).
"""

import io

from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.firms.permissions import IsFirmMember
from apps.returns.models import Shareholder, TaxReturn

from .renderer import (
    PRINT_PACKAGES,
    render_1125a,
    render_7004,
    render_8825,
    render_all_k1s,
    render_complete_return,
    render_k1,
    render_tax_return,
)
from .invoice import render_invoice
from .letter import render_letter


class PDFRenderMixin:
    """
    Mixin that adds PDF rendering actions to TaxReturnViewSet.

    Add this mixin to the TaxReturnViewSet class to enable PDF generation:

        class TaxReturnViewSet(PDFRenderMixin, AuditViewSetMixin, ...):
            ...
    """

    @action(detail=True, methods=["post"], url_path="render-pdf")
    def render_pdf(self, request, pk=None):
        """Generate a PDF for this tax return using the official IRS template."""
        from apps.returns.compute import compute_return

        tax_return = self.get_object()

        # Ensure all computed fields are up-to-date before rendering
        compute_return(tax_return)

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

    # ------------------------------------------------------------------
    # Schedule K-1 rendering
    # ------------------------------------------------------------------

    @action(detail=True, methods=["post"], url_path="render-k1s")
    def render_k1s(self, request, pk=None):
        """Generate all Schedule K-1 PDFs for this tax return."""
        from apps.returns.compute import compute_return

        tax_return = self.get_object()
        compute_return(tax_return)

        form_code = tax_return.form_definition.code
        if form_code not in ("1120-S",):
            return Response(
                {"error": f"K-1 generation not yet supported for {form_code}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            pdf_bytes = render_all_k1s(tax_return)
        except FileNotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        entity_name = (
            tax_return.tax_year.entity.name
            .replace(" ", "_")
            .replace("/", "-")
        )
        year = tax_return.tax_year.year
        filename = f"K-1s_{entity_name}_{year}.pdf"

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @action(
        detail=True,
        methods=["post"],
        url_path="render-k1/(?P<sh_id>[^/.]+)",
    )
    def render_k1_single(self, request, pk=None, sh_id=None):
        """Generate a single K-1 PDF for one shareholder."""
        from apps.returns.compute import compute_return

        tax_return = self.get_object()
        compute_return(tax_return)
        try:
            sh = Shareholder.objects.get(id=sh_id, tax_return=tax_return)
        except Shareholder.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            pdf_bytes = render_k1(tax_return, sh)
        except FileNotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        sh_name = sh.name.replace(" ", "_").replace("/", "-")
        year = tax_return.tax_year.year
        filename = f"K-1_{sh_name}_{year}.pdf"

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    # ------------------------------------------------------------------
    # Form 7206 rendering
    # ------------------------------------------------------------------

    @action(
        detail=True,
        methods=["post"],
        url_path="render-7206/(?P<sh_id>[^/.]+)",
    )
    def render_7206(self, request, pk=None, sh_id=None):
        """Generate Form 7206 (Self-Employed Health Insurance) for one shareholder."""
        tax_return = self.get_object()
        try:
            sh = Shareholder.objects.get(id=sh_id, tax_return=tax_return)
        except Shareholder.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if not sh.health_insurance_premium or sh.health_insurance_premium <= 0:
            return Response(
                {"error": "No health insurance premium recorded for this shareholder."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from .renderer import render_7206 as do_render_7206
            pdf_bytes = do_render_7206(tax_return, sh)
        except FileNotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except (ValueError, ImportError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        sh_name = sh.name.replace(" ", "_").replace("/", "-")
        year = tax_return.tax_year.year
        filename = f"7206_{sh_name}_{year}.pdf"

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    # ------------------------------------------------------------------
    # Form 1125-A rendering (Cost of Goods Sold)
    # ------------------------------------------------------------------

    @action(detail=True, methods=["post"], url_path="render-1125a")
    def render_1125a(self, request, pk=None):
        """Generate Form 1125-A (Cost of Goods Sold) for this tax return."""
        tax_return = self.get_object()

        try:
            pdf_bytes = render_1125a(tax_return)
        except FileNotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        entity_name = (
            tax_return.tax_year.entity.name
            .replace(" ", "_")
            .replace("/", "-")
        )
        year = tax_return.tax_year.year
        filename = f"1125-A_{entity_name}_{year}.pdf"

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    # ------------------------------------------------------------------
    # Form 8825 rendering (Rental Real Estate)
    # ------------------------------------------------------------------

    @action(detail=True, methods=["post"], url_path="render-8825")
    def render_8825(self, request, pk=None):
        """Generate Form 8825 (Rental Real Estate) for this tax return."""
        tax_return = self.get_object()

        try:
            pdf_bytes = render_8825(tax_return)
        except FileNotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        entity_name = (
            tax_return.tax_year.entity.name
            .replace(" ", "_")
            .replace("/", "-")
        )
        year = tax_return.tax_year.year
        filename = f"8825_{entity_name}_{year}.pdf"

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    # ------------------------------------------------------------------
    # Form 7203 rendering (Shareholder Stock and Debt Basis Limitations)
    # ------------------------------------------------------------------

    @action(
        detail=True,
        methods=["post"],
        url_path="render-7203/(?P<sh_id>[^/.]+)",
    )
    def render_7203(self, request, pk=None, sh_id=None):
        """Generate Form 7203 for one shareholder."""
        from apps.returns.compute import compute_return

        tax_return = self.get_object()
        try:
            sh = Shareholder.objects.get(id=sh_id, tax_return=tax_return)
        except Shareholder.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Ensure K-line values are fresh before computing 7203
        compute_return(tax_return)

        try:
            from .renderer import render_7203 as do_render_7203
            pdf_bytes = do_render_7203(tax_return, sh)
        except FileNotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        sh_name = sh.name.replace(" ", "_").replace("/", "-")
        year = tax_return.tax_year.year
        filename = f"7203_{sh_name}_{year}.pdf"

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @action(detail=True, methods=["post"], url_path="render-7203s")
    def render_7203s(self, request, pk=None):
        """Generate all Form 7203s for this return, concatenated."""
        from apps.returns.compute import compute_return

        tax_return = self.get_object()

        form_code = tax_return.form_definition.code
        if form_code not in ("1120-S",):
            return Response(
                {"error": f"7203 generation not supported for {form_code}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Ensure K-line values are fresh before computing 7203
        compute_return(tax_return)

        try:
            from .renderer import render_all_7203s
            pdf_bytes = render_all_7203s(tax_return)
        except FileNotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        entity_name = (
            tax_return.tax_year.entity.name
            .replace(" ", "_")
            .replace("/", "-")
        )
        year = tax_return.tax_year.year
        filename = f"7203s_{entity_name}_{year}.pdf"

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    # ------------------------------------------------------------------
    # Form 7004 rendering (Extension)
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Complete return rendering (all forms combined)
    # ------------------------------------------------------------------

    @action(detail=True, methods=["post"], url_path="render-complete")
    def render_complete(self, request, pk=None):
        """Generate forms for this return as one continuous PDF.

        Accepts optional `package` query param:
            client, filing, extension, state, k1s, invoice, letter
        """
        from apps.returns.compute import compute_return

        tax_return = self.get_object()
        package = request.query_params.get("package")

        # Ensure all computed fields (M-2, totals, etc.) are up-to-date
        compute_return(tax_return)

        if package and package not in PRINT_PACKAGES:
            return Response(
                {"error": f"Invalid package: {package!r}. Valid: {', '.join(PRINT_PACKAGES)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            pdf_bytes = render_complete_return(tax_return, package=package)
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        entity_name = (
            tax_return.tax_year.entity.name
            .replace(" ", "_")
            .replace("/", "-")
        )
        year = tax_return.tax_year.year
        form_code = tax_return.form_definition.code

        if package:
            label = PRINT_PACKAGES[package].replace(" ", "")
            filename = f"{form_code}_{label}_{entity_name}_{year}.pdf"
        else:
            filename = f"{form_code}_Complete_{entity_name}_{year}.pdf"

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    # ------------------------------------------------------------------
    # Invoice rendering
    # ------------------------------------------------------------------

    @action(detail=True, methods=["post"], url_path="render-invoice")
    def render_invoice_pdf(self, request, pk=None):
        """Generate an invoice PDF for this tax return."""
        tax_return = self.get_object()
        try:
            pdf_bytes = render_invoice(tax_return)
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        entity_name = (
            tax_return.tax_year.entity.name
            .replace(" ", "_")
            .replace("/", "-")
        )
        year = tax_return.tax_year.year
        filename = f"Invoice_{entity_name}_{year}.pdf"

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    # ------------------------------------------------------------------
    # Client Letter rendering
    # ------------------------------------------------------------------

    @action(detail=True, methods=["post"], url_path="render-letter")
    def render_letter_pdf(self, request, pk=None):
        """Generate a client transmittal letter PDF for this tax return."""
        tax_return = self.get_object()
        try:
            pdf_bytes = render_letter(tax_return)
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        entity_name = (
            tax_return.tax_year.entity.name
            .replace(" ", "_")
            .replace("/", "-")
        )
        year = tax_return.tax_year.year
        filename = f"Letter_{entity_name}_{year}.pdf"

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    # ------------------------------------------------------------------
    # Form 7004 rendering (Extension)
    # ------------------------------------------------------------------

    @action(detail=True, methods=["post"], url_path="render-7004")
    def render_7004_pdf(self, request, pk=None):
        """Generate Form 7004 (Extension) for this tax return."""
        tax_return = self.get_object()

        try:
            pdf_bytes = render_7004(tax_return)
        except FileNotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        entity_name = (
            tax_return.tax_year.entity.name
            .replace(" ", "_")
            .replace("/", "-")
        )
        year = tax_return.tax_year.year
        filename = f"7004_{entity_name}_{year}.pdf"

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
