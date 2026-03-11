"""
AcroForm field map for Schedule D (Form 1120-S) — Capital Gains and Losses
and Built-in Gains (2025).

Template: resources/irs_forms/2025/f1120ssd.pdf (53 AcroForm fields)

Two pages:
  Page 1 — Header, QOF checkbox, Part I (Short-Term), Part II (Long-Term)
  Page 2 — Part III (Built-In Gains Tax)

Part I   lines 1a–7:   Short-Term Capital Gains and Losses
Part II  lines 8a–15:  Long-Term Capital Gains and Losses
Part III lines 16–23:  Built-In Gains Tax

Table rows (1a, 1b, 2, 3, 8a, 8b, 9, 10) have four columns:
  (d) Proceeds, (e) Cost, (g) Adjustments, (h) Gain or (loss)
Single-amount lines carry only column (h) or a standalone amount.
"""

from . import AcroField, FieldMap

_P1 = "topmostSubform[0].Page1[0]"
_P2 = "topmostSubform[0].Page2[0]"

# Part I table rows
_PT1 = f"{_P1}.Table_PartI[0]"
# Part II table rows
_PT2 = f"{_P1}.Table_PartII[0]"

# ---------------------------------------------------------------------------
# HEADER_MAP — Entity identification
# ---------------------------------------------------------------------------

HEADER_MAP: FieldMap = {
    "entity_name": AcroField(f"{_P1}.f1_1[0]"),   # Name
    "ein":         AcroField(f"{_P1}.f1_2[0]"),    # EIN
}

# ---------------------------------------------------------------------------
# FIELD_MAP — Lines 1a through 23
# ---------------------------------------------------------------------------

