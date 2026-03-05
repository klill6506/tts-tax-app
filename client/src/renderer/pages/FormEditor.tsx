import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  get, patch, post, del,
  renderPdf, renderK1s, renderK1, render7206,
  render1125a, render8825, render7203, render7203s, render7004,
} from "../lib/api";
import { useFormContext } from "../lib/form-context";
import CurrencyInput from "../components/CurrencyInput";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface FieldValue {
  id: string;
  form_line: string;
  line_number: string;
  label: string;
  field_type: "currency" | "integer" | "text" | "boolean" | "percentage";
  section_code: string;
  value: string;
  is_overridden: boolean;
  is_computed: boolean;
}

interface OtherDeductionRow {
  id: string;
  description: string;
  amount: string;
  category: string;
  sort_order: number;
  source: string;
}

interface OfficerRow {
  id: string;
  name: string;
  title: string;
  ssn: string;
  percent_time: string;
  percent_ownership: string;
  compensation: string;
}

interface ShareholderRow {
  id: string;
  name: string;
  ssn: string;
  address_line1: string;
  address_line2: string;
  city: string;
  state: string;
  zip_code: string;
  ownership_percentage: string;
  beginning_shares: string;
  ending_shares: string;
  distributions: string;
  health_insurance_premium: string;
  // Form 7203 basis fields
  stock_basis_boy: string;
  capital_contributions: string;
  depletion: string;
  suspended_ordinary_loss: string;
  suspended_rental_re_loss: string;
  suspended_other_rental_loss: string;
  suspended_st_capital_loss: string;
  suspended_lt_capital_loss: string;
  suspended_1231_loss: string;
  suspended_other_loss: string;
  // Links & metadata
  linked_client: string | null;
  linked_client_name: string | null;
  is_active: boolean;
  sort_order: number;
}

interface RentalPropertyRow {
  id: string;
  description: string;
  property_type: string;
  fair_rental_days: number;
  personal_use_days: number;
  rents_received: string;
  advertising: string;
  auto_and_travel: string;
  cleaning_and_maintenance: string;
  commissions: string;
  insurance: string;
  legal_and_professional: string;
  interest_mortgage: string;
  interest_other: string;
  repairs: string;
  taxes: string;
  utilities: string;
  depreciation: string;
  other_expenses: string;
  total_expenses: string;
  net_rent: string;
}

interface EntityInfo {
  id: string;
  name: string;
  entity_type: string;
  legal_name: string;
  ein: string;
  phone: string;
  address_line1: string;
  address_line2: string;
  city: string;
  state: string;
  zip_code: string;
  date_incorporated: string;
  state_incorporated: string;
  business_activity: string;
  naics_code: string;
  client: string;
}

interface PreparerInfoData {
  id: string;
  preparer_name: string;
  ptin: string;
  signature_date: string | null;
  is_self_employed: boolean;
  firm_name: string;
  firm_ein: string;
  firm_phone: string;
  firm_address: string;
  firm_city: string;
  firm_state: string;
  firm_zip: string;
  designee_name: string;
  designee_phone: string;
  designee_pin: string;
}

interface PriorYearData {
  id: string;
  year: number;
  form_code: string;
  line_values: Record<string, number>;
  other_deductions: Record<string, number>;
  balance_sheet: Record<string, number>;
}

interface TaxReturnData {
  id: string;
  tax_year_id: string;
  year: number;
  entity_name: string;
  entity_id: string;
  client_name: string;
  form_code: string;
  status: string;
  accounting_method: string;
  tax_year_start: string | null;
  tax_year_end: string | null;
  is_initial_return: boolean;
  is_final_return: boolean;
  is_name_change: boolean;
  is_address_change: boolean;
  is_amended_return: boolean;
  s_election_date: string | null;
  number_of_shareholders: number | null;
  product_or_service: string;
  business_activity_code: string;
  // Extension (Form 7004)
  extension_filed: boolean;
  extension_date: string | null;
  tentative_tax: string;
  total_payments: string;
  balance_due: string;
  // Bank info
  bank_routing_number: string;
  bank_account_number: string;
  bank_account_type: string;
  // Preparer assignment
  preparer: string | null;
  preparer_display_name: string | null;
  staff_preparer: string | null;
  staff_preparer_display_name: string | null;
  signature_date: string | null;
  // State returns
  federal_return_id: string | null;
  filing_states: string[];
  state_returns: { id: string; form_code: string; status: string }[];
  field_values: FieldValue[];
  other_deductions: OtherDeductionRow[];
  officers: OfficerRow[];
  shareholders: ShareholderRow[];
  rental_properties: RentalPropertyRow[];
  preparer_info: PreparerInfoData | null;
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// Computed field formulas (mirrors server/apps/returns/compute.py)
// ---------------------------------------------------------------------------

function val(values: Record<string, number>, line: string): number {
  return values[line] ?? 0;
}

function sumLines(values: Record<string, number>, ...lines: string[]): number {
  return lines.reduce((acc, ln) => acc + val(values, ln), 0);
}

/** Ordered list of [line_number, formula].  Dependencies must come first. */
const FORMULAS_1120S: [string, (v: Record<string, number>) => number][] = [
  // Schedule A — Cost of Goods Sold
  ["A6", (v) => sumLines(v, "A1","A2","A3","A4","A5")],
  ["A8", (v) => val(v, "A6") - val(v, "A7")],
  // Page 1 — Income  (Line 2 = Schedule A line 8)
  ["2", (v) => val(v, "A8")],
  ["1c", (v) => val(v, "1a") - val(v, "1b")],
  ["3", (v) => val(v, "1c") - val(v, "2")],
  ["6", (v) => val(v, "3") + val(v, "4") + val(v, "5")],
  // Page 1 — Deductions
  ["20", (v) => sumLines(v, "7","8","9","10","11","12","13","14","15","16","17","18","19")],
  ["21", (v) => val(v, "6") - val(v, "20")],
  // Page 1 — Tax and Payments
  ["22c", (v) => val(v, "22a") + val(v, "22b")],
  ["23d", (v) => val(v, "23a") + val(v, "23b") + val(v, "23c")],
  ["25", (v) => Math.max(0, val(v, "22c") - val(v, "23d"))],
  ["26", (v) => Math.max(0, val(v, "23d") - val(v, "22c"))],
  // Schedule L — Balance Sheet (inventory flows from COGS)
  ["L3a", (v) => val(v, "A1")],
  ["L3d", (v) => val(v, "A7")],
  ["L14a", (v) => sumLines(v, "L1a","L2a","L3a","L5a","L7a") + val(v, "L9a") - val(v, "L9b")],
  ["L14d", (v) => sumLines(v, "L1d","L2d","L3d","L5d","L7d") + val(v, "L9d") - val(v, "L9e")],
  ["L27a", (v) => sumLines(v, "L15a","L17a","L18a","L20a","L21a","L23a","L24a","L25a")],
  ["L27d", (v) => sumLines(v, "L15d","L17d","L18d","L20d","L21d","L23d","L24d","L25d")],
  // Schedule M-1
  ["M1_4", (v) => sumLines(v, "M1_1","M1_2","M1_3a","M1_3b")],
  ["M1_7", (v) => val(v, "M1_5") + val(v, "M1_6")],
  ["M1_8", (v) => val(v, "M1_4") - val(v, "M1_7")],
  // Schedule M-2
  ["M2_2", (v) => Math.max(0, val(v, "21"))],
  ["M2_4", (v) => Math.max(0, -val(v, "21"))],
  ["M2_6", (v) => val(v, "M2_1") + val(v, "M2_2") + val(v, "M2_3") - val(v, "M2_4") - val(v, "M2_5")],
  ["M2_8", (v) => val(v, "M2_6") - val(v, "M2_7")],
];

/** GA-600S compute formulas (mirrors server compute.py GA section). */
const FORMULAS_GA600S: [string, (v: Record<string, number>) => number][] = [
  // Schedule 7 & 8
  ["S7_8", (v) => sumLines(v, "S7_1","S7_2","S7_3","S7_5","S7_6","S7_7")],
  ["S8_5", (v) => sumLines(v, "S8_1","S8_2","S8_3","S8_4")],
  // Schedule 6
  ["S6_3c", (v) => val(v, "S6_3a") - val(v, "S6_3b")],
  ["S6_7", (v) => sumLines(v, "S6_1","S6_2","S6_3c","S6_4a","S6_4b","S6_4c","S6_4d","S6_4e","S6_4f","S6_5","S6_6")],
  ["S6_8", (v) => val(v, "S7_8")],
  ["S6_9", (v) => val(v, "S6_7") + val(v, "S6_8")],
  ["S6_10", (v) => val(v, "S8_5")],
  ["S6_11", (v) => val(v, "S6_9") - val(v, "S6_10")],
  // Schedule 5
  ["S5_1", (v) => val(v, "S6_11")],
  ["S5_3", (v) => val(v, "S5_1") - val(v, "S5_2")],
  ["S5_5", (v) => val(v, "S5_3") * val(v, "S5_4")],
  ["S5_7", (v) => val(v, "S5_5") + val(v, "S5_6")],
  // Schedule 1
  ["S1_1", (v) => val(v, "S5_7")],
  ["S1_3", (v) => val(v, "S1_1") + val(v, "S1_2")],
  ["S1_6", (v) => val(v, "S1_3") - val(v, "S1_4") - val(v, "S1_5")],
  ["S1_7", (v) => Math.max(0, val(v, "S1_6")) * 0.0539],
  // Schedule 3
  ["S3_4", (v) => sumLines(v, "S3_1","S3_2","S3_3")],
  ["S3_6", (v) => val(v, "S3_4") * val(v, "S3_5")],
  // Schedule 4
  ["S4_1a", (v) => val(v, "S1_7")],
  ["S4_1c", (v) => val(v, "S4_1a") + val(v, "S4_1b")],
  ["S4_2c", (v) => val(v, "S4_2a") + val(v, "S4_2b")],
  ["S4_3c", (v) => val(v, "S4_3a") + val(v, "S4_3b")],
  ["S4_4c", (v) => val(v, "S4_4a") + val(v, "S4_4b")],
  ["S4_5a", (v) => Math.max(0, val(v,"S4_1a") - val(v,"S4_2a") - val(v,"S4_3a") - val(v,"S4_4a"))],
  ["S4_5b", (v) => Math.max(0, val(v,"S4_1b") - val(v,"S4_2b") - val(v,"S4_3b") - val(v,"S4_4b"))],
  ["S4_5c", (v) => val(v, "S4_5a") + val(v, "S4_5b")],
  ["S4_6a", (v) => Math.max(0, val(v,"S4_2a") + val(v,"S4_3a") + val(v,"S4_4a") - val(v,"S4_1a"))],
  ["S4_6b", (v) => Math.max(0, val(v,"S4_2b") + val(v,"S4_3b") + val(v,"S4_4b") - val(v,"S4_1b"))],
  ["S4_6c", (v) => val(v, "S4_6a") + val(v, "S4_6b")],
  ["S4_7c", (v) => val(v, "S4_7a") + val(v, "S4_7b")],
  ["S4_8c", (v) => val(v, "S4_8a") + val(v, "S4_8b")],
  ["S4_9c", (v) => val(v, "S4_9a") + val(v, "S4_9b")],
  ["S4_10a", (v) => val(v,"S4_5a") + val(v,"S4_7a") + val(v,"S4_8a") + val(v,"S4_9a")],
  ["S4_10b", (v) => val(v,"S4_5b") + val(v,"S4_7b") + val(v,"S4_8b") + val(v,"S4_9b")],
  ["S4_10c", (v) => val(v, "S4_10a") + val(v, "S4_10b")],
  ["S4_11a", (v) => val(v, "S4_6a")],
  ["S4_11b", (v) => val(v, "S4_6b")],
  ["S4_11c", (v) => val(v, "S4_11a") + val(v, "S4_11b")],
];

/** Set of line numbers that are computed — used for quick lookup. */
const COMPUTED_LINES = new Set([
  ...FORMULAS_1120S.map(([ln]) => ln),
  ...FORMULAS_GA600S.map(([ln]) => ln),
]);

/**
 * Run all formulas over current field values and return updated values.
 * Only updates computed fields — input fields are left untouched.
 */
function computeFields(fieldValues: FieldValue[], formCode?: string): FieldValue[] {
  // Select formula set based on form code
  const formulas = formCode === "GA-600S" ? FORMULAS_GA600S : FORMULAS_1120S;

  // Build line_number → numeric value map from all current values
  const numValues: Record<string, number> = {};
  for (const fv of fieldValues) {
    const n = parseFloat(fv.value);
    numValues[fv.line_number] = isNaN(n) ? 0 : n;
  }

  // Evaluate formulas in order
  const computedValues: Record<string, string> = {};
  for (const [lineNum, fn] of formulas) {
    const result = fn(numValues);
    numValues[lineNum] = result; // update for downstream formulas
    computedValues[lineNum] = result.toFixed(2);
  }

  // Return updated field values with computed results applied
  // Skip overridden computed fields — the user's manual value takes priority
  return fieldValues.map((fv) => {
    if (COMPUTED_LINES.has(fv.line_number) && !fv.is_overridden) {
      return { ...fv, value: computedValues[fv.line_number] ?? fv.value };
    }
    return fv;
  });
}

// ---------------------------------------------------------------------------
// Section tab metadata (matches seed_1120s.py section codes)
// ---------------------------------------------------------------------------

/** Each tab can show one or more section codes. */
const SECTION_TABS: { id: string; label: string; sections: string[] }[] = [
  { id: "info", label: "Info", sections: [] },
  { id: "shareholders", label: "Shareholders", sections: [] },
  { id: "page1", label: "Income & Ded.", sections: ["page1_income", "sched_a", "page1_deductions"] },
  { id: "sched_k", label: "Sched K", sections: ["sched_k"] },
  { id: "balance_sheets", label: "Balance Sheet", sections: ["sched_l", "sched_m1", "sched_m2"] },
  { id: "sched_b", label: "Sched B", sections: ["sched_b"] },
  { id: "rental", label: "Rental (8825)", sections: [] },
  { id: "tax_payments", label: "Tax & Payments", sections: ["page1_tax"] },
  { id: "prior_year", label: "PY Compare", sections: [] },
  { id: "state", label: "State", sections: [] },
];

/** GA-600S section tabs — shown when editing a GA state return. */
const GA_SECTION_TABS: { id: string; label: string; sections: string[] }[] = [
  { id: "info", label: "Info", sections: [] },
  { id: "sched_6", label: "Sched 6 — Income", sections: ["sched_6"] },
  { id: "sched_7", label: "Sched 7 — Additions", sections: ["sched_7"] },
  { id: "sched_8", label: "Sched 8 — Subtractions", sections: ["sched_8"] },
  { id: "sched_5", label: "Sched 5 — Apportionment", sections: ["sched_5"] },
  { id: "sched_3", label: "Sched 3 — Net Worth", sections: ["sched_3"] },
  { id: "sched_1", label: "Sched 1 — Tax", sections: ["sched_1"] },
  { id: "sched_4", label: "Sched 4 — Tax Due", sections: ["sched_4"] },
];

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function FormEditor() {
  const { taxReturnId } = useParams<{ taxReturnId: string }>();

  const [returnData, setReturnData] = useState<TaxReturnData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("info");
  const [primaryTab, setPrimaryTab] = useState<"input" | "forms" | "diagnostics">("input");

  // Prior year data
  const [priorYear, setPriorYear] = useState<PriorYearData | null>(null);

  useEffect(() => {
    if (!taxReturnId) return;
    get(`/tax-returns/${taxReturnId}/prior-year/`).then((res) => {
      if (res.ok) setPriorYear(res.data as PriorYearData);
    });
  }, [taxReturnId]);

  /** Lookup prior year amount for a form line number. */
  const pyLookup = useMemo(() => {
    if (!priorYear) return {};
    return priorYear.line_values;
  }, [priorYear]);

  // Form context — so AiHelpPanel knows which form/tab we're on
  const { setFormContext, clearFormContext } = useFormContext();
  useEffect(() => {
    if (returnData) {
      const tabLabel = SECTION_TABS.find((t) => t.id === activeTab)?.label || "";
      setFormContext(returnData.form_code, tabLabel);
    }
    return () => clearFormContext();
  }, [returnData?.form_code, activeTab]);

  // Dirty tracking
  const dirtyRef = useRef<Map<string, string>>(new Map());
  const [saveStatus, setSaveStatus] = useState<
    "idle" | "saving" | "saved" | "error"
  >("idle");
  const flushTimerRef = useRef<number | null>(null);

  // ---- Data fetching ----

  /** Set return data and recompute calculated fields. */
  function setReturnWithCompute(data: TaxReturnData) {
    setReturnData({
      ...data,
      field_values: computeFields(data.field_values, data.form_code),
    });
  }

  /** Re-fetch the full return (used after mutations in sub-tabs). */
  const refreshReturn = useCallback(async () => {
    if (!taxReturnId) return;
    const res = await get(`/tax-returns/${taxReturnId}/`);
    if (res.ok) setReturnWithCompute(res.data as TaxReturnData);
  }, [taxReturnId]);

  useEffect(() => {
    if (!taxReturnId) return;
    get(`/tax-returns/${taxReturnId}/`).then((res) => {
      if (res.ok) {
        setReturnWithCompute(res.data as TaxReturnData);
      } else {
        setError("Failed to load tax return.");
      }
      setLoading(false);
    });
  }, [taxReturnId]);

  // ---- Group fields by section ----

  const fieldsBySection = useMemo(() => {
    if (!returnData) return {};
    const map: Record<string, FieldValue[]> = {};
    for (const fv of returnData.field_values) {
      if (!map[fv.section_code]) map[fv.section_code] = [];
      map[fv.section_code].push(fv);
    }
    return map;
  }, [returnData]);

  const isStateReturn = returnData?.form_code === "GA-600S";
  const hasFilingStates = (returnData?.filing_states || []).length > 0 || (returnData?.state_returns || []).length > 0;
  const sectionTabs = useMemo(() => {
    if (isStateReturn) return GA_SECTION_TABS;
    let tabs = SECTION_TABS;
    // Hide State tab on federal returns if no filing states configured
    if (!hasFilingStates) tabs = tabs.filter((t) => t.id !== "state");
    // Hide PY Compare tab if no prior year data
    if (!priorYear) tabs = tabs.filter((t) => t.id !== "prior_year");
    return tabs;
  }, [isStateReturn, hasFilingStates, priorYear]);

  // Reset tab when switching between federal/state returns
  useEffect(() => {
    setActiveTab("info");
  }, [taxReturnId]);

  const activeTabDef = sectionTabs.find((t) => t.id === activeTab);

  /** All fields for the active tab (flattened across its sections). */
  const fieldsForActiveTab = useMemo(() => {
    if (!activeTabDef) return [];
    return activeTabDef.sections.flatMap((s) => fieldsBySection[s] || []);
  }, [activeTabDef, fieldsBySection]);

  // ---- Save logic ----

  async function flushDirty() {
    const dirty = dirtyRef.current;
    if (dirty.size === 0) return;

    const fields = Array.from(dirty.entries()).map(([form_line, value]) => ({
      form_line,
      value,
    }));

    dirtyRef.current = new Map();
    setSaveStatus("saving");

    const res = await patch(`/tax-returns/${taxReturnId}/fields/`, { fields });
    if (res.ok) {
      setSaveStatus("saved");
      // Re-fetch to get server-computed values
      const refresh = await get(`/tax-returns/${taxReturnId}/`);
      if (refresh.ok) setReturnWithCompute(refresh.data as TaxReturnData);
      setTimeout(
        () => setSaveStatus((s) => (s === "saved" ? "idle" : s)),
        2000,
      );
    } else {
      setSaveStatus("error");
      for (const f of fields) {
        dirtyRef.current.set(f.form_line, f.value);
      }
    }
  }

  function scheduleFlush() {
    if (flushTimerRef.current) clearTimeout(flushTimerRef.current);
    flushTimerRef.current = window.setTimeout(flushDirty, 500);
  }

  function handleFieldChange(formLineId: string, newValue: string) {
    dirtyRef.current.set(formLineId, newValue);

    // Update local state immediately and recompute calculated fields
    setReturnData((prev) => {
      if (!prev) return prev;
      const updated = prev.field_values.map((fv) =>
        fv.form_line === formLineId
          ? { ...fv, value: newValue, is_overridden: true }
          : fv,
      );
      return { ...prev, field_values: computeFields(updated, prev.form_code) };
    });

    scheduleFlush();
  }

  // ---- Import TB ----

  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<string | null>(null);

  async function handleImportTB() {
    if (!taxReturnId) return;
    setImporting(true);
    setImportResult(null);
    const res = await post(`/tax-returns/${taxReturnId}/import-tb/`);
    setImporting(false);
    if (res.ok) {
      const data = res.data as {
        imported: number;
        total_rows: number;
        mapped_rows: number;
        unmapped_rows: number;
      };
      setImportResult(
        `Imported ${data.imported} fields from ${data.mapped_rows}/${data.total_rows} mapped rows`,
      );
      // Reload the return data to show updated values (with computed fields)
      const refresh = await get(`/tax-returns/${taxReturnId}/`);
      if (refresh.ok) setReturnWithCompute(refresh.data as TaxReturnData);
      setTimeout(() => setImportResult(null), 5000);
    } else {
      const err = res.data as { error?: string };
      setImportResult(err.error || "Import failed.");
    }
  }

  // Ctrl+S keyboard shortcut
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        e.preventDefault();
        flushDirty();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [taxReturnId]);

