"""Extract text positions from Form 7206."""
import pdfplumber
from pathlib import Path

pdf_path = Path(__file__).resolve().parent.parent.parent / "resources" / "irs_forms" / "2025" / "f7206.pdf"

with pdfplumber.open(str(pdf_path)) as pdf:
    print(f"Total pages: {len(pdf.pages)}")
    for i, page in enumerate(pdf.pages):
        print(f"\nPAGE {i} — {page.width} x {page.height}")
        words = page.extract_words(keep_blank_chars=True)
        for w in words:
            pdf_y = page.height - w["top"]
            print(f"  x={w['x0']:6.1f}  y={pdf_y:6.1f}  w={w['x1']-w['x0']:5.1f}  text={w['text']!r}")
