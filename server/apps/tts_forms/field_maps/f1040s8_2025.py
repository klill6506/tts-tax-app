"""
AcroForm field map for IRS Schedule 8812 (Form 1040) — 2025 fillable PDF.

Source PDF: resources/irs_forms/2025/f1040s8.pdf
SHA256:     6936462d67e2309d14a795aa0b88ef613cc6d79617431cfda3a2edf44aea52db

Keys match the `line_number` values seeded by `seed_sch_8812` (L_1, L_2a,
... L_27). Compute output lives in `apps.returns.compute_8812` and is
stored on FormFieldValue rows whose `form_line.section.form` is SCH_8812.

Field discovery: scripts/dump_acroform_fields.py + scripts/inspect_8812_pdf3.py.
Page 1 has 19 text fields + 1 checkbox group; page 2 has 16 text fields + 2
checkbox groups. Line 15 ("Reserved for future use") is intentionally
omitted — there's an AcroForm widget for it but the spec marks it
reserved.
"""
from . import AcroField, FieldMap


# ============================================================================
# HEADER_MAP -- name + SSN (carried from parent 1040 Taxpayer)
# ============================================================================
HEADER_MAP: FieldMap = {
    "name_on_return": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_1[0]",
    ),
    "ssn": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_2[0]",
    ),
}


# ============================================================================
# FIELD_MAP -- Schedule 8812 line outputs (Part I / II-A / II-B / II-C)
# ============================================================================
FIELD_MAP: FieldMap = {
    # -------- Part I: Credit for Qualifying Children + Other Dependents --------
    # Line 1: AGI from Form 1040 line 11
    "L_1": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_3[0]",
        format="currency",
    ),
    # Line 2a: Puerto Rico excluded income
    "L_2a": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_4[0]",
        format="currency",
    ),
    # Line 2b: Form 2555 lines 45 + 50
    "L_2b": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_5[0]",
        format="currency",
    ),
    # Line 2c: Form 4563 line 15
    "L_2c": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_6[0]",
        format="currency",
    ),
    # Line 2d: 2a + 2b + 2c
    "L_2d": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_7[0]",
        format="currency",
    ),
    # Line 3: MAGI = Line 1 + Line 2d
    "L_3": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_8[0]",
        format="currency",
    ),
    # Line 4: # qualifying children with valid SSN under 17
    "L_4": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_9[0]",
        format="integer",
    ),
    # Line 5: Line 4 × $2,200 (OBBBA — TY 2025+)
    "L_5": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_10[0]",
        format="currency",
    ),
    # Line 6: # other dependents
    "L_6": AcroField(
        acro_name="topmostSubform[0].Page1[0].Line6ReadOrder[0].f1_11[0]",
        format="integer",
    ),
    # Line 7: Line 6 × $500
    "L_7": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_12[0]",
        format="currency",
    ),
    # Line 8: Line 5 + Line 7
    "L_8": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_13[0]",
        format="currency",
    ),
    # Line 9: phaseout threshold ($400K MFJ / $200K else)
    "L_9": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_14[0]",
        format="currency",
    ),
    # Line 10: rounded-up excess of MAGI over threshold
    "L_10": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_15[0]",
        format="currency",
    ),
    # Line 11: Line 10 × 5%
    "L_11": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_16[0]",
        format="currency",
    ),
    # Line 12: max(0, Line 8 − Line 11)
    "L_12": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_17[0]",
        format="currency",
    ),
    # Line 13: Credit Limit Worksheet A cap
    "L_13": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_18[0]",
        format="currency",
    ),
    # Line 14: smaller of 12 or 13 → Form 1040 Line 19
    "L_14": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_19[0]",
        format="currency",
    ),
    # Line 15 ("Reserved for future use") — widget exists at f2_1 but is
    # intentionally blank per IRS form.

    # -------- Part II-A: Additional CTC (15% method) --------
    # Line 16a: Line 12 − Line 14 (post-CTC overflow)
    "L_16a": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_2[0]",
        format="currency",
    ),
    # Line 16b sub-field: # qualifying children count (auto = Line 4)
    "L_16b_qc_count": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_3[0]",
        format="integer",
    ),
    # Line 16b: count × $1,700
    "L_16b": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_4[0]",
        format="currency",
    ),
    # Line 17: smaller of Line 16a or Line 16b
    "L_17": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_5[0]",
        format="currency",
    ),
    # Line 18a: Earned income
    "L_18a": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_6[0]",
        format="currency",
    ),
    # Line 18b: Nontaxable combat pay
    "L_18b": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_7[0]",
        format="currency",
    ),
    # Line 19: max(0, 18a − $2,500) if 18a > $2,500
    "L_19": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_8[0]",
        format="currency",
    ),
    # Line 20: Line 19 × 15%
    "L_20": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_9[0]",
        format="currency",
    ),

    # -------- Part II-B: Alternate path (3+ QC / Puerto Rico) --------
    # Line 21: Withheld SS + Medicare + Add'l Medicare (W-2 boxes 4+6)
    "L_21": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_10[0]",
        format="currency",
    ),
    # Line 22: Sch 1 line 15 + Sch 2 lines 5, 6, 13
    "L_22": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_11[0]",
        format="currency",
    ),
    # Line 23: Line 21 + Line 22
    "L_23": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_12[0]",
        format="currency",
    ),
    # Line 24: 1040 Line 27a (EITC) + Sch 3 Line 11 (excess SS/RRTA)
    "L_24": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_13[0]",
        format="currency",
    ),
    # Line 25: max(0, Line 23 − Line 24)
    "L_25": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_14[0]",
        format="currency",
    ),
    # Line 26: larger of Line 20 or Line 25
    "L_26": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_15[0]",
        format="currency",
    ),

    # -------- Part II-C: Additional Child Tax Credit (final) --------
    # Line 27: ACTC → Form 1040 Line 28
    "L_27": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_16[0]",
        format="currency",
    ),
}
