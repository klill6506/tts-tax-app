"""Quick verification script for the 1120-S AcroForm field map."""
import sys
import os

# Add server to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django
django.setup()

from apps.tts_forms.field_maps.f1120s_2025 import FIELD_MAP, HEADER_MAP

# Count by section prefix
sections = {}
for key in FIELD_MAP:
    if key.startswith("B"):
        prefix = "Schedule B"
    elif key.startswith("K"):
        prefix = "Schedule K"
    elif key.startswith("L"):
        prefix = "Schedule L"
    elif key.startswith("M1"):
        prefix = "Schedule M-1"
    elif key.startswith("M2"):
        prefix = "Schedule M-2"
    else:
        prefix = "Page 1 (Income/Ded/Tax)"
    sections[prefix] = sections.get(prefix, 0) + 1

print("=== HEADER_MAP ===")
print(f"  Total entries: {len(HEADER_MAP)}")
print()
print("=== FIELD_MAP by section ===")
for section in sorted(sections.keys()):
    print(f"  {section}: {sections[section]} entries")
print(f"  TOTAL: {len(FIELD_MAP)} entries")
print()

# Spot check some critical fields
checks = [
    ("1a", "Income line 1a"),
    ("6", "Total income"),
    ("21", "Ordinary business income"),
    ("26", "Amount owed"),
    ("K1", "Schedule K line 1"),
    ("K18a", "Schedule K line 18a"),
    ("L1_a", "Schedule L line 1 col a"),
    ("L27_d", "Schedule L line 27 col d"),
    ("M1_1", "Schedule M-1 line 1"),
    ("M2_8_d", "Schedule M-2 line 8 col d"),
    ("B3_yes", "Schedule B line 3 yes"),
    ("B4a_r1_name", "Schedule B 4a row 1 name"),
]
print("=== Spot checks ===")
all_ok = True
for key, desc in checks:
    found = FIELD_MAP.get(key) or HEADER_MAP.get(key)
    if found:
        print(f"  OK    {key:20s} ({desc}): {found.acro_name}")
    else:
        print(f"  MISS  {key:20s} ({desc})")
        all_ok = False

# Check for format distribution
formats = {}
for fm in (HEADER_MAP, FIELD_MAP):
    for key, field in fm.items():
        fmt = f"{field.field_type}/{field.format}"
        formats[fmt] = formats.get(fmt, 0) + 1

print()
print("=== Format distribution ===")
for fmt in sorted(formats.keys()):
    print(f"  {fmt}: {formats[fmt]}")

print()
if all_ok:
    print("All spot checks PASSED.")
else:
    print("Some spot checks FAILED!")
    sys.exit(1)
