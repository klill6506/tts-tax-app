"""Check page 1 of K-1 PDF."""
import pdfplumber
from pathlib import Path

pdf_path = Path(__file__).resolve().parent.parent.parent / "resources" / "irs_forms" / "2025" / "f1120ssk.pdf"

with pdfplumber.open(str(pdf_path)) as pdf:
    print(f"Total pages: {len(pdf.pages)}")
    if len(pdf.pages) > 1:
        page = pdf.pages[1]
        print(f"\nPAGE 1 — {page.width} x {page.height}")
        words = page.extract_words(keep_blank_chars=True)
        for w in words[:60]:
            pdf_y = page.height - w["top"]
            print(f"  x={w['x0']:6.1f}  y={pdf_y:6.1f}  text={w['text']!r}")
