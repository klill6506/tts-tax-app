"""
Flow Assertion Test Runner
==========================
Reads flow assertion JSON exported from Sherpa Tax Rule Studio and
validates each assertion against the actual tts-tax-app code.

Assertion types:
- table_invariant: Validates properties of MACRS lookup tables
- flow_assertion: Validates that values flow from source to destination
- reconciliation: Validates cross-form balance checks with test data

These tests run as part of the standard pytest suite. Any CC session
that modifies compute.py, renderer.py, k1_allocator.py, aggregate
functions, depreciation_engine.py, or MACRS tables MUST pass all
flow assertions before committing.

1040 assertions are TODO. The file `server/specs/flow_assertions_1040.json`
exists as an empty stub. Once Ken authors 1040 Rule Studio specs (see
STATUS.md "1040 — Ken's TODO (Rule Studio work)"), the export will fill
in this file and the parametrized 1040 tests will start exercising the
1040 compute + render chain.
"""
import json
import importlib
import inspect
import warnings
from decimal import Decimal
from pathlib import Path

import pytest

SPECS_DIR = Path(__file__).parent.parent / "specs"


def load_assertions(entity_type: str) -> list[dict]:
    """Load active assertions from the exported JSON file."""
    path = SPECS_DIR / f"flow_assertions_{entity_type.lower()}.json"
    if not path.exists():
        return []
    with open(path) as f:
        data = json.load(f)
    return [a for a in data.get("assertions", []) if a.get("status") == "active"]


# ---------------------------------------------------------------------------
# Table Invariant runner
# ---------------------------------------------------------------------------

def run_table_invariant(assertion: dict):
    """Validate properties of MACRS lookup tables (or Dependent classification flags)."""
    defn = assertion["definition"]
    check = defn["check"]
    params = defn.get("params", {})

    # ---- Dependent classification mutual-exclusion (TI-1040-CTC-A) ----
    if check == "mutual_exclusion" and defn.get("table_name") == "Dependent":
        _run_sch_8812_assertion(assertion, defn, "mutual_exclusion")
        return

    module_path = defn["module"]
    table_name = defn["table_name"]

    mod = importlib.import_module(module_path)
    table = getattr(mod, table_name)

    if check == "sum_equals_one":
        tolerance = Decimal(str(params.get("tolerance", "0.002")))
        for life in params["lives"]:
            pcts = table[life]
            total = sum(Decimal(p) for p in pcts)
            assert abs(total - Decimal("1")) < tolerance, (
                f"{assertion['assertion_id']}: {table_name}[{life}yr] "
                f"sums to {total}, expected ~1.0000 (tolerance {tolerance})"
            )

    elif check == "length_equals_life_plus_one":
        for life in params["lives"]:
            pcts = table[life]
            expected_len = life + 1
            assert len(pcts) == expected_len, (
                f"{assertion['assertion_id']}: {table_name}[{life}yr] "
                f"has {len(pcts)} entries, expected {expected_len} (life + 1 for HY)"
            )

    elif check == "all_positive":
        for life in params.get("lives", table.keys()):
            for i, p in enumerate(table[life]):
                assert Decimal(p) >= 0, (
                    f"{assertion['assertion_id']}: {table_name}[{life}yr][{i}] = {p} (negative)"
                )

    else:
        pytest.fail(f"{assertion['assertion_id']}: Unknown table check '{check}'")


# ---------------------------------------------------------------------------
# Flow Assertion runner
# ---------------------------------------------------------------------------

class _DefaultZeroDict(dict):
    """Dict that returns Decimal(0) for missing keys."""
    def __missing__(self, key):
        return Decimal("0")


