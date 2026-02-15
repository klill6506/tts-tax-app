#!/usr/bin/env python3
"""
Download and verify official IRS PDF form templates.

Reads forms_manifest.json, downloads each PDF from irs.gov, verifies the
SHA256 hash (if present), and updates the manifest with the computed hash.

Usage:
    python scripts/update_irs_forms.py [--force]

Flags:
    --force     Re-download even if local file already exists and hash matches.
"""

import hashlib
import json
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RESOURCES_DIR = REPO_ROOT / "resources" / "irs_forms"
MANIFEST_PATH = RESOURCES_DIR / "forms_manifest.json"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) TTS-Tax-App/1.0 "
    "(IRS Form Downloader)"
)


def sha256_file(path: Path) -> str:
    """Compute SHA-256 hex digest for a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def download_form(url: str, dest: Path) -> None:
    """Download a PDF from the IRS website."""
    print(f"  Downloading {url} ...")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            while True:
                chunk = resp.read(8192)
                if not chunk:
                    break
                f.write(chunk)
    print(f"  Saved to {dest}")


def main():
    force = "--force" in sys.argv

    if not MANIFEST_PATH.exists():
        print(f"ERROR: Manifest not found at {MANIFEST_PATH}")
        sys.exit(1)

    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)

    forms = manifest.get("forms", [])
    if not forms:
        print("No forms in manifest.")
        return

    updated = False
    errors = []

    for entry in forms:
        form_id = entry["form_id"]
        local_rel = entry["local_path"]
        local_path = RESOURCES_DIR / local_rel
        irs_url = entry["irs_url"]
        expected_sha = entry.get("sha256")

        print(f"\n--- {form_id} ({entry['title']}) ---")

        # Check if already downloaded and hash matches
        if local_path.exists() and not force:
            actual_sha = sha256_file(local_path)
            if expected_sha and actual_sha == expected_sha:
                print(f"  Already up to date (SHA256 matches).")
                continue
            elif expected_sha:
                print(f"  Hash mismatch — re-downloading.")
            else:
                print(f"  File exists but no SHA256 recorded — verifying.")
                entry["sha256"] = actual_sha
                updated = True
                print(f"  Recorded SHA256: {actual_sha}")
                continue

        # Download from IRS
        try:
            download_form(irs_url, local_path)
        except Exception as e:
            errors.append(f"{form_id}: Download failed — {e}")
            print(f"  ERROR: {e}")
            continue

        # Compute and verify hash
        actual_sha = sha256_file(local_path)
        if expected_sha and actual_sha != expected_sha:
            errors.append(
                f"{form_id}: SHA256 mismatch! Expected {expected_sha}, "
                f"got {actual_sha}. IRS may have updated the form."
            )
            print(f"  WARNING: SHA256 mismatch!")
            print(f"    Expected: {expected_sha}")
            print(f"    Actual:   {actual_sha}")
            print(f"  Updating manifest with new hash.")

        entry["sha256"] = actual_sha
        updated = True
        print(f"  SHA256: {actual_sha}")

    # Write updated manifest
    if updated:
        with open(MANIFEST_PATH, "w") as f:
            json.dump(manifest, f, indent=2)
            f.write("\n")
        print(f"\nManifest updated at {MANIFEST_PATH}")

    if errors:
        print(f"\n{'=' * 60}")
        print("ERRORS / WARNINGS:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("\nAll forms up to date.")


if __name__ == "__main__":
    main()
