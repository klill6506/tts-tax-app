"""
Export rule specs from Sherpa Tax Rule Studio database.
Connects to Rule Studio's Supabase instance (separate from tts-tax-app).
"""
import json
import sys
from pathlib import Path

import psycopg

RULE_STUDIO_DB = (
    "postgresql://postgres.ylqaejdqwuvwpglxnpgv:Tts580198$9"
    "@aws-1-us-east-1.pooler.supabase.com:5432/postgres"
)

SPECS_DIR = Path(__file__).resolve().parent.parent / "specs"


def connect():
    return psycopg.connect(RULE_STUDIO_DB)


def list_forms(conn):
    """List all tax forms in Rule Studio."""
    cur = conn.cursor()
    cur.execute(
        "SELECT id, jurisdiction, form_number, form_title, entity_types, "
        "tax_year, version, status "
        "FROM specs_taxform WHERE tax_year = 2025 ORDER BY form_number"
    )
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    return [dict(zip(cols, r)) for r in rows]


def export_form(conn, form_id: str, form_number: str) -> dict:
    """Export a complete form spec package."""
    cur = conn.cursor()

    # Metadata
    cur.execute(
        "SELECT id, jurisdiction, form_number, form_title, entity_types, "
        "tax_year, version, status, notes "
        "FROM specs_taxform WHERE id = %s", (form_id,)
    )
    cols = [d[0] for d in cur.description]
    form = dict(zip(cols, cur.fetchone()))

    # Facts
    cur.execute(
        "SELECT fact_key, label, data_type, required, default_value, "
        "validation_rule, choices, sort_order, notes "
        "FROM specs_formfact WHERE tax_form_id = %s ORDER BY sort_order, fact_key",
        (form_id,)
    )
    facts = [dict(zip([d[0] for d in cur.description], r)) for r in cur.fetchall()]

    # Rules (with authority links)
    cur.execute(
        "SELECT id, rule_id, title, description, rule_type, conditions, formula, "
        "inputs, outputs, precedence, exceptions, notes, sort_order "
        "FROM specs_formrule WHERE tax_form_id = %s ORDER BY sort_order, rule_id",
        (form_id,)
    )
    rule_cols = [d[0] for d in cur.description]
    raw_rules = [dict(zip(rule_cols, r)) for r in cur.fetchall()]

    rules = []
    for rule in raw_rules:
        rule_uuid = rule.pop("id")
        # Get authority links
        cur.execute(
            "SELECT ral.support_level, ral.relevance_note, "
            "asrc.source_code, asrc.title, asrc.citation, asrc.source_type, asrc.source_rank "
            "FROM sources_ruleauthoritylink ral "
            "JOIN sources_authoritysource asrc ON ral.authority_source_id = asrc.id "
            "WHERE ral.form_rule_id = %s ORDER BY ral.sort_order",
            (rule_uuid,)
        )
        auth_cols = [d[0] for d in cur.description]
        rule["authorities"] = [dict(zip(auth_cols, r)) for r in cur.fetchall()]
        rules.append(rule)

    # Lines
    cur.execute(
        "SELECT line_number, description, calculation, source_facts, source_rules, "
        "destination_form, line_type, notes, sort_order "
        "FROM specs_formline WHERE tax_form_id = %s ORDER BY sort_order, line_number",
        (form_id,)
    )
    lines = [dict(zip([d[0] for d in cur.description], r)) for r in cur.fetchall()]

    # Diagnostics
    cur.execute(
        "SELECT diagnostic_id, title, severity, condition, message, notes "
        "FROM specs_formdiagnostic WHERE tax_form_id = %s ORDER BY diagnostic_id",
        (form_id,)
    )
    diagnostics = [dict(zip([d[0] for d in cur.description], r)) for r in cur.fetchall()]

    # Test scenarios
    cur.execute(
        "SELECT scenario_name, scenario_type, inputs, expected_outputs, notes, sort_order "
        "FROM specs_testscenario WHERE tax_form_id = %s ORDER BY sort_order, scenario_name",
        (form_id,)
    )
    tests = [dict(zip([d[0] for d in cur.description], r)) for r in cur.fetchall()]

    return {
        "export_version": "1.0",
        "metadata": {
            "form_number": form["form_number"],
            "form_title": form["form_title"],
            "jurisdiction": form["jurisdiction"],
            "entity_types": form["entity_types"],
            "tax_year": form["tax_year"],
            "version": form["version"],
            "status": form["status"],
        },
        "facts": facts,
        "rules": rules,
        "line_map": lines,
        "diagnostics": diagnostics,
        "tests": tests,
    }


# Mapping from form_number in Rule Studio -> output filename
FORM_FILE_MAP = {
    # Core 1120-S forms
    "1120S_PAGE1": "1120s_page1_spec.json",
    "SCH_K_1120S": "1120s_sched_k_spec.json",
    "K1_1120S": "1120s_k1_spec.json",
    "1120S_M1": "1120s_m1_spec.json",
    "1120S_M2": "1120s_m2_spec.json",
    "SCHD_1120S": "sched_d_1120s_spec.json",
    "8949": "form_8949_spec.json",
    "4797": "form_4797_spec.json",
    # Supporting forms
    "4562": "form_4562_spec.json",
    "1125A": "form_1125a_spec.json",
    "1125E": "form_1125e_spec.json",
    "8825": "form_8825_spec.json",
    "7203": "form_7203_spec.json",
    # State
    "GA600S": "ga600s_spec.json",
    # Procedural
    "7004": "form_7004_spec.json",
    "8879S": "form_8879s_spec.json",
    "8453S": "form_8453s_spec.json",
}


def main():
    conn = connect()
    forms = list_forms(conn)

    print(f"Found {len(forms)} forms in Rule Studio (TY 2025):")
    for f in forms:
        print(f"  [{f['status']:>8}] {f['form_number']} - {f['form_title']} "
              f"(v{f['version']}, entities={f['entity_types']})")

    SPECS_DIR.mkdir(parents=True, exist_ok=True)

    # Deduplicate: if multiple versions, keep highest version
    best: dict[str, dict] = {}
    for f in forms:
        fn = f["form_number"]
        if fn not in best or f["version"] > best[fn]["version"]:
            best[fn] = f

    exported = 0
    for fn, f in best.items():
        outfile = FORM_FILE_MAP.get(fn)
        if not outfile:
            print(f"  SKIP: No output mapping for '{fn}'")
            continue

        print(f"\n  Exporting '{fn}' v{f['version']} -> {outfile}...")
        spec = export_form(conn, str(f["id"]), fn)
        outpath = SPECS_DIR / outfile
        with open(outpath, "w") as fp:
            json.dump(spec, fp, indent=2, default=str)
        print(f"    -> {outpath} ({len(spec['rules'])} rules, {len(spec['line_map'])} lines, "
              f"{len(spec['tests'])} tests, {len(spec['diagnostics'])} diagnostics)")
        exported += 1

    conn.close()
    print(f"\nDone. Exported {exported} specs to {SPECS_DIR}")


if __name__ == "__main__":
    main()
