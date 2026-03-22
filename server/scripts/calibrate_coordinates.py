"""
Coordinate calibration tool for PDF overlay forms.

Generates a PDF with red crosshair targets at each field's current
coordinate position, labeled with the field name. Used to visually
verify and adjust field positions.

Usage:
    poetry run python scripts/calibrate_coordinates.py --form ga600s
    poetry run python scripts/calibrate_coordinates.py --form f1065
    poetry run python scripts/calibrate_coordinates.py --form f1120
    poetry run python scripts/calibrate_coordinates.py --form f7206

Output: {form}_calibration.pdf in the current directory.
"""

import argparse
import importlib
import io
import sys
from pathlib import Path

# Add server to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Map form names to their coordinate module and template path
FORM_CONFIGS = {
    "ga600s": {
        "module": "apps.tts_forms.coordinates.fga600s",
        "field_map_attr": "FIELD_MAP",
        "header_map_attr": "HEADER_FIELDS",
        "template": "server/pdf_templates/ga600s_2025.pdf",
    },
    "f1065": {
        "module": "apps.tts_forms.coordinates.f1065",
        "field_map_attr": "FIELD_MAP",
        "header_map_attr": "HEADER_FIELDS",
        "template": "resources/irs_forms/2025/f1065.pdf",
    },
    "f1120": {
        "module": "apps.tts_forms.coordinates.f1120",
        "field_map_attr": "FIELD_MAP",
        "header_map_attr": "HEADER_FIELDS",
        "template": "resources/irs_forms/2025/f1120.pdf",
    },
    "f1120s": {
        "module": "apps.tts_forms.coordinates.f1120s",
        "field_map_attr": "FIELD_MAP",
        "header_map_attr": "HEADER_FIELDS",
        "template": "resources/irs_forms/2025/f1120s_print.pdf",
    },
    "f7206": {
        "module": "apps.tts_forms.coordinates.f7206",
        "field_map_attr": "FIELD_MAP",
        "header_map_attr": "HEADER_FIELDS",
        "template": "resources/irs_forms/2025/f7206.pdf",
    },
    "f1125a": {
        "module": "apps.tts_forms.coordinates.f1125a",
        "field_map_attr": "FIELD_MAP",
        "header_map_attr": "HEADER_FIELDS",
        "template": "resources/irs_forms/2025/f1125a.pdf",
    },
    "f7004": {
        "module": "apps.tts_forms.coordinates.f7004",
        "field_map_attr": "FIELD_MAP",
        "header_map_attr": "HEADER_FIELDS",
        "template": "resources/irs_forms/2025/f7004.pdf",
    },
    "f7203": {
        "module": "apps.tts_forms.coordinates.f7203",
        "field_map_attr": "FIELD_MAP",
        "header_map_attr": "HEADER_FIELDS",
        "template": "resources/irs_forms/2025/f7203.pdf",
    },
    "f8825": {
        "module": "apps.tts_forms.coordinates.f8825",
        "field_map_attr": "FIELD_MAP",
        "header_map_attr": "HEADER_FIELDS",
        "template": "resources/irs_forms/2025/f8825.pdf",
    },
}

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def generate_calibration_pdf(form_name: str) -> str:
    """Generate a calibration PDF with red targets at each field position."""
    config = FORM_CONFIGS.get(form_name)
    if not config:
        print(f"Unknown form: {form_name}")
        print(f"Available forms: {', '.join(sorted(FORM_CONFIGS.keys()))}")
        sys.exit(1)

    # Import coordinate maps
    module = importlib.import_module(config["module"])
    field_map = getattr(module, config["field_map_attr"])
    header_map = getattr(module, config["header_map_attr"], {})

    # Load template
    template_path = REPO_ROOT / config["template"]
    if not template_path.exists():
        print(f"Template not found: {template_path}")
        sys.exit(1)

    template_reader = PdfReader(str(template_path))
    page_count = len(template_reader.pages)
    page_sizes = []
    for page in template_reader.pages:
        box = page.mediabox
        page_sizes.append((float(box.width), float(box.height)))

    # Combine field maps
    all_fields: dict[str, object] = {}
    for key, coord in field_map.items():
        all_fields[key] = coord
    for key, coord in header_map.items():
        all_fields[f"H:{key}"] = coord

    # Create overlay with red targets
    overlay_buf = io.BytesIO()
    c = canvas.Canvas(overlay_buf)

    for page_idx in range(page_count):
        page_w, page_h = page_sizes[page_idx]
        c.setPageSize((page_w, page_h))

        for field_name, coord in all_fields.items():
            if coord.page != page_idx:
                continue

            x = coord.x
            y = coord.y

            # Draw crosshair
            c.setStrokeColor(colors.red)
            c.setLineWidth(0.5)
            arm = 4  # crosshair arm length
            c.line(x - arm, y, x + arm, y)
            c.line(x, y - arm, x, y + arm)

            # Draw small red dot at exact position
            c.setFillColor(colors.red)
            c.circle(x, y, 1.5, fill=1, stroke=0)

            # Draw field name label
            c.setFont("Helvetica", 5)
            c.setFillColor(colors.red)
            # Offset label to avoid overlapping the crosshair
            label_x = x + 5
            label_y = y + 3
            c.drawString(label_x, label_y, field_name)

            # If field has width, draw a faint box showing the field area
            if hasattr(coord, "width") and coord.width > 0:
                c.setStrokeColor(colors.Color(1, 0, 0, alpha=0.3))
                c.setLineWidth(0.25)
                c.rect(x, y - 2, coord.width, 12, fill=0, stroke=1)

        c.showPage()

    c.save()
    overlay_buf.seek(0)

    # Merge overlay onto template
    overlay_reader = PdfReader(overlay_buf)
    writer = PdfWriter()
    for i in range(page_count):
        page = template_reader.pages[i]
        if i < len(overlay_reader.pages):
            page.merge_page(overlay_reader.pages[i])
        writer.add_page(page)

    output_name = f"{form_name}_calibration.pdf"
    output_path = Path.cwd() / output_name
    with open(output_path, "wb") as f:
        writer.write(f)

    return str(output_path)


def main():
    parser = argparse.ArgumentParser(
        description="Generate coordinate calibration PDF for overlay forms"
    )
    parser.add_argument(
        "--form",
        required=True,
        choices=sorted(FORM_CONFIGS.keys()),
        help="Form to calibrate",
    )
    args = parser.parse_args()

    output = generate_calibration_pdf(args.form)
    print(f"Calibration PDF generated: {output}")
    field_count = 0
    config = FORM_CONFIGS[args.form]
    module = importlib.import_module(config["module"])
    field_map = getattr(module, config["field_map_attr"])
    header_map = getattr(module, config["header_map_attr"], {})
    field_count = len(field_map) + len(header_map)
    print(f"Total fields: {field_count}")


if __name__ == "__main__":
    main()
