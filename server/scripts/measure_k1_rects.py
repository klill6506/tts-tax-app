"""Extract rectangles/lines from K-1 to find amount box positions."""
import pdfplumber
from pathlib import Path

pdf_path = Path(__file__).resolve().parent.parent.parent / "resources" / "irs_forms" / "2025" / "f1120ssk.pdf"

with pdfplumber.open(str(pdf_path)) as pdf:
    page = pdf.pages[0]
    # Extract horizontal and vertical lines to find box boundaries
    rects = page.rects
    print(f"Found {len(rects)} rectangles")
    for r in sorted(rects, key=lambda r: (-r["top"], r["x0"]))[:30]:
        pdf_y0 = page.height - r["top"]
        pdf_y1 = page.height - r["bottom"]
        print(f"  x0={r['x0']:6.1f}  y0={pdf_y0:6.1f}  x1={r['x1']:6.1f}  y1={pdf_y1:6.1f}  w={r['x1']-r['x0']:5.1f}  h={abs(r['top']-r['bottom']):5.1f}")

    lines = page.lines
    print(f"\nFound {len(lines)} lines")
    # Just show vertical lines that might be column separators
    vlines = [l for l in lines if abs(l["x0"] - l["x1"]) < 1 and abs(l["top"] - l["bottom"]) > 50]
    print(f"\nVertical lines (height > 50):")
    for l in sorted(vlines, key=lambda l: l["x0"]):
        pdf_y0 = page.height - l["top"]
        pdf_y1 = page.height - l["bottom"]
        print(f"  x={l['x0']:6.1f}  y_top={pdf_y0:6.1f}  y_bot={pdf_y1:6.1f}  height={abs(l['top']-l['bottom']):5.1f}")