  // Auto-save every 10 seconds as a safety net
  useEffect(() => {
    const interval = window.setInterval(() => {
      flushDirty();
    }, 10_000);
    return () => clearInterval(interval);
  }, [taxReturnId]);

  // ---- Render ----

  if (loading) return <p className="text-sm text-tx-secondary">Loading...</p>;
  if (error)
    return <p className="text-sm text-danger">{error}</p>;
  if (!returnData)
    return <p className="text-sm text-danger">Return not found.</p>;

  return (
    <div>
      {/* Breadcrumb */}
      <div className="mb-4 text-sm text-tx-secondary">
        <Link to="/" className="text-primary-text hover:underline">
          Return Manager
        </Link>
        <span className="mx-2">/</span>
        <span className="text-tx">{returnData.client_name}</span>
        <span className="mx-2">/</span>
        <span className="text-tx">{returnData.entity_name}</span>
        <span className="mx-2">/</span>
        {returnData.federal_return_id ? (
          <>
            <Link to={`/tax-returns/${returnData.federal_return_id}/editor`} className="text-primary hover:underline">
              Federal Return
            </Link>
            <span className="mx-2">/</span>
            <span className="font-medium text-tx">
              {returnData.form_code} &mdash; {returnData.year}
            </span>
          </>
        ) : (
          <span className="font-medium text-tx">
            {returnData.form_code} &mdash; {returnData.year}
          </span>
        )}
      </div>

      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-tx">
            Form {returnData.form_code}
          </h1>
          <p className="text-sm text-tx-secondary">
            {returnData.entity_name} &mdash; Tax Year {returnData.year}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <ReturnStatusPill status={returnData.status} />
          {importResult && (
            <span className="text-sm font-medium text-success">
              {importResult}
            </span>
          )}
          <SaveStatusIndicator status={saveStatus} />
          {!isStateReturn && (
            <button
              onClick={handleImportTB}
              disabled={importing}
              className="rounded-lg bg-success px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-success-hover disabled:opacity-50"
            >
              {importing ? "Importing..." : "Import Trial Balance"}
            </button>
          )}
        </div>
      </div>

      {/* Primary tab bar — Input / Forms / Diagnostics */}
      <div className="mb-4 flex items-center gap-0 border-b-2 border-border">
        {(["input", "forms", "diagnostics"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setPrimaryTab(tab)}
            className={`px-5 py-2.5 text-sm font-semibold uppercase tracking-wide transition ${
              primaryTab === tab
                ? "border-b-2 border-primary text-primary-text -mb-[2px]"
                : "text-tx-secondary hover:text-tx"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* PRIMARY TAB: INPUT */}
      {primaryTab === "input" && (
        <>
          {/* Section tab bar */}
          <div className="mb-4 flex flex-wrap gap-1 border-b border-border">
            {sectionTabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`whitespace-nowrap px-3 py-1.5 text-xs font-medium transition ${
                  activeTab === tab.id
                    ? "border-b-2 border-primary text-primary-text"
                    : "text-tx-secondary hover:text-tx"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Active section content */}
          {activeTab === "info" ? (
            <InfoSection returnData={returnData} onRefresh={refreshReturn} />
          ) : activeTab === "shareholders" ? (
            <ShareholdersSection
              taxReturnId={taxReturnId!}
              shareholders={returnData.shareholders || []}
              onRefresh={refreshReturn}
            />
          ) : activeTab === "page1" ? (
            <IncomeDeductionsSection
              taxReturnId={taxReturnId!}
              fieldsBySection={fieldsBySection}
              otherDeductions={returnData.other_deductions || []}
              onChange={handleFieldChange}
              onRefresh={refreshReturn}
              priorYear={priorYear}
            />
          ) : activeTab === "rental" ? (
            <RentalPropertiesSection
              taxReturnId={taxReturnId!}
              properties={returnData.rental_properties || []}
              onRefresh={refreshReturn}
            />
          ) : activeTab === "balance_sheets" ? (
            <BalanceSheetsSection
              taxReturnId={taxReturnId!}
              fieldsBySection={fieldsBySection}
              onChange={handleFieldChange}
              onRefresh={refreshReturn}
              priorYear={priorYear}
            />
          ) : activeTab === "tax_payments" ? (
            <TaxPaymentsSection
              taxReturnId={taxReturnId!}
              fieldsBySection={fieldsBySection}
              returnData={returnData}
              onChange={handleFieldChange}
              onRefresh={refreshReturn}
            />
          ) : activeTab === "sched_b" ? (
            <ScheduleBSection
              fields={fieldsBySection["sched_b"] || []}
              returnData={returnData}
              onChange={handleFieldChange}
            />
          ) : activeTab === "prior_year" ? (
            <PriorYearSummarySection
              taxReturnId={taxReturnId!}
              fieldsBySection={fieldsBySection}
              priorYear={priorYear}
              currentYear={returnData.year}
            />
          ) : activeTab === "state" ? (
            <StateSection
              taxReturnId={taxReturnId!}
              returnData={returnData}
              onRefresh={refreshReturn}
            />
          ) : (
            <StandardSection
              sections={activeTabDef?.sections ?? []}
              fieldsBySection={fieldsBySection}
              onChange={handleFieldChange}
              pyLookup={pyLookup}
            />
          )}
        </>
      )}

      {/* PRIMARY TAB: FORMS */}
      {primaryTab === "forms" && (
        <FormsTab
          taxReturnId={taxReturnId!}
          returnData={returnData}
        />
      )}

      {/* PRIMARY TAB: DIAGNOSTICS */}
      {primaryTab === "diagnostics" && (
        <DiagnosticsTab
          taxYearId={returnData.tax_year_id}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Info Section — Entity + Return metadata + Officers
// ---------------------------------------------------------------------------

function InfoSection({
  returnData,
  onRefresh,
}: {
  returnData: TaxReturnData;
  onRefresh: () => Promise<void>;
}) {
  const [entity, setEntity] = useState<EntityInfo | null>(null);
  const [loadingEntity, setLoadingEntity] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);

  // Return-level editable fields
  const [accountingMethod, setAccountingMethod] = useState(
    returnData.accounting_method || "cash"
  );
  const [taxYearStart, setTaxYearStart] = useState(
    returnData.tax_year_start || ""
  );
  const [taxYearEnd, setTaxYearEnd] = useState(
    returnData.tax_year_end || ""
  );
  const [isInitialReturn, setIsInitialReturn] = useState(returnData.is_initial_return ?? false);
  const [isFinalReturn, setIsFinalReturn] = useState(returnData.is_final_return ?? false);
  const [isNameChange, setIsNameChange] = useState(returnData.is_name_change ?? false);
  const [isAddressChange, setIsAddressChange] = useState(returnData.is_address_change ?? false);
  const [isAmendedReturn, setIsAmendedReturn] = useState(returnData.is_amended_return ?? false);
  const [sElectionDate, setSElectionDate] = useState(returnData.s_election_date || "");
  const [numberOfShareholders, setNumberOfShareholders] = useState(
    returnData.number_of_shareholders != null ? String(returnData.number_of_shareholders) : ""
  );
  const [productOrService, setProductOrService] = useState(returnData.product_or_service || "");
  const [businessActivityCode, setBusinessActivityCode] = useState(returnData.business_activity_code || "");

  // Preparer (inline on Info tab)
  const [preparers, setPreparers] = useState<PreparerOption[]>([]);
  const [selectedPreparer, setSelectedPreparer] = useState<string>(returnData.preparer || "");
  const [staffPreparerId, setStaffPreparerId] = useState<string>(returnData.staff_preparer || "");
  const [signatureDate, setSignatureDate] = useState<string>(returnData.signature_date || "");

  // Officers
  const [officers, setOfficers] = useState<OfficerRow[]>(
    returnData.officers || []
  );
  const [editingOfficer, setEditingOfficer] = useState<Partial<OfficerRow> | null>(null);
  const [officerSaving, setOfficerSaving] = useState(false);
  const [alsoCreateShareholder, setAlsoCreateShareholder] = useState(false);

  // Load preparer list
  useEffect(() => {
    get("/preparers/").then((res) => {
      if (res.ok) setPreparers(res.data as PreparerOption[]);
    });
  }, []);

  useEffect(() => {
    if (!returnData.entity_id) {
      setLoadingEntity(false);
      return;
    }
    get(`/entities/${returnData.entity_id}/`).then((res) => {
      if (res.ok) setEntity(res.data as EntityInfo);
      setLoadingEntity(false);
    });
  }, [returnData.entity_id]);

  // Sync if returnData changes externally
  useEffect(() => {
    setAccountingMethod(returnData.accounting_method || "cash");
    setTaxYearStart(returnData.tax_year_start || "");
    setTaxYearEnd(returnData.tax_year_end || "");
    setIsInitialReturn(returnData.is_initial_return ?? false);
    setIsFinalReturn(returnData.is_final_return ?? false);
    setIsNameChange(returnData.is_name_change ?? false);
    setIsAddressChange(returnData.is_address_change ?? false);
    setIsAmendedReturn(returnData.is_amended_return ?? false);
    setSElectionDate(returnData.s_election_date || "");
    setNumberOfShareholders(
      returnData.number_of_shareholders != null ? String(returnData.number_of_shareholders) : ""
    );
    setProductOrService(returnData.product_or_service || "");
    setBusinessActivityCode(returnData.business_activity_code || "");
    setSelectedPreparer(returnData.preparer || "");
    setStaffPreparerId(returnData.staff_preparer || "");
    setSignatureDate(returnData.signature_date || "");
    setOfficers(returnData.officers || []);
  }, [returnData]);

  // Format helpers — auto-insert dashes for EIN, SSN, and phone
  function formatEIN(raw: string): string {
    const digits = raw.replace(/\D/g, "").slice(0, 9);
    if (digits.length > 2) return digits.slice(0, 2) + "-" + digits.slice(2);
    return digits;
  }

  function formatSSN(raw: string): string {
    const digits = raw.replace(/\D/g, "").slice(0, 9);
    if (digits.length > 5) return digits.slice(0, 3) + "-" + digits.slice(3, 5) + "-" + digits.slice(5);
    if (digits.length > 3) return digits.slice(0, 3) + "-" + digits.slice(3);
    return digits;
  }

  function formatPhone(raw: string): string {
    const digits = raw.replace(/\D/g, "").slice(0, 10);
    if (digits.length > 6) return digits.slice(0, 3) + "-" + digits.slice(3, 6) + "-" + digits.slice(6);
    if (digits.length > 3) return digits.slice(0, 3) + "-" + digits.slice(3);
    return digits;
  }

  // Entity field changes
  function handleEntityChange(field: keyof EntityInfo, value: string) {
    if (!entity) return;
    if (field === "ein") value = formatEIN(value);
    if (field === "phone") value = formatPhone(value);
    setEntity({ ...entity, [field]: value });
  }

  async function saveEntity() {
    if (!entity) return;
    setSaving(true);
    setSaveMsg(null);
    const res = await patch(`/entities/${entity.id}/`, {
      legal_name: entity.legal_name,
      ein: entity.ein,
      phone: entity.phone,
      address_line1: entity.address_line1,
      address_line2: entity.address_line2,
      city: entity.city,
      state: entity.state,
      zip_code: entity.zip_code,
      date_incorporated: entity.date_incorporated || null,
      state_incorporated: entity.state_incorporated,
      business_activity: entity.business_activity,
      naics_code: entity.naics_code,
      client: entity.client,
    });
    setSaving(false);
    if (res.ok) {
      setSaveMsg("Entity saved.");
      setTimeout(() => setSaveMsg(null), 3000);
    } else {
      setSaveMsg("Save failed.");
    }
  }

  async function saveReturnInfo() {
    setSaving(true);
    setSaveMsg(null);
    const res = await patch(`/tax-returns/${returnData.id}/info/`, {
      accounting_method: accountingMethod,
      tax_year_start: taxYearStart || null,
      tax_year_end: taxYearEnd || null,
      is_initial_return: isInitialReturn,
      is_final_return: isFinalReturn,
      is_name_change: isNameChange,
      is_address_change: isAddressChange,
      is_amended_return: isAmendedReturn,
      s_election_date: sElectionDate || null,
      number_of_shareholders: numberOfShareholders ? parseInt(numberOfShareholders) : null,
      product_or_service: productOrService,
      business_activity_code: businessActivityCode,
      preparer: selectedPreparer || "",
      staff_preparer: staffPreparerId || "",
      signature_date: signatureDate || "",
    });
    setSaving(false);
    if (res.ok) {
      await onRefresh();
      setSaveMsg("Return info saved.");
      setTimeout(() => setSaveMsg(null), 3000);
    } else {
      setSaveMsg("Save failed.");
    }
  }

  // Officer CRUD
  async function saveOfficer() {
    if (!editingOfficer) return;
    setOfficerSaving(true);
    if (editingOfficer.id) {
      // Update
      const res = await patch(
        `/tax-returns/${returnData.id}/officers/${editingOfficer.id}/`,
        {
          name: editingOfficer.name || "",
          title: editingOfficer.title || "",
          ssn: editingOfficer.ssn || "",
          percent_time: editingOfficer.percent_time || "0",
          percent_ownership: editingOfficer.percent_ownership || "0",
          compensation: editingOfficer.compensation || "0",
        }
      );
      if (res.ok) {
        await onRefresh();
        setEditingOfficer(null);
      }
    } else {
      // Create
      const res = await post(`/tax-returns/${returnData.id}/officers/`, {
        name: editingOfficer.name || "",
        title: editingOfficer.title || "",
        ssn: editingOfficer.ssn || "",
        percent_time: editingOfficer.percent_time || "0",
        percent_ownership: editingOfficer.percent_ownership || "0",
        compensation: editingOfficer.compensation || "0",
      });
      if (res.ok) {
        // Also create matching shareholder if checkbox was checked
        if (alsoCreateShareholder) {
          await post(`/tax-returns/${returnData.id}/shareholders/`, {
            name: editingOfficer.name || "",
            ssn: editingOfficer.ssn || "",
            ownership_percentage: editingOfficer.percent_ownership || "0",
          });
        }
        await onRefresh();
        setEditingOfficer(null);
        setAlsoCreateShareholder(false);
      }
    }
    setOfficerSaving(false);
  }

  async function deleteOfficer(officerId: string) {
    if (!confirm("Delete this officer?")) return;
    await del(`/tax-returns/${returnData.id}/officers/${officerId}/`);
    await onRefresh();
  }

  const inputClass =
    "w-full rounded-md border border-input-border bg-input px-2 py-1 text-sm text-tx shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring";

  if (loadingEntity) {
    return <p className="text-sm text-tx-secondary">Loading entity info...</p>;
  }

  return (
    <div className="space-y-6">
      {/* Top row: Entity + Return info cards */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Entity Information */}
        <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
          <h3 className="mb-4 text-sm font-bold text-tx">
            Entity Information
          </h3>
          {entity ? (
            <div className="space-y-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-tx-secondary">
                  Legal Name
                </label>
                <input
                  type="text"
                  value={entity.legal_name || ""}
                  onChange={(e) => handleEntityChange("legal_name", e.target.value)}
                  className={inputClass}
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-tx-secondary">
                  EIN
                </label>
                <input
                  type="text"
                  value={entity.ein || ""}
                  onChange={(e) => handleEntityChange("ein", e.target.value)}
                  className={inputClass}
                  placeholder="XX-XXXXXXX"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-tx-secondary">
                  Phone
                </label>
                <input
                  type="text"
                  value={entity.phone || ""}
                  onChange={(e) => handleEntityChange("phone", e.target.value)}
                  className={inputClass}
                  placeholder="XXX-XXX-XXXX"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-tx-secondary">
                  Address Line 1
                </label>
                <input
                  type="text"
                  value={entity.address_line1 || ""}
                  onChange={(e) => handleEntityChange("address_line1", e.target.value)}
                  className={inputClass}
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-tx-secondary">
                  Address Line 2
                </label>
                <input
                  type="text"
                  value={entity.address_line2 || ""}
                  onChange={(e) => handleEntityChange("address_line2", e.target.value)}
                  className={inputClass}
                />
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="mb-1 block text-xs font-medium text-tx-secondary">
                    City
                  </label>
                  <input
                    type="text"
                    value={entity.city || ""}
                    onChange={(e) => handleEntityChange("city", e.target.value)}
                    className={inputClass}
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-tx-secondary">
                    State
                  </label>
                  <input
                    type="text"
                    value={entity.state || ""}
                    onChange={(e) => handleEntityChange("state", e.target.value)}
                    className={inputClass}
                    maxLength={2}
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-tx-secondary">
                    ZIP Code
                  </label>
                  <input
                    type="text"
                    value={entity.zip_code || ""}
                    onChange={(e) => handleEntityChange("zip_code", e.target.value)}
                    className={inputClass}
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-xs font-medium text-tx-secondary">
                    Date Incorporated
                  </label>
                  <input
                    type="date"
                    value={entity.date_incorporated || ""}
                    onChange={(e) =>
                      handleEntityChange("date_incorporated", e.target.value)
                    }
                    className={inputClass}
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-tx-secondary">
                    State Incorporated
                  </label>
                  <input
                    type="text"
                    value={entity.state_incorporated || ""}
                    onChange={(e) =>
                      handleEntityChange("state_incorporated", e.target.value)
                    }
                    className={inputClass}
                    maxLength={2}
                  />
                </div>
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-tx-secondary">
                  Business Activity
                </label>
                <input
                  type="text"
                  value={entity.business_activity || ""}
                  onChange={(e) =>
                    handleEntityChange("business_activity", e.target.value)
                  }
                  className={inputClass}
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-tx-secondary">
                  NAICS Code
                </label>
                <input
                  type="text"
                  value={entity.naics_code || ""}
                  onChange={(e) => handleEntityChange("naics_code", e.target.value)}
                  className={inputClass}
                />
              </div>
              <button
                onClick={saveEntity}
                disabled={saving}
                className="mt-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-primary-hover disabled:opacity-50"
              >
                {saving ? "Saving..." : "Save Entity"}
              </button>
            </div>
          ) : (
            <p className="text-sm text-tx-muted">No entity data available.</p>
          )}
        </div>

        {/* Return Information */}
        <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
          <h3 className="mb-4 text-sm font-bold text-tx">
            Return Information
          </h3>
          <div className="space-y-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-tx-secondary">
                Accounting Method
              </label>
              <select
                value={accountingMethod}
                onChange={(e) => setAccountingMethod(e.target.value)}
                className={inputClass}
              >
                <option value="cash">Cash</option>
                <option value="accrual">Accrual</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-tx-secondary">
                Tax Year Start
              </label>
              <input
                type="date"
                value={taxYearStart}
                onChange={(e) => setTaxYearStart(e.target.value)}
                className={inputClass}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-tx-secondary">
                Tax Year End
              </label>
              <input
                type="date"
                value={taxYearEnd}
                onChange={(e) => setTaxYearEnd(e.target.value)}
                className={inputClass}
              />
            </div>

            {/* S-Corp specific fields */}
            {returnData.form_code === "1120-S" && (
              <>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="mb-1 block text-xs font-medium text-tx-secondary">
                      S Election Date
                    </label>
                    <input
                      type="date"
                      value={sElectionDate}
                      onChange={(e) => setSElectionDate(e.target.value)}
                      className={inputClass}
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-medium text-tx-secondary">
                      Number of Shareholders
                    </label>
                    <input
                      type="text"
                      inputMode="numeric"
                      value={numberOfShareholders}
                      onChange={(e) => setNumberOfShareholders(e.target.value.replace(/[^0-9]/g, ""))}
                      className={inputClass}
                    />
                  </div>
                </div>
              </>
            )}

            <div>
              <label className="mb-1 block text-xs font-medium text-tx-secondary">
                Product or Service
              </label>
              <input
                type="text"
                value={productOrService}
                onChange={(e) => setProductOrService(e.target.value)}
                className={inputClass}
                placeholder="e.g. Tax Preparation Services"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-tx-secondary">
                Business Activity Code
              </label>
              <input
                type="text"
                value={businessActivityCode}
                onChange={(e) => setBusinessActivityCode(e.target.value)}
                className={inputClass}
                placeholder="e.g. 541211"
              />
            </div>

            {/* Return flags */}
            <div>
              <label className="mb-2 block text-xs font-medium text-tx-secondary">
                Return Flags
              </label>
              <div className="grid grid-cols-2 gap-y-2 gap-x-4">
                <label className="flex items-center gap-2 text-sm text-tx cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isInitialReturn}
                    onChange={(e) => setIsInitialReturn(e.target.checked)}
                    className="h-4 w-4 rounded border-input-border text-primary focus:ring-primary"
                  />
                  Initial return
                </label>
                <label className="flex items-center gap-2 text-sm text-tx cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isFinalReturn}
                    onChange={(e) => setIsFinalReturn(e.target.checked)}
                    className="h-4 w-4 rounded border-input-border text-primary focus:ring-primary"
                  />
                  Final return
                </label>
                <label className="flex items-center gap-2 text-sm text-tx cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isNameChange}
                    onChange={(e) => setIsNameChange(e.target.checked)}
                    className="h-4 w-4 rounded border-input-border text-primary focus:ring-primary"
                  />
                  Name change
                </label>
                <label className="flex items-center gap-2 text-sm text-tx cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isAddressChange}
                    onChange={(e) => setIsAddressChange(e.target.checked)}
                    className="h-4 w-4 rounded border-input-border text-primary focus:ring-primary"
                  />
                  Address change
                </label>
                <label className="flex items-center gap-2 text-sm text-tx cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isAmendedReturn}
                    onChange={(e) => setIsAmendedReturn(e.target.checked)}
                    className="h-4 w-4 rounded border-input-border text-primary focus:ring-primary"
                  />
                  Amended return
                </label>
              </div>
            </div>

            <div className="pt-1">
              <p className="text-xs text-tx-muted">
                Form: {returnData.form_code} | Year: {returnData.year} | Status:{" "}
                {returnData.status}
              </p>
            </div>
            <button
              onClick={saveReturnInfo}
              disabled={saving}
              className="mt-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-primary-hover disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save Return Info"}
            </button>
          </div>
          {saveMsg && (
            <p className="mt-3 text-sm font-medium text-success">{saveMsg}</p>
          )}
        </div>
      </div>

      {/* Preparer Assignment (compact inline) */}
      <div className="rounded-xl border border-border bg-card px-5 py-3 shadow-sm">
        <h3 className="mb-2 text-sm font-bold text-tx">Preparer</h3>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="mb-0.5 block text-xs font-medium text-tx-secondary">Signing Preparer</label>
            <select value={selectedPreparer} onChange={(e) => setSelectedPreparer(e.target.value)} className={inputClass}>
              <option value="">— Select —</option>
              {preparers.filter((p) => p.is_active).map((p) => (
                <option key={p.id} value={p.id}>{p.name}{p.ptin ? ` (${p.ptin})` : ""}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-0.5 block text-xs font-medium text-tx-secondary">Staff Preparer</label>
            <select value={staffPreparerId} onChange={(e) => setStaffPreparerId(e.target.value)} className={inputClass}>
              <option value="">— Select —</option>
              {preparers.filter((p) => p.is_active).map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-0.5 block text-xs font-medium text-tx-secondary">Signature Date</label>
            <input type="date" value={signatureDate} onChange={(e) => setSignatureDate(e.target.value)} className={inputClass} />
          </div>
        </div>
      </div>

      {/* Officers */}
      <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-sm font-bold text-tx">
            Officers
          </h3>
          <button
            onClick={() =>
              setEditingOfficer({
                name: "",
                title: "",
                ssn: "",
                percent_time: "",
                percent_ownership: "",
                compensation: "",
              })
            }
            className="rounded-lg bg-success px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-success-hover"
          >
            Add Officer
          </button>
        </div>

        {officers.length === 0 && !editingOfficer && (
          <p className="text-sm text-tx-muted">No officers added yet.</p>
        )}

        {officers.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm zebra-table">
              <thead>
                <tr className="border-b border-border text-left">
                  <th className="pb-2 pr-4 font-semibold text-tx-secondary">Name</th>
                  <th className="pb-2 pr-4 font-semibold text-tx-secondary">Title</th>
                  <th className="pb-2 pr-4 font-semibold text-tx-secondary">SSN</th>
                  <th className="pb-2 pr-4 text-right font-semibold text-tx-secondary">
                    % Time
                  </th>
                  <th className="pb-2 pr-4 text-right font-semibold text-tx-secondary">
                    % Ownership
                  </th>
                  <th className="pb-2 pr-4 text-right font-semibold text-tx-secondary">
                    Compensation
                  </th>
                  <th className="pb-2 font-semibold text-tx-secondary">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle zebra-rows">
                {officers.map((o) => (
                  <tr key={o.id}>
                    <td className="py-2 pr-4 text-tx">{o.name}</td>
                    <td className="py-2 pr-4 text-tx">{o.title}</td>
                    <td className="py-2 pr-4 text-tx">{o.ssn}</td>
                    <td className="py-2 pr-4 text-right tabular-nums text-tx">
                      {o.percent_time ? `${o.percent_time}%` : ""}
                    </td>
                    <td className="py-2 pr-4 text-right tabular-nums text-tx">
                      {o.percent_ownership ? `${o.percent_ownership}%` : ""}
                    </td>
                    <td className="py-2 pr-4 text-right tabular-nums text-tx">
                      {o.compensation
                        ? parseFloat(o.compensation).toLocaleString("en-US", {
                            style: "currency",
                            currency: "USD",
                          })
                        : ""}
                    </td>
                    <td className="py-2">
                      <div className="flex gap-2">
                        <button
                          onClick={() => setEditingOfficer({ ...o })}
                          className="text-xs font-medium text-primary-text hover:underline"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => deleteOfficer(o.id)}
                          className="text-xs font-medium text-danger hover:text-danger-hover hover:underline"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Officer form (add / edit) */}
        {editingOfficer && (
          <div className="mt-4 rounded-lg border border-border bg-surface-alt p-4">
            <h4 className="mb-3 text-sm font-semibold text-tx">
              {editingOfficer.id ? "Edit Officer" : "New Officer"}
            </h4>
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">
              <div>
                <label className="mb-1 block text-xs font-medium text-tx-secondary">
                  Name
                </label>
                <input
                  type="text"
                  value={editingOfficer.name || ""}
                  onChange={(e) =>
                    setEditingOfficer({ ...editingOfficer, name: e.target.value })
                  }
                  className={inputClass}
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-tx-secondary">
                  Title
                </label>
                <input
                  type="text"
                  value={editingOfficer.title || ""}
                  onChange={(e) =>
                    setEditingOfficer({ ...editingOfficer, title: e.target.value })
                  }
                  className={inputClass}
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-tx-secondary">
                  SSN
                </label>
                <input
                  type="text"
                  value={editingOfficer.ssn || ""}
                  onChange={(e) =>
                    setEditingOfficer({ ...editingOfficer, ssn: formatSSN(e.target.value) })
                  }
                  className={inputClass}
                  placeholder="XXX-XX-XXXX"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-tx-secondary">
                  % Time
                </label>
                <input
                  type="text"
                  value={editingOfficer.percent_time || ""}
                  onChange={(e) =>
                    setEditingOfficer({
                      ...editingOfficer,
                      percent_time: e.target.value,
                    })
                  }
                  className={inputClass}
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-tx-secondary">
                  % Ownership
                </label>
                <input
                  type="text"
                  value={editingOfficer.percent_ownership || ""}
                  onChange={(e) =>
                    setEditingOfficer({
                      ...editingOfficer,
                      percent_ownership: e.target.value,
                    })
                  }
                  className={inputClass}
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-tx-secondary">
                  Compensation
                </label>
                <input
                  type="text"
                  value={editingOfficer.compensation || ""}
                  onChange={(e) =>
                    setEditingOfficer({
                      ...editingOfficer,
                      compensation: e.target.value,
                    })
                  }
                  className={inputClass}
                />
              </div>
            </div>
            {/* Cross-link checkbox — only show for new officers */}
            {!editingOfficer.id && (
              <div className="mt-3">
                <label className="flex items-center gap-2 text-sm text-tx cursor-pointer">
                  <input
                    type="checkbox"
                    checked={alsoCreateShareholder}
                    onChange={(e) => setAlsoCreateShareholder(e.target.checked)}
                    className="h-4 w-4 rounded border-input-border text-primary focus:ring-primary"
                  />
                  Also add as shareholder
                </label>
              </div>
            )}
            <div className="mt-3 flex gap-2">
              <button
                onClick={saveOfficer}
                disabled={officerSaving}
                className="rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-primary-hover disabled:opacity-50"
              >
                {officerSaving ? "Saving..." : "Save"}
              </button>
              <button
                onClick={() => { setEditingOfficer(null); setAlsoCreateShareholder(false); }}
                className="rounded-lg bg-surface-alt px-3 py-1.5 text-xs font-semibold text-tx shadow-sm transition hover:bg-border"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Preparer Section — Preparer, Firm, and Third-Party Designee
// ---------------------------------------------------------------------------

interface PreparerOption {
  id: string;
  name: string;
  ptin: string;
  is_active: boolean;
}

interface PreparerDetail {
  id: string;
  name: string;
  ptin: string;
  is_self_employed: boolean;
  firm_name: string;
  firm_ein: string;
  firm_phone: string;
  firm_address: string;
  firm_city: string;
  firm_state: string;
  firm_zip: string;
  designee_name: string;
  designee_phone: string;
  designee_pin: string;
  is_active: boolean;
}

function PreparerSection({
  taxReturnId,
  returnData,
  onRefresh,
}: {
  taxReturnId: string;
  returnData: TaxReturnData;
  onRefresh: () => Promise<void>;
}) {
  const navigate = useNavigate();
  const [preparers, setPreparers] = useState<PreparerOption[]>([]);
  const [selectedId, setSelectedId] = useState<string>(returnData.preparer || "");
  const [staffPreparerId, setStaffPreparerId] = useState<string>(returnData.staff_preparer || "");
  const [signatureDate, setSignatureDate] = useState<string>(returnData.signature_date || "");
  const [detail, setDetail] = useState<PreparerDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);

  // Load preparer list
  useEffect(() => {
    get("/preparers/").then((res) => {
      if (res.ok) setPreparers(res.data as PreparerOption[]);
      setLoading(false);
    });
  }, []);

  // Load detail when selection changes
  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    get(`/preparers/${selectedId}/`).then((res) => {
      if (res.ok) setDetail(res.data as PreparerDetail);
    });
  }, [selectedId]);

  // Sync from returnData when it refreshes
  useEffect(() => {
    setSelectedId(returnData.preparer || "");
    setStaffPreparerId(returnData.staff_preparer || "");
    setSignatureDate(returnData.signature_date || "");
  }, [returnData.preparer, returnData.staff_preparer, returnData.signature_date]);

  async function handleSave() {
    setSaving(true);
    setSaveMsg(null);
    const res = await patch(`/tax-returns/${taxReturnId}/info/`, {
      preparer: selectedId || "",
      staff_preparer: staffPreparerId || "",
      signature_date: signatureDate || "",
    });
    setSaving(false);
    if (res.ok) {
      await onRefresh();
      setSaveMsg("Preparer assignment saved.");
      setTimeout(() => setSaveMsg(null), 3000);
    } else {
      setSaveMsg("Save failed.");
    }
  }

  const inputClass =
    "w-full rounded-md border border-input-border bg-input px-2 py-1 text-sm text-tx shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring";

  if (loading) return <p className="text-sm text-tx-secondary">Loading preparers...</p>;

  return (
    <div className="space-y-6">
      {/* Preparer Selection */}
      <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
        <h3 className="mb-4 text-sm font-bold text-tx">Assign Preparer</h3>
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-tx-secondary">
                Signing Preparer
              </label>
              <select
                value={selectedId}
                onChange={(e) => setSelectedId(e.target.value)}
                className={inputClass}
              >
                <option value="">— Select —</option>
                {preparers.filter((p) => p.is_active).map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}{p.ptin ? ` (${p.ptin})` : ""}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-tx-secondary">
                Staff Preparer
              </label>
              <select
                value={staffPreparerId}
                onChange={(e) => setStaffPreparerId(e.target.value)}
                className={inputClass}
              >
                <option value="">— Select —</option>
                {preparers.filter((p) => p.is_active).map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-tx-secondary">
                Signature Date
              </label>
              <input
                type="date"
                value={signatureDate}
                onChange={(e) => setSignatureDate(e.target.value)}
                className={inputClass}
              />
            </div>
          </div>

          {/* Save */}
          <div className="flex items-center gap-3">
            <button
              onClick={handleSave}
              disabled={saving}
              className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-primary-hover disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save"}
            </button>
            {saveMsg && (
              <span className="text-sm font-medium text-success">{saveMsg}</span>
            )}
          </div>
        </div>
      </div>

      {/* Detail preview (read-only) */}
      {detail && (
        <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
          <h3 className="mb-4 text-sm font-bold text-tx">Preparer Details</h3>
          <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
            <div>
              <span className="text-tx-muted">Name:</span>{" "}
              <span className="font-medium text-tx">{detail.name}</span>
            </div>
            <div>
              <span className="text-tx-muted">PTIN:</span>{" "}
              <span className="font-mono text-tx">{detail.ptin || "—"}</span>
            </div>
            <div>
              <span className="text-tx-muted">Self-Employed:</span>{" "}
              <span className="text-tx">{detail.is_self_employed ? "Yes" : "No"}</span>
            </div>
            <div>
              <span className="text-tx-muted">Status:</span>{" "}
              <span className={detail.is_active ? "text-primary font-medium" : "text-tx-muted"}>
                {detail.is_active ? "Active" : "Inactive"}
              </span>
            </div>
            {detail.firm_name && (
              <>
                <div className="col-span-2 mt-2 border-t border-border-subtle pt-2">
                  <span className="text-xs font-semibold text-tx-muted uppercase">Firm Information</span>
                </div>
                <div>
                  <span className="text-tx-muted">Firm:</span>{" "}
                  <span className="text-tx">{detail.firm_name}</span>
                </div>
                <div>
                  <span className="text-tx-muted">EIN:</span>{" "}
                  <span className="font-mono text-tx">{detail.firm_ein || "—"}</span>
                </div>
                <div>
                  <span className="text-tx-muted">Phone:</span>{" "}
                  <span className="text-tx">{detail.firm_phone || "—"}</span>
                </div>
                <div>
                  <span className="text-tx-muted">Address:</span>{" "}
                  <span className="text-tx">
                    {[detail.firm_address, detail.firm_city, detail.firm_state, detail.firm_zip]
                      .filter(Boolean)
                      .join(", ") || "—"}
                  </span>
                </div>
              </>
            )}
            {detail.designee_name && (
              <>
                <div className="col-span-2 mt-2 border-t border-border-subtle pt-2">
                  <span className="text-xs font-semibold text-tx-muted uppercase">Third-Party Designee</span>
                </div>
                <div>
                  <span className="text-tx-muted">Name:</span>{" "}
                  <span className="text-tx">{detail.designee_name}</span>
                </div>
                <div>
                  <span className="text-tx-muted">Phone:</span>{" "}
                  <span className="text-tx">{detail.designee_phone || "—"}</span>
                </div>
                <div>
                  <span className="text-tx-muted">PIN:</span>{" "}
                  <span className="font-mono text-tx">{detail.designee_pin || "—"}</span>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Empty state */}
      {!selectedId && preparers.length === 0 && (
        <div className="rounded-xl border border-border bg-card p-5 shadow-sm text-center">
          <p className="text-sm text-tx-muted">No preparers have been created yet.</p>
          <button
            onClick={() => navigate("/admin/preparers")}
            className="mt-2 rounded-lg bg-success px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-success-hover"
          >
            Go to Preparer Manager
          </button>
        </div>
      )}

      {/* Link to manage */}
      <div className="text-center">
        <button
          onClick={() => navigate("/admin/preparers")}
          className="text-sm font-medium text-primary-text hover:underline"
        >
          Manage Preparers
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Income & Deductions Section (merged view)
// ---------------------------------------------------------------------------

/** Lines 7-19 that are standard deduction lines (not computed totals). */
const DEDUCTION_LINE_RANGE = ["7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19"];
/** Computed summary lines shown after deductions. */
const DEDUCTION_SUMMARY_LINES = ["20", "21"];
/** Tax & Payments section shown at the bottom. */
const TAX_SECTION_CODE = "page1_tax";

function IncomeDeductionsSection({
  taxReturnId,
  fieldsBySection,
  otherDeductions,
  onChange,
  onRefresh,
  priorYear,
}: {
  taxReturnId: string;
  fieldsBySection: Record<string, FieldValue[]>;
  otherDeductions: OtherDeductionRow[];
  onChange: (formLineId: string, value: string) => void;
  onRefresh: () => Promise<void>;
  priorYear: PriorYearData | null;
}) {
  const [categories, setCategories] = useState<string[]>([]);
  const [localOther, setLocalOther] = useState<OtherDeductionRow[]>(otherDeductions);

  useEffect(() => { setLocalOther(otherDeductions); }, [otherDeductions]);

  useEffect(() => {
    get("/tax-returns/deduction-categories/").then((res) => {
      if (res.ok) setCategories(res.data as string[]);
    });
  }, []);

  // --- Other deduction CRUD ---
  const [newDedId, setNewDedId] = useState<string | null>(null);

  async function addDeduction() {
    const res = await post(`/tax-returns/${taxReturnId}/other-deductions/`, {
      description: "",
      amount: "0",
      category: "",
      sort_order: localOther.length + 1,
      source: "manual",
    });
    if (res.ok) {
      setNewDedId((res.data as OtherDeductionRow).id);
      await onRefresh();
    } else {
      console.error("Failed to add deduction:", res);
      alert("Failed to add deduction. Please try again.");
    }
  }

  // Auto-focus on newly added deduction row
  useEffect(() => {
    if (newDedId) {
      const el = document.getElementById(`ded-desc-${newDedId}`);
      if (el) { el.focus(); el.scrollIntoView({ behavior: "smooth", block: "center" }); }
      setNewDedId(null);
    }
  }, [localOther, newDedId]);

  async function updateDeduction(dedId: string, field: string, value: string) {
    await patch(`/tax-returns/${taxReturnId}/other-deductions/${dedId}/`, { [field]: value });
    await onRefresh();
  }

  async function deleteDeduction(dedId: string) {
    if (!confirm("Delete this deduction?")) return;
    await del(`/tax-returns/${taxReturnId}/other-deductions/${dedId}/`);
    await onRefresh();
  }

  function handleLocalOtherChange(dedId: string, field: keyof OtherDeductionRow, value: string) {
    setLocalOther((prev) => prev.map((r) => (r.id === dedId ? { ...r, [field]: value } : r)));
  }

  // --- Separate fields by role ---
  const incomeFields = fieldsBySection["page1_income"] || [];
  const cogsFields = fieldsBySection["sched_a"] || [];
  const deductionFields = fieldsBySection["page1_deductions"] || [];
  const taxFields = fieldsBySection[TAX_SECTION_CODE] || [];

  // Split deductions into individual line items vs summary
  const stdDeductionItems = deductionFields.filter(
    (f) => DEDUCTION_LINE_RANGE.includes(f.line_number)
  );
  const summaryLines = deductionFields.filter(
    (f) => DEDUCTION_SUMMARY_LINES.includes(f.line_number)
  );

  // --- Build merged + sorted deduction list ---
  type DeductionItem =
    | { type: "form_line"; field: FieldValue }
    | { type: "other_ded"; row: OtherDeductionRow };

  const mergedDeductions: DeductionItem[] = useMemo(() => {
    const items: DeductionItem[] = [];

    // Add standard form deduction lines (skip Line 19 "Other deductions" — we show its detail inline)
    for (const f of stdDeductionItems) {
      if (f.line_number === "19") continue; // replaced by inline detail
      items.push({ type: "form_line", field: f });
    }

    // Add other deduction rows
    for (const row of localOther) {
      items.push({ type: "other_ded", row });
    }

    // Sort alphabetically by display label
    items.sort((a, b) => {
      const labelA = a.type === "form_line" ? a.field.label : (a.row.description || "zzz");
      const labelB = b.type === "form_line" ? b.field.label : (b.row.description || "zzz");
      return labelA.localeCompare(labelB, "en", { sensitivity: "base" });
    });

    return items;
  }, [stdDeductionItems, localOther]);

  const pyLines = priorYear?.line_values ?? {};
  const pyOther = priorYear?.other_deductions ?? {};
  const hasPY = priorYear !== null;

  return (
    <div className="space-y-4">
      {/* ===== INCOME ===== */}
      <div className="rounded-xl border border-border bg-card shadow-sm">
        <div className="px-4 py-1.5 text-xs font-bold uppercase tracking-wider text-tx-secondary bg-surface-alt rounded-t-xl">
          Income
        </div>
        <div className="flex items-center gap-4 border-b border-border bg-surface-alt px-4 py-1.5">
          <div className="w-14 shrink-0 text-xs font-semibold uppercase tracking-wider text-tx-secondary">Line</div>
          <div className="flex-1 text-xs font-semibold uppercase tracking-wider text-tx-secondary">Description</div>
          <div className="w-36 shrink-0 text-right text-xs font-semibold uppercase tracking-wider text-tx-secondary">Amount</div>
          {hasPY && (
            <div className="w-28 shrink-0 text-right text-xs font-semibold uppercase tracking-wider text-tx-muted">PY</div>
          )}
        </div>
        <div className="divide-y divide-border-subtle zebra-rows">
          {incomeFields.map((fv) => (
            <FieldRow key={fv.id} field={fv} onChange={onChange} pyValue={pyLines[fv.line_number]} showPY={hasPY} />
          ))}
        </div>
      </div>

      {/* ===== COST OF GOODS SOLD ===== */}
      {cogsFields.length > 0 && (
        <div className="rounded-xl border border-border bg-card shadow-sm">
          <div className="px-4 py-1.5 text-xs font-bold uppercase tracking-wider text-tx-secondary bg-surface-alt rounded-t-xl">
            Cost of Goods Sold
          </div>
          <div className="divide-y divide-border-subtle zebra-rows">
            {cogsFields.map((fv) => (
              <FieldRow key={fv.id} field={fv} onChange={onChange} pyValue={pyLines[fv.line_number]} showPY={hasPY} />
            ))}
          </div>
        </div>
      )}

      {/* ===== DEDUCTIONS (merged & alphabetical) ===== */}
      <div className="rounded-xl border border-border bg-card shadow-sm">
        <div className="flex items-center justify-between border-b border-border bg-surface-alt px-4 py-2 rounded-t-xl">
          <span className="text-xs font-bold uppercase tracking-wider text-tx-secondary">Deductions</span>
          <button
            onClick={addDeduction}
            className="rounded-lg bg-success px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-success-hover"
          >
            Add Deduction
          </button>
        </div>
        {/* Column header */}
        <div className="flex items-center gap-4 border-b border-border bg-surface-alt/50 px-4 py-1.5">
          <div className="w-14 shrink-0 text-xs font-semibold uppercase tracking-wider text-tx-secondary">Line</div>
          <div className="flex-1 text-xs font-semibold uppercase tracking-wider text-tx-secondary">Description</div>
          <div className="w-36 shrink-0 text-right text-xs font-semibold uppercase tracking-wider text-tx-secondary">Amount</div>
          {hasPY && (
            <div className="w-28 shrink-0 text-right text-xs font-semibold uppercase tracking-wider text-tx-muted">PY</div>
          )}
          <div className="w-16 shrink-0" />
        </div>
        <div className="divide-y divide-border-subtle zebra-rows">
          {mergedDeductions.map((item, idx) => {
            if (item.type === "form_line") {
              return (
                <div key={item.field.id} className={`flex items-center gap-4 px-4 py-1.5 ${item.field.is_computed ? "bg-surface-alt/50" : ""}`}>
                  <div className="w-14 shrink-0 text-xs font-medium text-tx-secondary">{item.field.line_number}</div>
                  <div className="flex-1">
                    <span className="text-xs text-tx">{item.field.label}</span>
                    {item.field.is_computed && <span className="ml-2 text-xs italic text-tx-muted">Calculated</span>}
                  </div>
                  <div className="w-36 shrink-0">
                    <FieldInput field={item.field} onChange={onChange} />
                  </div>
                  {hasPY && <PriorYearCell value={pyLines[item.field.line_number]} />}
                  <div className="w-16 shrink-0" />
                </div>
              );
            } else {
              const row = item.row;
              const isStandard = row.source === "standard";
              const isEmptyStandard = isStandard && parseFloat(row.amount || "0") === 0;
              return (
                <div key={row.id} className={`flex items-center gap-4 px-4 py-1.5 ${isEmptyStandard ? "opacity-70" : ""}`}>
                  <div className="w-14 shrink-0 text-xs text-tx-muted">•</div>
                  <div className="flex-1">
                    {isStandard ? (
                      <span className="inline-block px-2 py-0.5 text-xs text-tx">{row.description}</span>
                    ) : (
                      <>
                        <input
                          id={`ded-desc-${row.id}`}
                          type="text"
                          list={`ded-cats-${row.id}`}
                          value={row.description}
                          onChange={(e) => handleLocalOtherChange(row.id, "description", e.target.value)}
                          onBlur={(e) => updateDeduction(row.id, "description", e.target.value)}
                          className="w-full rounded-md border border-input-border bg-input px-2 py-1 text-sm text-tx shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring"
                          placeholder="Enter or select deduction..."
                        />
                        <datalist id={`ded-cats-${row.id}`}>
                          {categories.map((cat) => (
                            <option key={cat} value={cat} />
                          ))}
                        </datalist>
                      </>
                    )}
                  </div>
                  <div className="w-36 shrink-0">
                    <CurrencyInput
                      value={row.amount}
                      onValueChange={(v) => {
                        handleLocalOtherChange(row.id, "amount", v);
                        updateDeduction(row.id, "amount", v);
                      }}
                    />
                  </div>
                  {hasPY && <PriorYearCell value={pyOther[row.description]} />}
                  <div className="w-16 shrink-0 text-center">
                    {!isStandard && (
                      <button
                        onClick={() => deleteDeduction(row.id)}
                        className="text-xs font-medium text-danger hover:text-danger-hover hover:underline"
                      >
                        Delete
                      </button>
                    )}
                  </div>
                </div>
              );
            }
          })}

          {/* Summary lines: Total Deductions + Ordinary Business Income */}
          {summaryLines.map((fv) => (
            <FieldRow key={fv.id} field={fv} onChange={onChange} pyValue={pyLines[fv.line_number]} showPY={hasPY} />
          ))}
        </div>
      </div>

      {/* ===== TAX & PAYMENTS ===== */}
      {taxFields.length > 0 && (
        <div className="rounded-xl border border-border bg-card shadow-sm">
          <div className="px-4 py-1.5 text-xs font-bold uppercase tracking-wider text-tx-secondary bg-surface-alt rounded-t-xl">
            Tax and Payments
          </div>
          <div className="divide-y divide-border-subtle zebra-rows">
            {taxFields.map((fv) => (
              <FieldRow key={fv.id} field={fv} onChange={onChange} pyValue={pyLines[fv.line_number]} showPY={hasPY} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Other Deductions Section (legacy — kept for reference)
// ---------------------------------------------------------------------------

function OtherDeductionsSection({
  taxReturnId,
  deductions,
  onRefresh,
}: {
  taxReturnId: string;
  deductions: OtherDeductionRow[];
  onRefresh: () => Promise<void>;
}) {
  const [categories, setCategories] = useState<string[]>([]);
  const [saving, setSaving] = useState<string | null>(null); // id of row being saved
  const [localRows, setLocalRows] = useState<OtherDeductionRow[]>(deductions);

  // Sync when deductions prop changes
  useEffect(() => {
    setLocalRows(deductions);
  }, [deductions]);

  // Fetch categories on mount
  useEffect(() => {
    get("/tax-returns/deduction-categories/").then((res) => {
      if (res.ok) setCategories(res.data as string[]);
    });
  }, []);

  async function addDeduction() {
    const res = await post(`/tax-returns/${taxReturnId}/other-deductions/`, {
      description: "",
      amount: "0",
      category: "",
      sort_order: localRows.length + 1,
      source: "manual",
    });
    if (res.ok) {
      await onRefresh();
    }
  }

  async function updateDeduction(
    dedId: string,
    field: string,
    value: string
  ) {
    setSaving(dedId);
    await patch(`/tax-returns/${taxReturnId}/other-deductions/${dedId}/`, {
      [field]: value,
    });
    await onRefresh();
    setSaving(null);
  }

  async function deleteDeduction(dedId: string) {
    if (!confirm("Delete this deduction?")) return;
    await del(`/tax-returns/${taxReturnId}/other-deductions/${dedId}/`);
    await onRefresh();
  }

  // Local change handlers (update locally, then debounce save)
  function handleLocalChange(
    dedId: string,
    field: keyof OtherDeductionRow,
    value: string
  ) {
    setLocalRows((prev) =>
      prev.map((r) => (r.id === dedId ? { ...r, [field]: value } : r))
    );
  }

  const total = localRows.reduce((sum, d) => {
    const n = parseFloat(d.amount);
    return sum + (isNaN(n) ? 0 : n);
  }, 0);

  return (
    <div className="rounded-xl border border-border bg-card shadow-sm">
      <div className="flex items-center justify-between border-b border-border bg-surface-alt px-4 py-3">
        <h3 className="text-sm font-bold text-tx">
          Other Deductions
        </h3>
        <button
          onClick={addDeduction}
          className="rounded-lg bg-success px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-success-hover"
        >
          Add Deduction
        </button>
      </div>

      {localRows.length === 0 ? (
        <div className="px-4 py-8 text-center text-sm text-tx-muted">
          No other deductions. Click "Add Deduction" to create one.
        </div>
      ) : (
        <>
          {/* Column headers */}
          <div className="flex items-center gap-3 border-b border-border bg-surface-alt/50 px-4 py-2.5">
            <div className="flex-1 text-xs font-semibold uppercase tracking-wider text-tx-secondary">
              Description
            </div>
            <div className="w-44 shrink-0 text-right text-xs font-semibold uppercase tracking-wider text-tx-secondary">
              Amount
            </div>
            <div className="w-20 shrink-0 text-center text-xs font-semibold uppercase tracking-wider text-tx-secondary">
              Source
            </div>
            <div className="w-16 shrink-0 text-center text-xs font-semibold uppercase tracking-wider text-tx-secondary">
              Actions
            </div>
          </div>

          <div className="divide-y divide-border-subtle zebra-rows">
            {localRows.map((row) => (
              <div key={row.id} className="flex items-center gap-3 px-4 py-2.5">
                {/* Description — combobox style (dropdown of categories + freetext) */}
                <div className="flex-1">
                  <input
                    type="text"
                    list={`ded-cats-${row.id}`}
                    value={row.description}
                    onChange={(e) =>
                      handleLocalChange(row.id, "description", e.target.value)
                    }
                    onBlur={(e) =>
                      updateDeduction(row.id, "description", e.target.value)
                    }
                    className="w-full rounded-md border border-input-border bg-input px-3 py-2 text-sm text-tx shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring"
                    placeholder="Enter or select category..."
                  />
                  <datalist id={`ded-cats-${row.id}`}>
                    {categories.map((cat) => (
                      <option key={cat} value={cat} />
                    ))}
                  </datalist>
                </div>

                {/* Amount */}
                <div className="w-44 shrink-0">
                  <CurrencyInput
                    value={row.amount}
                    onValueChange={(v) => {
                      handleLocalChange(row.id, "amount", v);
                      updateDeduction(row.id, "amount", v);
                    }}
                  />
                </div>

                {/* Source pill */}
                <div className="w-20 shrink-0 text-center">
                  <span
                    className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                      row.source === "tb"
                        ? "bg-primary-subtle text-primary-text"
                        : row.source === "mapped"
                          ? "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
                          : "bg-surface-alt text-tx-secondary"
                    }`}
                  >
                    {row.source || "manual"}
                  </span>
                </div>

                {/* Delete */}
                <div className="w-16 shrink-0 text-center">
                  {saving === row.id ? (
                    <span className="text-xs text-primary-text">Saving...</span>
                  ) : (
                    <button
                      onClick={() => deleteDeduction(row.id)}
                      className="text-xs font-medium text-danger hover:text-danger-hover hover:underline"
                    >
                      Delete
                    </button>
                  )}
                </div>
              </div>
            ))}

            {/* Total row */}
            <div className="flex items-center gap-3 bg-surface-alt px-4 py-3 font-medium">
              <div className="flex-1 text-sm text-tx">Total</div>
              <div className="w-44 shrink-0 text-right text-sm tabular-nums text-tx">
                {total.toLocaleString("en-US", {
                  style: "currency",
                  currency: "USD",
                })}
              </div>
              <div className="w-20 shrink-0" />
              <div className="w-16 shrink-0" />
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shareholders Section
// ---------------------------------------------------------------------------

function ShareholdersSection({
  taxReturnId,
  shareholders,
  onRefresh,
}: {
  taxReturnId: string;
  shareholders: ShareholderRow[];
  onRefresh: () => Promise<void>;
}) {
  const [editing, setEditing] = useState<Partial<ShareholderRow> | null>(null);
  const [saving, setSaving] = useState(false);
  const [alsoCreateOfficer, setAlsoCreateOfficer] = useState(false);
  const [showBasis, setShowBasis] = useState(false);

  function formatSSN(raw: string): string {
    const digits = raw.replace(/\D/g, "").slice(0, 9);
    if (digits.length > 5) return digits.slice(0, 3) + "-" + digits.slice(3, 5) + "-" + digits.slice(5);
    if (digits.length > 3) return digits.slice(0, 3) + "-" + digits.slice(3);
    return digits;
  }

  async function saveShareholder() {
    if (!editing) return;
    setSaving(true);
    const payload = {
      name: editing.name || "",
      ssn: editing.ssn || "",
      address_line1: editing.address_line1 || "",
      address_line2: editing.address_line2 || "",
      city: editing.city || "",
      state: editing.state || "",
      zip_code: editing.zip_code || "",
      ownership_percentage: editing.ownership_percentage || "0",
      beginning_shares: editing.beginning_shares || "0",
      ending_shares: editing.ending_shares || "0",
      distributions: editing.distributions || "0",
      health_insurance_premium: editing.health_insurance_premium || "0",
      linked_client: editing.linked_client || null,
      // Form 7203 basis fields
      stock_basis_boy: editing.stock_basis_boy || "0",
      capital_contributions: editing.capital_contributions || "0",
      depletion: editing.depletion || "0",
      suspended_ordinary_loss: editing.suspended_ordinary_loss || "0",
      suspended_rental_re_loss: editing.suspended_rental_re_loss || "0",
      suspended_other_rental_loss: editing.suspended_other_rental_loss || "0",
      suspended_st_capital_loss: editing.suspended_st_capital_loss || "0",
      suspended_lt_capital_loss: editing.suspended_lt_capital_loss || "0",
      suspended_1231_loss: editing.suspended_1231_loss || "0",
      suspended_other_loss: editing.suspended_other_loss || "0",
    };

    if (editing.id) {
      await patch(`/tax-returns/${taxReturnId}/shareholders/${editing.id}/`, payload);
    } else {
      const res = await post(`/tax-returns/${taxReturnId}/shareholders/`, payload);
      // Also create matching officer if checkbox was checked
      if (res.ok && alsoCreateOfficer) {
        await post(`/tax-returns/${taxReturnId}/officers/`, {
          name: editing.name || "",
          ssn: editing.ssn || "",
          percent_ownership: editing.ownership_percentage || "0",
          title: "",
          compensation: "0",
        });
      }
    }
    await onRefresh();
    setEditing(null);
    setAlsoCreateOfficer(false);
    setSaving(false);
  }

  async function deleteShareholder(id: string) {
    if (!confirm("Delete this shareholder?")) return;
    await del(`/tax-returns/${taxReturnId}/shareholders/${id}/`);
    await onRefresh();
  }

  const totalOwnership = shareholders.reduce((sum, s) => {
    const n = parseFloat(s.ownership_percentage);
    return sum + (isNaN(n) ? 0 : n);
  }, 0);

  const inputClass =
    "w-full rounded-md border border-input-border bg-input px-2 py-1 text-sm text-tx shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring";

  return (
    <div className="rounded-xl border border-border bg-card shadow-sm">
      <div className="flex items-center justify-between border-b border-border bg-surface-alt px-4 py-3">
        <div>
          <h3 className="text-sm font-bold text-tx">Shareholders</h3>
          <p className="text-xs text-tx-muted">
            K-1 forms will be generated for each shareholder based on ownership percentage.
          </p>
        </div>
        <div className="flex gap-2">
          {shareholders.length > 0 && (
            <button
              onClick={async () => {
                try {
                  const r = await renderK1s(taxReturnId);
                  if (r?.pdfBase64) {
                    const blob = new Blob([Uint8Array.from(atob(r.pdfBase64), c => c.charCodeAt(0))], { type: "application/pdf" });
                    window.open(URL.createObjectURL(blob), "_blank");
                  } else {
                    alert(r?.error || "Failed to generate K-1s.");
                  }
                } catch {
                  alert("Failed to generate K-1s.");
                }
              }}
              className="rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-primary-hover"
            >
              Print All K-1s
            </button>
          )}
          <button
            onClick={() =>
              setEditing({
                name: "", ssn: "", address_line1: "", address_line2: "",
                city: "", state: "", zip_code: "", ownership_percentage: "",
                beginning_shares: "0", ending_shares: "0",
                distributions: "0", health_insurance_premium: "0",
                linked_client: null, linked_client_name: null,
              })
            }
            className="rounded-lg bg-success px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-success-hover"
          >
            Add Shareholder
          </button>
        </div>
      </div>

      {shareholders.length === 0 && !editing && (
        <div className="px-4 py-8 text-center text-sm text-tx-muted">
          No shareholders added yet. Add shareholders to enable K-1 generation.
        </div>
      )}

      {shareholders.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm zebra-table">
            <thead>
              <tr className="border-b border-border text-left">
                <th className="px-4 pb-2 pt-3 font-semibold text-tx-secondary">Name</th>
                <th className="px-4 pb-2 pt-3 font-semibold text-tx-secondary">SSN</th>
                <th className="px-4 pb-2 pt-3 font-semibold text-tx-secondary">City, State</th>
                <th className="px-4 pb-2 pt-3 text-right font-semibold text-tx-secondary">Ownership %</th>
                <th className="px-4 pb-2 pt-3 text-right font-semibold text-tx-secondary">Distributions</th>
                <th className="px-4 pb-2 pt-3 text-right font-semibold text-tx-secondary">Health Ins.</th>
                <th className="px-4 pb-2 pt-3 font-semibold text-tx-secondary">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle zebra-rows">
              {shareholders.map((s) => (
                <tr key={s.id}>
                  <td className="px-4 py-2 text-tx">
                    {s.name}
                    {s.linked_client_name && (
                      <span className="ml-1.5 rounded-full bg-primary-subtle px-1.5 py-0.5 text-[10px] font-medium text-primary-text" title={`Linked to client: ${s.linked_client_name}`}>
                        Linked
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-tx">{s.ssn}</td>
                  <td className="px-4 py-2 text-tx">
                    {[s.city, s.state].filter(Boolean).join(", ")}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums text-tx">
                    {s.ownership_percentage ? `${s.ownership_percentage}%` : ""}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums text-tx">
                    {parseFloat(s.distributions || "0") > 0 ? Number(s.distributions).toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 0 }) : ""}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums text-tx">
                    {parseFloat(s.health_insurance_premium || "0") > 0 ? Number(s.health_insurance_premium).toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 0 }) : ""}
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex flex-wrap gap-1.5">
                      <button
                        onClick={() => setEditing({ ...s, ownership_percentage: s.ownership_percentage, beginning_shares: String(s.beginning_shares), ending_shares: String(s.ending_shares) })}
                        className="text-xs font-medium text-primary-text hover:underline"
                      >
                        Edit
                      </button>
                      <button
                        onClick={async () => {
                          const r = await renderK1(taxReturnId, s.id);
                          if (r?.pdfBase64) {
                            const blob = new Blob([Uint8Array.from(atob(r.pdfBase64), c => c.charCodeAt(0))], { type: "application/pdf" });
                            window.open(URL.createObjectURL(blob), "_blank");
                          } else alert(r?.error || "Failed to generate K-1.");
                        }}
                        className="text-xs font-medium text-primary-text hover:underline"
                      >
                        K-1
                      </button>
                      {parseFloat(s.health_insurance_premium || "0") > 0 && (
                        <button
                          onClick={async () => {
                            const r = await render7206(taxReturnId, s.id);
                            if (r?.pdfBase64) {
                              const blob = new Blob([Uint8Array.from(atob(r.pdfBase64), c => c.charCodeAt(0))], { type: "application/pdf" });
                              window.open(URL.createObjectURL(blob), "_blank");
                            } else alert(r?.error || "Failed to generate Form 7206.");
                          }}
                          className="text-xs font-medium text-primary-text hover:underline"
                        >
                          7206
                        </button>
                      )}
                      <button
                        onClick={() => deleteShareholder(s.id)}
                        className="text-xs font-medium text-danger hover:text-danger-hover hover:underline"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t border-border bg-surface-alt">
                <td className="px-4 py-2 font-medium text-tx" colSpan={3}>Total</td>
                <td className={`px-4 py-2 text-right font-medium tabular-nums ${
                  Math.abs(totalOwnership - 100) < 0.01 ? "text-success" : "text-amber-600"
                }`}>
                  {totalOwnership.toFixed(2)}%
                </td>
                <td className="px-4 py-2 text-right font-medium tabular-nums text-tx">
                  {shareholders.reduce((sum, s) => sum + (parseFloat(s.distributions || "0") || 0), 0) > 0
                    ? shareholders.reduce((sum, s) => sum + (parseFloat(s.distributions || "0") || 0), 0).toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 0 })
                    : ""}
                </td>
                <td colSpan={2} />
              </tr>
            </tfoot>
          </table>
        </div>
      )}

      {/* Shareholder edit form */}
      {editing && (
        <div className="border-t border-border bg-surface-alt p-4">
          <h4 className="mb-3 text-sm font-semibold text-tx">
            {editing.id ? "Edit Shareholder" : "New Shareholder"}
          </h4>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <div className="col-span-2">
              <label className="mb-1 block text-xs font-medium text-tx-secondary">Name</label>
              <input type="text" value={editing.name || ""} onChange={(e) => setEditing({ ...editing, name: e.target.value })} className={inputClass} />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-tx-secondary">SSN</label>
              <input type="text" value={editing.ssn || ""} onChange={(e) => setEditing({ ...editing, ssn: formatSSN(e.target.value) })} className={inputClass} placeholder="XXX-XX-XXXX" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-tx-secondary">Ownership %</label>
              <input type="text" value={editing.ownership_percentage || ""} onChange={(e) => setEditing({ ...editing, ownership_percentage: e.target.value })} className={inputClass} />
            </div>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-3 lg:grid-cols-4">
            <div className="col-span-2">
              <label className="mb-1 block text-xs font-medium text-tx-secondary">Address</label>
              <input type="text" value={editing.address_line1 || ""} onChange={(e) => setEditing({ ...editing, address_line1: e.target.value })} className={inputClass} />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-tx-secondary">City</label>
              <input type="text" value={editing.city || ""} onChange={(e) => setEditing({ ...editing, city: e.target.value })} className={inputClass} />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="mb-1 block text-xs font-medium text-tx-secondary">State</label>
                <input type="text" value={editing.state || ""} onChange={(e) => setEditing({ ...editing, state: e.target.value })} className={inputClass} maxLength={2} />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-tx-secondary">ZIP</label>
                <input type="text" value={editing.zip_code || ""} onChange={(e) => setEditing({ ...editing, zip_code: e.target.value })} className={inputClass} />
              </div>
            </div>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-3 lg:grid-cols-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-tx-secondary">Beginning Shares</label>
              <input type="text" inputMode="numeric" value={editing.beginning_shares || "0"} onChange={(e) => setEditing({ ...editing, beginning_shares: e.target.value.replace(/[^0-9]/g, "") })} className={inputClass} />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-tx-secondary">Ending Shares</label>
              <input type="text" inputMode="numeric" value={editing.ending_shares || "0"} onChange={(e) => setEditing({ ...editing, ending_shares: e.target.value.replace(/[^0-9]/g, "") })} className={inputClass} />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-tx-secondary">Distributions</label>
              <CurrencyInput value={editing.distributions || "0"} onValueChange={(v) => setEditing({ ...editing, distributions: v })} />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-tx-secondary">Health Insurance Premium</label>
              <CurrencyInput value={editing.health_insurance_premium || "0"} onValueChange={(v) => setEditing({ ...editing, health_insurance_premium: v })} />
            </div>
          </div>
          {/* Form 7203 Basis Tracking (collapsible) */}
          <div className="mt-3">
            <button
              type="button"
              onClick={() => setShowBasis(!showBasis)}
              className="flex items-center gap-1 text-xs font-semibold text-primary hover:text-primary-hover"
            >
              <span className="text-[10px]">{showBasis ? "\u25BC" : "\u25B6"}</span>
              Basis Tracking (Form 7203)
            </button>
            {showBasis && (
              <div className="mt-2 rounded-lg border border-border-subtle bg-card p-3">
                <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                  <div>
                    <label className="mb-1 block text-xs font-medium text-tx-secondary">Stock Basis BOY</label>
                    <CurrencyInput value={editing.stock_basis_boy || "0"} onValueChange={(v) => setEditing({ ...editing, stock_basis_boy: v })} />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-medium text-tx-secondary">Capital Contributions</label>
                    <CurrencyInput value={editing.capital_contributions || "0"} onValueChange={(v) => setEditing({ ...editing, capital_contributions: v })} />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-medium text-tx-secondary">Depletion</label>
                    <CurrencyInput value={editing.depletion || "0"} onValueChange={(v) => setEditing({ ...editing, depletion: v })} />
                  </div>
                </div>
                <p className="mt-3 mb-1 text-xs font-semibold text-tx-muted uppercase">Suspended Prior Year Losses</p>
                <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                  <div>
                    <label className="mb-1 block text-xs font-medium text-tx-secondary">Ordinary Loss</label>
                    <CurrencyInput value={editing.suspended_ordinary_loss || "0"} onValueChange={(v) => setEditing({ ...editing, suspended_ordinary_loss: v })} />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-medium text-tx-secondary">Rental RE Loss</label>
                    <CurrencyInput value={editing.suspended_rental_re_loss || "0"} onValueChange={(v) => setEditing({ ...editing, suspended_rental_re_loss: v })} />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-medium text-tx-secondary">Other Rental Loss</label>
                    <CurrencyInput value={editing.suspended_other_rental_loss || "0"} onValueChange={(v) => setEditing({ ...editing, suspended_other_rental_loss: v })} />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-medium text-tx-secondary">ST Capital Loss</label>
                    <CurrencyInput value={editing.suspended_st_capital_loss || "0"} onValueChange={(v) => setEditing({ ...editing, suspended_st_capital_loss: v })} />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-medium text-tx-secondary">LT Capital Loss</label>
                    <CurrencyInput value={editing.suspended_lt_capital_loss || "0"} onValueChange={(v) => setEditing({ ...editing, suspended_lt_capital_loss: v })} />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-medium text-tx-secondary">Section 1231 Loss</label>
                    <CurrencyInput value={editing.suspended_1231_loss || "0"} onValueChange={(v) => setEditing({ ...editing, suspended_1231_loss: v })} />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-medium text-tx-secondary">Other Loss</label>
                    <CurrencyInput value={editing.suspended_other_loss || "0"} onValueChange={(v) => setEditing({ ...editing, suspended_other_loss: v })} />
                  </div>
                </div>
              </div>
            )}
          </div>
          {/* Cross-link checkbox — only show for new shareholders */}
          {!editing.id && (
            <div className="mt-3">
              <label className="flex items-center gap-2 text-sm text-tx cursor-pointer">
                <input
                  type="checkbox"
                  checked={alsoCreateOfficer}
                  onChange={(e) => setAlsoCreateOfficer(e.target.checked)}
                  className="h-4 w-4 rounded border-input-border text-primary focus:ring-primary"
                />
                Also add as officer
              </label>
            </div>
          )}
          <div className="mt-3 flex gap-2">
            <button onClick={saveShareholder} disabled={saving} className="rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-primary-hover disabled:opacity-50">
              {saving ? "Saving..." : "Save"}
            </button>
            <button onClick={() => { setEditing(null); setAlsoCreateOfficer(false); }} className="rounded-lg bg-surface-alt px-3 py-1.5 text-xs font-semibold text-tx shadow-sm transition hover:bg-border">
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Rental Properties Section (Form 8825)
// ---------------------------------------------------------------------------

const PROPERTY_TYPES: Record<string, string> = {
  "1": "Single family",
  "2": "Multi-family",
  "3": "Vacation/short-term",
  "4": "Commercial",
  "5": "Land",
  "6": "Other",
};

const EXPENSE_FIELDS: { key: keyof RentalPropertyRow; label: string }[] = [
  { key: "advertising", label: "Advertising" },
  { key: "auto_and_travel", label: "Auto and travel" },
  { key: "cleaning_and_maintenance", label: "Cleaning and maintenance" },
  { key: "commissions", label: "Commissions" },
  { key: "insurance", label: "Insurance" },
  { key: "legal_and_professional", label: "Legal and professional fees" },
  { key: "interest_mortgage", label: "Mortgage interest" },
  { key: "interest_other", label: "Other interest" },
  { key: "repairs", label: "Repairs" },
  { key: "taxes", label: "Taxes" },
  { key: "utilities", label: "Utilities" },
  { key: "depreciation", label: "Depreciation" },
  { key: "other_expenses", label: "Other expenses" },
];

function RentalPropertiesSection({
  taxReturnId,
  properties,
  onRefresh,
}: {
  taxReturnId: string;
  properties: RentalPropertyRow[];
  onRefresh: () => Promise<void>;
}) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [editing, setEditing] = useState<Partial<RentalPropertyRow> | null>(null);
  const [saving, setSaving] = useState(false);

  async function addProperty() {
    setSaving(true);
    const propNum = properties.length + 1;
    const res = await post(`/tax-returns/${taxReturnId}/rental-properties/`, {
      description: `Property ${propNum}`,
      property_type: "6",
      rents_received: "0",
    });
    if (res.ok) {
      await onRefresh();
      // Auto-expand the newly created property
      const newProp = res.data as RentalPropertyRow;
      if (newProp?.id) setExpandedId(newProp.id);
    } else {
      alert("Failed to add property. Please try again.");
    }
    setSaving(false);
  }

  async function updateProperty(id: string, data: Partial<RentalPropertyRow>) {
    await patch(`/tax-returns/${taxReturnId}/rental-properties/${id}/`, data);
    await onRefresh();
  }

  async function deleteProperty(id: string) {
    if (!confirm("Delete this rental property?")) return;
    await del(`/tax-returns/${taxReturnId}/rental-properties/${id}/`);
    await onRefresh();
  }

  const grandTotalRents = properties.reduce((s, p) => s + (parseFloat(p.rents_received) || 0), 0);
  const grandTotalExpenses = properties.reduce((s, p) => s + (parseFloat(p.total_expenses) || 0), 0);
  const grandNetRent = properties.reduce((s, p) => s + (parseFloat(p.net_rent) || 0), 0);

  const inputClass =
    "w-full rounded-md border border-input-border bg-input px-2 py-1 text-sm text-tx shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring";

  return (
    <div className="rounded-xl border border-border bg-card shadow-sm">
      <div className="flex items-center justify-between border-b border-border bg-surface-alt px-4 py-3">
        <div>
          <h3 className="text-sm font-bold text-tx">Rental Real Estate — Form 8825</h3>
          <p className="text-xs text-tx-muted">Net rental income flows to Schedule K, line 2.</p>
        </div>
        <button
          onClick={addProperty}
          disabled={saving}
          className="rounded-lg bg-success px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-success-hover disabled:opacity-50"
        >
          Add Property
        </button>
      </div>

      {properties.length === 0 && (
        <div className="px-4 py-8 text-center text-sm text-tx-muted">
          No rental properties. Click "Add Property" to create one.
        </div>
      )}

      {properties.length > 0 && (
        <div className="divide-y divide-border-subtle zebra-rows">
          {properties.map((prop) => {
            const isExpanded = expandedId === prop.id;
            return (
              <div key={prop.id}>
                {/* Summary row */}
                <div
                  className="flex cursor-pointer items-center gap-4 px-4 py-3 hover:bg-surface-alt/50"
                  onClick={() => setExpandedId(isExpanded ? null : prop.id)}
                >
                  <span className="text-tx-secondary">{isExpanded ? "\u25BC" : "\u25B6"}</span>
                  <div className="flex-1">
                    <span className="text-sm font-medium text-tx">
                      {prop.description || "(No description)"}
                    </span>
                    <span className="ml-2 text-xs text-tx-muted">
                      {PROPERTY_TYPES[prop.property_type] || "Other"}
                    </span>
                  </div>
                  <div className="w-32 text-right text-sm tabular-nums text-tx">
                    {parseFloat(prop.rents_received).toLocaleString("en-US", { style: "currency", currency: "USD" })}
                  </div>
                  <div className="w-32 text-right text-sm tabular-nums text-tx">
                    ({parseFloat(prop.total_expenses).toLocaleString("en-US", { style: "currency", currency: "USD" })})
                  </div>
                  <div className={`w-32 text-right text-sm font-medium tabular-nums ${parseFloat(prop.net_rent) >= 0 ? "text-tx" : "text-danger"}`}>
                    {parseFloat(prop.net_rent).toLocaleString("en-US", { style: "currency", currency: "USD" })}
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); deleteProperty(prop.id); }}
                    className="text-xs font-medium text-danger hover:text-danger-hover hover:underline"
                  >
                    Delete
                  </button>
                </div>

                {/* Expanded detail */}
                {isExpanded && (
                  <div className="border-t border-border bg-surface-alt/30 px-6 py-4">
                    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
                      <div className="col-span-2">
                        <label className="mb-1 block text-xs font-medium text-tx-secondary">Property Address / Description</label>
                        <input
                          type="text"
                          defaultValue={prop.description}
                          onBlur={(e) => updateProperty(prop.id, { description: e.target.value })}
                          className={inputClass}
                        />
                      </div>
                      <div>
                        <label className="mb-1 block text-xs font-medium text-tx-secondary">Property Type</label>
                        <select
                          defaultValue={prop.property_type}
                          onChange={(e) => updateProperty(prop.id, { property_type: e.target.value })}
                          className={inputClass}
                        >
                          {Object.entries(PROPERTY_TYPES).map(([k, v]) => (
                            <option key={k} value={k}>{v}</option>
                          ))}
                        </select>
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <label className="mb-1 block text-xs font-medium text-tx-secondary">Rental Days</label>
                          <input
                            type="number"
                            defaultValue={prop.fair_rental_days}
                            onBlur={(e) => updateProperty(prop.id, { fair_rental_days: parseInt(e.target.value) || 0 } as any)}
                            className={inputClass}
                          />
                        </div>
                        <div>
                          <label className="mb-1 block text-xs font-medium text-tx-secondary">Personal Days</label>
                          <input
                            type="number"
                            defaultValue={prop.personal_use_days}
                            onBlur={(e) => updateProperty(prop.id, { personal_use_days: parseInt(e.target.value) || 0 } as any)}
                            className={inputClass}
                          />
                        </div>
                      </div>
                    </div>

                    {/* Income */}
                    <div className="mt-4">
                      <label className="mb-1 block text-xs font-medium text-tx-secondary">Rents Received</label>
                      <div className="w-48">
                        <CurrencyInput
                          value={prop.rents_received}
                          onValueChange={(v) => updateProperty(prop.id, { rents_received: v })}
                        />
                      </div>
                    </div>

                    {/* Expenses grid */}
                    <h5 className="mt-4 mb-2 text-xs font-bold uppercase tracking-wider text-tx-secondary">Expenses</h5>
                    <div className="grid grid-cols-2 gap-x-6 gap-y-2 lg:grid-cols-3">
                      {EXPENSE_FIELDS.map(({ key, label }) => (
                        <div key={key} className="flex items-center gap-2">
                          <span className="w-40 shrink-0 text-xs text-tx-secondary">{label}</span>
                          <div className="w-32">
                            <CurrencyInput
                              value={prop[key] as string}
                              onValueChange={(v) => updateProperty(prop.id, { [key]: v })}
                            />
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Totals */}
                    <div className="mt-3 flex gap-6 border-t border-border pt-3">
                      <span className="text-sm text-tx-secondary">
                        Total Expenses: <strong className="text-tx">{parseFloat(prop.total_expenses).toLocaleString("en-US", { style: "currency", currency: "USD" })}</strong>
                      </span>
                      <span className="text-sm text-tx-secondary">
                        Net Rent: <strong className={parseFloat(prop.net_rent) >= 0 ? "text-success" : "text-danger"}>
                          {parseFloat(prop.net_rent).toLocaleString("en-US", { style: "currency", currency: "USD" })}
                        </strong>
                      </span>
                    </div>
                  </div>
                )}
              </div>
            );
          })}

          {/* Grand totals */}
          <div className="flex items-center gap-4 bg-surface-alt px-4 py-3 font-medium">
            <span className="text-tx-secondary">&nbsp;</span>
            <div className="flex-1 text-sm text-tx">Totals (all properties)</div>
            <div className="w-32 text-right text-sm tabular-nums text-tx">
              {grandTotalRents.toLocaleString("en-US", { style: "currency", currency: "USD" })}
            </div>
            <div className="w-32 text-right text-sm tabular-nums text-tx">
              ({grandTotalExpenses.toLocaleString("en-US", { style: "currency", currency: "USD" })})
            </div>
            <div className={`w-32 text-right text-sm font-bold tabular-nums ${grandNetRent >= 0 ? "text-success" : "text-danger"}`}>
              {grandNetRent.toLocaleString("en-US", { style: "currency", currency: "USD" })}
            </div>
            <div className="w-12" />
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Balance Sheets Section (Schedule L + M-1 + M-2 combined)
// ---------------------------------------------------------------------------

function BalanceSheetsSection({
  taxReturnId,
  fieldsBySection,
  onChange,
  onRefresh,
  priorYear,
}: {
  taxReturnId: string;
  fieldsBySection: Record<string, FieldValue[]>;
  onChange: (formLineId: string, value: string) => void;
  onRefresh: () => Promise<void>;
  priorYear: PriorYearData | null;
}) {
  const schedLFields = fieldsBySection["sched_l"] || [];
  const m1Fields = fieldsBySection["sched_m1"] || [];
  const m2Fields = fieldsBySection["sched_m2"] || [];
  const bsPyLines = priorYear?.line_values ?? {};
  const bsHasPY = priorYear !== null;

  async function populateBOY() {
    const res = await post(`/tax-returns/${taxReturnId}/populate-boy/`);
    if (res.ok) {
      await onRefresh();
    } else {
      alert("No prior year data found to populate from.");
    }
  }

  return (
    <div className="space-y-6">
      {/* Populate BOY button */}
      <div className="flex items-center justify-end">
        <button
          onClick={populateBOY}
          className="rounded-lg bg-primary-subtle px-3 py-1.5 text-xs font-medium text-primary-text transition hover:bg-primary hover:text-white"
          title="Copy prior year end-of-year balances into beginning-of-year fields"
        >
          Populate BOY from Prior Year
        </button>
      </div>
      <ScheduleLSection fields={schedLFields} onChange={onChange} />
      {m1Fields.length > 0 && (
        <div className="rounded-xl border border-border bg-card shadow-sm">
          <div className="px-4 py-1.5 text-xs font-bold uppercase tracking-wider text-tx-secondary bg-surface-alt border-b border-border">
            Schedule M-1 — Reconciliation of Income (Loss)
          </div>
          <div className="divide-y divide-border-subtle zebra-rows">
            {m1Fields.map((fv) => (
              <FieldRow key={fv.id} field={fv} onChange={onChange} pyValue={bsPyLines[fv.line_number]} showPY={bsHasPY} />
            ))}
          </div>
        </div>
      )}
      {m2Fields.length > 0 && (
        <div className="rounded-xl border border-border bg-card shadow-sm">
          <div className="px-4 py-1.5 text-xs font-bold uppercase tracking-wider text-tx-secondary bg-surface-alt border-b border-border">
            Schedule M-2 — Analysis of AAA, OAA, and STPI
          </div>
          <div className="divide-y divide-border-subtle zebra-rows">
            {m2Fields.map((fv) => (
              <FieldRow key={fv.id} field={fv} onChange={onChange} pyValue={bsPyLines[fv.line_number]} showPY={bsHasPY} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tax & Payments section
// ---------------------------------------------------------------------------

function TaxPaymentsSection({
  taxReturnId,
  fieldsBySection,
  returnData,
  onChange,
  onRefresh,
}: {
  taxReturnId: string;
  fieldsBySection: Record<string, FieldValue[]>;
  returnData: TaxReturnData;
  onChange: (formLineId: string, value: string) => void;
  onRefresh: () => Promise<void>;
}) {
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);

  // Extension fields
  const [extensionFiled, setExtensionFiled] = useState(returnData.extension_filed ?? false);
  const [extensionDate, setExtensionDate] = useState(returnData.extension_date || "");
  const [tentativeTax, setTentativeTax] = useState(returnData.tentative_tax || "0.00");
  const [totalPayments, setTotalPayments] = useState(returnData.total_payments || "0.00");
  const [balanceDue, setBalanceDue] = useState(returnData.balance_due || "0.00");

  // Bank info
  const [bankRouting, setBankRouting] = useState(returnData.bank_routing_number || "");
  const [bankAccount, setBankAccount] = useState(returnData.bank_account_number || "");
  const [bankType, setBankType] = useState(returnData.bank_account_type || "checking");

  // Sync when returnData changes
  useEffect(() => {
    setExtensionFiled(returnData.extension_filed ?? false);
    setExtensionDate(returnData.extension_date || "");
    setTentativeTax(returnData.tentative_tax || "0.00");
    setTotalPayments(returnData.total_payments || "0.00");
    setBalanceDue(returnData.balance_due || "0.00");
    setBankRouting(returnData.bank_routing_number || "");
    setBankAccount(returnData.bank_account_number || "");
    setBankType(returnData.bank_account_type || "checking");
  }, [returnData]);

  async function savePaymentInfo() {
    setSaving(true);
    setSaveMsg(null);
    const res = await patch(`/tax-returns/${taxReturnId}/info/`, {
      extension_filed: extensionFiled,
      extension_date: extensionDate || null,
      tentative_tax: tentativeTax || "0.00",
      total_payments: totalPayments || "0.00",
      balance_due: balanceDue || "0.00",
      bank_routing_number: bankRouting,
      bank_account_number: bankAccount,
      bank_account_type: bankType,
    });
    setSaving(false);
    if (res.ok) {
      await onRefresh();
      setSaveMsg("Payment info saved.");
      setTimeout(() => setSaveMsg(null), 3000);
    } else {
      setSaveMsg("Save failed.");
    }
  }

  const taxFields = fieldsBySection["page1_tax"] || [];

  return (
    <div className="space-y-6">
      {/* Extension (Form 7004) Card */}
      <div className="rounded-xl border border-border bg-card shadow-sm">
        <div className="flex items-center justify-between border-b border-border bg-surface-alt px-5 py-3">
          <h3 className="text-sm font-semibold text-tx">Extension (Form 7004)</h3>
          <button
            onClick={async () => {
              try {
                const r = await render7004(taxReturnId);
                if (r?.pdfBase64) {
                  const blob = new Blob(
                    [Uint8Array.from(atob(r.pdfBase64), c => c.charCodeAt(0))],
                    { type: "application/pdf" }
                  );
                  window.open(URL.createObjectURL(blob), "_blank");
                } else {
                  alert(r?.error || "Failed to generate Form 7004.");
                }
              } catch {
                alert("Failed to generate Form 7004.");
              }
            }}
            className="rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-primary-hover"
          >
            Print Form 7004
          </button>
        </div>
        <div className="p-5 space-y-4">
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="extension_filed"
              checked={extensionFiled}
              onChange={(e) => setExtensionFiled(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
            />
            <label htmlFor="extension_filed" className="text-sm font-medium text-tx">
              Extension Filed
            </label>
          </div>
          <div className="grid grid-cols-4 gap-4">
            <div>
              <label className="block text-xs font-medium text-tx-muted mb-1">Extension Date</label>
              <input
                type="date"
                value={extensionDate}
                onChange={(e) => setExtensionDate(e.target.value)}
                className="w-full rounded-md border border-border bg-field px-3 py-1.5 text-sm text-tx focus:ring-2 focus:ring-primary"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-tx-muted mb-1">Tentative Tax (Line 6)</label>
              <CurrencyInput
                value={tentativeTax}
                onValueChange={(v) => {
                  setTentativeTax(v);
                  const t = parseFloat(v) || 0;
                  const p = parseFloat(totalPayments) || 0;
                  setBalanceDue(Math.max(0, t - p).toFixed(2));
                }}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-tx-muted mb-1">Total Payments (Line 7)</label>
              <CurrencyInput
                value={totalPayments}
                onValueChange={(v) => {
                  setTotalPayments(v);
                  const t = parseFloat(tentativeTax) || 0;
                  const p = parseFloat(v) || 0;
                  setBalanceDue(Math.max(0, t - p).toFixed(2));
                }}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-tx-muted mb-1">Balance Due (Line 8)</label>
              <CurrencyInput
                value={balanceDue}
                onValueChange={setBalanceDue}
                readOnly
              />
            </div>
          </div>
        </div>
      </div>

      {/* Bank Information Card */}
      <div className="rounded-xl border border-border bg-card shadow-sm">
        <div className="border-b border-border bg-surface-alt px-5 py-3">
          <h3 className="text-sm font-semibold text-tx">Direct Deposit / Payment — Bank Information</h3>
        </div>
        <div className="p-5">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-tx-muted mb-1">Routing Number</label>
              <input
                type="text"
                value={bankRouting}
                onChange={(e) => setBankRouting(e.target.value.replace(/\D/g, "").slice(0, 9))}
                maxLength={9}
                placeholder="9 digits"
                className="w-full rounded-md border border-border bg-field px-3 py-1.5 text-sm text-tx font-mono focus:ring-2 focus:ring-primary"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-tx-muted mb-1">Account Number</label>
              <input
                type="text"
                value={bankAccount}
                onChange={(e) => setBankAccount(e.target.value.replace(/\D/g, "").slice(0, 17))}
                maxLength={17}
                placeholder="Up to 17 digits"
                className="w-full rounded-md border border-border bg-field px-3 py-1.5 text-sm text-tx font-mono focus:ring-2 focus:ring-primary"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-tx-muted mb-1">Account Type</label>
              <select
                value={bankType}
                onChange={(e) => setBankType(e.target.value)}
                className="w-full rounded-md border border-border bg-field px-3 py-1.5 text-sm text-tx focus:ring-2 focus:ring-primary"
              >
                <option value="checking">Checking</option>
                <option value="savings">Savings</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Save Button for Extension + Bank */}
      <div className="flex items-center gap-3">
        <button
          onClick={savePaymentInfo}
          disabled={saving}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-50"
        >
          {saving ? "Saving..." : "Save Payment Info"}
        </button>
        {saveMsg && (
          <span className={`text-sm ${saveMsg.includes("fail") ? "text-red-600" : "text-green-600"}`}>
            {saveMsg}
          </span>
        )}
      </div>

      {/* Page 1 Tax Lines (22a-27) */}
      {taxFields.length > 0 && (
        <div className="rounded-xl border border-border bg-card shadow-sm">
          <div className="border-b border-border bg-surface-alt px-5 py-3">
            <h3 className="text-sm font-semibold text-tx">Tax and Payments (Page 1, Lines 22–27)</h3>
          </div>
          <div className="divide-y divide-border-subtle">
            {taxFields.map((fv) => (
              <div key={fv.id} className="flex items-center gap-4 px-5 py-2.5">
                <div className="w-12 shrink-0 text-sm font-medium text-tx-secondary text-right">
                  {fv.line_number}
                </div>
                <div className="flex-1 min-w-0 text-sm text-tx truncate">
                  {fv.label}
                </div>
                <div className="w-36 shrink-0">
                  {fv.field_type === "currency" ? (
                    <CurrencyInput
                      value={fv.value}
                      onValueChange={(v) => onChange(fv.form_line, v)}
                      readOnly={fv.is_computed && !fv.is_overridden}
                    />
                  ) : (
                    <input
                      type="text"
                      value={fv.value}
                      onChange={(e) => onChange(fv.form_line, e.target.value)}
                      readOnly={fv.is_computed && !fv.is_overridden}
                      className="w-full rounded-md border border-border bg-field px-3 py-1.5 text-sm text-tx text-right focus:ring-2 focus:ring-primary read-only:bg-surface-alt read-only:text-tx-muted"
                    />
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Schedule B — Other Information (Yes/No question layout)
// ---------------------------------------------------------------------------

/** Accounting method labels. */
const ACCT_METHOD_LABELS: Record<string, string> = {
  cash: "Cash",
  accrual: "Accrual",
  other: "Other",
};

function ScheduleBSection({
  fields,
  returnData,
  onChange,
}: {
  fields: FieldValue[];
  returnData: TaxReturnData;
  onChange: (formLineId: string, value: string) => void;
}) {
  // Build lookup for conditional visibility
  const valByLine: Record<string, string> = {};
  for (const f of fields) {
    valByLine[f.line_number] = f.value;
  }

  // B14b only visible when B14a = Yes
  const show14b = valByLine["B14a"] === "true" || valByLine["B14a"] === "1";

  return (
    <div className="rounded-xl border border-border bg-card shadow-sm">
      {/* Header: Questions 1 & 2 (from return data, not form fields) */}
      <div className="border-b border-border bg-surface-alt px-5 py-2">
        <h3 className="text-xs font-semibold text-tx mb-1">Schedule B — Other Information</h3>
        <div className="grid grid-cols-2 gap-3 text-xs">
          <div>
            <span className="text-tx-muted">1. Accounting method: </span>
            <span className="font-medium text-tx">
              {ACCT_METHOD_LABELS[returnData.accounting_method] || returnData.accounting_method || "Not set"}
            </span>
            <span className="text-tx-muted text-xs ml-2">(set on Info tab)</span>
          </div>
          <div>
            <span className="text-tx-muted">2a. Business activity code: </span>
            <span className="font-medium text-tx">
              {returnData.business_activity_code || "—"}
            </span>
          </div>
          <div className="col-span-2">
            <span className="text-tx-muted">2b. Product or service: </span>
            <span className="font-medium text-tx">
              {returnData.product_or_service || "—"}
            </span>
          </div>
        </div>
      </div>

      {/* Yes/No questions */}
      <div className="divide-y divide-border-subtle">
        {fields.map((fv) => {
          // Hide B14b unless B14a = Yes
          if (fv.line_number === "B14b" && !show14b) return null;

          // Sub-question indentation
          const isSubQ = fv.line_number === "B14b";

          return (
            <div
              key={fv.id}
              className={`flex items-start gap-4 px-5 py-1.5 ${
                isSubQ ? "pl-12 bg-surface-alt/30" : ""
              }`}
            >
              {/* Question number */}
              <div className="w-10 shrink-0 pt-0.5 text-xs font-medium text-tx-secondary">
                {fv.line_number.replace("B", "")}
              </div>

              {/* Question text */}
              <div className="flex-1 min-w-0 pt-0.5">
                <span className="text-xs text-tx leading-snug">{fv.label}</span>
              </div>

              {/* Answer input */}
              <div className="w-36 shrink-0 flex justify-end pt-0.5">
                {fv.field_type === "boolean" ? (
                  <BooleanField
                    value={fv.value}
                    readOnly={fv.is_computed}
                    onChange={(v) => onChange(fv.form_line, v)}
                  />
                ) : fv.field_type === "currency" ? (
                  <CurrencyInput
                    value={fv.value}
                    onValueChange={(v) => onChange(fv.form_line, v)}
                    readOnly={fv.is_computed}
                  />
                ) : (
                  <TextInput
                    value={fv.value}
                    readOnly={fv.is_computed}
                    onChange={(v) => onChange(fv.form_line, v)}
                  />
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Standard section layout (Line / Description / Amount)
// ---------------------------------------------------------------------------

function StandardSection({
  sections,
  fieldsBySection,
  onChange,
  pyLookup,
}: {
  sections: string[];
  fieldsBySection: Record<string, FieldValue[]>;
  onChange: (formLineId: string, value: string) => void;
  pyLookup?: Record<string, number>;
}) {
  const hasPY = pyLookup && Object.keys(pyLookup).length > 0;
  return (
    <div className="rounded-xl border border-border bg-card shadow-sm">
      {sections.map((secCode, idx) => {
        const fields = fieldsBySection[secCode] || [];
        if (fields.length === 0) return null;
        return (
          <div key={secCode}>
            {/* Section divider for multi-section tabs */}
            {sections.length > 1 && (
              <div
                className={`px-4 py-1.5 text-xs font-bold uppercase tracking-wider text-tx-secondary bg-surface-alt ${
                  idx > 0 ? "border-t-2 border-border" : ""
                }`}
              >
                {secCode === "page1_income"
                  ? "Income"
                  : secCode === "page1_deductions"
                    ? "Deductions"
                    : secCode}
              </div>
            )}
            {/* Column headers (first section only) */}
            {idx === 0 && (
              <div className="flex items-center gap-4 border-b border-border bg-surface-alt px-4 py-1.5">
                <div className="w-14 shrink-0 text-xs font-semibold uppercase tracking-wider text-tx-secondary">
                  Line
                </div>
                <div className="flex-1 text-xs font-semibold uppercase tracking-wider text-tx-secondary">
                  Description
                </div>
                <div className="w-36 shrink-0 text-right text-xs font-semibold uppercase tracking-wider text-tx-secondary">
                  Amount
                </div>
                {hasPY && (
                  <div className="w-28 shrink-0 text-right text-xs font-semibold uppercase tracking-wider text-tx-muted">
                    PY
                  </div>
                )}
              </div>
            )}
            <div className="divide-y divide-border-subtle zebra-rows">
              {fields.map((fv) => (
                <FieldRow
                  key={fv.id}
                  field={fv}
                  onChange={onChange}
                  pyValue={pyLookup?.[fv.line_number]}
                  showPY={!!hasPY}
                />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Schedule L — Two-column layout (Beginning of Year / End of Year)
// ---------------------------------------------------------------------------

/** Extract the base line category from a Schedule L line number.
 *  e.g. "L1a" → "L1", "L1d" → "L1", "L9b" → "L9_depr", "L9e" → "L9_depr"
 */
function schedLGroup(lineNum: string): string {
  // Accumulated depreciation lines pair together
  if (lineNum === "L9b" || lineNum === "L9e") return "L9_depr";
  // Total lines
  if (lineNum === "L14a" || lineNum === "L14d") return "L14";
  if (lineNum === "L27a" || lineNum === "L27d") return "L27";
  // Standard: strip trailing letter → e.g. "L15a" → "L15", "L15d" → "L15"
  return lineNum.replace(/[a-e]$/, "");
}

function isBOY(lineNum: string): boolean {
  return lineNum.endsWith("a") || lineNum.endsWith("b");
}

function ScheduleLSection({
  fields,
  onChange,
}: {
  fields: FieldValue[];
  onChange: (formLineId: string, value: string) => void;
}) {
  // Group fields into pairs: [BOY, EOY] by category
  const groups: { label: string; boy?: FieldValue; eoy?: FieldValue }[] = [];
  const seen = new Set<string>();

  for (const fv of fields) {
    const group = schedLGroup(fv.line_number);
    if (seen.has(group)) continue;

    // Find the pair
    const pair = fields.filter((f) => schedLGroup(f.line_number) === group);
    const boy = pair.find((f) => isBOY(f.line_number));
    const eoy = pair.find((f) => !isBOY(f.line_number));

    // Use a cleaner label (strip "— beginning/end of year")
    const label = (boy?.label || eoy?.label || "")
      .replace(/ — (beginning|end)( of year)?/i, "")
      .replace(/ — (beginning|end)/i, "")
      .replace(/Less accumulated depreciation/, "Less accum. depreciation");

    groups.push({ label, boy, eoy });
    seen.add(group);
  }

  return (
    <div className="rounded-xl border border-border bg-card shadow-sm">
      {/* Column headers */}
      <div className="flex items-center gap-4 border-b border-border bg-surface-alt px-4 py-1.5">
        <div className="w-10 shrink-0 text-xs font-semibold uppercase tracking-wider text-tx-secondary">
          Line
        </div>
        <div className="flex-1 text-xs font-semibold uppercase tracking-wider text-tx-secondary">
          Description
        </div>
        <div className="w-36 shrink-0 text-right text-xs font-semibold uppercase tracking-wider text-tx-secondary">
          Beginning of Year
        </div>
        <div className="w-36 shrink-0 text-right text-xs font-semibold uppercase tracking-wider text-tx-secondary">
          End of Year
        </div>
      </div>

      <div className="divide-y divide-border-subtle zebra-rows">
        {groups.map((g, i) => {
          const lineNum = g.boy?.line_number?.replace(/[a-b]$/, "") ||
            g.eoy?.line_number?.replace(/[d-e]$/, "") || "";
          const groupKey = schedLGroup(g.boy?.line_number || g.eoy?.line_number || "");
          const isComputed = (g.boy?.is_computed || g.eoy?.is_computed) ?? false;

          // Section dividers
          const isTotalAssets = lineNum === "L14";
          const isFirstLiability = lineNum === "L15";
          const isFirstEquity = lineNum === "L21";
          const isTotalLE = lineNum === "L27";

          return (
            <div key={i}>
              {isFirstLiability && (
                <div className="px-4 py-1.5 text-xs font-bold uppercase tracking-wider text-tx-secondary bg-surface-alt border-t-2 border-border">
                  Liabilities
                </div>
              )}
              {isFirstEquity && (
                <div className="px-4 py-1.5 text-xs font-bold uppercase tracking-wider text-tx-secondary bg-surface-alt border-t border-border">
                  Equity
                </div>
              )}
              <div
                className={`flex items-center gap-4 px-4 py-1.5 ${
                  isComputed || isTotalAssets || isTotalLE
                    ? "bg-surface-alt/50 font-medium"
                    : ""
                }`}
              >
                <div className="w-10 shrink-0 text-xs text-tx-secondary">
                  {lineNum}
                </div>
                <div className="flex-1">
                  <span className="text-xs text-tx">{g.label}</span>
                  {isComputed && (
                    <span className="ml-2 text-xs italic text-tx-muted">
                      Calculated
                    </span>
                  )}
                </div>
                <div className="w-36 shrink-0">
                  {g.boy ? (
                    <FieldInput field={g.boy} onChange={onChange} />
                  ) : (
                    <div />
                  )}
                </div>
                <div className="w-36 shrink-0">
                  {g.eoy ? (
                    <FieldInput field={g.eoy} onChange={onChange} />
                  ) : (
                    <div />
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function FieldRow({
  field,
  onChange,
  pyValue,
  showPY = false,
}: {
  field: FieldValue;
  onChange: (formLineId: string, value: string) => void;
  pyValue?: number;
  showPY?: boolean;
}) {
  return (
    <div
      className={`flex items-center gap-4 px-4 py-1.5 ${
        field.is_computed ? "bg-surface-alt/50" : ""
      }`}
    >
      {/* Line number */}
      <div className="w-14 shrink-0 text-xs font-medium text-tx-secondary">
        {field.line_number}
      </div>

      {/* Label */}
      <div className="flex-1">
        <span className="text-xs text-tx">{field.label}</span>
        {field.is_computed && (
          <span className="ml-2 text-xs italic text-tx-muted">
            Calculated
          </span>
        )}
        {field.is_overridden && !field.is_computed && (
          <span
            className="ml-2 inline-block h-1.5 w-1.5 rounded-full bg-amber-400"
            title="Manual override"
          />
        )}
      </div>

      {/* Input */}
      <div className="w-36 shrink-0">
        <FieldInput field={field} onChange={onChange} />
      </div>

      {/* Prior year */}
      {showPY && <PriorYearCell value={pyValue} />}
    </div>
  );
}

function FieldInput({
  field,
  onChange,
}: {
  field: FieldValue;
  onChange: (formLineId: string, value: string) => void;
}) {
  switch (field.field_type) {
    case "currency":
      return (
        <CurrencyInput
          value={field.value}
          onValueChange={(v) => onChange(field.form_line, v)}
          readOnly={field.is_computed}
        />
      );
    case "boolean":
      return (
        <BooleanField
          value={field.value}
          readOnly={field.is_computed}
          onChange={(v) => onChange(field.form_line, v)}
        />
      );
    case "text":
      return (
        <TextInput
          value={field.value}
          readOnly={field.is_computed}
          onChange={(v) => onChange(field.form_line, v)}
        />
      );
    case "percentage":
      return (
        <PercentageInput
          value={field.value}
          readOnly={field.is_computed}
          onValueChange={(v) => onChange(field.form_line, v)}
        />
      );
    case "integer":
      return (
        <IntegerInput
          value={field.value}
          readOnly={field.is_computed}
          onValueChange={(v) => onChange(field.form_line, v)}
        />
      );
    default:
      return null;
  }
}

/** Grayed-out prior year amount cell. */
function PriorYearCell({ value }: { value?: number }) {
  if (value === undefined) {
    return <div className="w-28 shrink-0" />;
  }
  const formatted =
    value < 0
      ? `(${Math.abs(value).toLocaleString()})`
      : value.toLocaleString();
  return (
    <div className="w-28 shrink-0 text-right text-sm text-tx-muted tabular-nums">
      {formatted}
    </div>
  );
}

function TextInput({
  value,
  readOnly,
  onChange,
}: {
  value: string;
  readOnly?: boolean;
  onChange: (v: string) => void;
}) {
  const [local, setLocal] = useState(value);
  useEffect(() => {
    setLocal(value);
  }, [value]);
  return (
    <input
      type="text"
      value={local}
      readOnly={readOnly}
      onChange={(e) => setLocal(e.target.value)}
      onBlur={() => {
        if (local !== value) onChange(local);
      }}
      className={`w-full rounded-md border border-input-border px-2 py-1 text-sm text-tx shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring ${
        readOnly ? "bg-surface-alt text-tx-secondary cursor-default" : "bg-input"
      }`}
    />
  );
}

function IntegerInput({
  value,
  readOnly,
  onValueChange,
}: {
  value: string;
  readOnly?: boolean;
  onValueChange: (v: string) => void;
}) {
  const [local, setLocal] = useState(value);
  useEffect(() => {
    setLocal(value);
  }, [value]);
  return (
    <input
      type="text"
      inputMode="numeric"
      value={local}
      readOnly={readOnly}
      onChange={(e) => setLocal(e.target.value.replace(/[^0-9-]/g, ""))}
      onBlur={() => {
        if (local !== value) onValueChange(local);
      }}
      className={`w-full rounded-md border border-input-border px-2 py-1 text-right text-sm text-tx tabular-nums shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring ${
        readOnly ? "bg-surface-alt text-tx-secondary cursor-default" : "bg-input"
      }`}
    />
  );
}

function PercentageInput({
  value,
  readOnly,
  onValueChange,
}: {
  value: string;
  readOnly?: boolean;
  onValueChange: (v: string) => void;
}) {
  const [local, setLocal] = useState(value);
  useEffect(() => {
    setLocal(value);
  }, [value]);
  return (
    <div className="relative">
      <input
        type="text"
        inputMode="decimal"
        value={local}
        readOnly={readOnly}
        onChange={(e) => setLocal(e.target.value)}
        onBlur={() => {
          if (local !== value) onValueChange(local);
        }}
        className={`w-full rounded-md border border-input-border px-2 py-1 pr-7 text-right text-sm text-tx tabular-nums shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring ${
          readOnly ? "bg-surface-alt text-tx-secondary cursor-default" : "bg-input"
        }`}
      />
      <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-sm text-tx-muted">
        %
      </span>
    </div>
  );
}

function BooleanField({
  value,
  readOnly,
  onChange,
}: {
  value: string;
  readOnly?: boolean;
  onChange: (v: string) => void;
}) {
  const isYes = value === "true" || value === "1";
  const isNo = value === "false" || value === "0" || !value;
  return (
    <div className="flex items-center gap-3">
      <button
        type="button"
        disabled={readOnly}
        onClick={() => onChange("true")}
        className={`flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded border transition-colors ${
          isYes
            ? "border-primary bg-primary/10 text-primary"
            : "border-border-subtle bg-transparent text-tx-muted hover:border-border hover:text-tx-secondary"
        } ${readOnly ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
      >
        <span className={`inline-block w-3 h-3 rounded-sm border ${
          isYes ? "border-primary bg-primary text-white" : "border-border-subtle bg-white"
        } flex items-center justify-center text-[8px] leading-none`}>
          {isYes && "✓"}
        </span>
        Yes
      </button>
      <button
        type="button"
        disabled={readOnly}
        onClick={() => onChange("false")}
        className={`flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded border transition-colors ${
          isNo
            ? "border-primary bg-primary/10 text-primary"
            : "border-border-subtle bg-transparent text-tx-muted hover:border-border hover:text-tx-secondary"
        } ${readOnly ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
      >
        <span className={`inline-block w-3 h-3 rounded-sm border ${
          isNo ? "border-primary bg-primary text-white" : "border-border-subtle bg-white"
        } flex items-center justify-center text-[8px] leading-none`}>
          {isNo && "✓"}
        </span>
        No
      </button>
    </div>
  );
}

function ReturnStatusPill({ status }: { status: string }) {
  const colors: Record<string, string> = {
    draft: "bg-surface-alt text-tx-secondary",
    in_progress: "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
    in_review: "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
    approved: "bg-primary-subtle text-primary-text",
    filed: "bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  };
  return (
    <span
      className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
        colors[status] || colors.draft
      }`}
    >
      {status.replace("_", " ")}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Forms Tab — gallery of all renderable IRS form PDFs
// ---------------------------------------------------------------------------

/** Open a PDF blob in a new browser tab. */
function openPdfBlob(base64: string, filename: string) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  const blob = new Blob([bytes], { type: "application/pdf" });
  const url = URL.createObjectURL(blob);
  const w = window.open(url, "_blank");
  // Revoke after a delay so the browser has time to load
  if (w) setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

interface FormEntry {
  key: string;
  label: string;
  description: string;
  renderFn: () => Promise<{ ok: boolean; pdfBase64?: string; error?: string }>;
  condition?: boolean; // false = hide this entry
}

function FormsTab({
  taxReturnId,
  returnData,
}: {
  taxReturnId: string;
  returnData: TaxReturnData;
}) {
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const formCode = returnData.form_code;
  const shareholders = returnData.shareholders || [];
  const hasRentals = (returnData.rental_properties || []).length > 0;
  const hasCOGS = (returnData.field_values || []).some(
    (fv) => fv.section_code === "sched_a" && parseFloat(fv.value) !== 0,
  );

  // Build list of available forms
  const forms: FormEntry[] = useMemo(() => {
    const list: FormEntry[] = [
      {
        key: "main",
        label: `Form ${formCode}`,
        description: `Main return (Pages 1–5)`,
        renderFn: () => renderPdf(taxReturnId),
      },
      {
        key: "7004",
        label: "Form 7004",
        description: "Application for Automatic Extension of Time",
        renderFn: () => render7004(taxReturnId),
      },
    ];

    // COGS
    if (hasCOGS) {
      list.push({
        key: "1125a",
        label: "Form 1125-A",
        description: "Cost of Goods Sold",
        renderFn: () => render1125a(taxReturnId),
      });
    }

    // Rental
    if (hasRentals) {
      list.push({
        key: "8825",
        label: "Form 8825",
        description: "Rental Real Estate Income and Expenses",
        renderFn: () => render8825(taxReturnId),
      });
    }

    // State returns
    const stateReturns = returnData.state_returns || [];
    for (const sr of stateReturns) {
      list.push({
        key: `state-${sr.id}`,
        label: `${sr.form_code}`,
        description: `State return`,
        renderFn: () => renderPdf(sr.id),
      });
    }
    // If this IS a state return, the main form is already the state form
    if (formCode === "GA-600S") {
      // Already rendered as "main" — no additional entries needed
    }

    // Shareholder-level forms (1120-S only)
    if (formCode === "1120-S" && shareholders.length > 0) {
      // All K-1s combined
      list.push({
        key: "k1s-all",
        label: "Schedule K-1 (All)",
        description: `All ${shareholders.length} Schedule K-1s combined`,
        renderFn: () => renderK1s(taxReturnId),
      });

      // Individual K-1s
      for (const sh of shareholders) {
        list.push({
          key: `k1-${sh.id}`,
          label: `K-1: ${sh.name}`,
          description: `${sh.ownership_percentage}% ownership`,
          renderFn: () => renderK1(taxReturnId, sh.id),
        });
      }

      // All 7203s combined
      list.push({
        key: "7203s-all",
        label: "Form 7203 (All)",
        description: "All shareholder basis limitation forms",
        renderFn: () => render7203s(taxReturnId),
      });

      // Individual 7203s
      for (const sh of shareholders) {
        list.push({
          key: `7203-${sh.id}`,
          label: `7203: ${sh.name}`,
          description: "Stock and Debt Basis Limitations",
          renderFn: () => render7203(taxReturnId, sh.id),
        });
      }

      // 7206 for shareholders with health insurance
      for (const sh of shareholders) {
        const premium = parseFloat(sh.health_insurance_premium || "0");
        if (premium > 0) {
          list.push({
            key: `7206-${sh.id}`,
            label: `7206: ${sh.name}`,
            description: "Self-Employed Health Insurance Deduction",
            renderFn: () => render7206(taxReturnId, sh.id),
          });
        }
      }
    }

    return list;
  }, [taxReturnId, formCode, shareholders, hasRentals, hasCOGS]);

  const [activeForm, setActiveForm] = useState<string>("main");
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const pdfUrlRef = useRef<string | null>(null);

  // Auto-load the selected form's PDF
  async function loadForm(key: string) {
    const entry = forms.find((f) => f.key === key);
    if (!entry) return;

    // Revoke previous URL
    if (pdfUrlRef.current) {
      URL.revokeObjectURL(pdfUrlRef.current);
      pdfUrlRef.current = null;
    }
    setPdfUrl(null);
    setLoading(key);
    setError(null);

    const res = await entry.renderFn();
    setLoading(null);

    if (res.ok && res.pdfBase64) {
      const binary = atob(res.pdfBase64);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      const blob = new Blob([bytes], { type: "application/pdf" });
      const url = URL.createObjectURL(blob);
      pdfUrlRef.current = url;
      setPdfUrl(url);
    } else {
      setError(res.error || "Failed to generate PDF.");
    }
  }

  // Auto-load main form on first render
  useEffect(() => {
    loadForm("main");
    return () => {
      if (pdfUrlRef.current) URL.revokeObjectURL(pdfUrlRef.current);
    };
  }, [taxReturnId]);

  function handleSelectForm(key: string) {
    setActiveForm(key);
    loadForm(key);
  }

  function handleDownload() {
    if (!pdfUrl) return;
    const entry = forms.find((f) => f.key === activeForm);
    const a = document.createElement("a");
    a.href = pdfUrl;
    a.download = `${entry?.label || "form"}.pdf`;
    a.click();
  }

  // Group forms for sidebar
  const groups: { title: string; entries: FormEntry[] }[] = [
    { title: "Return", entries: forms.filter((f) => ["main", "7004", "1125a", "8825"].includes(f.key)) },
    { title: "State", entries: forms.filter((f) => f.key.startsWith("state-")) },
    { title: "K-1s", entries: forms.filter((f) => f.key === "k1s-all" || f.key.startsWith("k1-")) },
    { title: "Basis (7203)", entries: forms.filter((f) => f.key === "7203s-all" || f.key.startsWith("7203-")) },
    { title: "Health (7206)", entries: forms.filter((f) => f.key.startsWith("7206-")) },
  ].filter((g) => g.entries.length > 0);

  return (
    <div className="flex gap-0 -mx-2" style={{ height: "calc(100vh - 14rem)" }}>
      {/* Sidebar — form selector */}
      <div className="w-56 shrink-0 overflow-y-auto border-r border-border bg-card">
        {groups.map((group) => (
          <div key={group.title}>
            <div className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-tx-muted bg-surface-alt border-b border-border-subtle">
              {group.title}
            </div>
            {group.entries.map((entry) => (
              <button
                key={entry.key}
                onClick={() => handleSelectForm(entry.key)}
                className={`block w-full text-left px-3 py-2 text-sm transition border-b border-border-subtle ${
                  activeForm === entry.key
                    ? "bg-primary-subtle text-primary-text font-semibold"
                    : "text-tx hover:bg-surface-alt/50"
                }`}
              >
                {entry.label}
              </button>
            ))}
          </div>
        ))}
      </div>

      {/* PDF viewer */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Toolbar */}
        <div className="flex items-center justify-between border-b border-border bg-card px-4 py-1.5">
          <span className="text-sm font-semibold text-tx">
            {forms.find((f) => f.key === activeForm)?.label || ""}
          </span>
          <button
            onClick={handleDownload}
            disabled={!pdfUrl}
            className="rounded-lg bg-primary px-3 py-1 text-sm font-semibold text-white hover:bg-primary-hover disabled:opacity-50"
          >
            Download
          </button>
        </div>

        {/* PDF content */}
        {loading && (
          <div className="flex flex-1 items-center justify-center">
            <div className="text-center">
              <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-4 border-primary-subtle border-t-primary" />
              <p className="text-sm text-tx-secondary">Generating PDF...</p>
            </div>
          </div>
        )}
        {error && !loading && (
          <div className="flex flex-1 items-center justify-center">
            <p className="text-sm text-danger">{error}</p>
          </div>
        )}
        {pdfUrl && !loading && (
          <iframe
            src={pdfUrl}
            className="flex-1 border-0"
            title="Form PDF"
          />
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// State Section — filing states + create state return
// ---------------------------------------------------------------------------

function StateSection({
  taxReturnId,
  returnData,
  onRefresh,
}: {
  taxReturnId: string;
  returnData: TaxReturnData;
  onRefresh: () => Promise<void>;
}) {
  const navigate = useNavigate();
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const filingStates = returnData.filing_states || [];
  const stateReturns = returnData.state_returns || [];

  // Map of state code → state return (if created)
  const stateReturnMap: Record<string, { id: string; form_code: string; status: string }> = {};
  for (const sr of stateReturns) {
    // Extract state from form_code (e.g., "GA-600S" → "GA")
    const stateCode = sr.form_code.split("-")[0];
    stateReturnMap[stateCode] = sr;
  }

  async function handleCreateStateReturn(stateCode: string) {
    setCreating(true);
    setError(null);
    const res = await post(`/tax-returns/${taxReturnId}/create-state-return/`, {
      state: stateCode,
    });
    setCreating(false);
    if (res.ok) {
      await onRefresh();
    } else {
      const data = res.data as { error?: string };
      setError(data?.error || "Failed to create state return.");
    }
  }

  // Supported states
  const SUPPORTED_STATES: Record<string, string> = {
    GA: "Georgia (Form 600S)",
  };

  return (
    <div className="space-y-6">
      {/* Filing States */}
      <div className="rounded-lg border border-border bg-card p-5">
        <h3 className="text-base font-semibold text-tx mb-4">State Filing</h3>

        {filingStates.length === 0 ? (
          <p className="text-sm text-tx-secondary">
            No filing states configured. Edit the entity&apos;s state address or
            update the tax year&apos;s filing states to enable state returns.
          </p>
        ) : (
          <div className="space-y-3">
            {filingStates.map((stateCode) => {
              const sr = stateReturnMap[stateCode];
              const supported = stateCode in SUPPORTED_STATES;
              return (
                <div
                  key={stateCode}
                  className="flex items-center justify-between rounded-lg border border-border-subtle bg-surface-alt/30 px-4 py-3"
                >
                  <div>
                    <span className="text-sm font-semibold text-tx">
                      {SUPPORTED_STATES[stateCode] || stateCode}
                    </span>
                    {sr && (
                      <span className="ml-2 inline-flex items-center rounded-full bg-primary-subtle px-2 py-0.5 text-xs font-medium text-primary-text">
                        {sr.status}
                      </span>
                    )}
                  </div>
                  <div>
                    {sr ? (
                      <button
                        onClick={() => navigate(`/tax-returns/${sr.id}/editor`)}
                        className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white hover:bg-primary-hover"
                      >
                        Open {sr.form_code}
                      </button>
                    ) : supported ? (
                      <button
                        onClick={() => handleCreateStateReturn(stateCode)}
                        disabled={creating}
                        className="rounded-lg bg-green-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-green-700 disabled:opacity-50"
                      >
                        {creating ? "Creating..." : `Create ${SUPPORTED_STATES[stateCode]?.split(" ")[0] || stateCode} Return`}
                      </button>
                    ) : (
                      <span className="text-xs text-tx-muted">Not yet supported</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {error && (
          <p className="mt-3 text-sm text-danger">{error}</p>
        )}
      </div>

      {/* Quick add state */}
      {filingStates.length === 0 && (
        <div className="rounded-lg border border-border bg-card p-5">
          <p className="text-sm text-tx-secondary">
            Tip: The tax year&apos;s filing states are automatically set from the
            entity&apos;s address state when created. You can also add states via
            the API.
          </p>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Prior Year Summary Section — CY vs PY comparison
// ---------------------------------------------------------------------------

/** Groups of lines for the PY comparison view. */
const PY_COMPARE_GROUPS: { title: string; lines: { ln: string; label: string }[] }[] = [
  {
    title: "Page 1 — Income",
    lines: [
      { ln: "1a", label: "Gross receipts or sales" },
      { ln: "1b", label: "Returns and allowances" },
      { ln: "1c", label: "Net receipts" },
      { ln: "2", label: "Cost of goods sold" },
      { ln: "3", label: "Gross profit" },
      { ln: "4", label: "Net gain (loss) from Form 4797" },
      { ln: "5", label: "Other income (loss)" },
      { ln: "6", label: "Total income (loss)" },
    ],
  },
  {
    title: "Page 1 — Deductions",
    lines: [
      { ln: "7", label: "Compensation of officers" },
      { ln: "8", label: "Salaries and wages" },
      { ln: "9", label: "Repairs and maintenance" },
      { ln: "10", label: "Bad debts" },
      { ln: "11", label: "Rents" },
      { ln: "12", label: "Taxes and licenses" },
      { ln: "13", label: "Interest" },
      { ln: "14", label: "Depreciation" },
      { ln: "17", label: "Pension/profit-sharing plans" },
      { ln: "18", label: "Employee benefit programs" },
      { ln: "19", label: "Other deductions" },
      { ln: "20", label: "Total deductions" },
      { ln: "21", label: "Ordinary business income (loss)" },
    ],
  },
  {
    title: "Schedule K Highlights",
    lines: [
      { ln: "K1", label: "Ordinary business income (loss)" },
      { ln: "K2", label: "Net rental real estate income (loss)" },
      { ln: "K5a", label: "Net short-term capital gain (loss)" },
      { ln: "K6", label: "Net long-term capital gain (loss)" },
      { ln: "K11", label: "Section 179 deduction" },
      { ln: "K12a", label: "Charitable contributions" },
      { ln: "K16c", label: "Nondeductible expenses" },
      { ln: "K16d", label: "Distributions" },
      { ln: "K18", label: "Total income/loss reconciliation" },
    ],
  },
  {
    title: "Balance Sheet (EOY)",
    lines: [
      { ln: "L1d", label: "Cash" },
      { ln: "L2d", label: "Trade notes and accounts receivable" },
      { ln: "L3d", label: "Inventories" },
      { ln: "L9d", label: "Buildings and other depreciable assets" },
      { ln: "L14d", label: "Total assets" },
      { ln: "L15d", label: "Accounts payable" },
      { ln: "L20d", label: "Loans from shareholders" },
      { ln: "L24d", label: "Retained earnings" },
      { ln: "L27d", label: "Total liabilities and shareholders' equity" },
    ],
  },
  {
    title: "Schedule M-2 (AAA)",
    lines: [
      { ln: "M2_1", label: "Balance at beginning of year" },
      { ln: "M2_2", label: "Ordinary income" },
      { ln: "M2_5", label: "Other reductions" },
      { ln: "M2_7", label: "Distributions" },
      { ln: "M2_8", label: "Balance at end of year" },
    ],
  },
];

interface InterestTrendData {
  form_code: string;
  interest_line: string;
  years: { year: number; amount: string | null }[];
}

function PriorYearSummarySection({
  taxReturnId,
  fieldsBySection,
  priorYear,
  currentYear,
}: {
  taxReturnId: string;
  fieldsBySection: Record<string, FieldValue[]>;
  priorYear: PriorYearData | null;
  currentYear: number;
}) {
  const [interestTrend, setInterestTrend] = useState<InterestTrendData | null>(null);

  useEffect(() => {
    get(`/tax-returns/${taxReturnId}/interest-trend/`).then((res) => {
      if (res.ok) setInterestTrend(res.data as InterestTrendData);
    });
  }, [taxReturnId]);

  if (!priorYear) {
    return (
      <div className="rounded-xl border border-border bg-card p-8 text-center shadow-sm">
        <p className="text-sm text-tx-secondary">No prior year data available for comparison.</p>
      </div>
    );
  }

  // Build CY lookup: line_number → number
  const cyLookup: Record<string, number> = {};
  for (const fields of Object.values(fieldsBySection)) {
    for (const f of fields) {
      const num = parseFloat(f.value);
      if (!isNaN(num)) cyLookup[f.line_number] = num;
    }
  }

  const pyLines = priorYear.line_values ?? {};
  const pyYear = priorYear.year;

  const fmt = (n: number | undefined) =>
    n !== undefined && n !== 0
      ? n.toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 })
      : "—";

  const fmtPct = (cy: number, py: number) => {
    if (!py) return "";
    const pct = ((cy - py) / Math.abs(py)) * 100;
    return `${pct >= 0 ? "+" : ""}${pct.toFixed(0)}%`;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-tx">
          Prior Year Comparison — {currentYear} vs {pyYear}
        </h3>
        <span className="text-xs text-tx-secondary">
          Source: {priorYear.form_code}
        </span>
      </div>

      {/* 3-Year Interest Expense Card */}
      {interestTrend && interestTrend.years.length > 0 && (
        <div className="rounded-xl border border-primary/20 bg-primary/5 shadow-sm">
          <div className="border-b border-primary/20 bg-primary/10 px-4 py-2 rounded-t-xl">
            <h4 className="text-sm font-semibold text-primary-text">
              3-Year Interest Expense (Line {interestTrend.interest_line})
            </h4>
          </div>
          <div className="flex divide-x divide-primary/20">
            {interestTrend.years.map((yr) => {
              const amt = yr.amount !== null ? parseFloat(yr.amount) : null;
              return (
                <div key={yr.year} className="flex-1 px-4 py-3 text-center">
                  <div className="text-xs font-medium text-tx-secondary">{yr.year}</div>
                  <div className="mt-1 text-lg font-semibold tabular-nums font-mono text-tx">
                    {amt !== null
                      ? `$${amt.toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
                      : "—"}
                  </div>
                  {yr.year === currentYear && (
                    <div className="text-[10px] text-tx-muted">Current</div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {PY_COMPARE_GROUPS.map((group) => {
        // Only show groups that have at least some data
        const hasData = group.lines.some(
          (l) => (cyLookup[l.ln] ?? 0) !== 0 || (pyLines[l.ln] ?? 0) !== 0
        );
        if (!hasData) return null;

        return (
          <div key={group.title} className="rounded-xl border border-border bg-card shadow-sm">
            <div className="border-b border-border bg-slate-50 px-4 py-2 rounded-t-xl">
              <h4 className="text-sm font-semibold text-tx">{group.title}</h4>
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-xs text-tx-secondary">
                  <th className="px-4 py-1.5 text-left font-medium">Line</th>
                  <th className="px-4 py-1.5 text-left font-medium">Description</th>
                  <th className="px-4 py-1.5 text-right font-medium">{currentYear} (CY)</th>
                  <th className="px-4 py-1.5 text-right font-medium">{pyYear} (PY)</th>
                  <th className="px-4 py-1.5 text-right font-medium">Change</th>
                  <th className="px-4 py-1.5 text-right font-medium">%</th>
                </tr>
              </thead>
              <tbody>
                {group.lines.map((l) => {
                  const cy = cyLookup[l.ln] ?? 0;
                  const py = pyLines[l.ln] ?? 0;
                  const diff = cy - py;
                  const hasDiff = Math.abs(diff) >= 1;

                  return (
                    <tr key={l.ln} className="border-b border-border/50 hover:bg-slate-50/50">
                      <td className="px-4 py-1 text-tx-secondary font-mono text-xs">{l.ln}</td>
                      <td className="px-4 py-1 text-tx">{l.label}</td>
                      <td className="px-4 py-1 text-right font-mono tabular-nums">{fmt(cy)}</td>
                      <td className="px-4 py-1 text-right font-mono tabular-nums text-tx-secondary">{fmt(py)}</td>
                      <td className={`px-4 py-1 text-right font-mono tabular-nums ${
                        hasDiff ? (diff > 0 ? "text-success" : "text-danger") : "text-tx-muted"
                      }`}>
                        {hasDiff ? `${diff > 0 ? "+" : ""}${fmt(diff)}` : "—"}
                      </td>
                      <td className={`px-4 py-1 text-right text-xs ${
                        hasDiff ? (diff > 0 ? "text-success" : "text-danger") : "text-tx-muted"
                      }`}>
                        {hasDiff ? fmtPct(cy, py) : ""}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Diagnostics Tab — validation findings
// ---------------------------------------------------------------------------

interface DiagnosticFinding {
  id: string;
  severity: "error" | "warning" | "info";
  message: string;
  details: Record<string, unknown> | null;
  is_resolved: boolean;
  rule_name: string;
}

interface DiagnosticRunData {
  id: string;
  status: string;
  finding_count: number;
  started_at: string;
  completed_at: string | null;
  findings: DiagnosticFinding[];
}

function DiagnosticsTab({ taxYearId }: { taxYearId: string }) {
  const [runs, setRuns] = useState<DiagnosticRunData[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function fetchRuns() {
    const res = await get(`/diagnostic-runs/?tax_year=${taxYearId}`);
    if (res.ok) {
      setRuns((res.data as { results?: DiagnosticRunData[] }).results || (res.data as DiagnosticRunData[]));
    }
    setLoading(false);
  }

  useEffect(() => {
    fetchRuns();
  }, [taxYearId]);

  async function handleRun() {
    setRunning(true);
    setError(null);
    const res = await post("/diagnostic-runs/run/", { tax_year: taxYearId });
    setRunning(false);
    if (res.ok) {
      fetchRuns();
    } else {
      const err = res.data as { error?: string };
      setError(err.error || "Failed to run diagnostics.");
    }
  }

  const latestRun = runs.length > 0 ? runs[0] : null;
  const findings = latestRun?.findings || [];
  const errors = findings.filter((f) => f.severity === "error");
  const warnings = findings.filter((f) => f.severity === "warning");
  const infos = findings.filter((f) => f.severity === "info");

  const SEVERITY_STYLES: Record<string, { bg: string; text: string; label: string }> = {
    error: { bg: "bg-danger/10", text: "text-danger", label: "Error" },
    warning: { bg: "bg-warning/10", text: "text-warning-dark", label: "Warning" },
    info: { bg: "bg-primary/10", text: "text-primary-text", label: "Info" },
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-tx">Return Diagnostics</h3>
          {latestRun && (
            <p className="text-sm text-tx-secondary">
              Last run: {new Date(latestRun.started_at).toLocaleString()}
              {" — "}
              {latestRun.finding_count} finding{latestRun.finding_count !== 1 ? "s" : ""}
            </p>
          )}
        </div>
        <button
          onClick={handleRun}
          disabled={running}
          className="rounded-lg bg-success px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-success-hover disabled:opacity-50"
        >
          {running ? "Running..." : "Run Diagnostics"}
        </button>
      </div>

      {error && (
        <div className="rounded-lg bg-danger/10 px-4 py-2 text-sm text-danger">{error}</div>
      )}

      {loading && <p className="text-sm text-tx-secondary">Loading...</p>}

      {!loading && !latestRun && (
        <div className="rounded-xl border border-border bg-card p-8 text-center shadow-sm">
          <p className="text-sm text-tx-secondary">No diagnostics have been run yet.</p>
          <p className="mt-1 text-sm text-tx-secondary">Click "Run Diagnostics" to check this return for issues.</p>
        </div>
      )}

      {/* Summary pills */}
      {latestRun && findings.length > 0 && (
        <div className="flex gap-3">
          {errors.length > 0 && (
            <span className="rounded-full bg-danger/10 px-3 py-1 text-sm font-semibold text-danger">
              {errors.length} Error{errors.length !== 1 ? "s" : ""}
            </span>
          )}
          {warnings.length > 0 && (
            <span className="rounded-full bg-warning/10 px-3 py-1 text-sm font-semibold text-warning-dark">
              {warnings.length} Warning{warnings.length !== 1 ? "s" : ""}
            </span>
          )}
          {infos.length > 0 && (
            <span className="rounded-full bg-primary/10 px-3 py-1 text-sm font-semibold text-primary-text">
              {infos.length} Info
            </span>
          )}
        </div>
      )}

      {latestRun && findings.length === 0 && (
        <div className="rounded-xl border border-success/30 bg-success/5 p-6 text-center shadow-sm">
          <svg className="mx-auto mb-2 h-8 w-8 text-success" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-sm font-semibold text-success">No issues found</p>
        </div>
      )}

      {/* Findings list */}
      {findings.length > 0 && (
        <div className="rounded-xl border border-border bg-card shadow-sm divide-y divide-border-subtle">
          {[...errors, ...warnings, ...infos].map((f) => {
            const style = SEVERITY_STYLES[f.severity] || SEVERITY_STYLES.info;
            return (
              <div key={f.id} className="flex items-start gap-3 px-5 py-3">
                <span className={`mt-0.5 shrink-0 rounded px-2 py-0.5 text-xs font-bold uppercase ${style.bg} ${style.text}`}>
                  {style.label}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-tx">{f.message}</p>
                  {f.details && Object.keys(f.details).length > 0 && (
                    <p className="mt-1 text-xs text-tx-secondary">
                      {JSON.stringify(f.details)}
                    </p>
                  )}
                </div>
                <span className="text-xs text-tx-muted">{f.rule_name}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Save Status Indicator
// ---------------------------------------------------------------------------

function SaveStatusIndicator({
  status,
}: {
  status: "idle" | "saving" | "saved" | "error";
}) {
  const config = {
    idle: { text: "Auto-save on", icon: "check", color: "text-tx-muted" },
    saving: { text: "Saving...", icon: "sync", color: "text-primary-text" },
    saved: { text: "All changes saved", icon: "check", color: "text-success" },
    error: { text: "Save failed — retrying", icon: "warn", color: "text-danger" },
  };
  const { text, icon, color } = config[status];
  return (
    <span className={`flex items-center gap-1.5 text-xs font-medium ${color}`}>
      {icon === "check" && (
        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
        </svg>
      )}
      {icon === "sync" && (
        <svg className="h-3.5 w-3.5 animate-spin" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
        </svg>
      )}
      {icon === "warn" && (
        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
        </svg>
      )}
      {text}
    </span>
  );
}
