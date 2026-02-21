from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status

from apps.firms.permissions import IsFirmMember

from .models import HelpQuery
from .service import ask_gemini


@api_view(["POST"])
@permission_classes([IsFirmMember])
def ask(request):
    """Handle an AI help question.

    Expects JSON: { "question": "...", "form_code": "1120-S", "section": "Income" }
    Returns: { "answer": "..." }
    """
    question = (request.data.get("question") or "").strip()
    if not question:
        return Response(
            {"error": "Question is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    form_code = request.data.get("form_code", "")
    section = request.data.get("section", "")
    mode = request.data.get("mode", "grounded")
    if mode not in ("grounded", "broad"):
        mode = "grounded"

    # Call Gemini
    answer = ask_gemini(
        question, form_code=form_code, section=section, mode=mode
    )

    # Save audit trail
    HelpQuery.objects.create(
        user=request.user,
        firm=request.firm,
        form_code=form_code,
        section=section,
        question=question,
        response=answer,
        mode=mode,
    )

    return Response({"answer": answer, "mode": mode})