FIELD_MAP: FieldMap = {
    # QOF checkbox (Did the corporation dispose of any investment in a QOF?)
    "SD_QOF_YES": AcroField(f"{_P1}.c1_1[0]", field_type="checkbox", format="boolean"),
    "SD_QOF_NO":  AcroField(f"{_P1}.c1_1[1]", field_type="checkbox", format="boolean"),

    # -----------------------------------------------------------------------
    # Part I — Short-Term Capital Gains and Losses (lines 1a–7)
    # -----------------------------------------------------------------------

    # Line 1a — Totals for short-term transactions on 1099-B/1099-DA
    #           (basis reported to IRS, no adjustments)
    "SD_1a_proceeds": AcroField(f"{_PT1}.Row1a[0].f1_3[0]",  format="currency"),
    "SD_1a_cost":     AcroField(f"{_PT1}.Row1a[0].f1_4[0]",  format="currency"),
    "SD_1a_adj":      AcroField(f"{_PT1}.Row1a[0].f1_5[0]",  format="currency"),
    "SD_1a_gain":     AcroField(f"{_PT1}.Row1a[0].f1_6[0]",  format="currency"),

    # Line 1b — Totals from Form 8949 with Box A or Box G checked
    "SD_1b_proceeds": AcroField(f"{_PT1}.Row1b[0].f1_7[0]",  format="currency"),
    "SD_1b_cost":     AcroField(f"{_PT1}.Row1b[0].f1_8[0]",  format="currency"),
    "SD_1b_adj":      AcroField(f"{_PT1}.Row1b[0].f1_9[0]",  format="currency"),
    "SD_1b_gain":     AcroField(f"{_PT1}.Row1b[0].f1_10[0]", format="currency"),

    # Line 2 — Totals from Form 8949 with Box B or Box H checked
    "SD_2_proceeds":  AcroField(f"{_PT1}.Row2[0].f1_11[0]",  format="currency"),
    "SD_2_cost":      AcroField(f"{_PT1}.Row2[0].f1_12[0]",  format="currency"),
    "SD_2_adj":       AcroField(f"{_PT1}.Row2[0].f1_13[0]",  format="currency"),
    "SD_2_gain":      AcroField(f"{_PT1}.Row2[0].f1_14[0]",  format="currency"),

    # Line 3 — Totals from Form 8949 with Box C or Box I checked
    "SD_3_proceeds":  AcroField(f"{_PT1}.Row3[0].f1_15[0]",  format="currency"),
    "SD_3_cost":      AcroField(f"{_PT1}.Row3[0].f1_16[0]",  format="currency"),
    "SD_3_adj":       AcroField(f"{_PT1}.Row3[0].f1_17[0]",  format="currency"),
    "SD_3_gain":      AcroField(f"{_PT1}.Row3[0].f1_18[0]",  format="currency"),

    # Line 4 — Short-term gain from installment sales (Form 6252, line 26 or 37)
    "SD_4": AcroField(f"{_P1}.f1_19[0]", format="currency"),

    # Line 5 — Short-term gain or (loss) from like-kind exchanges (Form 8824)
    "SD_5": AcroField(f"{_P1}.f1_20[0]", format="currency"),

    # Line 6 — Tax on short-term capital gain included on line 23
    "SD_6": AcroField(f"{_P1}.f1_21[0]", format="currency"),

    # Line 7 — Net short-term capital gain or (loss)
    #           (combine lines 1a through 6 in column h)
    "SD_7": AcroField(f"{_P1}.f1_22[0]", format="currency"),

    # -----------------------------------------------------------------------
    # Part II — Long-Term Capital Gains and Losses (lines 8a–15)
    # -----------------------------------------------------------------------

    # Line 8a — Totals for long-term transactions on 1099-B/1099-DA
    #           (basis reported to IRS, no adjustments)
    "SD_8a_proceeds": AcroField(f"{_PT2}.Row8a[0].f1_23[0]", format="currency"),
    "SD_8a_cost":     AcroField(f"{_PT2}.Row8a[0].f1_24[0]", format="currency"),
    "SD_8a_adj":      AcroField(f"{_PT2}.Row8a[0].f1_25[0]", format="currency"),
    "SD_8a_gain":     AcroField(f"{_PT2}.Row8a[0].f1_26[0]", format="currency"),

    # Line 8b — Totals from Form 8949 with Box D or Box J checked
    "SD_8b_proceeds": AcroField(f"{_PT2}.Row8b[0].f1_27[0]", format="currency"),
    "SD_8b_cost":     AcroField(f"{_PT2}.Row8b[0].f1_28[0]", format="currency"),
    "SD_8b_adj":      AcroField(f"{_PT2}.Row8b[0].f1_29[0]", format="currency"),
    "SD_8b_gain":     AcroField(f"{_PT2}.Row8b[0].f1_30[0]", format="currency"),

    # Line 9 — Totals from Form 8949 with Box E or Box K checked
    "SD_9_proceeds":  AcroField(f"{_PT2}.Row9[0].f1_31[0]",  format="currency"),
    "SD_9_cost":      AcroField(f"{_PT2}.Row9[0].f1_32[0]",  format="currency"),
    "SD_9_adj":       AcroField(f"{_PT2}.Row9[0].f1_33[0]",  format="currency"),
    "SD_9_gain":      AcroField(f"{_PT2}.Row9[0].f1_34[0]",  format="currency"),

    # Line 10 — Totals from Form 8949 with Box F or Box L checked
    "SD_10_proceeds": AcroField(f"{_PT2}.Row10[0].f1_35[0]", format="currency"),
    "SD_10_cost":     AcroField(f"{_PT2}.Row10[0].f1_36[0]", format="currency"),
    "SD_10_adj":      AcroField(f"{_PT2}.Row10[0].f1_37[0]", format="currency"),
    "SD_10_gain":     AcroField(f"{_PT2}.Row10[0].f1_38[0]", format="currency"),

    # Line 11 — Long-term gain from installment sales (Form 6252, line 26 or 37)
    "SD_11": AcroField(f"{_P1}.f1_39[0]", format="currency"),

    # Line 12 — Long-term gain or (loss) from like-kind exchanges (Form 8824)
    "SD_12": AcroField(f"{_P1}.f1_40[0]", format="currency"),

    # Line 13 — Capital gain distributions
    "SD_13": AcroField(f"{_P1}.f1_41[0]", format="currency"),

    # Line 14 — Tax on long-term capital gain included on line 23
    "SD_14": AcroField(f"{_P1}.f1_42[0]", format="currency"),

    # Line 15 — Net long-term capital gain or (loss)
    #           (combine lines 8a through 14 in column h)
    "SD_15": AcroField(f"{_P1}.f1_43[0]", format="currency"),

    # -----------------------------------------------------------------------
    # Part III — Built-In Gains Tax (lines 16–23, page 2)
    # -----------------------------------------------------------------------

    # Line 16 — Excess of recognized built-in gains over recognized built-in losses
    "SD_16": AcroField(f"{_P2}.f2_1[0]", format="currency"),

    # Line 17 — Taxable income
    "SD_17": AcroField(f"{_P2}.f2_2[0]", format="currency"),

    # Line 18 — Net recognized built-in gain
    #           (smallest of line 16, line 17, or Schedule B line 8)
    "SD_18": AcroField(f"{_P2}.f2_3[0]", format="currency"),

    # Line 19 — Section 1374(b)(2) deduction
    "SD_19": AcroField(f"{_P2}.f2_4[0]", format="currency"),

    # Line 20 — Subtract line 19 from line 18 (if zero or less, enter -0-)
    "SD_20": AcroField(f"{_P2}.f2_5[0]", format="currency"),

    # Line 21 — Enter 21% (0.21) of line 20
    "SD_21": AcroField(f"{_P2}.f2_6[0]", format="currency"),

    # Line 22 — Section 1374(b)(3) business credit and minimum tax credit
    #           carryforwards from C corporation years
    "SD_22": AcroField(f"{_P2}.f2_7[0]", format="currency"),

    # Line 23 — Tax (line 21 minus line 22, if zero or less enter -0-)
    #           Enter here and on Form 1120-S, page 1, line 23b
    "SD_23": AcroField(f"{_P2}.f2_8[0]", format="currency"),
}
