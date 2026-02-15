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

5. **Update templates via the script** — run `python scripts/update_irs_forms.py`
   to download and verify IRS PDFs. Never commit manually-downloaded PDFs without
   recording them in the manifest.

6. **Coordinate mappings** live in `server/apps/tts_forms/coordinates/` — one
   module per form (e.g., `f1120s.py`). Each maps `line_number` → `FieldCoord`
   with `(page, x, y, width, alignment, font_size)`.

## Adding a New IRS Form

1. Add the form entry to `resources/irs_forms/forms_manifest.json`.
2. Run `python scripts/update_irs_forms.py` to download the PDF.
3. Create a coordinate mapping module in `server/apps/tts_forms/coordinates/`.
4. Register the coordinate map in `renderer.py`'s `COORDINATE_REGISTRY`.
5. Add tests in `server/tests/test_tts_forms.py`.

## Architecture

```
resources/irs_forms/
├── forms_manifest.json     ← Template registry (URL + SHA256)
└── <year>/
    └── <form>.pdf          ← Immutable IRS template

server/apps/tts_forms/
├── renderer.py             ← Core render() and render_tax_return() API
├── statements.py           ← Supporting statement page generator
├── coordinates/
│   └── f1120s.py           ← Field position mappings per form
└── views.py                ← PDFRenderMixin (adds render-pdf endpoint)

scripts/
└── update_irs_forms.py     ← Downloads + verifies IRS PDFs
```

## Rendering Pipeline

1. Load official IRS PDF template from `resources/irs_forms/<year>/<form>.pdf`.
2. Create a transparent overlay using ReportLab with field values at exact
   coordinates from the coordinate mapping.
3. Merge overlay onto template using pypdf.
4. Append any statement pages after the main form.
5. Return the combined PDF bytes.

## Fonts

- Use **Courier** (monospace) for form field values — safe across all PDF viewers.
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
