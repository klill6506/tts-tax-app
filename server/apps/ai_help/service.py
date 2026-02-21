"""Google Gemini API wrapper for tax preparation help.

Supports two modes:
- **grounded**: Answers are based on official IRS instruction text extracted
  from downloaded PDFs. The full instruction text is included in the prompt.
- **broad**: General tax knowledge without instruction text constraints.
"""

import logging

from django.conf import settings

from .instruction_cache import get_instruction_text

logger = logging.getLogger(__name__)

GROUNDED_SYSTEM_PROMPT = (
    "You are a tax preparation expert assistant for a CPA firm. "
    "You have been given the OFFICIAL IRS instructions for the form the preparer "
    "is working on. Answer the question using ONLY the provided IRS instruction text. "
    "Cite specific line numbers, sections, or page references from the instructions "
    "when possible. If the instructions do not contain sufficient information to "
    "answer the question, clearly state that and suggest the preparer consult the "
    "full IRS publication or a licensed professional. "
    "Keep responses focused and practical for someone actively preparing returns."
)

BROAD_SYSTEM_PROMPT = (
    "You are a tax preparation expert assistant for a CPA firm. "
    "Provide concise, accurate guidance about IRS forms and tax concepts. "
    "Reference official IRS instructions and publications when possible. "
    "Do not give legal or accounting advice — instead, flag when the user "
    "should consult a licensed professional. "
    "Keep responses focused and practical for someone actively preparing returns."
)


def ask_gemini(
    question: str,
    form_code: str = "",
    section: str = "",
    mode: str = "grounded",
) -> str:
    """Send a question to Google Gemini and return the response text.

    Args:
        question: The user's question.
        form_code: IRS form code (e.g., "1120-S").
        section: Current form section (e.g., "Income & Ded.").
        mode: "grounded" for IRS instruction-based answers, "broad" for general.

    Returns a user-friendly message if the API key is not configured or
    if the API call fails.
    """
    api_key = getattr(settings, "GEMINI_API_KEY", "")
    if not api_key:
        return (
            "AI Help is not yet configured. To enable it, add your "
            "Google Gemini API key to the server .env file as GEMINI_API_KEY. "
            "You can get a free key at https://ai.google.dev/"
        )

    try:
        from google import genai  # type: ignore

        client = genai.Client(api_key=api_key)

        # Build context line
        context_parts = []
        if form_code:
            context_parts.append(f"The preparer is working on IRS Form {form_code}.")
        if section:
            context_parts.append(f"They are in the '{section}' section of the form.")
        context = " ".join(context_parts)

        # Choose system prompt and optionally load instruction text
        instruction_text = None
        if mode == "grounded" and form_code:
            instruction_text = get_instruction_text(form_code)

        if instruction_text:
            # Grounded mode with instructions available
            prompt_parts = [
                GROUNDED_SYSTEM_PROMPT,
                "",
                f"--- BEGIN IRS INSTRUCTIONS FOR FORM {form_code} ---",
                instruction_text,
                f"--- END IRS INSTRUCTIONS FOR FORM {form_code} ---",
                "",
                context,
                "",
                f"Question: {question}",
            ]
        else:
            # Broad mode, or grounded mode with no instructions available
            system_prompt = BROAD_SYSTEM_PROMPT
            if mode == "grounded" and form_code and not instruction_text:
                # Wanted grounded but instructions not available — note this
                system_prompt += (
                    " Note: IRS instruction text is not available for this form. "
                    "Answer from your general tax knowledge."
                )
            prompt_parts = [
                system_prompt,
                "",
                context,
                "",
                f"Question: {question}",
            ]

        full_prompt = "\n".join(prompt_parts)

        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=full_prompt,
        )
        return response.text

    except ImportError:
        logger.warning("google-genai package not installed")
        return (
            "The Google GenAI package is not installed. "
            "Run: poetry add google-genai"
        )
    except Exception as e:
        logger.exception("Gemini API error")
        return f"AI Help encountered an error: {str(e)}"
