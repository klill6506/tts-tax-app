"""Quick verification of the 1120-S AcroForm field map."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

from apps.tts_forms.field_maps.f1120s_2025 import FIELD_MAP, HEADER_MAP

print(f"HEADER_MAP: {len(HEADER_MAP)} entries")
print(f"FIELD_MAP: {len(FIELD_MAP)} entries")
print(f"Total: {len(HEADER_MAP) + len(FIELD_MAP)} entries")
print()

print("Sample HEADER entries:")
for k in list(HEADER_MAP)[:5]:
    a = HEADER_MAP[k]
    print(f"  {k}: acro={a.acro_name}, type={a.field_type}, fmt={a.format}")

print()
print("Sample FIELD entries (income):")
for k in ["1a", "1b", "1c", "2", "3", "4", "5", "6"]:
    a = FIELD_MAP.get(k)
    if a:
        print(f"  Line {k}: acro={a.acro_name}, fmt={a.format}")
    else:
        print(f"  Line {k}: MISSING")

print()
print("Sample FIELD entries (Schedule K):")
for k in ["K1", "K2", "K3", "K12a", "K16c"]:
    a = FIELD_MAP.get(k)
    if a:
        print(f"  {k}: acro={a.acro_name}, fmt={a.format}")
    else:
        print(f"  {k}: MISSING")

print()
print("Sample FIELD entries (Schedule L):")
for k in ["L1a", "L1d", "L15a", "L15d", "L27d"]:
    a = FIELD_MAP.get(k)
    if a:
        print(f"  {k}: acro={a.acro_name}")
    else:
        print(f"  {k}: MISSING")

print()
print("Sample FIELD entries (M-1, M-2):")
for k in ["M1_1", "M1_3b", "M1_8", "M2_1a", "M2_8d"]:
    a = FIELD_MAP.get(k)
    if a:
        print(f"  {k}: acro={a.acro_name}")
    else:
        print(f"  {k}: MISSING")

print()
print("Schedule B checkboxes:")
for k in ["B1_yes", "B1_no", "B3_yes", "B3_no"]:
    a = FIELD_MAP.get(k)
    if a:
        print(f"  {k}: acro={a.acro_name}, type={a.field_type}")
    else:
        print(f"  {k}: MISSING")