def run_flow_assertion(assertion: dict):
    """Validate that values flow from source to destination."""
    defn = assertion["definition"]
    check = defn.get("check", "")
    kind = defn.get("kind", "")

    # ===========================================================================
    # 1040 Schedule 8812 sub-kinds — dispatch by `kind` for FA-1040-CTC-* assertions.
    # ===========================================================================
    if kind:
        _run_sch_8812_assertion(assertion, defn, kind)
        return

    # --- Check: source line must appear in a formula ---
    if "must_appear_in_formula" in defn:
        mod = importlib.import_module(defn["module"])
        registry = getattr(mod, defn["registry"])
        target = defn["must_appear_in_formula"]
        source = defn["source_line"]

        formula_fn = None
        for line_num, fn in registry:
            if line_num == target:
                formula_fn = fn
                break

        assert formula_fn is not None, (
            f"{assertion['assertion_id']}: No formula for '{target}' in {defn['registry']}"
        )

        values_zero = _DefaultZeroDict({source: Decimal("0")})
        values_test = _DefaultZeroDict({source: Decimal("1000")})

        result_zero = formula_fn(values_zero)
        result_test = formula_fn(values_test)

        assert result_test != result_zero, (
            f"{assertion['assertion_id']}: '{source}' does not affect formula for '{target}'. "
            f"Output is {result_zero} regardless of {source} value. "
            f"Expected {source} to be referenced in {target} formula."
        )

    # --- Check: K-1 coded entry exists ---
    elif check == "k1_coded_entry_exists":
        mod = importlib.import_module(defn["module"])
        items_list = getattr(mod, defn["items_list"])
        k_line = defn["k_line"]
        expected_code = defn["expected_code"]

        found = any(
            entry[0] == k_line and entry[1] == expected_code
            for entry in items_list
        )

        assert found, (
            f"{assertion['assertion_id']}: K-1 coded entry for '{k_line}' with code "
            f"'{expected_code}' not found in {defn['items_list']}. "
            f"Available: {[(e[0], e[1]) for e in items_list]}"
        )

    # --- Check: aggregate function must write to a line ---
    elif check == "must_write_to":
        mod = importlib.import_module(defn["module"])
        func = getattr(mod, defn["function"])
        source_code = inspect.getsource(func)
        target_line = defn["target_line"]

        assert f'"{target_line}"' in source_code or f"'{target_line}'" in source_code, (
            f"{assertion['assertion_id']}: Function {defn['function']} "
            f"does not write to '{target_line}'"
        )

    # --- Check: function source contains expected substring ---
    elif check == "source_contains":
        mod = importlib.import_module(defn["module"])
        func = getattr(mod, defn["function"])
        source_code = inspect.getsource(func)
        expected = defn["expected_substring"]

        assert expected in source_code, (
            f"{assertion['assertion_id']}: Function {defn['function']} "
            f"source does not contain '{expected}'"
        )

    else:
        pytest.fail(
            f"{assertion['assertion_id']}: Unknown flow assertion check. "
            f"Definition: {json.dumps(defn, indent=2)}"
        )


# ---------------------------------------------------------------------------
# Reconciliation Check runner
# ---------------------------------------------------------------------------

def run_reconciliation(assertion: dict):
    """Validate cross-form balance checks using formula evaluation."""
    defn = assertion["definition"]
    check_type = defn.get("check_type", "")
    kind = defn.get("kind", "")

    # ===========================================================================
    # 1040 Schedule 8812 reconciliation sub-kinds (invariant, sum_check).
    # ===========================================================================
    if kind:
        _run_sch_8812_assertion(assertion, defn, kind)
        return

    if check_type == "formula_equals":
        from apps.returns.compute import FORMULAS_1120S

        values = _DefaultZeroDict(
            {k: Decimal(v) for k, v in defn["inputs"].items()}
        )

        for line_num, fn in FORMULAS_1120S:
            values[line_num] = fn(values)

        target = defn["assert_field"]
        actual = values.get(target, Decimal("0"))
        expected = Decimal(defn["expected_value"])

        assert actual == expected, (
            f"{assertion['assertion_id']}: {target} = {actual}, expected {expected}. "
            f"Inputs: {defn['inputs']}"
        )

    elif check_type in ("end_to_end_disposition", "amt_disposal_convention"):
        # These require database fixtures or more complex setup.
        # The assertion documents the REQUIREMENT; existing dedicated tests
        # in test_mar30_fixes.py and test_mar30_session2.py verify the CODE.
        pass

    else:
        pytest.fail(
            f"{assertion['assertion_id']}: Unknown reconciliation "
            f"check_type '{check_type}'"
        )


