"""Quick script to extract text positions from f1120s.pdf pages 3 and 4."""
import fitz

from pathlib import Path
pdf_path = Path(__file__).resolve().parent.parent / "resources" / "irs_forms" / "2025" / "f1120s.pdf"
doc = fitz.open(str(pdf_path))

# Page 3 (index 3) — K17/K18 + Schedule L
page3 = doc[3]
blocks = page3.get_text("dict")["blocks"]
print("=" * 70)
print("PAGE 3 — Text near K17/K18 area (pdf_y > 620)")
print("=" * 70)
for b in blocks:
    if "lines" not in b:
        continue
    for line in b["lines"]:
        for span in line["spans"]:
            fitz_y = span["bbox"][1]
            pdf_y = 792 - fitz_y
            if pdf_y > 620:
                text = span["text"].strip()
                if text:
                    print(f"  pdf_y={pdf_y:.1f}  x={span['bbox'][0]:.1f}  text={text[:80]}")

# Page 4 (index 4) — M-1 and M-2
page4 = doc[4]
blocks4 = page4.get_text("dict")["blocks"]
print()
print("=" * 70)
print("PAGE 4 — Text in M-1 area (pdf_y > 550)")
print("=" * 70)
for b in blocks4:
    if "lines" not in b:
        continue
    for line in b["lines"]:
        for span in line["spans"]:
            fitz_y = span["bbox"][1]
            pdf_y = 792 - fitz_y
            if pdf_y > 550:
                text = span["text"].strip()
                if text:
                    print(f"  pdf_y={pdf_y:.1f}  x={span['bbox'][0]:.1f}  text={text[:80]}")
