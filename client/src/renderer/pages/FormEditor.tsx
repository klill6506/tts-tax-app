import { useEffect, useMemo, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { get, patch, post } from "../lib/api";
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

interface TaxReturnData {
  id: string;
  tax_year_id: string;
  year: number;
  entity_name: string;
  client_name: string;
  form_code: string;
  status: string;
  field_values: FieldValue[];
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
  // Schedule L — Balance Sheet
  ["L14a", (v) => sumLines(v, "L1a","L2a","L5a","L7a") + val(v, "L9a") - val(v, "L9b")],
  ["L14d", (v) => sumLines(v, "L1d","L2d","L5d","L7d") + val(v, "L9d") - val(v, "L9e")],
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

/** Set of line numbers that are computed — used for quick lookup. */
const COMPUTED_LINES = new Set(FORMULAS_1120S.map(([ln]) => ln));

/**
 * Run all formulas over current field values and return updated values.
 * Only updates computed fields — input fields are left untouched.
 */
function computeFields(fieldValues: FieldValue[]): FieldValue[] {
  // Build line_number → numeric value map from all current values
  const numValues: Record<string, number> = {};
  for (const fv of fieldValues) {
    const n = parseFloat(fv.value);
    numValues[fv.line_number] = isNaN(n) ? 0 : n;
  }

  // Evaluate formulas in order
  const computedValues: Record<string, string> = {};
  for (const [lineNum, fn] of FORMULAS_1120S) {
    const result = fn(numValues);
    numValues[lineNum] = result; // update for downstream formulas
    computedValues[lineNum] = result.toFixed(2);
  }

  // Return updated field values with computed results applied
  return fieldValues.map((fv) => {
    if (COMPUTED_LINES.has(fv.line_number)) {
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
  { id: "page1", label: "Page 1", sections: ["page1_income", "page1_deductions"] },
  { id: "sched_a", label: "COGS", sections: ["sched_a"] },
  { id: "page1_tax", label: "Tax & Payments", sections: ["page1_tax"] },
  { id: "sched_k", label: "Schedule K", sections: ["sched_k"] },
  { id: "sched_l", label: "Schedule L", sections: ["sched_l"] },
  { id: "sched_m1", label: "M-1", sections: ["sched_m1"] },
  { id: "sched_m2", label: "M-2", sections: ["sched_m2"] },
];

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function FormEditor() {
  const { taxReturnId } = useParams<{ taxReturnId: string }>();

  const [returnData, setReturnData] = useState<TaxReturnData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("page1");

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
      field_values: computeFields(data.field_values),
    });
  }

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

  const activeTabDef = SECTION_TABS.find((t) => t.id === activeTab);

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
      return { ...prev, field_values: computeFields(updated) };
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

  // ---- Render ----

  if (loading) return <p className="text-sm text-slate-500">Loading...</p>;
  if (error)
    return <p className="text-sm text-red-600">{error}</p>;
  if (!returnData)
    return <p className="text-sm text-red-600">Return not found.</p>;

  return (
    <div>
      {/* Breadcrumb */}
      <div className="mb-4 text-sm text-slate-500">
        <Link to="/clients" className="text-blue-600 hover:underline">
          Clients
        </Link>
        <span className="mx-2">/</span>
        <span className="text-slate-800">{returnData.client_name}</span>
        <span className="mx-2">/</span>
        <span className="text-slate-800">{returnData.entity_name}</span>
      </div>

      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Form {returnData.form_code}
          </h1>
          <p className="text-sm text-slate-500">
            {returnData.entity_name} &mdash; Tax Year {returnData.year}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <ReturnStatusPill status={returnData.status} />
          {importResult && (
            <span className="text-sm font-medium text-green-600">
              {importResult}
            </span>
          )}
          <SaveStatusIndicator status={saveStatus} />
          <button
            onClick={handleImportTB}
            disabled={importing}
            className="rounded-md bg-green-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-green-700 disabled:opacity-50"
          >
            {importing ? "Importing..." : "Import Trial Balance"}
          </button>
          <button
            onClick={flushDirty}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700"
          >
            Save All
          </button>
        </div>
      </div>

      {/* Tab bar */}
      <div className="mb-4 flex gap-1 overflow-x-auto border-b border-slate-200">
        {SECTION_TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`whitespace-nowrap px-4 py-2.5 text-sm font-medium transition ${
              activeTab === tab.id
                ? "border-b-2 border-blue-600 text-blue-700"
                : "text-slate-500 hover:text-slate-800"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Active section content */}
      {activeTab === "sched_l" ? (
        <ScheduleLSection
          fields={fieldsForActiveTab}
          onChange={handleFieldChange}
        />
      ) : (
        <StandardSection
          sections={activeTabDef?.sections ?? []}
          fieldsBySection={fieldsBySection}
          onChange={handleFieldChange}
        />
      )}
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
}: {
  sections: string[];
  fieldsBySection: Record<string, FieldValue[]>;
  onChange: (formLineId: string, value: string) => void;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
      {sections.map((secCode, idx) => {
        const fields = fieldsBySection[secCode] || [];
        if (fields.length === 0) return null;
        return (
          <div key={secCode}>
            {/* Section divider for multi-section tabs */}
            {sections.length > 1 && (
              <div
                className={`px-4 py-2 text-xs font-bold uppercase tracking-wider text-slate-600 bg-slate-100 ${
                  idx > 0 ? "border-t-2 border-slate-200" : ""
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
              <div className="flex items-center gap-4 border-b border-slate-200 bg-slate-50 px-4 py-2.5">
                <div className="w-14 shrink-0 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Line
                </div>
                <div className="flex-1 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Description
                </div>
                <div className="w-48 shrink-0 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Amount
                </div>
              </div>
            )}
            <div className="divide-y divide-slate-100">
              {fields.map((fv) => (
                <FieldRow key={fv.id} field={fv} onChange={onChange} />
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
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
      {/* Column headers */}
      <div className="flex items-center gap-4 border-b border-slate-200 bg-slate-50 px-4 py-2.5">
        <div className="w-10 shrink-0 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Line
        </div>
        <div className="flex-1 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Description
        </div>
        <div className="w-40 shrink-0 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">
          Beginning of Year
        </div>
        <div className="w-40 shrink-0 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">
          End of Year
        </div>
      </div>

      <div className="divide-y divide-slate-100">
        {groups.map((g, i) => {
          const lineNum = g.boy?.line_number?.replace(/[a-b]$/, "") ||
            g.eoy?.line_number?.replace(/[d-e]$/, "") || "";
          const isComputed = (g.boy?.is_computed || g.eoy?.is_computed) ?? false;

          // Section dividers
          const isTotalAssets = lineNum === "L14";
          const isFirstLiability = lineNum === "L15";
          const isFirstEquity = lineNum === "L21";
          const isTotalLE = lineNum === "L27";

          return (
            <div key={i}>
              {isFirstLiability && (
                <div className="px-4 py-2 text-xs font-bold uppercase tracking-wider text-slate-600 bg-slate-100 border-t-2 border-slate-200">
                  Liabilities
                </div>
              )}
              {isFirstEquity && (
                <div className="px-4 py-2 text-xs font-bold uppercase tracking-wider text-slate-600 bg-slate-100 border-t border-slate-200">
                  Equity
                </div>
              )}
              <div
                className={`flex items-center gap-4 px-4 py-3 ${
                  isComputed || isTotalAssets || isTotalLE
                    ? "bg-slate-50/50 font-medium"
                    : ""
                }`}
              >
                <div className="w-10 shrink-0 text-sm text-slate-500">
                  {lineNum}
                </div>
                <div className="flex-1">
                  <span className="text-sm text-slate-900">{g.label}</span>
                  {isComputed && (
                    <span className="ml-2 text-xs italic text-slate-400">
                      Calculated
                    </span>
                  )}
                </div>
                <div className="w-40 shrink-0">
                  {g.boy ? (
                    <FieldInput field={g.boy} onChange={onChange} />
                  ) : (
                    <div />
                  )}
                </div>
                <div className="w-40 shrink-0">
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
}: {
  field: FieldValue;
  onChange: (formLineId: string, value: string) => void;
}) {
  return (
    <div
      className={`flex items-center gap-4 px-4 py-3 ${
        field.is_computed ? "bg-slate-50/50" : ""
      }`}
    >
      {/* Line number */}
      <div className="w-14 shrink-0 text-sm font-medium text-slate-500">
        {field.line_number}
      </div>

      {/* Label */}
      <div className="flex-1">
        <span className="text-sm text-slate-900">{field.label}</span>
        {field.is_computed && (
          <span className="ml-2 text-xs italic text-slate-400">
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
      <div className="w-48 shrink-0">
        <FieldInput field={field} onChange={onChange} />
      </div>
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
      className={`w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 ${
        readOnly ? "bg-slate-50 text-slate-500 cursor-default" : "bg-white"
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
      className={`w-full rounded-md border border-slate-300 px-3 py-2 text-right text-sm tabular-nums shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 ${
        readOnly ? "bg-slate-50 text-slate-500 cursor-default" : "bg-white"
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
        className={`w-full rounded-md border border-slate-300 px-3 py-2 pr-8 text-right text-sm tabular-nums shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 ${
          readOnly ? "bg-slate-50 text-slate-500 cursor-default" : "bg-white"
        }`}
      />
      <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-sm text-slate-400">
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
  const checked = value === "true" || value === "1";
  return (
    <label className="flex items-center justify-end gap-2 cursor-pointer">
      <input
        type="checkbox"
        checked={checked}
        disabled={readOnly}
        onChange={(e) => onChange(e.target.checked ? "true" : "false")}
        className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
      />
      <span className="text-sm text-slate-600">{checked ? "Yes" : "No"}</span>
    </label>
  );
}

function ReturnStatusPill({ status }: { status: string }) {
  const colors: Record<string, string> = {
    draft: "bg-slate-100 text-slate-600",
    in_progress: "bg-amber-50 text-amber-700",
    in_review: "bg-amber-50 text-amber-700",
    approved: "bg-blue-50 text-blue-700",
    filed: "bg-green-50 text-green-700",
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

function SaveStatusIndicator({
  status,
}: {
  status: "idle" | "saving" | "saved" | "error";
}) {
  if (status === "idle") return null;
  const config = {
    saving: { text: "Saving...", color: "text-slate-500" },
    saved: { text: "Saved", color: "text-green-600" },
    error: { text: "Save failed", color: "text-red-600" },
  };
  const { text, color } = config[status];
  return <span className={`text-sm font-medium ${color}`}>{text}</span>;
}