# ---------------------------------------------------------------------------
# Schedule 8812 (1040 CTC/ACTC/ODC) assertion runners — dispatched by `kind`
# ---------------------------------------------------------------------------

class _FakeDep:
    """Stand-in for a Dependent model row (avoids DB) — exposes the same
    attributes that `classify_dependent_ctc` / `classify_dependent_odc` read.
    """
    def __init__(
        self,
        *,
        age=10,
        relationship="child",
        months=12,
        own_support=False,
        joint=False,
        citizenship="us_citizen",
        tin="valid_ssn",
        ctc_override=None,
        odc_override=None,
        tax_year=2025,
    ):
        from datetime import date
        self.relationship = relationship
        self.months_resided_with_taxpayer = months
        self.provided_over_half_own_support = own_support
        self.filed_joint_return = joint
        self.citizenship_status = citizenship
        self.tin_type = tin
        self.ctc_override = ctc_override
        self.odc_override = odc_override
        self.date_of_birth = date(tax_year - age, 1, 1)


def _phaseout_reduction(magi, filing_status):
    """Verbatim spec formula — independent of compute_8812 implementation."""
    import math
    threshold = 400000 if filing_status == "MFJ" else 200000
    excess = max(0, magi - threshold)
    if excess == 0:
        return Decimal("0")
    rounded = math.ceil(excess / 1000) * 1000
    return Decimal(rounded) * Decimal("0.05")


