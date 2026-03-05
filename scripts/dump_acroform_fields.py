#!/usr/bin/env python3
"""
Dump all AcroForm field names from an IRS fillable PDF.

Usage:
    python scripts/dump_acroform_fields.py resources/irs_forms/2025/f1120s.pdf
    python scripts/dump_acroform_fields.py resources/irs_forms/2025/f1120s.pdf --json

Outputs a table of every AcroForm widget found:
    page | short_name | full_name | type | rect(x0,y0,x1,y1)

With --json, also writes a .fields.json file alongside the PDF.
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import fitz  # pymupdf
except ImportError:
    print("ERROR: pymupdf is required. Install with: pip install pymupdf")
    sys.exit(1)


def dump_fields(pdf_path: str, write_json: bool = False) -> list[dict]:
    """Extract all AcroForm fields from a PDF.

    Returns a list of dicts with keys:
        page, short_name, full_name, field_type, rect, on_state (for checkboxes)
    """
    doc = fitz.open(pdf_path)
    fields = []

    for page_idx, page in enumerate(doc):
        for widget in page.widgets():
            # Short name is the last segment of the hierarchical name
            full_name = widget.field_name or ""
            parts = full_name.replace("]", "").split("[")
            # Extract just the field ID like "f1_01" from
            # "topmostSubform[0].Page1[0].f1_01[0]"
            short_name = full_name.split(".")[-1].split("[")[0] if "." in full_name else full_name.split("[")[0]

            field_info = {
                "page": page_idx,
                "short_name": short_name,
                "full_name": full_name,
                "field_type": widget.field_type_string,
                "rect": [round(r, 1) for r in widget.rect],
            }

            # For checkboxes, record the on-state value
            if widget.field_type_string == "CheckBox":
                try:
                    field_info["on_state"] = widget.on_state()
                except Exception:
                    field_info["on_state"] = None

            fields.append(field_info)

    doc.close()
    return fields


def print_table(fields: list[dict]) -> None:
    """Pretty-print fields as a table."""
    if not fields:
        print("No AcroForm fields found in this PDF.")
        return

    print(f"\n{'Page':>4}  {'Short Name':<16}  {'Type':<12}  {'Rect (x0, y0, x1, y1)':<32}  Full Name")
    print("-" * 120)
    for f in fields:
        rect_str = f"({f['rect'][0]:>5.1f}, {f['rect'][1]:>5.1f}, {f['rect'][2]:>5.1f}, {f['rect'][3]:>5.1f})"
        on_state = f"  on={f['on_state']}" if f.get("on_state") else ""
        print(f"{f['page']:>4}  {f['short_name']:<16}  {f['field_type']:<12}  {rect_str:<32}  {f['full_name']}{on_state}")

    print(f"\nTotal: {len(fields)} fields")

    # Summary by type
    types = {}
    for f in fields:
        types[f["field_type"]] = types.get(f["field_type"], 0) + 1
    print("By type:", ", ".join(f"{t}: {c}" for t, c in sorted(types.items())))

    # Summary by page
    pages = {}
    for f in fields:
        pages[f["page"]] = pages.get(f["page"], 0) + 1
    print("By page:", ", ".join(f"Page {p}: {c}" for p, c in sorted(pages.items())))


def main():
    parser = argparse.ArgumentParser(description="Dump AcroForm fields from an IRS PDF")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("--json", action="store_true", help="Write a .fields.json file")
    args = parser.parse_args()

    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"ERROR: File not found: {pdf_path}")
        sys.exit(1)

    print(f"Scanning: {pdf_path}")
    fields = dump_fields(str(pdf_path))
    print_table(fields)

    if args.json:
        json_path = pdf_path.with_suffix(".fields.json")
        with open(json_path, "w") as f:
            json.dump(fields, f, indent=2)
        print(f"\nJSON written to: {json_path}")


if __name__ == "__main__":
    main()
