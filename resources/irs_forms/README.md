# IRS Form Templates

This directory contains official IRS PDF templates used as backgrounds for
tax return PDF rendering.

## Rules

- **Never draw IRS forms from scratch.** Always overlay data onto official PDFs.
- Templates are immutable — never modify the IRS PDFs themselves.
- All templates must be tracked in `forms_manifest.json` with URL + SHA256.
- Update templates via `scripts/update_irs_forms.py`.

## Directory Structure

```
resources/irs_forms/
├── forms_manifest.json    # Registry of all IRS PDF templates
├── README.md              # This file
└── 2025/                  # Tax year directory
    ├── f1120s.pdf         # Form 1120-S
    └── f1120sk1.pdf       # Schedule K-1 (Form 1120-S)
```

## Adding a New Form

1. Add an entry to `forms_manifest.json` with the IRS download URL.
2. Run `python scripts/update_irs_forms.py` to download and verify.
3. Add coordinate mappings in `server/apps/tts_forms/coordinates/`.
