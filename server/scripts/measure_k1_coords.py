"""Extract text positions from Schedule K-1 (Form 1120-S) PDF to help calibrate coordinates."""
import pdfplumber
from pathlib import Path

pdf_path = Path(__file__).resolve().parent.parent.parent / "resources" / "irs_forms" / "2025" / "f1120ssk.pdf"

with pdfplumber.open(str(pdf_path)) as pdf:
    for i, page in enumerate(pdf.pages):
        print(f"\n{'='*80}")
        print(f"PAGE {i} — {page.width} x {page.height}")
        print(f"{'='*80}")
        words = page.extract_words(keep_blank_chars=True, extra_attrs=["fontname", "size"])
        for w in words:
            # Show text, position (x0, top converted to PDF bottom-origin y)
            pdf_y = page.height - w["top"]  # Convert to bottom-origin
            print(f"  x={w['x0']:6.1f}  y={pdf_y:6.1f}  w={w['x1']-w['x0']:5.1f}  text={w['text']!r}")
