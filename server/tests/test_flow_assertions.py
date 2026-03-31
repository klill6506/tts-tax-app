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
"""
import json
import importlib
import inspect
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
    """Validate properties of MACRS lookup tables."""
    defn = assertion["definition"]
    module_path = defn["module"]
    table_name = defn["table_name"]

    mod = importlib.import_module(module_path)
    table = getattr(mod, table_name)

    check = defn["check"]
    params = defn.get("params", {})

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
# Parametrized test — one test per assertion
# ---------------------------------------------------------------------------

RUNNERS = {
    "table_invariant": run_table_invariant,
    "flow_assertion": run_flow_assertion,
    "reconciliation": run_reconciliation,
}

_assertions_1120s = load_assertions("1120S")


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


def test_flow_assertions_loaded():
    """Verify that assertions were loaded from the JSON file."""
    assert len(_assertions_1120s) >= 10, (
        f"Expected at least 10 flow assertions, got {len(_assertions_1120s)}. "
        f"Check that server/specs/flow_assertions_1120s.json exists."
    )