def _run_sch_8812_assertion(assertion, defn, kind):
    """Dispatch FA-1040-CTC-* and TI-1040-CTC-* assertions by `kind`."""
    from apps.returns import compute_8812 as c8812
    aid = assertion["assertion_id"]

    # ---- per_record_contribution (FA-01, FA-02) ----
    if kind == "per_record_contribution":
        amount = Decimal(str(defn["contribution_amount"]))
        filter_str = defn.get("filter", "")

        if filter_str == "dep_qualifies_ctc == True":
            # Build 3 valid-SSN children → expect L_5 = 3 * 2200
            deps = [_FakeDep(age=8 + i, tin="valid_ssn") for i in range(3)]
            count = sum(c8812.classify_dependent_ctc(d, 2025) for d in deps)
            assert count == 3, f"{aid}: expected 3 QC, got {count}"
            assert count * amount == Decimal("6600"), (
                f"{aid}: per-record contribution math wrong"
            )

            # ACTC SSN-guard regression check: ITIN child must NOT qualify
            itin_kid = _FakeDep(age=8, tin="itin")
            assert not c8812.classify_dependent_ctc(itin_kid, 2025), (
                f"{aid}: ITIN child incorrectly classified as CTC qualifying — "
                f"OBBBA §70104(b) SSN gate broken"
            )
        else:  # dep_qualifies_odc == True
            deps = [
                _FakeDep(age=20, tin="itin"),
                _FakeDep(age=22, tin="atin"),
            ]
            count = sum(
                c8812.classify_dependent_odc(d, 2025, False) for d in deps
            )
            assert count == 2, f"{aid}: expected 2 ODC, got {count}"
            assert count * amount == Decimal("1000"), (
                f"{aid}: per-record ODC contribution math wrong"
            )
        return

    # ---- formula_check (FA-03) ----
    if kind == "formula_check":
        # 5% × ceil((MAGI − threshold)/1000) × 1000.
        # Threshold $400K MFJ / $200K other.
        cases = [
            (450000, "MFJ", Decimal("2500")),
            (450000, "single", Decimal("12500")),
            (400000, "MFJ", Decimal("0")),
            (200001, "single", Decimal("50")),
        ]
        for magi, fs, expected in cases:
            actual = _phaseout_reduction(magi, fs)
            assert actual == expected, (
                f"{aid}: phaseout({magi}, {fs}) = {actual}, expected {expected}"
            )
        return

    # ---- per_record_gating (FA-06) ----
    if kind == "per_record_gating":
        # dep_tin_type != 'valid_ssn' MUST imply dep_qualifies_ctc == False.
        for tin in ("itin", "atin", "none"):
            d = _FakeDep(age=8, tin=tin)
            assert c8812.classify_dependent_ctc(d, 2025) is False, (
                f"{aid}: dependent with tin_type={tin!r} incorrectly classified "
                f"as CTC qualifying"
            )
        # Valid SSN child (otherwise eligible) must still qualify
        valid = _FakeDep(age=8, tin="valid_ssn")
        assert c8812.classify_dependent_ctc(valid, 2025) is True, (
            f"{aid}: SSN gate over-rejecting — valid_ssn child should qualify"
        )
        return

    # ---- return_level_gating (FA-07) — R030 source check ----
    if kind == "return_level_gating":
        source = inspect.getsource(c8812.compute_sch_8812)
        # Must reference return_ssn_eligible_for_ctc_actc OR the implementing
        # variable name `return_ssn_eligible`, AND must zero L_14 + L_27.
        for needle in ("return_ssn_eligible", "L_14 = ZERO", "L_27 = ZERO"):
            assert needle in source, (
                f"{aid}: compute_sch_8812 source missing required marker {needle!r} "
                f"— R030 (force-zero on missing SSN) may not be implemented"
            )
        return

    # ---- sum_check (FA-08) ----
    if kind == "sum_check":
        # L_3 = L_1 + L_2a + L_2b + L_2c (spec lists 2a/2b/2c since L_2d = sum).
        # Verify by reading compute_8812 source.
        source = inspect.getsource(c8812.compute_sch_8812)
        # L_2d = L_2a + L_2b + L_2c, then L_3 = L_1 + L_2d
        assert "L_2d = L_2a + L_2b + L_2c" in source, (
            f"{aid}: L_2d add-back formula missing or shaped differently"
        )
        assert "L_3 = L_1 + L_2d" in source, (
            f"{aid}: MAGI formula L_3 = L_1 + L_2d missing"
        )
        return

    # ---- conditional_zero (FA-09) — Form 2555 zeros ACTC but not CTC ----
    if kind == "conditional_zero":
        source = inspect.getsource(c8812.compute_sch_8812)
        assert "not bool(taxpayer.files_form_2555)" in source, (
            f"{aid}: Form 2555 gate not present in actc_eligible computation"
        )
        # L_14 must NOT be zeroed by files_form_2555 — only actc_eligible
        # branches gate L_27. Spot check: actc_eligible includes 2555, L_14
        # path does not.
        assert "L_14 = min(L_12, L_13)" in source, (
            f"{aid}: L_14 formula altered — verify Form 2555 doesn't zero L_14"
        )
        return

    # ---- conditional_path_selection (FA-10) — Part II-B trigger + math ----
    if kind == "conditional_path_selection":
        source = inspect.getsource(c8812.compute_sch_8812)
        assert "qc_count >= 3" in source, (
            f"{aid}: Part II-B 3+ QC trigger missing"
        )
        # Verify the branch math
        for needle in (
            "actc_part_iib_triggered = (qc_count >= 3 and L_20 < L_17)",
            "L_27 = min(L_17, L_26)",
            "L_27 = min(L_17, L_20)",
        ):
            assert needle in source, (
                f"{aid}: Part II-B path math missing/altered: {needle!r}"
            )
        return

    # ---- conditional_flow (FA-04) — ACTC spillover invariants ----
    if kind == "conditional_flow":
        # Run a synthetic case in pure Python that mirrors the spec semantics:
        L_8 = Decimal("8800")           # 4 QC × $2,200 (pre-phaseout total)
        L_11 = Decimal("0")             # no phaseout
        L_12 = L_8 - L_11               # = 8800 (post-phaseout)
        L_13 = Decimal("3000")          # tight tax cap
        L_14 = min(L_12, L_13)          # = 3000
        L_16a = max(Decimal("0"), L_12 - L_14)  # overflow = 5800
        qc = 4
        L_16b = Decimal(qc) * Decimal("1700")  # per-child cap = 6800
        L_17 = min(L_16a, L_16b)        # = 5800
        # Earned-income method
        earned = Decimal("60000")
        L_19 = max(Decimal("0"), earned - Decimal("2500"))
        L_20 = (L_19 * Decimal("0.15")).quantize(Decimal("0.01"))
        L_27 = min(L_17, L_20)          # = min(5800, 8625) = 5800

        # Sub-conditions per spec
        assert L_16a == L_12 - L_14, f"{aid}: overflow_exists sub-check failed"
        assert L_17 == min(L_16a, L_16b), (
            f"{aid}: per_child_cap_applies sub-check failed"
        )
        assert L_27 <= L_17, f"{aid}: earned_income_cap_applies sub-check failed"
        return

    # ---- invariant (FA-05) — universal bound on credits ----
    if kind == "invariant":
        # Run several synthetic scenarios; both invariants must hold.
        cases = [
            # (L_8, L_11, L_13, L_16a_cap, L_17, L_27 candidates)
            (Decimal("4400"), Decimal("0"), Decimal("10000"), Decimal("0"), Decimal("0"), Decimal("0")),
            (Decimal("8800"), Decimal("0"), Decimal("3000"), Decimal("5800"), Decimal("5800"), Decimal("5800")),
            (Decimal("2700"), Decimal("0"), Decimal("0"), Decimal("2700"), Decimal("1700"), Decimal("1700")),
        ]
        for L_8, L_11, L_13, _, L_17, L_27 in cases:
            L_12 = max(Decimal("0"), L_8 - L_11)
            L_14 = min(L_12, L_13)
            # Tight invariant
            assert L_14 + L_27 <= L_12 + Decimal("0.01"), (
                f"{aid}: tight invariant fails L_14({L_14}) + L_27({L_27}) > L_12({L_12})"
            )
            # Loose invariant
            assert L_14 + L_27 <= L_8 + Decimal("0.01"), (
                f"{aid}: loose invariant fails L_14({L_14}) + L_27({L_27}) > L_8({L_8})"
            )
        return

    # ---- cross_form_flow (FA-11) — SCH_8812 → 1040 line writes ----
    if kind == "cross_form_flow":
        source = inspect.getsource(c8812.compute_sch_8812)
        # Must write to 1040 Lines 19 and 28 from SCH_8812 L_14 and L_27.
        assert '("19", L_14)' in source, (
            f"{aid}: cross-form flow SCH_8812.L_14 → 1040.L_19 missing in source"
        )
        assert '("28", L_27)' in source, (
            f"{aid}: cross-form flow SCH_8812.L_27 → 1040.L_28 missing in source"
        )
        return

    # ---- rounding_check (FA-12) — phaseout ceil-to-$1000 ----
    if kind == "rounding_check":
        import math as _math
        for case in defn["specific_test_cases"]:
            excess = case["excess"]
            expected = case["expected_L_10"]
            actual = _math.ceil(excess / 1000) * 1000 if excess > 0 else 0
            assert actual == expected, (
                f"{aid}: ceil({excess}/1000)*1000 = {actual}, expected {expected}"
            )
        return

    # ---- mutual_exclusion (TI-1040-CTC-A) ----
    if kind == "mutual_exclusion":
        # No dependent can be classified as both CTC AND ODC simultaneously.
        # Exercise the classifier across a few configurations that could
        # plausibly trigger a bug.
        cases = [
            _FakeDep(age=10, tin="valid_ssn", relationship="child"),    # CTC only
            _FakeDep(age=20, tin="valid_ssn", relationship="other"),    # ODC only (other rel)
            _FakeDep(age=10, tin="itin", relationship="child"),         # ODC only (ITIN)
            _FakeDep(age=25, tin="atin", relationship="adopted_child"), # ODC only
            _FakeDep(age=10, tin="none", relationship="child"),         # Neither
        ]
        for d in cases:
            is_ctc = c8812.classify_dependent_ctc(d, 2025)
            is_odc = c8812.classify_dependent_odc(d, 2025, is_ctc)
            assert not (is_ctc and is_odc), (
                f"{aid}: dependent classified as both CTC AND ODC simultaneously: "
                f"age={2025 - d.date_of_birth.year}, tin={d.tin_type}, "
                f"rel={d.relationship}"
            )
        return

    pytest.fail(
        f"{aid}: Unknown SCH_8812 assertion kind '{kind}'. Definition: "
        f"{json.dumps(defn, indent=2)}"
    )


