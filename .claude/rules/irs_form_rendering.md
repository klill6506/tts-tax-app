# Skill: IRS_FORM_RENDERING

## Core Rules (always enforced)

1. **Never draw IRS forms from scratch.** Always use official IRS PDF templates
   from `resources/irs_forms/<year>/` as the background layer.

2. **All PDF output must use the renderer service:**
   `apps.tts_forms.renderer.render(form_id, tax_year, data)` or
   `apps.tts_forms.renderer.render_tax_return(tax_return)`.

3. **If a form line needs detail breakdown** (e.g., Line 19 "Other deductions"),
   place the total on the IRS form line and output a **Statement page** — never
   fake an IRS layout for supporting detail. Use
   `apps.tts_forms.statements.render_statement_pages()`.

4. **Manifest is the source of truth.** Every IRS PDF template must be registered
   in `resources/irs_forms/forms_manifest.json` with:
   - `form_id`, `form_code`, `title`, `tax_year`
   - `irs_url` (canonical IRS download link)
   - `sha256` (populated after download)
   - `local_path` (relative to `resources/irs_forms/`)
   - `has_acroform` (true if the PDF has fillable AcroForm fields)

5. **Update templates via the script** — run `python scripts/update_irs_forms.py`
   to download and verify IRS PDFs. Never commit manually-downloaded PDFs without
   recording them in the manifest.

## Rendering Backends

The renderer supports two backends. It auto-selects based on `ACROFORM_REGISTRY`:

### AcroForm Filling (preferred)
- Fills named fields in IRS fillable PDFs using pymupdf
- Field maps live in `server/apps/tts_forms/field_maps/` — one module per form
- Each maps `line_number` -> `AcroField(acro_name, field_type, format)`
- Registered in `ACROFORM_REGISTRY` in `renderer.py`
- **Use this for all new forms that have AcroForm fields**

### Coordinate Overlay (legacy)
- Draws text at pixel positions using ReportLab + pypdf
- Coordinate maps live in `server/apps/tts_forms/coordinates/` — one module per form
- Each maps `line_number` -> `FieldCoord(page, x, y, width, alignment, font_size)`
- Registered in `COORDINATE_REGISTRY` in `renderer.py`
- **Used for forms without AcroForm fields** (e.g., GA-600S state form)

## Adding a New IRS Form (AcroForm Path — Preferred)

1. Add the form entry to `resources/irs_forms/forms_manifest.json` with `has_acroform: true`.
2. Run `python scripts/update_irs_forms.py` to download the PDF.
3. Run `python scripts/dump_acroform_fields.py resources/irs_forms/<year>/<form>.pdf`
   to discover all AcroForm field names (writes JSON + table output).
4. Create a field map module in `server/apps/tts_forms/field_maps/<form>.py`:
   - Define `HEADER_MAP: FieldMap` and `FIELD_MAP: FieldMap`
   - Map each `line_number` to `AcroField(acro_name="...", format="currency")`
5. Register in `renderer.py`:
   - Import the maps
   - Add to `ACROFORM_REGISTRY` and `ACROFORM_HEADER_REGISTRY`
6. Add field map validation tests in `server/tests/test_acroform_filler.py`.

## Adding a New Form (Coordinate Path — State Forms Only)

1. Add the form entry to `resources/irs_forms/forms_manifest.json`.
2. Run `python scripts/update_irs_forms.py` to download the PDF.
3. Create a coordinate mapping module in `server/apps/tts_forms/coordinates/`.
4. Register the coordinate map in `renderer.py`'s `COORDINATE_REGISTRY`.
5. Add tests in `server/tests/test_tts_forms.py`.

## Architecture

```
resources/irs_forms/
|-- forms_manifest.json     <- Template registry (URL + SHA256 + has_acroform)
+-- <year>/
    +-- <form>.pdf          <- IRS fillable PDF template

server/apps/tts_forms/
|-- renderer.py             <- Core render() API (auto-selects backend)
|-- acroform_filler.py      <- AcroForm filling engine (pymupdf)
|-- formatting.py           <- Shared value formatters (currency, boolean, etc.)
|-- statements.py           <- Supporting statement page generator
|-- field_maps/
|   |-- __init__.py         <- AcroField dataclass + FieldMap type
|   +-- f1120s.py           <- 1120-S field map (pattern for all forms)
|-- coordinates/
|   +-- f1120s.py           <- Legacy coordinate positions (kept as fallback)
+-- views.py                <- PDFRenderMixin (adds render-pdf endpoint)

scripts/
|-- dump_acroform_fields.py <- Discovery tool: dumps all AcroForm fields from a PDF
+-- update_irs_forms.py     <- Downloads + verifies IRS PDFs
```

## Rendering Pipeline

### AcroForm Path (forms in ACROFORM_REGISTRY)
1. Load IRS fillable PDF template with pymupdf (`fitz.open`)
2. Build pending values: pre-format all field values keyed by AcroForm name
3. Iterate pages -> widgets, fill matching values inline
4. For checkboxes: use `widget.on_state()` for checked, `"Off"` for unchecked
5. Flatten: set `widget.field_flags |= READ_ONLY` on filled widgets
6. Append any statement pages after the main form
7. Return PDF bytes

### Coordinate Path (forms NOT in ACROFORM_REGISTRY)
1. Load IRS PDF template, strip AcroForm widgets (purple backgrounds)
2. Create transparent overlay using ReportLab with field values at exact positions
3. Merge overlay onto template using pypdf
4. Append any statement pages after the main form
5. Return combined PDF bytes

## Fonts

- Use **Courier** (monospace) for coordinate overlay values — safe across all PDF viewers.
- AcroForm path uses the PDF's built-in field fonts (set by the IRS template).
- Use **Helvetica-Bold** for statement page headers.
- Avoid decorative or system fonts that may not render consistently.

## IRS Source URLs

- Forms & Instructions: `https://www.irs.gov/forms-instructions`
- PDF repository: `https://www.irs.gov/pub/irs-pdf/`
- Common form filenames:
  - Form 1120-S: `f1120s.pdf`
  - Schedule K-1 (1120-S): `f1120sk1.pdf`
  - Form 1120: `f1120.pdf`
  - Form 1065: `f1065.pdf`
  - Form 1040: `f1040.pdf`
