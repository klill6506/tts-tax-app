"""IRS instruction PDF text extraction with LRU cache.

Extracts full text from IRS instruction PDFs using pdfplumber and caches
the results in memory for the lifetime of the Django process. The first
query for a given form triggers PDF parsing (~1-2 seconds for a 40-page
document); subsequent queries return instantly from cache.
"""

import logging
from functools import lru_cache
from pathlib import Path

import pdfplumber  # type: ignore
from django.conf import settings

logger = logging.getLogger(__name__)

# Maps form_code → instruction PDF filename.
# K-1 codes map to their parent form's instruction booklet.
INSTRUCTION_FILES: dict[str, str] = {
    "1120-S": "i1120s.pdf",
    "1120-S-K1": "i1120s.pdf",
    "1065": "i1065.pdf",
    "1065-K1": "i1065.pdf",
    "1120": "i1120.pdf",
}


def _get_instruction_pdf_path(form_code: str, tax_year: int = 2025) -> Path | None:
    """Resolve the file path for an instruction PDF, or None if unknown/missing."""
    filename = INSTRUCTION_FILES.get(form_code)
    if not filename:
        return None

    pdf_path = Path(settings.IRS_FORMS_DIR) / str(tax_year) / filename
    if not pdf_path.exists():
        logger.warning("Instruction PDF not found: %s", pdf_path)
        return None

    return pdf_path


@lru_cache(maxsize=8)
def get_instruction_text(form_code: str, tax_year: int = 2025) -> str | None:
    """Extract the full text of an IRS instruction PDF.

    Returns None if the form code is unknown, the PDF is missing, or
    text extraction fails. Results are cached in memory.
    """
    pdf_path = _get_instruction_pdf_path(form_code, tax_year)
    if pdf_path is None:
        return None

    try:
        pages_text = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text)

        if not pages_text:
            logger.warning("No text extracted from %s", pdf_path)
            return None

        full_text = "\n\n".join(pages_text)
        logger.info(
            "Extracted %d chars from %d pages of %s",
            len(full_text),
            len(pages_text),
            pdf_path.name,
        )
        return full_text

    except Exception:
        logger.exception("Failed to extract text from %s", pdf_path)
        return None


def clear_cache() -> None:
    """Clear the instruction text cache (useful for tests and PDF updates)."""
    get_instruction_text.cache_clear()
