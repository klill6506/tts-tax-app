import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { get, patch, post, del } from "../lib/api";
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
  field_values: FieldValue[];
  other_deductions: OtherDeductionRow[];
  officers: OfficerRow[];
  shareholders: ShareholderRow[];
  rental_properties: RentalPropertyRow[];
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
  { id: "page1", label: "Income & Deductions", sections: ["page1_income", "sched_a", "page1_deductions"] },
  { id: "other_ded", label: "Other Ded.", sections: [] },
  { id: "rental", label: "Rental (8825)", sections: [] },
  { id: "sched_b", label: "Schedule B", sections: ["sched_b"] },
  { id: "sched_k", label: "Schedule K", sections: ["sched_k"] },
  { id: "balance_sheets", label: "Balance Sheets", sections: ["sched_l", "sched_m1", "sched_m2"] },
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
          Client Manager
        </Link>
        <span className="mx-2">/</span>
        <span className="text-tx">{returnData.client_name}</span>
        <span className="mx-2">/</span>
        <span className="text-tx">{returnData.entity_name}</span>
        <span className="mx-2">/</span>
        <span className="font-medium text-tx">
          {returnData.form_code} &mdash; {returnData.year}
        </span>
      </div>

      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
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
          <Link
            to={`/tax-returns/${taxReturnId}/preview`}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-primary-hover"
          >
            Preview
          </Link>
          <button
            onClick={handleImportTB}
            disabled={importing}
            className="rounded-lg bg-success px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-success-hover disabled:opacity-50"
          >
            {importing ? "Importing..." : "Import Trial Balance"}
          </button>
        </div>
      </div>

      {/* Tab bar */}
      <div className="mb-4 flex gap-1 overflow-x-auto border-b border-border">
        {SECTION_TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`whitespace-nowrap px-4 py-2.5 text-sm font-medium transition ${
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
      ) : activeTab === "other_ded" ? (
        <OtherDeductionsSection
          taxReturnId={taxReturnId!}
          deductions={returnData.other_deductions || []}
          onRefresh={refreshReturn}
        />
      ) : activeTab === "rental" ? (
        <RentalPropertiesSection
          taxReturnId={taxReturnId!}
          properties={returnData.rental_properties || []}
          onRefresh={refreshReturn}
        />
      ) : activeTab === "balance_sheets" ? (
        <BalanceSheetsSection
          fieldsBySection={fieldsBySection}
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

  // Officers
  const [officers, setOfficers] = useState<OfficerRow[]>(
    returnData.officers || []
  );
  const [editingOfficer, setEditingOfficer] = useState<Partial<OfficerRow> | null>(null);
  const [officerSaving, setOfficerSaving] = useState(false);

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
    setOfficers(returnData.officers || []);
  }, [returnData]);

  // Format helpers — auto-insert dashes for EIN (XX-XXXXXXX) and SSN (XXX-XX-XXXX)
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

  // Entity field changes
  function handleEntityChange(field: keyof EntityInfo, value: string) {
    if (!entity) return;
    if (field === "ein") value = formatEIN(value);
    setEntity({ ...entity, [field]: value });
  }

  async function saveEntity() {
    if (!entity) return;
    setSaving(true);
    setSaveMsg(null);
    const res = await patch(`/entities/${entity.id}/`, {
      legal_name: entity.legal_name,
      ein: entity.ein,
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
        percent_ownership: editingOfficer.percent_ownership || "0",
        compensation: editingOfficer.compensation || "0",
      });
      if (res.ok) {
        await onRefresh();
        setEditingOfficer(null);
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
    "w-full rounded-md border border-input-border bg-input px-3 py-2 text-sm text-tx shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring";

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
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left">
                  <th className="pb-2 pr-4 font-semibold text-tx-secondary">Name</th>
                  <th className="pb-2 pr-4 font-semibold text-tx-secondary">Title</th>
                  <th className="pb-2 pr-4 font-semibold text-tx-secondary">SSN</th>
                  <th className="pb-2 pr-4 text-right font-semibold text-tx-secondary">
                    % Ownership
                  </th>
                  <th className="pb-2 pr-4 text-right font-semibold text-tx-secondary">
                    Compensation
                  </th>
                  <th className="pb-2 font-semibold text-tx-secondary">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle">
                {officers.map((o) => (
                  <tr key={o.id}>
                    <td className="py-2 pr-4 text-tx">{o.name}</td>
                    <td className="py-2 pr-4 text-tx">{o.title}</td>
                    <td className="py-2 pr-4 text-tx">{o.ssn}</td>
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
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
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
            <div className="mt-3 flex gap-2">
              <button
                onClick={saveOfficer}
                disabled={officerSaving}
                className="rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-primary-hover disabled:opacity-50"
              >
                {officerSaving ? "Saving..." : "Save"}
              </button>
              <button
                onClick={() => setEditingOfficer(null)}
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
// Other Deductions Section
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

          <div className="divide-y divide-border-subtle">
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
    };

    if (editing.id) {
      await patch(`/tax-returns/${taxReturnId}/shareholders/${editing.id}/`, payload);
    } else {
      await post(`/tax-returns/${taxReturnId}/shareholders/`, payload);
    }
    await onRefresh();
    setEditing(null);
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
    "w-full rounded-md border border-input-border bg-input px-3 py-2 text-sm text-tx shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring";

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
                  const res = await post(`/tax-returns/${taxReturnId}/render-k1s/`, {});
                  if (res.ok) {
                    const blob = new Blob([Uint8Array.from(atob((res.data as any).pdf || ""), c => c.charCodeAt(0))], { type: "application/pdf" });
                    window.open(URL.createObjectURL(blob), "_blank");
                  } else {
                    // Try IPC bridge for Electron
                    if (window.api?.renderK1s) {
                      const r = await window.api.renderK1s(taxReturnId);
                      if (r?.pdfBase64) {
                        const blob = new Blob([Uint8Array.from(atob(r.pdfBase64), c => c.charCodeAt(0))], { type: "application/pdf" });
                        window.open(URL.createObjectURL(blob), "_blank");
                      } else {
                        alert(r?.error || "Failed to generate K-1s.");
                      }
                    }
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
          <table className="w-full text-sm">
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
            <tbody className="divide-y divide-border-subtle">
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
                          if (window.api?.renderK1) {
                            const r = await window.api.renderK1(taxReturnId, s.id);
                            if (r?.pdfBase64) {
                              const blob = new Blob([Uint8Array.from(atob(r.pdfBase64), c => c.charCodeAt(0))], { type: "application/pdf" });
                              window.open(URL.createObjectURL(blob), "_blank");
                            } else alert(r?.error || "Failed to generate K-1.");
                          }
                        }}
                        className="text-xs font-medium text-primary-text hover:underline"
                      >
                        K-1
                      </button>
                      {parseFloat(s.health_insurance_premium || "0") > 0 && (
                        <button
                          onClick={async () => {
                            if (window.api?.render7206) {
                              const r = await window.api.render7206(taxReturnId, s.id);
                              if (r?.pdfBase64) {
                                const blob = new Blob([Uint8Array.from(atob(r.pdfBase64), c => c.charCodeAt(0))], { type: "application/pdf" });
                                window.open(URL.createObjectURL(blob), "_blank");
                              } else alert(r?.error || "Failed to generate Form 7206.");
                            }
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
          <div className="mt-3 flex gap-2">
            <button onClick={saveShareholder} disabled={saving} className="rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-primary-hover disabled:opacity-50">
              {saving ? "Saving..." : "Save"}
            </button>
            <button onClick={() => setEditing(null)} className="rounded-lg bg-surface-alt px-3 py-1.5 text-xs font-semibold text-tx shadow-sm transition hover:bg-border">
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
    await post(`/tax-returns/${taxReturnId}/rental-properties/`, {
      description: "",
      property_type: "6",
      rents_received: "0",
    });
    await onRefresh();
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
    "w-full rounded-md border border-input-border bg-input px-3 py-2 text-sm text-tx shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring";

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
        <div className="divide-y divide-border-subtle">
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
  fieldsBySection,
  onChange,
}: {
  fieldsBySection: Record<string, FieldValue[]>;
  onChange: (formLineId: string, value: string) => void;
}) {
  const schedLFields = fieldsBySection["sched_l"] || [];
  const m1Fields = fieldsBySection["sched_m1"] || [];
  const m2Fields = fieldsBySection["sched_m2"] || [];

  return (
    <div className="space-y-6">
      <ScheduleLSection fields={schedLFields} onChange={onChange} />
      {m1Fields.length > 0 && (
        <div className="rounded-xl border border-border bg-card shadow-sm">
          <div className="px-4 py-2.5 text-xs font-bold uppercase tracking-wider text-tx-secondary bg-surface-alt border-b border-border">
            Schedule M-1 — Reconciliation of Income (Loss)
          </div>
          <div className="divide-y divide-border-subtle">
            {m1Fields.map((fv) => (
              <FieldRow key={fv.id} field={fv} onChange={onChange} />
            ))}
          </div>
        </div>
      )}
      {m2Fields.length > 0 && (
        <div className="rounded-xl border border-border bg-card shadow-sm">
          <div className="px-4 py-2.5 text-xs font-bold uppercase tracking-wider text-tx-secondary bg-surface-alt border-b border-border">
            Schedule M-2 — Analysis of AAA, OAA, and STPI
          </div>
          <div className="divide-y divide-border-subtle">
            {m2Fields.map((fv) => (
              <FieldRow key={fv.id} field={fv} onChange={onChange} />
            ))}
          </div>
        </div>
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
    <div className="rounded-xl border border-border bg-card shadow-sm">
      {sections.map((secCode, idx) => {
        const fields = fieldsBySection[secCode] || [];
        if (fields.length === 0) return null;
        return (
          <div key={secCode}>
            {/* Section divider for multi-section tabs */}
            {sections.length > 1 && (
              <div
                className={`px-4 py-2 text-xs font-bold uppercase tracking-wider text-tx-secondary bg-surface-alt ${
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
              <div className="flex items-center gap-4 border-b border-border bg-surface-alt px-4 py-2.5">
                <div className="w-14 shrink-0 text-xs font-semibold uppercase tracking-wider text-tx-secondary">
                  Line
                </div>
                <div className="flex-1 text-xs font-semibold uppercase tracking-wider text-tx-secondary">
                  Description
                </div>
                <div className="w-48 shrink-0 text-right text-xs font-semibold uppercase tracking-wider text-tx-secondary">
                  Amount
                </div>
              </div>
            )}
            <div className="divide-y divide-border-subtle">
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
    <div className="rounded-xl border border-border bg-card shadow-sm">
      {/* Column headers */}
      <div className="flex items-center gap-4 border-b border-border bg-surface-alt px-4 py-2.5">
        <div className="w-10 shrink-0 text-xs font-semibold uppercase tracking-wider text-tx-secondary">
          Line
        </div>
        <div className="flex-1 text-xs font-semibold uppercase tracking-wider text-tx-secondary">
          Description
        </div>
        <div className="w-40 shrink-0 text-right text-xs font-semibold uppercase tracking-wider text-tx-secondary">
          Beginning of Year
        </div>
        <div className="w-40 shrink-0 text-right text-xs font-semibold uppercase tracking-wider text-tx-secondary">
          End of Year
        </div>
      </div>

      <div className="divide-y divide-border-subtle">
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
                <div className="px-4 py-2 text-xs font-bold uppercase tracking-wider text-tx-secondary bg-surface-alt border-t-2 border-border">
                  Liabilities
                </div>
              )}
              {isFirstEquity && (
                <div className="px-4 py-2 text-xs font-bold uppercase tracking-wider text-tx-secondary bg-surface-alt border-t border-border">
                  Equity
                </div>
              )}
              <div
                className={`flex items-center gap-4 px-4 py-3 ${
                  isComputed || isTotalAssets || isTotalLE
                    ? "bg-surface-alt/50 font-medium"
                    : ""
                }`}
              >
                <div className="w-10 shrink-0 text-sm text-tx-secondary">
                  {lineNum}
                </div>
                <div className="flex-1">
                  <span className="text-sm text-tx">{g.label}</span>
                  {isComputed && (
                    <span className="ml-2 text-xs italic text-tx-muted">
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
        field.is_computed ? "bg-surface-alt/50" : ""
      }`}
    >
      {/* Line number */}
      <div className="w-14 shrink-0 text-sm font-medium text-tx-secondary">
        {field.line_number}
      </div>

      {/* Label */}
      <div className="flex-1">
        <span className="text-sm text-tx">{field.label}</span>
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
      className={`w-full rounded-md border border-input-border px-3 py-2 text-sm text-tx shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring ${
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
      className={`w-full rounded-md border border-input-border px-3 py-2 text-right text-sm text-tx tabular-nums shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring ${
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
        className={`w-full rounded-md border border-input-border px-3 py-2 pr-8 text-right text-sm text-tx tabular-nums shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring ${
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
  const checked = value === "true" || value === "1";
  return (
    <label className="flex items-center justify-end gap-2 cursor-pointer">
      <input
        type="checkbox"
        checked={checked}
        disabled={readOnly}
        onChange={(e) => onChange(e.target.checked ? "true" : "false")}
        className="h-4 w-4 rounded border-input-border text-primary focus:ring-primary"
      />
      <span className="text-sm text-tx-secondary">{checked ? "Yes" : "No"}</span>
    </label>
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