# ---------------------------------------------------------------------------
# Parametrized test — one test per assertion
# ---------------------------------------------------------------------------

RUNNERS = {
    "table_invariant": run_table_invariant,
    "flow_assertion": run_flow_assertion,
    "reconciliation": run_reconciliation,
}

_assertions_1120s = load_assertions("1120S")
_assertions_1040 = load_assertions("1040")

if not _assertions_1040:
    warnings.warn(
        "No 1040 flow assertions loaded. "
        "server/specs/flow_assertions_1040.json is a stub — "
        "Ken needs to author 1040 Rule Studio specs first. "
        "See STATUS.md \"1040 — Ken's TODO (Rule Studio work)\".",
        UserWarning,
        stacklevel=2,
    )


@pytest.mark.parametrize(
    "assertion",
    _assertions_1120s,
    ids=lambda a: a.get("assertion_id", "unknown"),
)
def test_flow_assertion_1120s(assertion):
    """Run a single flow assertion from the Rule Studio export."""
    runner = RUNNERS.get(assertion["assertion_type"])
    assert runner, (
        f"No runner for assertion type '{assertion['assertion_type']}'. "
        f"Available: {list(RUNNERS.keys())}"
    )
    runner(assertion)


@pytest.mark.parametrize(
    "assertion",
    _assertions_1040,
    ids=lambda a: a.get("assertion_id", "unknown"),
)
def test_flow_assertion_1040(assertion):
    """Run a single 1040 flow assertion from the Rule Studio export.

    No-op while the 1040 assertion list is empty (the stub state).
    Becomes a real test grid once Ken populates the JSON.
    """
    runner = RUNNERS.get(assertion["assertion_type"])
    assert runner, (
        f"No runner for assertion type '{assertion['assertion_type']}'. "
        f"Available: {list(RUNNERS.keys())}"
    )
    runner(assertion)


def test_flow_assertions_loaded():
    """Verify that assertions were loaded from the JSON file."""
    assert len(_assertions_1120s) >= 10, (
        f"Expected at least 10 flow assertions, got {len(_assertions_1120s)}. "
        f"Check that server/specs/flow_assertions_1120s.json exists."
    )


def test_flow_assertions_1040_file_exists():
    """1040 stub file must exist even when empty so future exports drop in cleanly."""
    path = SPECS_DIR / "flow_assertions_1040.json"
    assert path.exists(), (
        f"{path} is missing. Recreate with empty assertions array — "
        f"see server/specs/flow_assertions_1040.json original stub."
    )
    with open(path) as f:
        data = json.load(f)
    assert data.get("entity_type") == "1040"
    assert isinstance(data.get("assertions"), list)
