import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, Link, useNavigate, useOutletContext } from "react-router-dom";
import type { AppShellContext } from "../components/AppShell";
import {
  get, patch, post, del, uploadFile,
  renderPdf, renderK1s, renderK1, render7206,
  render1125a, render8825, render7203, render7203s, render7004,
  renderComplete,
  getPageMap,
} from "../lib/api";
import { useFormContext } from "../lib/form-context";
import CurrencyInput from "../components/CurrencyInput";
import PdfViewer from "../components/PdfViewer";

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

interface LineItemDetailRow {
  id: string;
  line_number: string;
  description: string;
  amount: string;
  amount_boy: string;
  amount_eoy: string;
  sort_order: number;
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

interface DispositionRow {
  id: string;
  description: string;
  date_acquired: string | null;
  date_acquired_various: boolean;
  date_sold: string | null;
  date_sold_various: boolean;
  sales_price: string;
  cost_basis: string;
  amt_cost_basis: string | null;
  state_cost_basis: string | null;
  state_amt_cost_basis: string | null;
  expenses_of_sale: string;
  term: "short" | "long";
  nontaxable_federal: boolean;
  nontaxable_state: boolean;
  related_party_loss: boolean;
  securities_trader: boolean;
  is_4797: boolean;
  inherited_property: boolean;
  net_investment_income_tax: string;
  gain_loss: string;
  sort_order: number;
}

interface DepreciationAssetRow {
  id: string;
  asset_number: number;
  description: string;
  group_label: string;
  property_label: string;
  date_acquired: string;
  date_sold: string | null;
  cost_basis: string;
  business_pct: string;
  method: string;
  convention: string;
  life: string | null;
  sec_179_elected: string;
  sec_179_prior: string;
  bonus_pct: string;
  bonus_amount: string;
  prior_depreciation: string;
  current_depreciation: string;
  amt_method: string;
  amt_life: string | null;
  amt_prior_depreciation: string;
  amt_current_depreciation: string;
  state_method: string;
  state_life: string | null;
  state_prior_depreciation: string;
  state_current_depreciation: string;
  state_bonus_disallowed: string;
  flow_to: string;
  rental_property: string | null;
  is_listed_property: boolean;
  vehicle_miles_total: number | null;
  vehicle_miles_business: number | null;
  is_amortization: boolean;
  amort_code: string;
  amort_months: number | null;
  sales_price: string | null;
  expenses_of_sale: string | null;
  depreciation_recapture: string | null;
  capital_gain: string | null;
  gain_loss_on_sale: string | null;
  amt_gain_loss_on_sale: string | null;
  amt_depreciation_recapture: string | null;
  amt_capital_gain: string | null;
  imported_from_lacerte: boolean;
  lacerte_asset_no: number | null;
  sort_order: number;
  method_display: string;
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
  dispositions: DispositionRow[];
  depreciation_assets: DepreciationAssetRow[];
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
  // Admin — Invoice
  ["INV_TOTAL", (v) => sumLines(v, "INV_PREP_FEE","INV_FEE_2","INV_FEE_3")],
  // Schedule A — Cost of Goods Sold
  ["A6", (v) => sumLines(v, "A1","A2","A3","A4","A5")],
  ["A8", (v) => val(v, "A6") - val(v, "A7")],
  // Page 1 — Income  (Line 2 = Schedule A line 8)
  ["2", (v) => val(v, "A8")],
  ["1c", (v) => val(v, "1a") - val(v, "1b")],
  ["3", (v) => val(v, "1c") - val(v, "2")],
  ["6", (v) => val(v, "3") + val(v, "4") + val(v, "5")],
  // Meals — deductible portions
  ["D_MEALS_DED", (v) => val(v, "D_MEALS_50") * 0.50 + val(v, "D_MEALS_DOT") * 0.80],
  ["D_MEALS_NONDED", (v) => val(v, "D_MEALS_50") * 0.50 + val(v, "D_MEALS_DOT") * 0.20 + val(v, "D_ENTERTAINMENT")],
  // Page 1 — Deductions
  ["19", (v) => sumLines(v,
    "D_ACCT","D_ANSW","D_AUTO","D_BANK","D_COMM","D_DELI",
    "D_DUES","D_GIFT","D_INSU","D_JANI","D_LAUN","D_LICE","D_LEGA",
    "D_MEALS_DED","D_MISC","D_OFFI","D_ORGN","D_OUTS","D_PARK",
    "D_POST","D_PRNT","D_SECU","D_SUPP","D_TELE","D_TOOL",
    "D_TRAV","D_UNIF","D_UTIL","D_WAST",
    "D_FREE1","D_FREE2","D_FREE3","D_FREE4","D_FREE5","D_FREE6",
  )],
  ["20", (v) => sumLines(v, "7","8","9","10","11","12","13","14","15","16","17","18","19")],
  ["21", (v) => val(v, "6") - val(v, "20")],
  // Page 1 — Tax and Payments
  ["22c", (v) => val(v, "22a") + val(v, "22b")],
  ["23d", (v) => val(v, "23a") + val(v, "23b") + val(v, "23c")],
  ["25", (v) => Math.max(0, val(v, "22c") - val(v, "23d"))],
  ["26", (v) => Math.max(0, val(v, "23d") - val(v, "22c"))],
  // Schedule K — nondeductible expenses
  ["K16c", (v) => val(v, "D_MEALS_NONDED")],
  // Schedule L — Balance Sheet (inventory flows from COGS)
  ["L3a", (v) => val(v, "A1")],
  ["L3d", (v) => val(v, "A7")],
  ["L15a", (v) => sumLines(v, "L1a","L3a","L4a","L5a","L6a","L7a","L8a","L9a","L12a","L14a")
    + val(v, "L2a") - val(v, "L2b")
    + val(v, "L10a") - val(v, "L10b")
    + val(v, "L11a") - val(v, "L11b")
    + val(v, "L13a") - val(v, "L13b")],
  ["L15d", (v) => sumLines(v, "L1d","L3d","L4d","L5d","L6d","L7d","L8d","L9d","L12d","L14d")
    + val(v, "L2d") - val(v, "L2e")
    + val(v, "L10d") - val(v, "L10e")
    + val(v, "L11d") - val(v, "L11e")
    + val(v, "L13d") - val(v, "L13e")],
  // Schedule M-1
  ["M1_3b", (v) => val(v, "D_MEALS_NONDED")],
  ["M1_4", (v) => sumLines(v, "M1_1","M1_2","M1_3a","M1_3b","M1_3c")],
  ["M1_7", (v) => sumLines(v, "M1_5a","M1_5b","M1_6a","M1_6b")],
  ["M1_8", (v) => val(v, "M1_4") - val(v, "M1_7")],
  // Schedule M-2 — 4 columns: (a) AAA, (b) OAA, (c) STPI, (d) Accu E&P
  // Column (a) AAA
  ["M2_2a", (v) => Math.max(0, val(v, "21"))],
  ["M2_4a", (v) => Math.max(0, -val(v, "21"))],
  ["M2_5a", (v) => sumLines(v, "K12a","K11","K16c")],
  ["M2_6a", (v) => val(v, "M2_1a") + val(v, "M2_2a") + val(v, "M2_3a") - val(v, "M2_4a") - val(v, "M2_5a")],
  ["M2_7a", (v) => val(v, "K16d")],
  ["M2_8a", (v) => val(v, "M2_6a") - val(v, "M2_7a")],
  // Column (b) OAA
  ["M2_6b", (v) => val(v, "M2_1b") + val(v, "M2_2b") + val(v, "M2_3b") - val(v, "M2_4b") - val(v, "M2_5b")],
  ["M2_8b", (v) => val(v, "M2_6b") - val(v, "M2_7b")],
  // Column (c) STPI
  ["M2_6c", (v) => val(v, "M2_1c") + val(v, "M2_2c") + val(v, "M2_3c") - val(v, "M2_4c") - val(v, "M2_5c")],
  ["M2_8c", (v) => val(v, "M2_6c") - val(v, "M2_7c")],
  // Column (d) Accu E&P
  ["M2_6d", (v) => val(v, "M2_1d") + val(v, "M2_2d") + val(v, "M2_3d") - val(v, "M2_4d") - val(v, "M2_5d")],
  ["M2_8d", (v) => val(v, "M2_6d") - val(v, "M2_7d")],
  // Schedule L — Retained earnings & total (depend on M-2)
  ["L24a", (v) => sumLines(v, "M2_1a","M2_1b","M2_1c","M2_1d")],
  ["L24d", (v) => sumLines(v, "M2_8a","M2_8b","M2_8c","M2_8d")],
  ["L27a", (v) => sumLines(v, "L16a","L17a","L18a","L19a","L20a","L21a","L22a","L23a","L24a","L25a") - val(v, "L26a")],
  ["L27d", (v) => sumLines(v, "L16d","L17d","L18d","L19d","L20d","L21d","L22d","L23d","L24d","L25d") - val(v, "L26d")],
  // Schedule F — Farm Income
  ["F1c", (v) => val(v, "F1a") - val(v, "F1b")],
  ["F9", (v) => sumLines(v, "F1c","F2","F3","F4","F5","F6","F7","F8")],
  ["F33", (v) => sumLines(v, "F10","F11","F12","F13","F14","F15","F16","F17","F18","F19","F20","F21a","F21b","F22","F23","F24a","F24b","F25","F26","F27","F28","F29","F30","F31","F32")],
  ["F34", (v) => val(v, "F9") - val(v, "F33")],
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
  // Income tax only applies when PTET is elected; most S-Corps owe $0
  ["S1_7", (v) => val(v, "GA_PTET") > 0 ? Math.max(0, val(v, "S1_6")) * 0.0539 : 0],
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
    computedValues[lineNum] = Math.round(result).toString();
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
  { id: "info", label: "Client Info", sections: [] },
  { id: "admin", label: "Admin", sections: ["admin"] },
  { id: "shareholders", label: "Shareholders", sections: [] },
  { id: "page1", label: "Income & Ded.", sections: ["page1_income", "sched_a", "page1_deductions"] },
  { id: "sched_k", label: "Sched K", sections: ["sched_k"] },
  { id: "balance_sheets", label: "Balance Sheet", sections: ["sched_l", "sched_m1", "sched_m2"] },
  { id: "sched_b", label: "Sched B", sections: ["sched_b"] },
  { id: "basis_7203", label: "Form 7203", sections: [] },
  { id: "rental", label: "Rental (8825)", sections: [] },
  { id: "dispositions", label: "Dispositions", sections: [] },
  { id: "depreciation", label: "Depreciation", sections: [] },
  { id: "schedule_f", label: "Schedule F", sections: ["sched_f"] },
  { id: "tax_payments", label: "Extensions", sections: ["page1_tax"] },
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
  const navigate = useNavigate();
  const { setEditorBreadcrumb } = useOutletContext<AppShellContext>();

  const [returnData, setReturnData] = useState<TaxReturnData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("info");
  const [primaryTab, setPrimaryTab] = useState<"input" | "forms" | "diagnostics">("input");

  // Push breadcrumb into the AppShell toolbar
  useEffect(() => {
    if (!returnData) {
      setEditorBreadcrumb(null);
      return;
    }
    setEditorBreadcrumb(
      <div className="flex items-center text-sm">
        <Link to="/" className="text-tx-on-dark/70 hover:text-white hover:underline">
          Return Manager
        </Link>
        <span className="mx-1.5 text-tx-on-dark/40">/</span>
        <span className="text-tx-on-dark/90">{returnData.client_name}</span>
        <span className="mx-1.5 text-tx-on-dark/40">/</span>
        <span className="text-tx-on-dark/90">{returnData.entity_name}</span>
        <span className="mx-1.5 text-tx-on-dark/40">/</span>
        {returnData.federal_return_id ? (
          <>
            <Link
              to={`/tax-returns/${returnData.federal_return_id}/editor`}
              className="text-tx-on-dark/70 hover:text-white hover:underline"
            >
              Federal Return
            </Link>
            <span className="mx-1.5 text-blue-300/60">/</span>
          </>
        ) : null}
        <span className="font-semibold text-white">
          {returnData.form_code} &mdash; {returnData.year}
        </span>
        <ReturnStatusPill status={returnData.status} />
        <SaveStatusIndicator status={saveStatus} />
      </div>,
    );
    return () => setEditorBreadcrumb(null);
  }, [returnData, setEditorBreadcrumb]);

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

  // State returns are hidden from the Return Manager list, so users
  // access them only via the federal return's State tab.  No redirect
  // needed — let the editor load GA_SECTION_TABS normally.

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
      {/* Compact utility bar — Import TB moves here (status + save are in toolbar breadcrumb) */}
      {importResult && (
        <div className="mb-2 text-sm font-medium text-success">{importResult}</div>
      )}

      {/* Primary tab bar — Input / Forms / Diagnostics */}
      <div className="sticky top-0 z-10 bg-surface -mx-4 px-4 mb-2 flex items-center gap-0 border-b-2 border-border">
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
          <div className="sticky top-[42px] z-10 bg-surface -mx-4 px-4 mb-2 flex items-center gap-1 border-b border-border overflow-x-auto scrollbar-hide">
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
            {!isStateReturn && (
              <button
                onClick={handleImportTB}
                disabled={importing}
                className="ml-auto shrink-0 whitespace-nowrap rounded px-2 py-1 text-xs font-medium text-success hover:bg-success/10 disabled:opacity-50"
              >
                {importing ? "Importing..." : "Import TB"}
              </button>
            )}
          </div>

          {/* Active section content */}
          {activeTab === "info" ? (
            <InfoSection returnData={returnData} onRefresh={refreshReturn} />
          ) : activeTab === "admin" ? (
            <AdminSection
              fieldsBySection={fieldsBySection}
              onChange={handleFieldChange}
            />
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
              onChange={handleFieldChange}
              onRefresh={refreshReturn}
              priorYear={priorYear}
            />
          ) : activeTab === "basis_7203" ? (
            <Form7203Section
              taxReturnId={taxReturnId!}
              shareholders={returnData.shareholders || []}
              fieldValues={returnData.field_values || []}
              onRefresh={refreshReturn}
            />
          ) : activeTab === "rental" ? (
            <RentalPropertiesSection
              taxReturnId={taxReturnId!}
              properties={returnData.rental_properties || []}
              onRefresh={refreshReturn}
            />
          ) : activeTab === "dispositions" ? (
            <DispositionsSection
              taxReturnId={taxReturnId!}
              dispositions={returnData.dispositions || []}
              onRefresh={refreshReturn}
            />
          ) : activeTab === "depreciation" ? (
            <DepreciationSection
              taxReturnId={taxReturnId!}
              assets={returnData.depreciation_assets || []}
              rentalProperties={returnData.rental_properties || []}
              onRefresh={refreshReturn}
            />
          ) : activeTab === "schedule_f" ? (
            <ScheduleFSection
              fieldsBySection={fieldsBySection}
              onChange={handleFieldChange}
              pyLookup={pyLookup}
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
              onRefresh={refreshReturn}
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

  // Autosave entity (debounced)
  const entityTimerRef = useRef<number | null>(null);
  useEffect(() => {
    if (!entity || loadingEntity) return;
    if (entityTimerRef.current) clearTimeout(entityTimerRef.current);
    entityTimerRef.current = window.setTimeout(() => { saveEntity(); }, 800);
    return () => { if (entityTimerRef.current) clearTimeout(entityTimerRef.current); };
  }, [entity]);

  // Autosave return info (debounced)
  const returnTimerRef = useRef<number | null>(null);
  useEffect(() => {
    if (loadingEntity) return; // don't fire on initial load
    if (returnTimerRef.current) clearTimeout(returnTimerRef.current);
    returnTimerRef.current = window.setTimeout(() => { saveReturnInfo(); }, 800);
    return () => { if (returnTimerRef.current) clearTimeout(returnTimerRef.current); };
  }, [accountingMethod, taxYearStart, taxYearEnd, isInitialReturn, isFinalReturn,
      isNameChange, isAddressChange, isAmendedReturn, sElectionDate,
      numberOfShareholders, productOrService, businessActivityCode,
      selectedPreparer, staffPreparerId, signatureDate]);

  // Officer inline edit (debounced save on blur)
  async function updateOfficerField(officerId: string, field: string, value: string) {
    await patch(`/tax-returns/${returnData.id}/officers/${officerId}/`, { [field]: value });
    await onRefresh();
  }

  function handleOfficerLocalChange(officerId: string, field: string, value: string) {
    setOfficers((prev) => prev.map((o) => (o.id === officerId ? { ...o, [field]: value } : o)));
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
                    <td className="py-1 pr-2"><input type="text" value={o.name} onChange={(e) => handleOfficerLocalChange(o.id, "name", e.target.value)} onBlur={(e) => updateOfficerField(o.id, "name", e.target.value)} className={inputClass} /></td>
                    <td className="py-1 pr-2"><input type="text" value={o.title} onChange={(e) => handleOfficerLocalChange(o.id, "title", e.target.value)} onBlur={(e) => updateOfficerField(o.id, "title", e.target.value)} className={inputClass} /></td>
                    <td className="py-1 pr-2"><input type="text" value={o.ssn} onChange={(e) => handleOfficerLocalChange(o.id, "ssn", formatSSN(e.target.value))} onBlur={(e) => updateOfficerField(o.id, "ssn", e.target.value)} className={inputClass} placeholder="XXX-XX-XXXX" /></td>
                    <td className="py-1 pr-2"><input type="text" value={o.percent_time} onChange={(e) => handleOfficerLocalChange(o.id, "percent_time", e.target.value)} onBlur={(e) => updateOfficerField(o.id, "percent_time", e.target.value || "0")} className={`${inputClass} text-right`} /></td>
                    <td className="py-1 pr-2"><input type="text" value={o.percent_ownership} onChange={(e) => handleOfficerLocalChange(o.id, "percent_ownership", e.target.value)} onBlur={(e) => updateOfficerField(o.id, "percent_ownership", e.target.value || "0")} className={`${inputClass} text-right`} /></td>
                    <td className="py-1 pr-2"><input type="text" value={o.compensation} onChange={(e) => handleOfficerLocalChange(o.id, "compensation", e.target.value)} onBlur={(e) => updateOfficerField(o.id, "compensation", e.target.value || "0")} className={`${inputClass} text-right`} /></td>
                    <td className="py-1">
                      <button onClick={() => deleteOfficer(o.id)} className="text-xs font-medium text-danger hover:text-danger-hover hover:underline">Delete</button>
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
const DEDUCTION_SUMMARY_LINES = ["19", "20", "21"];
const FREE_FORM_DEDUCTION_PAIRS = ["D_FREE1", "D_FREE2", "D_FREE3", "D_FREE4", "D_FREE5", "D_FREE6"];
const MEALS_FIELDS = ["D_MEALS_50", "D_MEALS_DOT", "D_ENTERTAINMENT", "D_MEALS_DED", "D_MEALS_NONDED"];
/** Tax & Payments section shown at the bottom. */
const TAX_SECTION_CODE = "page1_tax";

function IncomeDeductionsSection({
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
  // --- Separate fields by role ---
  const incomeFields = fieldsBySection["page1_income"] || [];
  const cogsFields = fieldsBySection["sched_a"] || [];
  const deductionFields = fieldsBySection["page1_deductions"] || [];
  const taxFields = fieldsBySection[TAX_SECTION_CODE] || [];

  const summaryLines = deductionFields.filter(
    (f) => DEDUCTION_SUMMARY_LINES.includes(f.line_number)
  );

  const pyLines = priorYear?.line_values ?? {};
  const hasPY = priorYear !== null;

  // Separate deduction fields into: named (label + amount), meals group, free-form pairs, summary
  const { namedDeductions, mealsGroup, freeFormPairs } = useMemo(() => {
    const named: FieldValue[] = [];
    const meals: FieldValue[] = [];
    const freeDescs = new Map<string, FieldValue>();  // e.g. D_FREE1_DESC -> field
    const freeAmts = new Map<string, FieldValue>();   // e.g. D_FREE1 -> field
    for (const f of deductionFields) {
      if (DEDUCTION_SUMMARY_LINES.includes(f.line_number)) continue;
      if (f.line_number.endsWith("_DESC")) {
        freeDescs.set(f.line_number.replace("_DESC", ""), f);
      } else if (FREE_FORM_DEDUCTION_PAIRS.includes(f.line_number)) {
        freeAmts.set(f.line_number, f);
      } else if (MEALS_FIELDS.includes(f.line_number)) {
        meals.push(f);
      } else {
        named.push(f);
      }
    }
    named.sort((a, b) => a.label.localeCompare(b.label, "en", { sensitivity: "base" }));
    // Sort meals in seed order: 50%, DOT 80%, Entertainment
    meals.sort((a, b) => MEALS_FIELDS.indexOf(a.line_number) - MEALS_FIELDS.indexOf(b.line_number));
    const pairs = FREE_FORM_DEDUCTION_PAIRS.map((ln) => ({
      desc: freeDescs.get(ln),
      amt: freeAmts.get(ln),
    })).filter((p) => p.desc && p.amt) as { desc: FieldValue; amt: FieldValue }[];
    return { namedDeductions: named, mealsGroup: meals, freeFormPairs: pairs };
  }, [deductionFields]);

  // Balance columns: left gets enough named to match right (remaining named + free-form)
  const rightNamedCount = namedDeductions.length - Math.ceil((namedDeductions.length + freeFormPairs.length) / 2);
  const leftCount = namedDeductions.length - rightNamedCount;
  const leftDeductions = namedDeductions.slice(0, leftCount);
  const rightDeductions = namedDeductions.slice(leftCount);

  return (
    <div className="space-y-4">
      {/* ===== INCOME (left) + COGS (right) side by side ===== */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-border bg-card shadow-sm">
          <div className="px-4 py-1.5 text-xs font-bold uppercase tracking-wider text-tx-secondary bg-surface-alt rounded-t-xl">
            Income
          </div>
          <div className="divide-y divide-border-subtle">
            {incomeFields.map((fv) => (
              <FieldRow key={fv.id} field={fv} onChange={onChange} pyValue={pyLines[fv.line_number]} showPY={hasPY} />
            ))}
          </div>
        </div>

        {cogsFields.length > 0 && (
          <div className="rounded-xl border border-border bg-card shadow-sm">
            <div className="px-4 py-1.5 text-xs font-bold uppercase tracking-wider text-tx-secondary bg-surface-alt rounded-t-xl">
              Cost of Goods Sold
            </div>
            <div className="divide-y divide-border-subtle">
              {cogsFields.map((fv) => {
                if (fv.line_number === "A9a") {
                  return (
                    <div key={fv.id} className="flex items-center gap-4 px-4 py-1.5">
                      <div className="w-14 shrink-0 text-xs font-medium text-tx-secondary">{fv.line_number}</div>
                      <div className="flex-1"><span className="text-xs text-tx">{fv.label}</span></div>
                      <div className="w-36 shrink-0">
                        <select
                          value={fv.value || ""}
                          onChange={(e) => onChange(fv.form_line, e.target.value)}
                          className="w-full rounded-md border border-input-border bg-input px-2 py-1 text-xs text-tx shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring"
                        >
                          <option value="">Select...</option>
                          <option value="Cost">Cost</option>
                          <option value="Lower of cost or market">Lower of cost or market</option>
                        </select>
                      </div>
                    </div>
                  );
                }
                return <FieldRow key={fv.id} field={fv} onChange={onChange} pyValue={pyLines[fv.line_number]} showPY={hasPY} />;
              })}
            </div>
          </div>
        )}
      </div>

      {/* ===== DEDUCTIONS — flat 2-column grid, alphabetical ===== */}
      <div className="rounded-xl border border-border bg-card shadow-sm">
        <div className="px-4 py-1.5 text-xs font-bold uppercase tracking-wider text-tx-secondary bg-surface-alt rounded-t-xl">
          Deductions
        </div>
        <div className="grid grid-cols-1 gap-0 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-border-subtle">
          {/* Left column: named deductions A–O */}
          <div className="divide-y divide-border-subtle">
            {leftDeductions.map((field) => (
              <div key={field.id} className="flex items-center gap-2 px-3 py-1">
                <div className="flex-1 min-w-0">
                  <span className="text-xs text-tx truncate">{field.label}</span>
                </div>
                <div className="w-28 shrink-0">
                  <FieldInput field={field} onChange={onChange} />
                </div>
              </div>
            ))}
          </div>
          {/* Right column: named deductions O–W + 6 free-form rows */}
          <div className="divide-y divide-border-subtle">
            {rightDeductions.map((field) => (
              <div key={field.id} className="flex items-center gap-2 px-3 py-1">
                <div className="flex-1 min-w-0">
                  <span className="text-xs text-tx truncate">{field.label}</span>
                </div>
                <div className="w-28 shrink-0">
                  <FieldInput field={field} onChange={onChange} />
                </div>
              </div>
            ))}
            {freeFormPairs.map(({ desc, amt }) => (
              <div key={amt.id} className="flex items-center gap-2 px-3 py-1">
                <div className="flex-1 min-w-0">
                  <TextInput
                    value={desc.value || ""}
                    onChange={(v) => onChange(desc.form_line, v)}
                    placeholder="Description"
                  />
                </div>
                <div className="w-28 shrink-0">
                  <CurrencyInput
                    value={amt.value}
                    onValueChange={(v) => onChange(amt.form_line, v)}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Meals & Entertainment grouped sub-section */}
        {mealsGroup.length > 0 && (
          <div className="border-t border-border">
            <div className="px-4 py-1 text-xs font-bold uppercase tracking-wider text-tx-secondary bg-surface-alt/50">
              Meals &amp; Entertainment
            </div>
            <div className="divide-y divide-border-subtle">
              {mealsGroup.map((field) => (
                <div key={field.id} className="flex items-center gap-2 px-3 py-1">
                  <div className="flex-1 min-w-0">
                    <span className="text-xs text-tx truncate">{field.label}</span>
                  </div>
                  <div className="w-28 shrink-0">
                    <FieldInput field={field} onChange={onChange} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Summary lines: Other Deductions, Total Deductions, Ordinary Business Income */}
        <div className="border-t border-border divide-y divide-border-subtle bg-surface-alt/30">
          {summaryLines.map((fv) => (
            <FieldRow key={fv.id} field={fv} onChange={onChange} pyValue={pyLines[fv.line_number]} showPY={hasPY} />
          ))}
        </div>
      </div>

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
  const [adding, setAdding] = useState(false);
  const [alsoCreateOfficer, setAlsoCreateOfficer] = useState(false);

  function formatSSN(raw: string): string {
    const digits = raw.replace(/\D/g, "").slice(0, 9);
    if (digits.length > 5) return digits.slice(0, 3) + "-" + digits.slice(3, 5) + "-" + digits.slice(5);
    if (digits.length > 3) return digits.slice(0, 3) + "-" + digits.slice(3);
    return digits;
  }

  async function addShareholder() {
    setAdding(true);
    const res = await post(`/tax-returns/${taxReturnId}/shareholders/`, {
      name: "", ssn: "", address_line1: "", city: "", state: "", zip_code: "",
      ownership_percentage: "0", beginning_shares: "0", ending_shares: "0",
      distributions: "0", health_insurance_premium: "0",
    });
    if (res.ok) {
      if (alsoCreateOfficer) {
        await post(`/tax-returns/${taxReturnId}/officers/`, {
          name: "", ssn: "", percent_ownership: "0", title: "", compensation: "0",
        });
      }
      await onRefresh();
    }
    setAdding(false);
    setAlsoCreateOfficer(false);
  }

  async function updateField(shId: string, field: string, value: string) {
    await patch(`/tax-returns/${taxReturnId}/shareholders/${shId}/`, { [field]: value });
    await onRefresh();
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
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-bold text-tx">Shareholders</h3>
          <p className="text-xs text-tx-muted">
            K-1 forms will be generated for each shareholder based on ownership percentage.
            {shareholders.length > 0 && (
              <span className={`ml-2 font-medium ${Math.abs(totalOwnership - 100) < 0.01 ? "text-success" : "text-amber-600"}`}>
                Total: {totalOwnership.toFixed(2)}%
              </span>
            )}
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
            onClick={addShareholder}
            disabled={adding}
            className="rounded-lg bg-success px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-success-hover disabled:opacity-50"
          >
            Add Shareholder
          </button>
        </div>
      </div>

      {shareholders.length === 0 && (
        <div className="rounded-xl border border-border bg-card px-4 py-8 text-center text-sm text-tx-muted">
          No shareholders added yet. Add shareholders to enable K-1 generation.
        </div>
      )}

      {shareholders.map((s) => (
        <div key={s.id} className="rounded-xl border border-border bg-card shadow-sm">
          <div className="flex items-center justify-between border-b border-border bg-surface-alt px-4 py-2 rounded-t-xl">
            <span className="text-xs font-bold text-tx">{s.name || "(New Shareholder)"}</span>
            <div className="flex items-center gap-2">
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
                className="text-xs font-medium text-danger hover:underline"
              >
                Delete
              </button>
            </div>
          </div>
          <div className="px-4 py-3 space-y-3">
            {/* Row 1: Name, SSN, Ownership */}
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              <div className="col-span-2">
                <label className="mb-0.5 block text-[10px] font-medium text-tx-muted">Name</label>
                <input type="text" defaultValue={s.name} onBlur={(e) => updateField(s.id, "name", e.target.value)} className={inputClass + " text-xs"} />
              </div>
              <div>
                <label className="mb-0.5 block text-[10px] font-medium text-tx-muted">SSN</label>
                <input type="text" defaultValue={s.ssn} onBlur={(e) => updateField(s.id, "ssn", e.target.value)}
                  onChange={(e) => { e.target.value = formatSSN(e.target.value); }}
                  className={inputClass + " text-xs"} placeholder="XXX-XX-XXXX" />
              </div>
              <div>
                <label className="mb-0.5 block text-[10px] font-medium text-tx-muted">Ownership %</label>
                <input type="text" defaultValue={s.ownership_percentage} onBlur={(e) => updateField(s.id, "ownership_percentage", e.target.value)} className={inputClass + " text-xs"} />
              </div>
            </div>
            {/* Row 2: Address */}
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              <div className="col-span-2">
                <label className="mb-0.5 block text-[10px] font-medium text-tx-muted">Address</label>
                <input type="text" defaultValue={s.address_line1} onBlur={(e) => updateField(s.id, "address_line1", e.target.value)} className={inputClass + " text-xs"} />
              </div>
              <div>
                <label className="mb-0.5 block text-[10px] font-medium text-tx-muted">City</label>
                <input type="text" defaultValue={s.city} onBlur={(e) => updateField(s.id, "city", e.target.value)} className={inputClass + " text-xs"} />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="mb-0.5 block text-[10px] font-medium text-tx-muted">State</label>
                  <input type="text" defaultValue={s.state} onBlur={(e) => updateField(s.id, "state", e.target.value)} className={inputClass + " text-xs"} maxLength={2} />
                </div>
                <div>
                  <label className="mb-0.5 block text-[10px] font-medium text-tx-muted">ZIP</label>
                  <input type="text" defaultValue={s.zip_code} onBlur={(e) => updateField(s.id, "zip_code", e.target.value)} className={inputClass + " text-xs"} />
                </div>
              </div>
            </div>
            {/* Row 3: Shares, Distributions, Health Insurance */}
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
              <div>
                <label className="mb-0.5 block text-[10px] font-medium text-tx-muted">Beginning Shares</label>
                <input type="text" inputMode="numeric" defaultValue={s.beginning_shares}
                  onBlur={(e) => updateField(s.id, "beginning_shares", e.target.value.replace(/[^0-9]/g, ""))}
                  className={inputClass + " text-xs"} />
              </div>
              <div>
                <label className="mb-0.5 block text-[10px] font-medium text-tx-muted">Ending Shares</label>
                <input type="text" inputMode="numeric" defaultValue={s.ending_shares}
                  onBlur={(e) => updateField(s.id, "ending_shares", e.target.value.replace(/[^0-9]/g, ""))}
                  className={inputClass + " text-xs"} />
              </div>
              <div>
                <label className="mb-0.5 block text-[10px] font-medium text-tx-muted">Distributions</label>
                <CurrencyInput value={s.distributions || "0"} onValueChange={(v) => updateField(s.id, "distributions", v)} />
              </div>
              <div>
                <label className="mb-0.5 block text-[10px] font-medium text-tx-muted">Capital Contributed</label>
                <CurrencyInput value={s.capital_contributions || "0"} onValueChange={(v) => updateField(s.id, "capital_contributions", v)} />
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Form 7203 — Shareholder Stock and Debt Basis (separate tab)
// ---------------------------------------------------------------------------

function Form7203Section({
  taxReturnId,
  shareholders,
  fieldValues,
  onRefresh,
}: {
  taxReturnId: string;
  shareholders: ShareholderRow[];
  fieldValues: FieldValue[];
  onRefresh: () => Promise<void>;
}) {
  const [selectedIdx, setSelectedIdx] = useState(0);
  const sh = shareholders[selectedIdx] || null;

  // Build K-value lookup for current year income items (flow to 7203)
  const kValues: Record<string, number> = {};
  for (const fv of fieldValues) {
    const n = parseFloat(fv.value);
    if (!isNaN(n)) kValues[fv.line_number] = n;
  }

  // Save shareholder field on blur
  async function saveSHField(shId: string, field: string, value: string) {
    await patch(`/tax-returns/${taxReturnId}/shareholders/${shId}/`, { [field]: value });
    await onRefresh();
  }

  const inputClass =
    "w-full rounded-md border border-input-border bg-input px-2 py-1 text-sm text-tx shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring";

  if (shareholders.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-card p-8 text-center text-sm text-tx-muted">
        Add shareholders on the Shareholders tab to use Form 7203 basis tracking.
      </div>
    );
  }

  // Compute 7203 values from K-1 items * ownership %
  const pct = sh ? (parseFloat(sh.ownership_percentage) || 0) / 100 : 0;
  const kLine = (k: string) => (kValues[k] ?? 0) * pct;

  const stockBasisBOY = parseFloat(sh?.stock_basis_boy || "0");
  const capitalContributions = parseFloat(sh?.capital_contributions || "0");
  const ordinaryIncome = kLine("K1") > 0 ? kLine("K1") : 0;
  const rentalREIncome = kLine("K2") > 0 ? kLine("K2") : 0;
  const otherRentalIncome = kLine("K3") > 0 ? kLine("K3") : 0;
  const interestIncome = kLine("K4");
  const ordinaryDividends = kLine("K5a");
  const royalties = kLine("K6");
  const netCapitalGains = (kLine("K7") > 0 ? kLine("K7") : 0) + (kLine("K8a") > 0 ? kLine("K8a") : 0);
  const net1231Gain = kLine("K9") > 0 ? kLine("K9") : 0;
  const otherIncome = kLine("K10") > 0 ? kLine("K10") : 0;
  const taxExemptIncome = kLine("K16a") + kLine("K16b");
  const otherBasisIncrease = 0; // placeholder

  const totalIncreases = ordinaryIncome + rentalREIncome + otherRentalIncome +
    interestIncome + ordinaryDividends + royalties + netCapitalGains +
    net1231Gain + otherIncome + taxExemptIncome + otherBasisIncrease;

  const line5 = stockBasisBOY + capitalContributions + totalIncreases;
  const distributions = parseFloat(sh?.distributions || "0");
  const stockAfterDist = Math.max(0, line5 - distributions);

  const nondeductible = kLine("K16c");
  const businessCredits = 0;
  const totalReductions = nondeductible + businessCredits;
  const stockBeforeLoss = Math.max(0, stockAfterDist - totalReductions);

  // Losses that reduce basis
  const ordinaryLoss = kLine("K1") < 0 ? -kLine("K1") : 0;
  const rentalRELoss = kLine("K2") < 0 ? -kLine("K2") : 0;
  const otherRentalLoss = kLine("K3") < 0 ? -kLine("K3") : 0;
  const sec1231Loss = kLine("K9") < 0 ? -kLine("K9") : 0;
  const stCapitalLoss = kLine("K7") < 0 ? -kLine("K7") : 0;
  const ltCapitalLoss = kLine("K8a") < 0 ? -kLine("K8a") : 0;
  const totalLossItems = ordinaryLoss + rentalRELoss + otherRentalLoss + sec1231Loss + stCapitalLoss + ltCapitalLoss;
  const allowableLoss = Math.min(totalLossItems, stockBeforeLoss);
  const stockBasisEOY = Math.max(0, stockBeforeLoss - allowableLoss);

  const fmt = (n: number) => n.toLocaleString("en-US", { style: "currency", currency: "USD" });

  function BasisRow({ label, value, bold }: { label: string; value: number; bold?: boolean }) {
    return (
      <div className={`flex items-center justify-between px-4 py-1 ${bold ? "bg-surface-alt font-semibold" : ""}`}>
        <span className="text-xs text-tx">{label}</span>
        <span className="text-xs tabular-nums text-tx">{fmt(value)}</span>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Shareholder selector */}
      <div className="flex items-center gap-3">
        <label className="text-xs font-medium text-tx-secondary">Shareholder:</label>
        <select
          value={selectedIdx}
          onChange={(e) => setSelectedIdx(Number(e.target.value))}
          className={inputClass + " max-w-xs"}
        >
          {shareholders.map((s, i) => (
            <option key={s.id} value={i}>{s.name} ({s.ownership_percentage}%)</option>
          ))}
        </select>
        <button
          onClick={async () => {
            const r = await render7203(taxReturnId, sh?.id);
            if (r?.pdfBase64) {
              const blob = new Blob([Uint8Array.from(atob(r.pdfBase64), c => c.charCodeAt(0))], { type: "application/pdf" });
              window.open(URL.createObjectURL(blob), "_blank");
            } else alert(r?.error || "Failed to generate Form 7203.");
          }}
          className="rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-primary-hover"
        >
          Print 7203
        </button>
      </div>

      {sh && (
        <div className="space-y-4">
          {/* Stock Basis Calculation (vertical, full width) */}
          <div className="rounded-xl border border-border bg-card shadow-sm max-w-2xl">
            <div className="px-4 py-2 text-xs font-bold uppercase tracking-wider text-tx-secondary bg-surface-alt rounded-t-xl border-b border-border">
              Part I — Stock Basis Calculation
            </div>
            <div className="divide-y divide-border-subtle">
              <div className="flex items-center justify-between px-4 py-1.5">
                <span className="text-xs text-tx">1. Stock Basis BOY</span>
                <div className="w-36">
                  <CurrencyInput value={sh.stock_basis_boy || "0"} onValueChange={(v) => saveSHField(sh.id, "stock_basis_boy", v)} />
                </div>
              </div>
              <div className="flex items-center justify-between px-4 py-1.5">
                <span className="text-xs text-tx">2. Capital Contributions</span>
                <div className="w-36">
                  <CurrencyInput value={sh.capital_contributions || "0"} onValueChange={(v) => saveSHField(sh.id, "capital_contributions", v)} />
                </div>
              </div>
              <BasisRow label="3a. Ordinary Income" value={ordinaryIncome} />
              <BasisRow label="3b. Net Rental RE Income" value={rentalREIncome} />
              <BasisRow label="3c. Other Net Rental Income" value={otherRentalIncome} />
              <BasisRow label="3d. Interest Income" value={interestIncome} />
              <BasisRow label="3e. Ordinary Dividends" value={ordinaryDividends} />
              <BasisRow label="3f. Royalties" value={royalties} />
              <BasisRow label="3g. Net Capital Gains" value={netCapitalGains} />
              <BasisRow label="3h. Net Section 1231 Gain" value={net1231Gain} />
              <BasisRow label="3i. Other Income" value={otherIncome} />
              <BasisRow label="3j. Excess depletion adjustment" value={0} />
              <BasisRow label="3k. Tax-exempt Income" value={taxExemptIncome} />
              <BasisRow label="3l. Recapture of business credits" value={0} />
              <BasisRow label="3m. Other items that increase basis" value={otherBasisIncrease} />
              <BasisRow label="4. Total of 3a through 3m" value={totalIncreases} bold />
              <BasisRow label="5. Total of lines 1, 2, and 4" value={line5} bold />
              <div className="flex items-center justify-between px-4 py-1.5">
                <span className="text-xs text-tx">6. Distributions</span>
                <div className="w-36">
                  <CurrencyInput value={sh.distributions || "0"} onValueChange={(v) => saveSHField(sh.id, "distributions", v)} />
                </div>
              </div>
              <BasisRow label="7. Stock basis after distributions (6 minus 5, not less than 0)" value={stockAfterDist} bold />
              <BasisRow label="8a. Nondeductible expenses" value={nondeductible} />
              <BasisRow label="8b. Depletion (oil and gas)" value={0} />
              <BasisRow label="8c. Business credits" value={businessCredits} />
              <BasisRow label="9. Add lines 8a through 8c" value={totalReductions} />
              <BasisRow label="10. Stock basis before loss and deduction items (7 minus 9, not less than 0)" value={stockBeforeLoss} bold />
              <BasisRow label="11. Allowable loss and deduction items" value={allowableLoss} />
              <BasisRow label="12. Debt basis restoration" value={0} />
              <BasisRow label="13. Other items that decrease stock basis" value={0} />
              <BasisRow label="14. Add lines 11, 12, and 13" value={allowableLoss} />
              <BasisRow label="15. Stock basis at end of year (line 10 minus line 14, not less than 0)" value={stockBasisEOY} bold />
            </div>
          </div>

          {/* Debt Basis Calculation */}
          <div className="rounded-xl border border-border bg-card shadow-sm max-w-2xl">
            <div className="px-4 py-2 text-xs font-bold uppercase tracking-wider text-tx-secondary bg-surface-alt rounded-t-xl border-b border-border">
              Part II — Debt Basis Calculation
            </div>
            <ShareholderLoansPanel taxReturnId={taxReturnId} shareholder={sh} onRefresh={onRefresh} />
          </div>
        </div>
      )}
    </div>
  );
}

// Shareholder Loans sub-panel for Form 7203 Debt Basis
function ShareholderLoansPanel({
  taxReturnId,
  shareholder,
  onRefresh,
}: {
  taxReturnId: string;
  shareholder: ShareholderRow;
  onRefresh: () => Promise<void>;
}) {
  const [loans, setLoans] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    get(`/tax-returns/${taxReturnId}/shareholders/${shareholder.id}/loans/`).then((res) => {
      if (res.ok) setLoans(res.data as any[]);
      setLoading(false);
    });
  }, [shareholder.id]);

  async function addLoan() {
    const res = await post(`/tax-returns/${taxReturnId}/shareholders/${shareholder.id}/loans/`, {
      description: `Loan ${loans.length + 1}`,
      loan_balance_boy: "0",
      additional_loans: "0",
      loan_repayments: "0",
    });
    if (res.ok) {
      setLoans([...loans, res.data]);
    }
  }

  async function updateLoan(loanId: string, field: string, value: string) {
    await patch(`/tax-returns/${taxReturnId}/shareholders/${shareholder.id}/loans/${loanId}/`, { [field]: value });
    // Refresh loans
    const res = await get(`/tax-returns/${taxReturnId}/shareholders/${shareholder.id}/loans/`);
    if (res.ok) setLoans(res.data as any[]);
  }

  async function deleteLoan(loanId: string) {
    if (!confirm("Delete this loan?")) return;
    await del(`/tax-returns/${taxReturnId}/shareholders/${shareholder.id}/loans/${loanId}/`);
    setLoans(loans.filter((l) => l.id !== loanId));
  }

  const inputClass =
    "w-full rounded-md border border-input-border bg-input px-2 py-1 text-sm text-tx shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring";

  if (loading) return <div className="p-4 text-xs text-tx-muted">Loading loans...</div>;

  return (
    <div className="p-4 space-y-3">
      {loans.length === 0 && (
        <p className="text-xs text-tx-muted">No shareholder loans. Add a loan to track debt basis.</p>
      )}
      {loans.map((loan) => {
        const balBefore = (parseFloat(loan.loan_balance_boy) || 0) + (parseFloat(loan.additional_loans) || 0);
        const balEOY = balBefore - (parseFloat(loan.loan_repayments) || 0);
        return (
          <div key={loan.id} className="rounded-lg border border-border-subtle bg-surface-alt/30 p-3 space-y-2">
            <div className="flex items-center justify-between">
              <input
                type="text"
                value={loan.description}
                onChange={(e) => setLoans(loans.map((l) => l.id === loan.id ? { ...l, description: e.target.value } : l))}
                onBlur={(e) => updateLoan(loan.id, "description", e.target.value)}
                className={inputClass + " max-w-xs text-xs font-medium"}
                placeholder="Loan description"
              />
              <button onClick={() => deleteLoan(loan.id)} className="text-xs text-danger hover:underline">Delete</button>
            </div>
            {/* Loan detail fields */}
            <div className="grid grid-cols-4 gap-2">
              <div>
                <label className="text-[10px] text-tx-muted">Original Loan Amt</label>
                <CurrencyInput value={loan.original_loan_amount || "0"} onValueChange={(v) => {
                  setLoans(loans.map((l) => l.id === loan.id ? { ...l, original_loan_amount: v } : l));
                  updateLoan(loan.id, "original_loan_amount", v);
                }} />
              </div>
              <div>
                <label className="text-[10px] text-tx-muted">Interest Rate (%)</label>
                <input
                  type="text"
                  value={loan.interest_rate || ""}
                  onChange={(e) => setLoans(loans.map((l) => l.id === loan.id ? { ...l, interest_rate: e.target.value } : l))}
                  onBlur={(e) => updateLoan(loan.id, "interest_rate", e.target.value || "0")}
                  className={inputClass + " text-right text-xs"}
                  placeholder="e.g. 5.24"
                />
              </div>
              <div>
                <label className="text-[10px] text-tx-muted">Payment Amt</label>
                <CurrencyInput value={loan.payment_amount || "0"} onValueChange={(v) => {
                  setLoans(loans.map((l) => l.id === loan.id ? { ...l, payment_amount: v } : l));
                  updateLoan(loan.id, "payment_amount", v);
                }} />
              </div>
              <div>
                <label className="text-[10px] text-tx-muted">Maturity Date</label>
                <input
                  type="date"
                  value={loan.maturity_date || ""}
                  onChange={(e) => {
                    setLoans(loans.map((l) => l.id === loan.id ? { ...l, maturity_date: e.target.value } : l));
                    updateLoan(loan.id, "maturity_date", e.target.value || null);
                  }}
                  className={inputClass + " text-xs"}
                />
              </div>
            </div>
            {/* Balance calculation */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[10px] text-tx-muted">16. Loan Balance BOY</label>
                <CurrencyInput value={loan.loan_balance_boy || "0"} onValueChange={(v) => {
                  setLoans(loans.map((l) => l.id === loan.id ? { ...l, loan_balance_boy: v } : l));
                  updateLoan(loan.id, "loan_balance_boy", v);
                }} />
              </div>
              <div>
                <label className="text-[10px] text-tx-muted">17. Additional Loans</label>
                <CurrencyInput value={loan.additional_loans || "0"} onValueChange={(v) => {
                  setLoans(loans.map((l) => l.id === loan.id ? { ...l, additional_loans: v } : l));
                  updateLoan(loan.id, "additional_loans", v);
                }} />
              </div>
              <div>
                <label className="text-[10px] text-tx-muted">18. Balance Before Repayment</label>
                <div className="text-sm tabular-nums text-tx py-1">{balBefore.toLocaleString("en-US", { style: "currency", currency: "USD" })}</div>
              </div>
              <div>
                <label className="text-[10px] text-tx-muted">19. Principal Repayment</label>
                <CurrencyInput value={loan.loan_repayments || "0"} onValueChange={(v) => {
                  setLoans(loans.map((l) => l.id === loan.id ? { ...l, loan_repayments: v } : l));
                  updateLoan(loan.id, "loan_repayments", v);
                }} />
              </div>
              <div className="col-span-2">
                <label className="text-[10px] text-tx-muted">20. Loan Balance EOY</label>
                <div className="text-sm font-medium tabular-nums text-tx py-1">{balEOY.toLocaleString("en-US", { style: "currency", currency: "USD" })}</div>
              </div>
            </div>
          </div>
        );
      })}
      <button
        onClick={addLoan}
        className="rounded-lg bg-success px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-success-hover"
      >
        Add Loan
      </button>
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
  const [saving, setSaving] = useState(false);
  const seededRef = useRef(false);

  // Auto-seed 3 blank properties on first visit if none exist
  useEffect(() => {
    if (properties.length === 0 && !seededRef.current) {
      seededRef.current = true;
      (async () => {
        for (let i = 1; i <= 3; i++) {
          await post(`/tax-returns/${taxReturnId}/rental-properties/`, {
            description: `Property ${i}`,
            property_type: "6",
            rents_received: "0",
          });
        }
        await onRefresh();
      })();
    }
  }, [properties.length]);

  async function addProperty() {
    setSaving(true);
    const propNum = properties.length + 1;
    const res = await post(`/tax-returns/${taxReturnId}/rental-properties/`, {
      description: `Property ${propNum}`,
      property_type: "6",
      rents_received: "0",
    });
    if (res.ok) await onRefresh();
    else alert("Failed to add property.");
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

  const fmt = (n: number) => n.toLocaleString("en-US", { style: "currency", currency: "USD" });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
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
        <div className="rounded-xl border border-border bg-card px-4 py-8 text-center text-sm text-tx-muted">
          No rental properties. Click "Add Property" to create one.
        </div>
      )}

      {/* Side-by-side property columns (3 across) */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {properties.map((prop) => (
          <div key={prop.id} className="rounded-xl border border-border bg-card shadow-sm">
            <div className="flex items-center justify-between border-b border-border bg-surface-alt px-3 py-1.5 rounded-t-xl">
              <span className="text-xs font-bold text-tx truncate">{prop.description || "(No description)"}</span>
              <button onClick={() => deleteProperty(prop.id)} className="text-xs text-danger hover:underline shrink-0 ml-1">Del</button>
            </div>
            <div className="px-3 py-2 space-y-2">
              {/* Property info */}
              <div>
                <input type="text" defaultValue={prop.description} onBlur={(e) => updateProperty(prop.id, { description: e.target.value })} className={inputClass + " text-xs"} placeholder="Address / Description" />
              </div>
              <div className="grid grid-cols-3 gap-1.5">
                <select defaultValue={prop.property_type} onChange={(e) => updateProperty(prop.id, { property_type: e.target.value })} className={inputClass + " text-xs"}>
                  {Object.entries(PROPERTY_TYPES).map(([k, v]) => (<option key={k} value={k}>{v}</option>))}
                </select>
                <input type="number" defaultValue={prop.fair_rental_days} onBlur={(e) => updateProperty(prop.id, { fair_rental_days: parseInt(e.target.value) || 0 } as any)} className={inputClass + " text-xs"} placeholder="Rent days" title="Rental days" />
                <input type="number" defaultValue={prop.personal_use_days} onBlur={(e) => updateProperty(prop.id, { personal_use_days: parseInt(e.target.value) || 0 } as any)} className={inputClass + " text-xs"} placeholder="Pers days" title="Personal days" />
              </div>
              {/* Income + Expenses stacked */}
              <div className="space-y-0.5">
                <div className="flex items-center gap-1.5">
                  <span className="w-28 shrink-0 text-xs font-semibold text-tx truncate">Rents Received</span>
                  <CurrencyInput value={prop.rents_received} onValueChange={(v) => updateProperty(prop.id, { rents_received: v })} />
                </div>
                {EXPENSE_FIELDS.map(({ key, label }) => (
                  <div key={key} className="flex items-center gap-1.5">
                    <span className="w-28 shrink-0 text-xs text-tx-secondary truncate" title={label}>{label}</span>
                    <CurrencyInput value={prop[key] as string} onValueChange={(v) => updateProperty(prop.id, { [key]: v })} />
                  </div>
                ))}
              </div>
              <div className="flex gap-3 border-t border-border-subtle pt-1.5">
                <span className="text-xs text-tx-secondary">Exp: <strong className="text-tx">{fmt(parseFloat(prop.total_expenses))}</strong></span>
                <span className="text-xs text-tx-secondary">Net: <strong className={parseFloat(prop.net_rent) >= 0 ? "text-success" : "text-danger"}>{fmt(parseFloat(prop.net_rent))}</strong></span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Grand totals */}
      {properties.length > 1 && (
        <div className="rounded-xl border border-border bg-surface-alt px-4 py-3">
          <div className="flex gap-6">
            <span className="text-xs font-bold text-tx">All Properties Total</span>
            <span className="text-xs text-tx-secondary">Rents: <strong className="text-tx">{fmt(grandTotalRents)}</strong></span>
            <span className="text-xs text-tx-secondary">Expenses: <strong className="text-tx">{fmt(grandTotalExpenses)}</strong></span>
            <span className="text-xs text-tx-secondary">Net: <strong className={grandNetRent >= 0 ? "text-success" : "text-danger"}>{fmt(grandNetRent)}</strong></span>
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
      <ScheduleLSection fields={schedLFields} onChange={onChange} taxReturnId={taxReturnId} onRefresh={onRefresh} />
      {m1Fields.length > 0 && (() => {
        // M-1 two-column layout: Lines 1-4 on left, Lines 5-8 on right (like the IRS form)
        const leftLines = m1Fields.filter((f) => ["M1_1","M1_2","M1_3a","M1_3b","M1_3c","M1_4"].includes(f.line_number));
        const rightLineNums = ["M1_5a","M1_5b","M1_6a","M1_6b","M1_7","M1_8"];
        const rightLines = m1Fields.filter((f) => rightLineNums.includes(f.line_number));
        return (
          <div className="rounded-xl border border-border bg-card shadow-sm">
            <div className="px-4 py-1.5 text-xs font-bold uppercase tracking-wider text-tx-secondary bg-surface-alt border-b border-border">
              Schedule M-1 — Reconciliation of Income (Loss)
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-border-subtle">
              <div className="divide-y divide-border-subtle">
                {leftLines.map((fv) => (
                  <FieldRowWithSub key={fv.id} field={fv} onChange={onChange} pyValue={bsPyLines[fv.line_number]} showPY={bsHasPY} taxReturnId={taxReturnId} onRefresh={onRefresh} />
                ))}
              </div>
              <div className="divide-y divide-border-subtle">
                {rightLines.map((fv) => (
                  <FieldRowWithSub key={fv.id} field={fv} onChange={onChange} pyValue={bsPyLines[fv.line_number]} showPY={bsHasPY} taxReturnId={taxReturnId} onRefresh={onRefresh} />
                ))}
              </div>
            </div>
          </div>
        );
      })()}
      {(() => {
        if (m2Fields.length === 0) return (
          <div className="rounded-xl border border-border bg-card shadow-sm">
            <div className="px-4 py-1.5 text-xs font-bold uppercase tracking-wider text-tx-secondary bg-surface-alt border-b border-border">
              Schedule M-2 — Analysis of AAA, OAA, and STPI
            </div>
            <div className="px-4 py-3 text-xs text-tx-muted">No M-2 fields found. Delete and recreate this return to populate M-2.</div>
          </div>
        );
        // Build lookup: line_number -> FieldValue
        const m2 = Object.fromEntries(m2Fields.map((f) => [f.line_number, f]));
        const M2_ROWS = [
          { row: 1, label: "Balance at beginning of tax year" },
          { row: 2, label: "Ordinary income from page 1, line 21" },
          { row: 3, label: "Other additions" },
          { row: 4, label: "Loss from page 1, line 21" },
          { row: 5, label: "Other reductions" },
          { row: 6, label: "Combine lines 1 through 5" },
          { row: 7, label: "Distributions" },
          { row: 8, label: "Balance at end of tax year" },
        ];
        const COLS = ["a", "b", "c", "d"] as const;
        const COL_HEADERS = ["(a) AAA", "(b) OAA", "(c) STPI", "(d) Accu E&P"];
        return (
          <div className="rounded-xl border border-border bg-card shadow-sm">
            <div className="px-4 py-1.5 text-xs font-bold uppercase tracking-wider text-tx-secondary bg-surface-alt border-b border-border">
              Schedule M-2 — Analysis of AAA, OAA, and STPI
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-surface-alt">
                  <th className="px-3 py-1.5 text-left text-xs font-semibold text-tx-secondary w-8">#</th>
                  <th className="px-3 py-1.5 text-left text-xs font-semibold text-tx-secondary">Description</th>
                  {COL_HEADERS.map((h) => (
                    <th key={h} className="px-2 py-1.5 text-right text-xs font-semibold text-tx-secondary w-36">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle">
                {M2_ROWS.map(({ row, label }) => (
                  <tr key={row} className="hover:bg-surface-alt/50">
                    <td className="px-3 py-1 text-xs text-tx-muted">{row}</td>
                    <td className="px-3 py-1 text-xs text-tx">{label}</td>
                    {COLS.map((col) => {
                      const ln = `M2_${row}${col}`;
                      const fv = m2[ln];
                      if (!fv) return <td key={col} className="px-2 py-1" />;
                      return (
                        <td key={col} className="px-2 py-1">
                          <CurrencyInput
                            value={fv.value}
                            onValueChange={(v) => onChange(fv.form_line, v)}
                            readOnly={fv.is_computed && !fv.is_overridden}
                            className={`text-xs ${fv.is_computed && !fv.is_overridden ? "bg-surface-alt text-tx-secondary cursor-default" : ""}`}
                          />
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      })()}
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

  // Autosave extension/payment info (debounced)
  const paymentTimerRef = useRef<number | null>(null);
  useEffect(() => {
    if (paymentTimerRef.current) clearTimeout(paymentTimerRef.current);
    paymentTimerRef.current = window.setTimeout(() => { savePaymentInfo(); }, 800);
    return () => { if (paymentTimerRef.current) clearTimeout(paymentTimerRef.current); };
  }, [extensionFiled, extensionDate, tentativeTax, totalPayments, balanceDue,
      bankRouting, bankAccount, bankType]);

  const taxFields = fieldsBySection["page1_tax"] || [];

  return (
    <div className="space-y-6">
      {/* Extension (Form 7004) Card */}
      <div className="rounded-xl border border-border bg-card shadow-sm">
        <div className="flex items-center justify-between border-b border-border bg-surface-alt px-5 py-3">
          <h3 className="text-sm font-semibold text-tx">Extensions & Tax Payments</h3>
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
              File Automatic Extension (Form 7004)
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
// Schedule F — Profit or Loss From Farming
// ---------------------------------------------------------------------------
// Admin Section (Invoice + Letter)
// ---------------------------------------------------------------------------

const FILING_METHOD_OPTIONS = ["E-File", "Paper", "Extension Filed"];
const STATE_FILING_METHOD_OPTIONS = ["E-File", "Paper", "Not Required", "Extension Filed"];

function AdminSection({
  fieldsBySection,
  onChange,
}: {
  fieldsBySection: Record<string, FieldValue[]>;
  onChange: (formLineId: string, value: string) => void;
}) {
  const allFields = fieldsBySection["admin"] || [];

  if (allFields.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-card px-4 py-8 text-center text-sm text-tx-muted">
        No Admin data found. Re-run the seed command to create Admin fields.
      </div>
    );
  }

  const fieldMap: Record<string, FieldValue> = {};
  for (const f of allFields) fieldMap[f.line_number] = f;

  const invFeeRows = [
    { desc: null, amount: fieldMap["INV_PREP_FEE"], label: "Preparation Fee" },
    { desc: fieldMap["INV_FEE_2_DESC"], amount: fieldMap["INV_FEE_2"], label: "Additional Fee 2" },
    { desc: fieldMap["INV_FEE_3_DESC"], amount: fieldMap["INV_FEE_3"], label: "Additional Fee 3" },
  ];

  const estRows = [1, 2, 3, 4].map((n) => ({
    tax: fieldMap[`LTR_EST_TAX_${n}`],
    date: fieldMap[`LTR_EST_DATE_${n}`],
  }));

  return (
    <div className="space-y-4">
      {/* Invoice */}
      <div className="rounded-xl border border-border bg-card shadow-sm">
        <div className="px-4 py-1.5 text-xs font-bold uppercase tracking-wider text-tx-secondary bg-surface-alt rounded-t-xl">
          Invoice
        </div>
        <div className="divide-y divide-border-subtle">
          {/* Fee header row */}
          <div className="flex items-center gap-2 px-3 py-1 bg-surface-alt/50">
            <div className="flex-1 text-xs font-semibold text-tx-secondary">Description</div>
            <div className="w-36 shrink-0 text-right text-xs font-semibold text-tx-secondary">Amount</div>
          </div>
          {invFeeRows.map((row, i) => (
            <div key={i} className="flex items-center gap-2 px-3 py-1.5">
              <div className="flex-1 min-w-0">
                {row.desc ? (
                  <FieldInput field={row.desc} onChange={onChange} />
                ) : (
                  <span className="text-xs text-tx">{row.label}</span>
                )}
              </div>
              <div className="w-36 shrink-0">
                {row.amount && <FieldInput field={row.amount} onChange={onChange} />}
              </div>
            </div>
          ))}
          {/* Memo */}
          {fieldMap["INV_MEMO"] && (
            <div className="flex items-center gap-2 px-3 py-1.5">
              <div className="w-24 shrink-0 text-xs text-tx-secondary">Memo</div>
              <div className="flex-1">
                <FieldInput field={fieldMap["INV_MEMO"]} onChange={onChange} />
              </div>
            </div>
          )}
          {/* Total */}
          {fieldMap["INV_TOTAL"] && (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-surface-alt/30 border-t border-border">
              <div className="flex-1 text-xs font-semibold text-tx">Total</div>
              <div className="w-36 shrink-0">
                <FieldInput field={fieldMap["INV_TOTAL"]} onChange={onChange} />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Letter */}
      <div className="rounded-xl border border-border bg-card shadow-sm">
        <div className="px-4 py-1.5 text-xs font-bold uppercase tracking-wider text-tx-secondary bg-surface-alt rounded-t-xl">
          Engagement Letter / Filing Info
        </div>
        <div className="divide-y divide-border-subtle">
          {/* Filing method */}
          {fieldMap["LTR_FILING_METHOD"] && (
            <div className="flex items-center gap-2 px-3 py-1.5">
              <div className="w-48 shrink-0 text-xs text-tx">Federal filing method</div>
              <div className="w-44 shrink-0">
                <select
                  className="w-full rounded border border-border bg-card px-2 py-1 text-sm text-tx"
                  value={fieldMap["LTR_FILING_METHOD"].value || ""}
                  onChange={(e) => onChange(fieldMap["LTR_FILING_METHOD"].form_line, e.target.value)}
                >
                  <option value="">— Select —</option>
                  {FILING_METHOD_OPTIONS.map((opt) => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              </div>
            </div>
          )}
          {/* 8879 needed */}
          {fieldMap["LTR_8879_NEEDED"] && (
            <div className="flex items-center gap-2 px-3 py-1.5">
              <div className="w-48 shrink-0 text-xs text-tx">Form 8879 needed</div>
              <div className="w-44 shrink-0">
                <FieldInput field={fieldMap["LTR_8879_NEEDED"]} onChange={onChange} />
              </div>
            </div>
          )}
          {/* State filing method */}
          {fieldMap["LTR_ST_FILING"] && (
            <div className="flex items-center gap-2 px-3 py-1.5">
              <div className="w-48 shrink-0 text-xs text-tx">State filing method</div>
              <div className="w-44 shrink-0">
                <select
                  className="w-full rounded border border-border bg-card px-2 py-1 text-sm text-tx"
                  value={fieldMap["LTR_ST_FILING"].value || ""}
                  onChange={(e) => onChange(fieldMap["LTR_ST_FILING"].form_line, e.target.value)}
                >
                  <option value="">— Select —</option>
                  {STATE_FILING_METHOD_OPTIONS.map((opt) => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              </div>
            </div>
          )}
          {/* Balance due / due dates */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-0 divide-y md:divide-y-0 md:divide-x divide-border-subtle">
            <div className="divide-y divide-border-subtle">
              <div className="px-3 py-1 bg-surface-alt/50">
                <span className="text-xs font-semibold text-tx-secondary">Federal</span>
              </div>
              {fieldMap["LTR_FED_BALANCE"] && (
                <div className="flex items-center gap-2 px-3 py-1.5">
                  <div className="flex-1 text-xs text-tx">Balance due</div>
                  <div className="w-36 shrink-0">
                    <FieldInput field={fieldMap["LTR_FED_BALANCE"]} onChange={onChange} />
                  </div>
                </div>
              )}
              {fieldMap["LTR_FED_DUE_DATE"] && (
                <div className="flex items-center gap-2 px-3 py-1.5">
                  <div className="flex-1 text-xs text-tx">Due date</div>
                  <div className="w-36 shrink-0">
                    <FieldInput field={fieldMap["LTR_FED_DUE_DATE"]} onChange={onChange} />
                  </div>
                </div>
              )}
            </div>
            <div className="divide-y divide-border-subtle">
              <div className="px-3 py-1 bg-surface-alt/50">
                <span className="text-xs font-semibold text-tx-secondary">Georgia</span>
              </div>
              {fieldMap["LTR_GA_BALANCE"] && (
                <div className="flex items-center gap-2 px-3 py-1.5">
                  <div className="flex-1 text-xs text-tx">Balance due</div>
                  <div className="w-36 shrink-0">
                    <FieldInput field={fieldMap["LTR_GA_BALANCE"]} onChange={onChange} />
                  </div>
                </div>
              )}
              {fieldMap["LTR_GA_DUE_DATE"] && (
                <div className="flex items-center gap-2 px-3 py-1.5">
                  <div className="flex-1 text-xs text-tx">Due date</div>
                  <div className="w-36 shrink-0">
                    <FieldInput field={fieldMap["LTR_GA_DUE_DATE"]} onChange={onChange} />
                  </div>
                </div>
              )}
            </div>
          </div>
          {/* Quarterly estimates */}
          <div className="px-3 py-1 bg-surface-alt/50">
            <span className="text-xs font-semibold text-tx-secondary">Quarterly Estimated Tax Payments</span>
          </div>
          <div>
            <div className="flex items-center gap-2 px-3 py-1 bg-surface-alt/30">
              <div className="w-16 shrink-0 text-xs font-semibold text-tx-secondary">Quarter</div>
              <div className="flex-1 text-xs font-semibold text-tx-secondary">Due Date</div>
              <div className="w-36 shrink-0 text-right text-xs font-semibold text-tx-secondary">Amount</div>
            </div>
            {estRows.map((row, i) => (
              <div key={i} className="flex items-center gap-2 px-3 py-1 border-t border-border-subtle">
                <div className="w-16 shrink-0 text-xs text-tx-secondary">Q{i + 1}</div>
                <div className="flex-1">
                  {row.date && <FieldInput field={row.date} onChange={onChange} />}
                </div>
                <div className="w-36 shrink-0">
                  {row.tax && <FieldInput field={row.tax} onChange={onChange} />}
                </div>
              </div>
            ))}
          </div>
          {/* Custom note */}
          {fieldMap["LTR_CUSTOM_NOTE"] && (
            <div className="px-3 py-2">
              <div className="text-xs text-tx-secondary mb-1">Custom Note</div>
              <textarea
                className="w-full rounded border border-border bg-card px-2 py-1 text-sm text-tx resize-y"
                rows={3}
                value={fieldMap["LTR_CUSTOM_NOTE"].value || ""}
                onChange={(e) => onChange(fieldMap["LTR_CUSTOM_NOTE"].form_line, e.target.value)}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Schedule F Section
// ---------------------------------------------------------------------------

/** Lines that are farm income (Part I). */
const SCHED_F_INCOME_LINES = ["F1a","F1b","F1c","F2","F3","F4","F5","F6","F7","F8","F9"];
/** Lines that are farm expenses (Part II). */
const SCHED_F_EXPENSE_LINES = [
  "F10","F11","F12","F13","F14","F15","F16","F17","F18","F19","F20",
  "F21a","F21b","F22","F23","F24a","F24b","F25","F26","F27","F28",
  "F29","F30","F31","F32",
];
/** Header lines (text/boolean at the top). */
const SCHED_F_HEADER_LINES = ["FH_CROP","FH_CODE","FH_METHOD","FH_EIN","FH_PARTICIPATION","FH_1099_RECEIVED","FH_1099_FILED"];

function ScheduleFSection({
  fieldsBySection,
  onChange,
  pyLookup,
}: {
  fieldsBySection: Record<string, FieldValue[]>;
  onChange: (formLineId: string, value: string) => void;
  pyLookup?: Record<string, number>;
}) {
  const allFields = fieldsBySection["sched_f"] || [];

  const headerFields = allFields.filter((f) => SCHED_F_HEADER_LINES.includes(f.line_number));
  const incomeFields = allFields.filter((f) => SCHED_F_INCOME_LINES.includes(f.line_number));
  const expenseFields = allFields.filter((f) => SCHED_F_EXPENSE_LINES.includes(f.line_number));
  const summaryFields = allFields.filter((f) => f.line_number === "F33" || f.line_number === "F34");

  if (allFields.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-card px-4 py-8 text-center text-sm text-tx-muted">
        No Schedule F data found. Re-run the seed command to create Schedule F fields.
      </div>
    );
  }

  // Split expenses into two columns
  const midpoint = Math.ceil(expenseFields.length / 2);
  const leftExpenses = expenseFields.slice(0, midpoint);
  const rightExpenses = expenseFields.slice(midpoint);
  const hasPY = pyLookup && Object.keys(pyLookup).length > 0;

  return (
    <div className="space-y-4">
      {/* Header fields */}
      {headerFields.length > 0 && (
        <div className="rounded-xl border border-border bg-card shadow-sm">
          <div className="px-4 py-1.5 text-xs font-bold uppercase tracking-wider text-tx-secondary bg-surface-alt rounded-t-xl">
            Schedule F — Farm Information
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-0 divide-y md:divide-y-0 md:divide-x divide-border-subtle">
            <div className="divide-y divide-border-subtle">
              {headerFields.filter((_, i) => i < 4).map((fv) => (
                <div key={fv.id} className="flex items-center gap-2 px-3 py-1.5">
                  <div className="flex-1 min-w-0">
                    <span className="text-xs text-tx">{fv.label}</span>
                  </div>
                  <div className="w-36 shrink-0">
                    <FieldInput field={fv} onChange={onChange} />
                  </div>
                </div>
              ))}
            </div>
            <div className="divide-y divide-border-subtle">
              {headerFields.filter((_, i) => i >= 4).map((fv) => (
                <div key={fv.id} className="flex items-center gap-2 px-3 py-1.5">
                  <div className="flex-1 min-w-0">
                    <span className="text-xs text-tx">{fv.label}</span>
                  </div>
                  <div className="w-36 shrink-0">
                    <FieldInput field={fv} onChange={onChange} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Part I — Farm Income */}
      <div className="rounded-xl border border-border bg-card shadow-sm">
        <div className="px-4 py-1.5 text-xs font-bold uppercase tracking-wider text-tx-secondary bg-surface-alt rounded-t-xl">
          Part I — Farm Income
        </div>
        <div className="flex items-center gap-4 border-b border-border bg-surface-alt px-4 py-1.5">
          <div className="w-14 shrink-0 text-xs font-semibold uppercase tracking-wider text-tx-secondary">Line</div>
          <div className="flex-1 text-xs font-semibold uppercase tracking-wider text-tx-secondary">Description</div>
          <div className="w-36 shrink-0 text-right text-xs font-semibold uppercase tracking-wider text-tx-secondary">Amount</div>
          {hasPY && <div className="w-28 shrink-0 text-right text-xs font-semibold uppercase tracking-wider text-tx-muted">PY</div>}
        </div>
        <div className="divide-y divide-border-subtle">
          {incomeFields.map((fv) => (
            <FieldRow key={fv.id} field={fv} onChange={onChange} pyValue={pyLookup?.[fv.line_number]} showPY={!!hasPY} />
          ))}
        </div>
      </div>

      {/* Part II — Farm Expenses (2-column layout) */}
      <div className="rounded-xl border border-border bg-card shadow-sm">
        <div className="px-4 py-1.5 text-xs font-bold uppercase tracking-wider text-tx-secondary bg-surface-alt rounded-t-xl">
          Part II — Farm Expenses
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-0 divide-y lg:divide-y-0 lg:divide-x divide-border-subtle">
          <div className="divide-y divide-border-subtle">
            {leftExpenses.map((fv) => (
              <div key={fv.id} className="flex items-center gap-2 px-3 py-1">
                <div className="w-10 shrink-0 text-xs font-medium text-tx-secondary">{fv.line_number}</div>
                <div className="flex-1 min-w-0"><span className="text-xs text-tx truncate">{fv.label}</span></div>
                <div className="w-28 shrink-0"><FieldInput field={fv} onChange={onChange} /></div>
              </div>
            ))}
          </div>
          <div className="divide-y divide-border-subtle">
            {rightExpenses.map((fv) => (
              <div key={fv.id} className="flex items-center gap-2 px-3 py-1">
                <div className="w-10 shrink-0 text-xs font-medium text-tx-secondary">{fv.line_number}</div>
                <div className="flex-1 min-w-0"><span className="text-xs text-tx truncate">{fv.label}</span></div>
                <div className="w-28 shrink-0"><FieldInput field={fv} onChange={onChange} /></div>
              </div>
            ))}
          </div>
        </div>

        {/* Summary lines: F33 Total + F34 Net profit/loss */}
        <div className="border-t border-border divide-y divide-border-subtle bg-surface-alt/30">
          {summaryFields.map((fv) => (
            <FieldRow key={fv.id} field={fv} onChange={onChange} pyValue={pyLookup?.[fv.line_number]} showPY={!!hasPY} />
          ))}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Dispositions Section (Schedule D / Form 4797)
// ---------------------------------------------------------------------------

function DispositionsSection({
  taxReturnId,
  dispositions,
  onRefresh,
}: {
  taxReturnId: string;
  dispositions: DispositionRow[];
  onRefresh: () => Promise<void>;
}) {
  const [saving, setSaving] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  async function addDisposition() {
    setSaving(true);
    const res = await post(`/tax-returns/${taxReturnId}/dispositions/`, {
      description: "",
      sales_price: "0",
      cost_basis: "0",
      expenses_of_sale: "0",
      term: "long",
      sort_order: dispositions.length,
    });
    if (res.ok) {
      await onRefresh();
      setEditingId((res.data as DispositionRow).id);
    }
    setSaving(false);
  }

  async function updateDisposition(id: string, data: Partial<DispositionRow>) {
    await patch(`/tax-returns/${taxReturnId}/dispositions/${id}/`, data);
    await onRefresh();
  }

  async function deleteDisposition(id: string) {
    if (!confirm("Delete this disposition?")) return;
    await del(`/tax-returns/${taxReturnId}/dispositions/${id}/`);
    await onRefresh();
  }

  const fmt = (n: number) => n.toLocaleString("en-US", { style: "currency", currency: "USD" });
  const inputClass = "w-full rounded-md border border-input-border bg-input px-2 py-1 text-xs text-tx shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring";

  const totalGain = dispositions.reduce((s, d) => s + (parseFloat(d.gain_loss) || 0), 0);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-bold text-tx">Dispositions — Schedule D / Form 4797</h3>
          <p className="text-xs text-tx-muted">Asset sales and exchanges. Data flows to Schedule D and Form 4797.</p>
        </div>
        <button
          onClick={addDisposition}
          disabled={saving}
          className="rounded-lg bg-success px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-success-hover disabled:opacity-50"
        >
          Add Disposition
        </button>
      </div>

      {dispositions.length === 0 && (
        <div className="rounded-xl border border-border bg-card px-4 py-8 text-center text-sm text-tx-muted">
          No dispositions. Click "Add Disposition" to enter an asset sale.
        </div>
      )}

      {/* List view */}
      {dispositions.length > 0 && (
        <div className="rounded-xl border border-border bg-card shadow-sm overflow-hidden">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-surface-alt text-tx-secondary">
                <th className="text-left px-3 py-1.5 font-semibold">Description</th>
                <th className="text-left px-3 py-1.5 font-semibold">Acquired</th>
                <th className="text-left px-3 py-1.5 font-semibold">Sold</th>
                <th className="text-right px-3 py-1.5 font-semibold">Sales Price</th>
                <th className="text-right px-3 py-1.5 font-semibold">Basis</th>
                <th className="text-right px-3 py-1.5 font-semibold">Gain/Loss</th>
                <th className="text-center px-3 py-1.5 font-semibold">Term</th>
                <th className="text-center px-3 py-1.5 font-semibold">Type</th>
                <th className="px-3 py-1.5"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle">
              {dispositions.map((d) => (
                <tr key={d.id} className="hover:bg-surface-alt/30">
                  <td className="px-3 py-1.5 max-w-[200px] truncate">{d.description || "(No description)"}</td>
                  <td className="px-3 py-1.5 whitespace-nowrap">{d.date_acquired_various ? "Various" : d.date_acquired || "—"}</td>
                  <td className="px-3 py-1.5 whitespace-nowrap">{d.date_sold_various ? "Various" : d.date_sold || "—"}</td>
                  <td className="px-3 py-1.5 text-right tabular-nums">{fmt(parseFloat(d.sales_price) || 0)}</td>
                  <td className="px-3 py-1.5 text-right tabular-nums">{fmt(parseFloat(d.cost_basis) || 0)}</td>
                  <td className={`px-3 py-1.5 text-right tabular-nums font-medium ${parseFloat(d.gain_loss) >= 0 ? "text-success" : "text-danger"}`}>
                    {fmt(parseFloat(d.gain_loss) || 0)}
                  </td>
                  <td className="px-3 py-1.5 text-center">{d.term === "short" ? "ST" : "LT"}</td>
                  <td className="px-3 py-1.5 text-center">{d.is_4797 ? "4797" : "Sch D"}</td>
                  <td className="px-3 py-1.5 text-right whitespace-nowrap">
                    <button onClick={() => setEditingId(editingId === d.id ? null : d.id)} className="text-primary hover:underline mr-2">
                      {editingId === d.id ? "Close" : "Edit"}
                    </button>
                    <button onClick={() => deleteDisposition(d.id)} className="text-danger hover:underline">Del</button>
                  </td>
                </tr>
              ))}
            </tbody>
            {dispositions.length > 1 && (
              <tfoot>
                <tr className="bg-surface-alt font-semibold">
                  <td colSpan={5} className="px-3 py-1.5 text-right">Total Gain/Loss:</td>
                  <td className={`px-3 py-1.5 text-right tabular-nums ${totalGain >= 0 ? "text-success" : "text-danger"}`}>
                    {fmt(totalGain)}
                  </td>
                  <td colSpan={3}></td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      )}

      {/* Edit form (inline below list) */}
      {editingId && (
        <DispositionEditForm
          disposition={dispositions.find((d) => d.id === editingId)!}
          onSave={(data) => updateDisposition(editingId, data)}
          onClose={() => setEditingId(null)}
        />
      )}
    </div>
  );
}

function DispositionEditForm({
  disposition,
  onSave,
  onClose,
}: {
  disposition: DispositionRow;
  onSave: (data: Partial<DispositionRow>) => Promise<void>;
  onClose: () => void;
}) {
  const [saving, setSaving] = useState(false);
  const inputClass = "w-full rounded-md border border-input-border bg-input px-2 py-1 text-xs text-tx shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring";

  async function save(data: Partial<DispositionRow>) {
    setSaving(true);
    await onSave(data);
    setSaving(false);
  }

  return (
    <div className="rounded-xl border border-border bg-card shadow-sm">
      <div className="flex items-center justify-between border-b border-border bg-surface-alt px-4 py-1.5 rounded-t-xl">
        <span className="text-xs font-bold text-tx">Edit Disposition</span>
        <button onClick={onClose} className="text-xs text-tx-secondary hover:text-tx">&times; Close</button>
      </div>
      <div className="px-4 py-3 space-y-3">
        {/* Row 1: Description */}
        <div>
          <label className="block text-xs font-medium text-tx-secondary mb-0.5">Description of property</label>
          <input type="text" defaultValue={disposition.description} onBlur={(e) => save({ description: e.target.value })} className={inputClass} />
        </div>

        {/* Row 2: Dates */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-tx-secondary mb-0.5">Date acquired</label>
            <div className="flex items-center gap-2">
              <input
                type="date"
                defaultValue={disposition.date_acquired || ""}
                disabled={disposition.date_acquired_various}
                onBlur={(e) => save({ date_acquired: e.target.value || null } as any)}
                className={inputClass}
              />
              <label className="flex items-center gap-1 text-xs text-tx-secondary whitespace-nowrap">
                <input
                  type="checkbox"
                  checked={disposition.date_acquired_various}
                  onChange={(e) => save({ date_acquired_various: e.target.checked, ...(e.target.checked ? { date_acquired: null } : {}) } as any)}
                />
                Various
              </label>
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-tx-secondary mb-0.5">Date sold</label>
            <div className="flex items-center gap-2">
              <input
                type="date"
                defaultValue={disposition.date_sold || ""}
                disabled={disposition.date_sold_various}
                onBlur={(e) => save({ date_sold: e.target.value || null } as any)}
                className={inputClass}
              />
              <label className="flex items-center gap-1 text-xs text-tx-secondary whitespace-nowrap">
                <input
                  type="checkbox"
                  checked={disposition.date_sold_various}
                  onChange={(e) => save({ date_sold_various: e.target.checked, ...(e.target.checked ? { date_sold: null } : {}) } as any)}
                />
                Various
              </label>
            </div>
          </div>
        </div>

        {/* Row 3: Amounts */}
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-tx-secondary mb-0.5">Sales price</label>
            <CurrencyInput value={disposition.sales_price} onValueChange={(v) => save({ sales_price: v })} />
          </div>
          <div>
            <label className="block text-xs font-medium text-tx-secondary mb-0.5">Cost or other basis</label>
            <CurrencyInput value={disposition.cost_basis} onValueChange={(v) => save({ cost_basis: v })} />
          </div>
          <div>
            <label className="block text-xs font-medium text-tx-secondary mb-0.5">Expenses of sale</label>
            <CurrencyInput value={disposition.expenses_of_sale} onValueChange={(v) => save({ expenses_of_sale: v })} />
          </div>
        </div>

        {/* Row 4: Optional cost basis overrides */}
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-tx-secondary mb-0.5">AMT cost basis <span className="text-tx-muted">(optional)</span></label>
            <CurrencyInput value={disposition.amt_cost_basis ?? ""} onValueChange={(v) => save({ amt_cost_basis: v || null } as any)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-tx-secondary mb-0.5">State cost basis <span className="text-tx-muted">(optional)</span></label>
            <CurrencyInput value={disposition.state_cost_basis ?? ""} onValueChange={(v) => save({ state_cost_basis: v || null } as any)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-tx-secondary mb-0.5">State AMT basis <span className="text-tx-muted">(optional)</span></label>
            <CurrencyInput value={disposition.state_amt_cost_basis ?? ""} onValueChange={(v) => save({ state_amt_cost_basis: v || null } as any)} />
          </div>
        </div>

        {/* Row 5: Classification */}
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-tx-secondary mb-0.5">Term</label>
            <select
              defaultValue={disposition.term}
              onChange={(e) => save({ term: e.target.value as "short" | "long" })}
              className={inputClass}
            >
              <option value="short">Short-term</option>
              <option value="long">Long-term</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-tx-secondary mb-0.5">Form type</label>
            <select
              defaultValue={disposition.is_4797 ? "4797" : "schd"}
              onChange={(e) => save({ is_4797: e.target.value === "4797" })}
              className={inputClass}
            >
              <option value="schd">Schedule D (noninvestment)</option>
              <option value="4797">Form 4797 (investment)</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-tx-secondary mb-0.5">Net investment income tax</label>
            <select
              defaultValue={disposition.net_investment_income_tax}
              onChange={(e) => save({ net_investment_income_tax: e.target.value })}
              className={inputClass}
            >
              <option value="yes">Yes</option>
              <option value="no">No</option>
            </select>
          </div>
        </div>

        {/* Row 6: Checkboxes */}
        <div className="flex flex-wrap gap-x-6 gap-y-1 pt-1">
          {([
            ["nontaxable_federal", "Nontaxable to federal"],
            ["nontaxable_state", "Nontaxable to state"],
            ["related_party_loss", "Related party loss"],
            ["securities_trader", "Securities trader"],
            ["inherited_property", "Inherited (stepped-up basis)"],
          ] as [keyof DispositionRow, string][]).map(([key, label]) => (
            <label key={key} className="flex items-center gap-1.5 text-xs text-tx">
              <input
                type="checkbox"
                checked={!!disposition[key]}
                onChange={(e) => save({ [key]: e.target.checked })}
                className="rounded border-input-border"
              />
              {label}
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Depreciation Assets
// ---------------------------------------------------------------------------

const GROUP_CHOICES = [
  "Buildings",
  "Machinery and Equipment",
  "Furniture and Fixtures",
  "Land",
  "Improvements",
  "Vehicles",
  "Intangibles/Amortization",
];

const LIFE_CHOICES = ["3", "5", "7", "10", "15", "20", "27.5", "39"];

interface ImportPreviewAsset {
  asset_number: number;
  description: string;
  date_acquired: string | null;
  date_sold: string | null;
  cost_basis: number;
  business_pct: number;
  section_179: number;
  prior_depreciation: number;
  current_depreciation: number;
  method: string;
  convention: string;
  life: number;
  asset_group: string;
}

interface ImportPreviewResponse {
  parsed_count: number;
  errors: string[];
  warnings: string[];
  preview: ImportPreviewAsset[];
}

function DepreciationSection({
  taxReturnId,
  assets,
  rentalProperties,
  onRefresh,
}: {
  taxReturnId: string;
  assets: DepreciationAssetRow[];
  rentalProperties: { id: string; description: string }[];
  onRefresh: () => Promise<void>;
}) {
  const [saving, setSaving] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [importPreview, setImportPreview] = useState<ImportPreviewResponse | null>(null);
  const [importing, setImporting] = useState(false);
  const [importMsg, setImportMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fmt = (n: number) => n.toLocaleString("en-US", { style: "currency", currency: "USD" });
  const num = (s: string | null | undefined) => parseFloat(s || "0") || 0;

  // Store file reference so we can re-send for commit
  const importFileRef = useRef<File | null>(null);

  async function handleFileSelected(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    importFileRef.current = file;
    setImporting(true);
    setImportMsg(null);
    setImportPreview(null);
    try {
      const res = await uploadFile(
        `/tax-returns/${taxReturnId}/import-depreciation/`,
        {},
        file,
      );
      const data = res.data as Record<string, unknown>;
      if (!res.ok) {
        const errMsg = (data?.error as string) || (data?.detail as string) || `Server error ${res.status}`;
        const errors = (data?.errors as string[]) || [];
        setImportMsg(errors.length ? `${errMsg}: ${errors.join("; ")}` : errMsg);
      } else {
        setImportPreview(data as unknown as ImportPreviewResponse);
      }
    } catch (err) {
      setImportMsg(`Network error: ${(err as Error).message}`);
    }
    setImporting(false);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  async function commitImport() {
    if (!importPreview || !importFileRef.current) return;
    setImporting(true);
    setImportMsg(null);
    try {
      const res = await uploadFile(
        `/tax-returns/${taxReturnId}/import-depreciation/?commit=true`,
        {},
        importFileRef.current,
      );
      const data = res.data as Record<string, unknown>;
      if (!res.ok) {
        const errMsg = (data?.error as string) || (data?.detail as string) || `Server error ${res.status}`;
        setImportMsg(errMsg);
      } else {
        setImportMsg(`${data.imported_count} assets imported successfully`);
        setImportPreview(null);
        importFileRef.current = null;
        await onRefresh();
      }
    } catch (err) {
      setImportMsg(`Network error: ${(err as Error).message}`);
    }
    setImporting(false);
  }

  async function addAsset() {
    setSaving(true);
    const res = await post(`/tax-returns/${taxReturnId}/depreciation/`, {
      description: "",
      group_label: "Machinery and Equipment",
      date_acquired: "",
      cost_basis: "0",
      method: "200DB",
      convention: "HY",
      life: "7",
      flow_to: "page1",
    });
    if (res.ok) {
      await onRefresh();
      setEditingId((res.data as DepreciationAssetRow).id);
    }
    setSaving(false);
  }

  async function updateAsset(id: string, data: Record<string, unknown>) {
    await patch(`/tax-returns/${taxReturnId}/depreciation/${id}/`, data);
    await onRefresh();
  }

  async function calculateAll() {
    setSaving(true);
    await post(`/tax-returns/${taxReturnId}/depreciation/calculate/`);
    await onRefresh();
    setSaving(false);
  }

  async function deleteAsset(id: string) {
    if (!confirm("Delete this asset?")) return;
    await del(`/tax-returns/${taxReturnId}/depreciation/${id}/`);
    await onRefresh();
  }

  // Group assets by property_label then group_label
  const grouped = useMemo(() => {
    const byProperty: Record<string, DepreciationAssetRow[]> = {};
    for (const a of assets) {
      const key = a.property_label || "(Page 1 Business)";
      if (!byProperty[key]) byProperty[key] = [];
      byProperty[key].push(a);
    }
    return byProperty;
  }, [assets]);

  // Summary totals
  const totals = useMemo(() => {
    let sec179 = 0, bonus = 0, regular = 0, total = 0, amtTotal = 0, stateDisallowed = 0;
    let disposalGainLoss = 0, disposalRecapture = 0, disposalAmtAdj = 0;
    for (const a of assets) {
      sec179 += num(a.sec_179_elected);
      bonus += num(a.bonus_amount);
      const curr = num(a.current_depreciation);
      regular += curr - num(a.sec_179_elected) - num(a.bonus_amount);
      total += curr;
      amtTotal += num(a.amt_current_depreciation);
      stateDisallowed += num(a.state_bonus_disallowed);
      if (a.date_sold && a.gain_loss_on_sale != null) {
        disposalGainLoss += num(a.gain_loss_on_sale);
        disposalRecapture += num(a.depreciation_recapture);
        disposalAmtAdj += num(a.amt_gain_loss_on_sale) - num(a.gain_loss_on_sale);
      }
    }
    const amtPref = total - amtTotal;
    return { sec179, bonus, regular: Math.max(0, regular), total, amtTotal, amtPref, stateDisallowed, disposalGainLoss, disposalRecapture, disposalAmtAdj };
  }, [assets]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-bold text-tx">Depreciation &amp; Amortization</h3>
          <p className="text-xs text-tx-muted">Assets flow to Page 1 Line 14, Form 8825, or Schedule F.</p>
        </div>
        <div className="flex gap-2">
          {assets.length > 0 && (
            <button
              onClick={calculateAll}
              disabled={saving}
              className="rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-primary-hover disabled:opacity-50"
            >
              Calculate All
            </button>
          )}
          <input
            type="file"
            ref={fileInputRef}
            accept=".txt"
            onChange={handleFileSelected}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={importing}
            className="rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-amber-700 disabled:opacity-50"
          >
            {importing ? "Parsing..." : "Import"}
          </button>
          <button
            onClick={addAsset}
            disabled={saving}
            className="rounded-lg bg-success px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-success-hover disabled:opacity-50"
          >
            Add Asset
          </button>
        </div>
      </div>

      {/* Import status message */}
      {importMsg && !importPreview && (
        <div className={`rounded-lg border px-4 py-2 text-sm ${
          importMsg.includes("successfully") ? "border-green-300 bg-green-50 text-green-800" : "border-red-300 bg-red-50 text-red-800"
        }`}>
          {importMsg}
          <button onClick={() => setImportMsg(null)} className="ml-2 text-xs underline">dismiss</button>
        </div>
      )}

      {/* Import preview panel */}
      {importPreview && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-bold text-amber-900">
              Import Preview — {importPreview.parsed_count} assets found
            </h4>
            <div className="flex gap-2">
              <button
                onClick={() => { setImportPreview(null); importFileRef.current = null; }}
                className="rounded-lg border border-amber-400 px-3 py-1 text-xs font-medium text-amber-800 hover:bg-amber-100"
              >
                Cancel
              </button>
              <button
                onClick={commitImport}
                disabled={importing || importPreview.errors.length > 0}
                className="rounded-lg bg-green-600 px-3 py-1 text-xs font-semibold text-white shadow-sm hover:bg-green-700 disabled:opacity-50"
              >
                {importing ? "Importing..." : "Import All"}
              </button>
            </div>
          </div>

          {importPreview.errors.length > 0 && (
            <div className="rounded border border-red-300 bg-red-50 p-2 text-xs text-red-800">
              <strong>Errors (must fix before import):</strong>
              <ul className="list-disc ml-4 mt-1">{importPreview.errors.map((e, i) => <li key={i}>{e}</li>)}</ul>
            </div>
          )}
          {importPreview.warnings.length > 0 && (
            <div className="rounded border border-yellow-300 bg-yellow-50 p-2 text-xs text-yellow-800">
              <strong>Warnings:</strong>
              <ul className="list-disc ml-4 mt-1">{importPreview.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>
            </div>
          )}

          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-amber-300 text-left text-amber-900">
                  <th className="px-2 py-1">#</th>
                  <th className="px-2 py-1">Description</th>
                  <th className="px-2 py-1">Acquired</th>
                  <th className="px-2 py-1 text-right">Cost</th>
                  <th className="px-2 py-1">Method/Life</th>
                  <th className="px-2 py-1 text-right">Prior Depr</th>
                  <th className="px-2 py-1">Group</th>
                </tr>
              </thead>
              <tbody>
                {importPreview.preview.map((a, i) => (
                  <tr key={i} className="border-b border-amber-200">
                    <td className="px-2 py-1 tabular-nums">{a.asset_number}</td>
                    <td className="px-2 py-1">{a.description}</td>
                    <td className="px-2 py-1">{a.date_acquired || ""}</td>
                    <td className="px-2 py-1 text-right tabular-nums">{a.cost_basis.toLocaleString()}</td>
                    <td className="px-2 py-1">{a.method} {a.convention} {a.life}yr</td>
                    <td className="px-2 py-1 text-right tabular-nums">{a.prior_depreciation.toLocaleString()}</td>
                    <td className="px-2 py-1 text-tx-muted">{a.asset_group}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {assets.length === 0 && !importPreview && (
        <div className="rounded-xl border border-border bg-card px-4 py-8 text-center text-sm text-tx-muted">
          No depreciation assets. Click "Add Asset" to enter an asset.
        </div>
      )}

      {/* Grid grouped by property_label */}
      {Object.entries(grouped).map(([propLabel, propAssets]) => {
        const propTotal = propAssets.reduce((s, a) => s + num(a.current_depreciation), 0);
        // Sub-group by group_label
        const byGroup: Record<string, DepreciationAssetRow[]> = {};
        for (const a of propAssets) {
          if (!byGroup[a.group_label]) byGroup[a.group_label] = [];
          byGroup[a.group_label].push(a);
        }

        return (
          <div key={propLabel} className="rounded-xl border border-border bg-card shadow-sm overflow-hidden">
            {Object.keys(grouped).length > 1 && (
              <div className="bg-surface-alt px-3 py-1 border-b border-border">
                <span className="text-xs font-bold text-tx">{propLabel}</span>
                <span className="text-xs text-tx-muted ml-2">Total: {fmt(propTotal)}</span>
              </div>
            )}
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-surface-alt text-tx-secondary">
                  <th className="text-left px-2 py-1 font-semibold w-8">#</th>
                  <th className="text-left px-2 py-1 font-semibold">Description</th>
                  <th className="text-left px-2 py-1 font-semibold">Acquired</th>
                  <th className="text-left px-2 py-1 font-semibold">Sold</th>
                  <th className="text-right px-2 py-1 font-semibold">Cost/Basis</th>
                  <th className="text-right px-2 py-1 font-semibold">Bus%</th>
                  <th className="text-right px-2 py-1 font-semibold">Prior Depr</th>
                  <th className="text-right px-2 py-1 font-semibold">179/Bonus</th>
                  <th className="text-left px-2 py-1 font-semibold">Method</th>
                  <th className="text-right px-2 py-1 font-semibold">Current Depr</th>
                  <th className="text-right px-2 py-1 font-semibold">AMT Depr</th>
                  <th className="text-right px-2 py-1 font-semibold">Gain/Loss</th>
                  <th className="px-2 py-1"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle">
                {Object.entries(byGroup).map(([groupLabel, groupAssets]) => {
                  const groupTotal = groupAssets.reduce((s, a) => s + num(a.current_depreciation), 0);
                  return (
                    <Fragment key={groupLabel}>
                      <tr className="bg-surface-alt/50">
                        <td colSpan={9} className="px-2 py-0.5 text-xs font-semibold text-tx-secondary">{groupLabel}</td>
                        <td className="px-2 py-0.5 text-right text-xs font-semibold tabular-nums text-tx-secondary">{fmt(groupTotal)}</td>
                        <td></td>
                        <td></td>
                        <td></td>
                      </tr>
                      {groupAssets.map((a) => {
                        const disposed = !!a.date_sold;
                        const rowClass = disposed ? "hover:bg-surface-alt/30 italic text-tx-muted" : "hover:bg-surface-alt/30";
                        return (
                        <tr key={a.id} className={rowClass}>
                          <td className="px-2 py-1 text-tx-muted">{a.asset_number}</td>
                          <td className="px-2 py-1 max-w-[180px] truncate">{a.description || "(No description)"}</td>
                          <td className="px-2 py-1 whitespace-nowrap">{a.date_acquired || "\u2014"}</td>
                          <td className="px-2 py-1 whitespace-nowrap">{a.date_sold || "\u2014"}</td>
                          <td className="px-2 py-1 text-right tabular-nums">{fmt(num(a.cost_basis))}</td>
                          <td className="px-2 py-1 text-right tabular-nums">{num(a.business_pct)}%</td>
                          <td className="px-2 py-1 text-right tabular-nums">{fmt(num(a.prior_depreciation))}</td>
                          <td className="px-2 py-1 text-right tabular-nums">
                            {num(a.sec_179_elected) > 0 || num(a.bonus_amount) > 0
                              ? fmt(num(a.sec_179_elected) + num(a.bonus_amount))
                              : "\u2014"}
                          </td>
                          <td className="px-2 py-1 whitespace-nowrap text-tx-muted">{a.method_display}</td>
                          <td className="px-2 py-1 text-right tabular-nums font-medium">{fmt(num(a.current_depreciation))}</td>
                          <td className={`px-2 py-1 text-right tabular-nums ${
                            a.method === "NONE" || a.group_label === "Land" ? "text-tx-muted"
                            : Math.abs(num(a.amt_current_depreciation) - num(a.current_depreciation)) > 0.005 ? "text-amber-600 font-medium" : ""
                          }`}>
                            {a.method === "NONE" || a.group_label === "Land" ? "\u2014" : fmt(num(a.amt_current_depreciation))}
                          </td>
                          <td className="px-2 py-1 text-right tabular-nums">
                            {disposed && a.gain_loss_on_sale != null
                              ? <span className={num(a.gain_loss_on_sale) >= 0 ? "text-tx" : "text-danger"}>{fmt(num(a.gain_loss_on_sale))}</span>
                              : "\u2014"}
                          </td>
                          <td className="px-2 py-1 text-right whitespace-nowrap not-italic">
                            <button onClick={() => setEditingId(editingId === a.id ? null : a.id)} className="text-primary hover:underline mr-2">
                              {editingId === a.id ? "Close" : "Edit"}
                            </button>
                            <button onClick={() => deleteAsset(a.id)} className="text-danger hover:underline">Del</button>
                          </td>
                        </tr>
                        );
                      })}
                    </Fragment>
                  );
                })}
              </tbody>
              {propAssets.length > 1 && Object.keys(grouped).length > 1 && (
                <tfoot>
                  <tr className="bg-surface-alt font-semibold">
                    <td colSpan={9} className="px-2 py-1 text-right text-xs">Property Total:</td>
                    <td className="px-2 py-1 text-right tabular-nums text-xs">{fmt(propTotal)}</td>
                    <td></td>
                    <td></td>
                    <td></td>
                  </tr>
                </tfoot>
              )}
            </table>
          </div>
        );
      })}

      {/* Grand total */}
      {assets.length > 0 && (
        <div className="rounded-xl border border-border bg-card shadow-sm overflow-hidden">
          <table className="w-full text-xs">
            <tbody>
              <tr className="bg-surface-alt font-bold">
                <td colSpan={9} className="px-3 py-1.5 text-right">Grand Total Current Depreciation:</td>
                <td className="px-3 py-1.5 text-right tabular-nums">{fmt(totals.total)}</td>
                <td className="px-3 py-1.5 text-right tabular-nums">{fmt(totals.amtTotal)}</td>
                <td></td>
                <td className="w-20"></td>
              </tr>
            </tbody>
          </table>
        </div>
      )}

      {/* Edit form */}
      {editingId && assets.find((a) => a.id === editingId) && (
        <DepreciationEditForm
          asset={assets.find((a) => a.id === editingId)!}
          rentalProperties={rentalProperties}
          existingLabels={[...new Set(assets.map((a) => a.property_label).filter(Boolean))]}
          onSave={(data) => updateAsset(editingId, data)}
          onClose={() => setEditingId(null)}
        />
      )}

      {/* Summary panel */}
      {assets.length > 0 && (
        <div className="rounded-xl border border-border bg-card shadow-sm px-4 py-3">
          <h4 className="text-xs font-bold text-tx mb-2">Depreciation Summary</h4>
          <div className="grid grid-cols-2 gap-x-8 gap-y-1 text-xs max-w-md">
            <span className="text-tx-secondary">Section 179 Elected:</span>
            <span className="text-right tabular-nums font-medium">{fmt(totals.sec179)}</span>
            <span className="text-tx-secondary">Bonus Depreciation:</span>
            <span className="text-right tabular-nums font-medium">{fmt(totals.bonus)}</span>
            <span className="text-tx-secondary">Regular MACRS/SL:</span>
            <span className="text-right tabular-nums font-medium">{fmt(totals.regular)}</span>
            <span className="col-span-2 border-t border-border my-1"></span>
            <span className="text-tx font-bold">Total Current Depreciation:</span>
            <span className="text-right tabular-nums font-bold">{fmt(totals.total)}</span>
            <span className="text-tx-secondary">AMT Depreciation Total:</span>
            <span className="text-right tabular-nums font-medium">{fmt(totals.amtTotal)}</span>
            {totals.amtPref !== 0 && (<>
              <span className="text-tx-secondary">AMT Preference Item:</span>
              <span className="text-right tabular-nums font-medium text-amber-600">{fmt(totals.amtPref)}</span>
            </>)}
            <span className="text-tx-secondary">GA Bonus Disallowed:</span>
            <span className="text-right tabular-nums font-medium">{fmt(totals.stateDisallowed)}</span>
            {totals.disposalGainLoss !== 0 && (<>
              <span className="col-span-2 border-t border-border my-1"></span>
              <span className="text-tx-secondary">Total Disposal Gains:</span>
              <span className={`text-right tabular-nums font-medium ${totals.disposalGainLoss >= 0 ? "" : "text-danger"}`}>{fmt(totals.disposalGainLoss)}</span>
              <span className="text-tx-secondary">Total Depr Recapture:</span>
              <span className="text-right tabular-nums font-medium">{fmt(totals.disposalRecapture)}</span>
              {totals.disposalAmtAdj !== 0 && (<>
                <span className="text-tx-secondary">Total AMT Adjustment:</span>
                <span className="text-right tabular-nums font-medium">{fmt(totals.disposalAmtAdj)}</span>
              </>)}
            </>)}
          </div>
        </div>
      )}
    </div>
  );
}

function DepreciationEditForm({
  asset,
  rentalProperties,
  existingLabels,
  onSave,
  onClose,
}: {
  asset: DepreciationAssetRow;
  rentalProperties: { id: string; description: string }[];
  existingLabels: string[];
  onSave: (data: Record<string, unknown>) => Promise<void>;
  onClose: () => void;
}) {
  const [saving, setSaving] = useState(false);
  const inputClass = "w-full rounded-md border border-input-border bg-input px-2 py-1 text-xs text-tx shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring";
  const [showAmt, setShowAmt] = useState(false);
  const [showVehicle, setShowVehicle] = useState(asset.group_label === "Vehicles");
  const [showAmort, setShowAmort] = useState(asset.group_label === "Intangibles/Amortization");
  const [showDisposal, setShowDisposal] = useState(!!asset.date_sold);

  async function save(data: Record<string, unknown>) {
    setSaving(true);
    await onSave(data);
    setSaving(false);
  }

  return (
    <div className="rounded-xl border border-border bg-card shadow-sm">
      <div className="flex items-center justify-between border-b border-border bg-surface-alt px-4 py-1.5 rounded-t-xl">
        <span className="text-xs font-bold text-tx">Edit Asset #{asset.asset_number}</span>
        <button onClick={onClose} className="text-xs text-tx-secondary hover:text-tx">&times; Close</button>
      </div>
      <div className="px-4 py-3 space-y-3">
        {/* Section 1: Basic Info */}
        <div className="text-xs font-bold text-tx-secondary uppercase tracking-wider">Basic Info</div>
        <div className="grid grid-cols-3 gap-4">
          <div className="col-span-2">
            <label className="block text-xs font-medium text-tx-secondary mb-0.5">Description</label>
            <input type="text" defaultValue={asset.description} onBlur={(e) => save({ description: e.target.value })} className={inputClass} />
          </div>
          <div>
            <label className="block text-xs font-medium text-tx-secondary mb-0.5">Group</label>
            <select
              defaultValue={asset.group_label}
              onChange={(e) => {
                const g = e.target.value;
                save({ group_label: g });
                setShowVehicle(g === "Vehicles");
                setShowAmort(g === "Intangibles/Amortization");
              }}
              className={inputClass}
            >
              {GROUP_CHOICES.map((g) => <option key={g} value={g}>{g}</option>)}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-4 gap-4">
          <div>
            <label className="block text-xs font-medium text-tx-secondary mb-0.5">Property / Location Group</label>
            <input
              type="text"
              list="property-labels"
              defaultValue={asset.property_label}
              onBlur={(e) => save({ property_label: e.target.value })}
              placeholder="(blank = page 1)"
              className={inputClass}
            />
            <datalist id="property-labels">
              {existingLabels.map((l) => <option key={l} value={l} />)}
            </datalist>
            <p className="text-[10px] text-tx-muted mt-0.5">Group assets by property address or location. Leave blank for Page 1 business assets.</p>
          </div>
          <div>
            <label className="block text-xs font-medium text-tx-secondary mb-0.5">Date Acquired</label>
            <input type="date" defaultValue={asset.date_acquired || ""} onBlur={(e) => save({ date_acquired: e.target.value || null })} className={inputClass} />
          </div>
          <div>
            <label className="block text-xs font-medium text-tx-secondary mb-0.5">Flow To</label>
            <select defaultValue={asset.flow_to} onChange={(e) => save({ flow_to: e.target.value })} className={inputClass}>
              <option value="page1">Page 1 (Line 14)</option>
              <option value="8825">Form 8825</option>
              <option value="sched_f">Schedule F</option>
            </select>
          </div>
        </div>

        {asset.flow_to === "8825" && (
          <div className="grid grid-cols-4 gap-4">
            <div>
              <label className="block text-xs font-medium text-tx-secondary mb-0.5">Rental Property</label>
              <select defaultValue={asset.rental_property || ""} onChange={(e) => save({ rental_property: e.target.value || null })} className={inputClass}>
                <option value="">-- Select --</option>
                {rentalProperties.map((p) => <option key={p.id} value={p.id}>{p.description}</option>)}
              </select>
            </div>
          </div>
        )}

        <div className="grid grid-cols-4 gap-4">
          <div>
            <label className="block text-xs font-medium text-tx-secondary mb-0.5">Cost Basis</label>
            <CurrencyInput value={asset.cost_basis} onValueChange={(v) => save({ cost_basis: v })} />
          </div>
          <div>
            <label className="block text-xs font-medium text-tx-secondary mb-0.5">Business Use %</label>
            <input type="number" step="0.01" min="0" max="100" defaultValue={asset.business_pct} onBlur={(e) => save({ business_pct: e.target.value })} className={inputClass} />
          </div>
        </div>

        {/* Section 2: Depreciation Method */}
        <div className="text-xs font-bold text-tx-secondary uppercase tracking-wider pt-2">Depreciation Method</div>
        <div className="grid grid-cols-5 gap-4">
          <div>
            <label className="block text-xs font-medium text-tx-secondary mb-0.5">Method</label>
            <select defaultValue={asset.method} onChange={(e) => save({ method: e.target.value })} className={inputClass}>
              <option value="200DB">MACRS 200DB</option>
              <option value="150DB">MACRS 150DB</option>
              <option value="SL">Straight-Line</option>
              <option value="NONE">None</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-tx-secondary mb-0.5">Convention</label>
            <select defaultValue={asset.convention} onChange={(e) => save({ convention: e.target.value })} className={inputClass}>
              <option value="HY">HY (Half-Year)</option>
              <option value="MQ">MQ (Mid-Quarter)</option>
              <option value="MM">MM (Mid-Month)</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-tx-secondary mb-0.5">Life (years)</label>
            <select defaultValue={asset.life || ""} onChange={(e) => save({ life: e.target.value || null })} className={inputClass}>
              <option value="">--</option>
              {LIFE_CHOICES.map((l) => <option key={l} value={l}>{l}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-tx-secondary mb-0.5">Section 179</label>
            <CurrencyInput value={asset.sec_179_elected} onValueChange={(v) => save({ sec_179_elected: v })} />
          </div>
          <div>
            <label className="block text-xs font-medium text-tx-secondary mb-0.5">Bonus %</label>
            <input type="number" step="1" min="0" max="100" defaultValue={asset.bonus_pct} onBlur={(e) => save({ bonus_pct: e.target.value })} className={inputClass} />
          </div>
        </div>

        <div className="grid grid-cols-5 gap-4">
          <div>
            <label className="block text-xs font-medium text-tx-secondary mb-0.5">Prior Accum. Depreciation</label>
            <CurrencyInput value={asset.prior_depreciation} onValueChange={(v) => save({ prior_depreciation: v })} />
          </div>
          <div>
            <label className="block text-xs font-medium text-tx-secondary mb-0.5">Current Depreciation</label>
            <div className="px-2 py-1 text-xs font-medium text-yellow-700 bg-yellow-50 rounded-md border border-yellow-200 tabular-nums">
              {parseFloat(asset.current_depreciation || "0").toLocaleString("en-US", { style: "currency", currency: "USD" })}
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-tx-secondary mb-0.5">Bonus Amount</label>
            <div className="px-2 py-1 text-xs font-medium text-yellow-700 bg-yellow-50 rounded-md border border-yellow-200 tabular-nums">
              {parseFloat(asset.bonus_amount || "0").toLocaleString("en-US", { style: "currency", currency: "USD" })}
            </div>
          </div>
        </div>

        {/* Section 3: AMT (collapsible) */}
        <div>
          <button onClick={() => setShowAmt(!showAmt)} className="text-xs font-bold text-tx-secondary uppercase tracking-wider hover:text-tx pt-2">
            {showAmt ? "\u25BC" : "\u25B6"} AMT Depreciation
          </button>
          {showAmt && (
            <div className="grid grid-cols-4 gap-4 mt-2">
              <div>
                <label className="block text-xs font-medium text-tx-secondary mb-0.5">AMT Method</label>
                <select defaultValue={asset.amt_method} onChange={(e) => save({ amt_method: e.target.value })} className={inputClass}>
                  <option value="">(auto)</option>
                  <option value="150DB">150DB</option>
                  <option value="SL">S/L</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-tx-secondary mb-0.5">AMT Life</label>
                <select defaultValue={asset.amt_life || ""} onChange={(e) => save({ amt_life: e.target.value || null })} className={inputClass}>
                  <option value="">(same)</option>
                  {LIFE_CHOICES.map((l) => <option key={l} value={l}>{l}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-tx-secondary mb-0.5">AMT Prior Depreciation</label>
                <CurrencyInput value={asset.amt_prior_depreciation} onValueChange={(v) => save({ amt_prior_depreciation: v })} />
              </div>
              <div>
                <label className="block text-xs font-medium text-tx-secondary mb-0.5">AMT Current</label>
                <div className="px-2 py-1 text-xs font-medium text-yellow-700 bg-yellow-50 rounded-md border border-yellow-200 tabular-nums">
                  {parseFloat(asset.amt_current_depreciation || "0").toLocaleString("en-US", { style: "currency", currency: "USD" })}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Section 4: Vehicle / Listed Property (only if Vehicles group) */}
        {showVehicle && (
          <div>
            <div className="text-xs font-bold text-tx-secondary uppercase tracking-wider pt-2">Vehicle / Listed Property</div>
            <div className="grid grid-cols-3 gap-4 mt-2">
              <div>
                <label className="flex items-center gap-1.5 text-xs text-tx">
                  <input
                    type="checkbox"
                    checked={asset.is_listed_property}
                    onChange={(e) => save({ is_listed_property: e.target.checked })}
                    className="rounded border-input-border"
                  />
                  Listed Property
                </label>
              </div>
              <div>
                <label className="block text-xs font-medium text-tx-secondary mb-0.5">Total Miles</label>
                <input type="number" defaultValue={asset.vehicle_miles_total ?? ""} onBlur={(e) => save({ vehicle_miles_total: e.target.value ? parseInt(e.target.value) : null })} className={inputClass} />
              </div>
              <div>
                <label className="block text-xs font-medium text-tx-secondary mb-0.5">Business Miles</label>
                <input type="number" defaultValue={asset.vehicle_miles_business ?? ""} onBlur={(e) => save({ vehicle_miles_business: e.target.value ? parseInt(e.target.value) : null })} className={inputClass} />
              </div>
            </div>
          </div>
        )}

        {/* Section 5: Disposal Information (collapsible) */}
        {(() => {
          const p = (s: string | null | undefined) => parseFloat(s || "0") || 0;
          const f = (n: number) => n.toLocaleString("en-US", { style: "currency", currency: "USD" });
          const hasDisposal = asset.gain_loss_on_sale != null;
          const regGain = p(asset.gain_loss_on_sale);
          const amtGain = p(asset.amt_gain_loss_on_sale);
          const amtDiff = hasDisposal && Math.abs(amtGain - regGain) > 0.005;
          const amtAdj = amtGain - regGain;
          // Yellow computed style
          const yel = "px-2 py-0.5 text-xs tabular-nums text-yellow-700 bg-yellow-50 rounded border border-yellow-200 text-right font-medium";
          // Grey read-only
          const gry = "px-2 py-0.5 text-xs tabular-nums text-tx-muted italic text-right";
          // Red for losses
          const redVal = "px-2 py-0.5 text-xs tabular-nums text-danger bg-red-50 rounded border border-red-200 text-right font-medium";
          const valStyle = (n: number) => n < 0 ? redVal : yel;
          return (
          <div>
            <button onClick={() => setShowDisposal(!showDisposal)} className="text-xs font-bold text-tx-secondary uppercase tracking-wider hover:text-tx pt-2">
              {showDisposal ? "\u25BC" : "\u25B6"} Disposal Information
            </button>
            {showDisposal && (
              <div className="mt-2 space-y-3">
                {/* Date Sold input */}
                <div className="grid grid-cols-4 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-tx-secondary mb-0.5">Date Sold</label>
                    <input type="date" defaultValue={asset.date_sold || ""} onBlur={(e) => save({ date_sold: e.target.value || null })} className={inputClass} />
                  </div>
                </div>

                {/* Two-column breakdown table */}
                <table className="text-xs w-full max-w-lg">
                  <thead>
                    <tr>
                      <th className="text-left px-2 py-1 font-semibold text-tx-secondary w-48"></th>
                      <th className="text-right px-2 py-1 font-semibold text-tx-secondary w-36">Regular</th>
                      <th className="text-right px-2 py-1 font-semibold text-tx-secondary w-36">AMT</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td className="px-2 py-1 text-tx-secondary">Sales Price:</td>
                      <td className="px-2 py-1"><CurrencyInput value={asset.sales_price ?? ""} onValueChange={(v) => save({ sales_price: v || null })} /></td>
                      <td className={gry}>{hasDisposal ? f(p(asset.sales_price)) : "\u2014"}</td>
                    </tr>
                    <tr>
                      <td className="px-2 py-1 text-tx-secondary">Less: Expenses of Sale:</td>
                      <td className="px-2 py-1"><CurrencyInput value={asset.expenses_of_sale ?? ""} onValueChange={(v) => save({ expenses_of_sale: v || null })} /></td>
                      <td className={gry}>{hasDisposal ? `(${f(p(asset.expenses_of_sale))})` : "\u2014"}</td>
                    </tr>
                    <tr>
                      <td className="px-2 py-1 text-tx-muted italic">Less: Adjusted Basis:</td>
                      <td className={gry}>{hasDisposal ? (() => {
                        const adjBasis = p(asset.cost_basis) - p(asset.prior_depreciation) - p(asset.current_depreciation) - p(asset.sec_179_elected) - p(asset.bonus_amount);
                        return `(${f(Math.abs(adjBasis))})`;
                      })() : "\u2014"}</td>
                      <td className={gry}>{hasDisposal ? (() => {
                        const amtAdjBasis = p(asset.cost_basis) - p(asset.amt_prior_depreciation) - p(asset.amt_current_depreciation) - p(asset.sec_179_elected);
                        return `(${f(Math.abs(amtAdjBasis))})`;
                      })() : "\u2014"}</td>
                    </tr>
                    <tr className="border-t border-border">
                      <td className="px-2 py-1 font-bold text-tx">{regGain < 0 ? "Total Loss:" : "Total Gain:"}</td>
                      <td className={valStyle(regGain)}>{hasDisposal ? f(regGain) : "\u2014"}</td>
                      <td className={valStyle(amtGain)}>{hasDisposal ? f(amtGain) : "\u2014"}</td>
                    </tr>
                    {hasDisposal && regGain > 0 && (
                      <>
                        <tr>
                          <td className="px-2 py-1 pl-6 text-tx-secondary">Capital Gain:</td>
                          <td className={yel}>{f(p(asset.capital_gain))}</td>
                          <td className={yel}>{f(p(asset.amt_capital_gain))}</td>
                        </tr>
                        <tr>
                          <td className="px-2 py-1 pl-6 text-tx-secondary">Depr Recapture (1245):</td>
                          <td className={yel}>{f(p(asset.depreciation_recapture))}</td>
                          <td className={yel}>{f(p(asset.amt_depreciation_recapture))}</td>
                        </tr>
                      </>
                    )}
                    {hasDisposal && (
                      <tr>
                        <td className="px-2 py-1 text-tx-secondary">AMT Adjustment:</td>
                        <td className={gry}></td>
                        <td className={amtDiff ? (amtAdj > 0 ? redVal : yel) : gry}>
                          {amtDiff ? f(amtAdj) : "No AMT Difference"}
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>
          );
        })()}

        {/* Section 6: Amortization (only if Intangibles group) */}
        {showAmort && (
          <div>
            <div className="text-xs font-bold text-tx-secondary uppercase tracking-wider pt-2">Amortization</div>
            <div className="grid grid-cols-3 gap-4 mt-2">
              <div>
                <label className="block text-xs font-medium text-tx-secondary mb-0.5">Amortization Code</label>
                <select defaultValue={asset.amort_code} onChange={(e) => save({ amort_code: e.target.value, is_amortization: true })} className={inputClass}>
                  <option value="">-- Select --</option>
                  <option value="197">Section 197 (Intangibles)</option>
                  <option value="195">Section 195 (Startup Costs)</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-tx-secondary mb-0.5">Amortization Months</label>
                <input type="number" defaultValue={asset.amort_months ?? ""} onBlur={(e) => save({ amort_months: e.target.value ? parseInt(e.target.value) : null })} className={inputClass} />
              </div>
            </div>
          </div>
        )}
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
  // Accumulated depreciation/depletion/amortization lines pair together
  if (lineNum === "L2b" || lineNum === "L2e") return "L2_bad_debt";
  if (lineNum === "L10b" || lineNum === "L10e") return "L10_depr";
  if (lineNum === "L11b" || lineNum === "L11e") return "L11_depl";
  if (lineNum === "L13b" || lineNum === "L13e") return "L13_amort";
  // Total lines
  if (lineNum === "L15a" || lineNum === "L15d") return "L15";
  if (lineNum === "L27a" || lineNum === "L27d") return "L27";
  // Standard: strip trailing letter → e.g. "L16a" → "L16", "L16d" → "L16"
  return lineNum.replace(/[a-e]$/, "");
}

function isBOY(lineNum: string): boolean {
  return lineNum.endsWith("a") || lineNum.endsWith("b");
}

function ScheduleLSection({
  fields,
  onChange,
  taxReturnId,
  onRefresh,
}: {
  fields: FieldValue[];
  onChange: (formLineId: string, value: string) => void;
  taxReturnId: string;
  onRefresh: () => Promise<void>;
}) {
  const [expandedSubs, setExpandedSubs] = useState<Set<string>>(new Set());
  function toggleSub(ln: string) {
    setExpandedSubs((prev) => {
      const next = new Set(prev);
      next.has(ln) ? next.delete(ln) : next.add(ln);
      return next;
    });
  }

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
      .replace(/Less accumulated depreciation/, "Less accum. depreciation")
      .replace(/Less accumulated depletion/, "Less accum. depletion")
      .replace(/Less accumulated amortization/, "Less accum. amortization")
      .replace(/Less allowance for bad debts/, "Less bad debt allowance");

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
          const isTotalAssets = lineNum === "L15";
          const isFirstLiability = lineNum === "L16";
          const isFirstEquity = lineNum === "L22";
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
                <div className="flex-1 flex items-center gap-1">
                  <span className="text-xs text-tx">{g.label}</span>
                  {isComputed && (
                    <span className="ml-1 text-xs italic text-tx-muted">
                      Calculated
                    </span>
                  )}
                  {lineNum in SUBSCHEDULE_LINES && (
                    <button
                      onClick={() => toggleSub(lineNum)}
                      className="ml-1 text-[10px] font-medium text-primary hover:underline"
                      title="Show/hide detail breakdown"
                    >
                      {expandedSubs.has(lineNum) ? "▾ Hide detail" : "▸ Detail"}
                    </button>
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
              {lineNum in SUBSCHEDULE_LINES && expandedSubs.has(lineNum) && (
                <div className="px-4 pb-2">
                  <SubSchedulePanel
                    taxReturnId={taxReturnId}
                    lineNumber={lineNum}
                    onRefresh={onRefresh}
                  />
                </div>
              )}
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

// Lines that support sub-schedule drill-downs
const SUBSCHEDULE_LINES: Record<string, { type: "single" | "balance_sheet"; label: string }> = {
  M1_2: { type: "single", label: "Income on books not on return" },
  M1_3c: { type: "single", label: "Other M-1 additions" },
  M1_5b: { type: "single", label: "Other M-1 income on return not on books" },
  M1_6b: { type: "single", label: "Other M-1 deductions on books not on return" },
  L6: { type: "balance_sheet", label: "Other current assets" },
  L9: { type: "balance_sheet", label: "Other investments" },
  L14: { type: "balance_sheet", label: "Other assets" },
  L18: { type: "balance_sheet", label: "Other current liabilities" },
  L21: { type: "balance_sheet", label: "Other liabilities" },
};

function SubSchedulePanel({
  taxReturnId,
  lineNumber,
  onRefresh,
}: {
  taxReturnId: string;
  lineNumber: string;
  onRefresh: () => Promise<void>;
}) {
  const config = SUBSCHEDULE_LINES[lineNumber];
  const isBs = config?.type === "balance_sheet";

  const [items, setItems] = useState<LineItemDetailRow[]>([]);
  const [loading, setLoading] = useState(true);

  // Create a local-only placeholder row (not yet saved to DB)
  function makeBlankRow(sortOrder: number): LineItemDetailRow {
    return {
      id: `local-${crypto.randomUUID()}`,
      line_number: lineNumber,
      description: "",
      amount: "0",
      amount_boy: "0",
      amount_eoy: "0",
      sort_order: sortOrder,
    };
  }

  useEffect(() => {
    get(`/tax-returns/${taxReturnId}/line-details/?line_number=${lineNumber}`).then((res) => {
      if (res.ok) {
        const existing = res.data as LineItemDetailRow[];
        if (existing.length > 0) {
          setItems(existing);
        } else {
          // Show 4 blank local rows (no DB calls)
          setItems([1, 2, 3, 4].map(makeBlankRow));
        }
      }
      setLoading(false);
    });
  }, [taxReturnId, lineNumber]);

  // Save a local row to the server, replacing the local ID with the real one
  async function ensureSaved(localId: string, field: string, value: string) {
    const item = items.find((i) => i.id === localId);
    if (!item) return;

    if (localId.startsWith("local-")) {
      // First edit — create on server
      const payload = { ...item, [field]: value };
      const res = await post(`/tax-returns/${taxReturnId}/line-details/`, {
        line_number: lineNumber,
        description: payload.description,
        amount: payload.amount,
        amount_boy: payload.amount_boy,
        amount_eoy: payload.amount_eoy,
        sort_order: payload.sort_order,
      });
      if (res.ok) {
        const saved = res.data as LineItemDetailRow;
        setItems((prev) => prev.map((i) => (i.id === localId ? saved : i)));
        await onRefresh();
      }
    } else {
      // Already saved — patch
      await patch(`/tax-returns/${taxReturnId}/line-details/${localId}/`, { [field]: value });
      await onRefresh();
    }
  }

  async function addItem() {
    setItems((prev) => [...prev, makeBlankRow(prev.length + 1)]);
  }

  async function deleteItem(itemId: string) {
    if (itemId.startsWith("local-")) {
      setItems(items.filter((i) => i.id !== itemId));
    } else {
      await del(`/tax-returns/${taxReturnId}/line-details/${itemId}/`);
      setItems(items.filter((i) => i.id !== itemId));
      await onRefresh();
    }
  }

  function handleLocalChange(itemId: string, field: string, value: string) {
    setItems((prev) => prev.map((i) => (i.id === itemId ? { ...i, [field]: value } : i)));
  }

  const inputClass =
    "w-full rounded-md border border-input-border bg-input px-2 py-0.5 text-xs text-tx shadow-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-focus-ring";

  if (loading) return <div className="px-4 py-2 text-xs text-tx-muted">Loading...</div>;

  return (
    <div className="border border-border-subtle rounded-lg bg-surface-alt/20 p-2 mt-1 space-y-1">
      {isBs && items.length > 0 && (
        <div className="flex items-center gap-1.5 px-1 pb-0.5">
          <span className="flex-1" />
          <span className="w-28 text-center text-[10px] font-semibold text-tx-muted">BOY</span>
          <span className="w-28 text-center text-[10px] font-semibold text-tx-muted">EOY</span>
          <span className="w-4" />
        </div>
      )}
      {items.map((item) => (
        <div key={item.id} className="flex items-center gap-1.5">
          <input
            id={`lid-desc-${item.id}`}
            type="text"
            value={item.description}
            onChange={(e) => handleLocalChange(item.id, "description", e.target.value)}
            onBlur={(e) => ensureSaved(item.id, "description", e.target.value)}
            className={inputClass + (isBs ? " flex-1" : " w-48")}
            placeholder="Description"
          />
          {isBs ? (
            <>
              <div className="w-28">
                <CurrencyInput
                  value={item.amount_boy}
                  onValueChange={(v) => { handleLocalChange(item.id, "amount_boy", v); ensureSaved(item.id, "amount_boy", v); }}
                  className="text-xs"
                />
              </div>
              <div className="w-28">
                <CurrencyInput
                  value={item.amount_eoy}
                  onValueChange={(v) => { handleLocalChange(item.id, "amount_eoy", v); ensureSaved(item.id, "amount_eoy", v); }}
                  className="text-xs"
                />
              </div>
            </>
          ) : (
            <div className="w-32">
              <CurrencyInput
                value={item.amount}
                onValueChange={(v) => { handleLocalChange(item.id, "amount", v); ensureSaved(item.id, "amount", v); }}
                className="text-xs"
              />
            </div>
          )}
          <button
            onClick={() => deleteItem(item.id)}
            className="text-[10px] text-danger hover:underline shrink-0"
          >
            ✕
          </button>
        </div>
      ))}
      <button
        onClick={addItem}
        className="text-[10px] font-medium text-primary hover:underline px-1"
      >
        + Add detail
      </button>
    </div>
  );
}

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

function FieldRowWithSub({
  field,
  onChange,
  pyValue,
  showPY = false,
  taxReturnId,
  onRefresh,
}: {
  field: FieldValue;
  onChange: (formLineId: string, value: string) => void;
  pyValue?: number;
  showPY?: boolean;
  taxReturnId: string;
  onRefresh: () => Promise<void>;
}) {
  const hasSub = field.line_number in SUBSCHEDULE_LINES;
  const [expanded, setExpanded] = useState(false);

  return (
    <div>
      <div
        className={`flex items-center gap-4 px-4 py-1.5 ${
          field.is_computed ? "bg-surface-alt/50" : ""
        }`}
      >
        <div className="w-14 shrink-0 text-xs font-medium text-tx-secondary">
          {field.line_number}
        </div>
        <div className="flex-1 flex items-center gap-1">
          <span className="text-xs text-tx">{field.label}</span>
          {field.is_computed && (
            <span className="ml-1 text-xs italic text-tx-muted">Calculated</span>
          )}
          {hasSub && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="ml-1 text-[10px] font-medium text-primary hover:underline"
              title="Show/hide detail breakdown"
            >
              {expanded ? "▾ Hide detail" : "▸ Detail"}
            </button>
          )}
        </div>
        <div className="w-36 shrink-0">
          <FieldInput field={field} onChange={onChange} />
        </div>
        {showPY && <PriorYearCell value={pyValue} />}
      </div>
      {hasSub && expanded && (
        <div className="px-4 pb-2">
          <SubSchedulePanel
            taxReturnId={taxReturnId}
            lineNumber={field.line_number}
            onRefresh={onRefresh}
          />
        </div>
      )}
    </div>
  );
}

/**
 * Arrow/Enter key navigation: move focus to next/previous input field.
 * Enter and ArrowDown move to next field; ArrowUp moves to previous.
 */
function handleArrowNav(e: React.KeyboardEvent<HTMLInputElement>) {
  if (e.key !== "ArrowDown" && e.key !== "ArrowUp" && e.key !== "Enter") return;
  e.preventDefault();
  const inputs = Array.from(
    document.querySelectorAll<HTMLInputElement>(
      'input[type="text"]:not([readonly]), select:not([disabled])',
    ),
  );
  const idx = inputs.indexOf(e.currentTarget);
  if (idx < 0) return;
  const next = e.key === "ArrowUp" ? idx - 1 : idx + 1;
  if (next >= 0 && next < inputs.length) {
    inputs[next].focus();
  }
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
  placeholder,
}: {
  value: string;
  readOnly?: boolean;
  onChange: (v: string) => void;
  placeholder?: string;
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
      placeholder={placeholder}
      onChange={(e) => setLocal(e.target.value)}
      onBlur={() => {
        if (local !== value) onChange(local);
      }}
      onKeyDown={handleArrowNav}
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
      onKeyDown={handleArrowNav}
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
        onKeyDown={handleArrowNav}
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
// Forms Tab — full-width continuous return viewer
// ---------------------------------------------------------------------------

// Hardcoded fallback (used if API hasn't loaded yet)
const DEFAULT_PRINT_PACKAGES = [
  { value: "", label: "All Forms" },
  { value: "client", label: "Client Copy" },
  { value: "filing", label: "Filing Copy" },
  { value: "extension", label: "Extension Package" },
  { value: "state", label: "State Only" },
  { value: "k1s", label: "K-1 Package" },
  { value: "invoice", label: "Invoice Only" },
  { value: "letter", label: "Letter Only" },
];

function FormsTab({
  taxReturnId,
  returnData,
}: {
  taxReturnId: string;
  returnData: TaxReturnData;
}) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [pdfData, setPdfData] = useState<Uint8Array | null>(null);
  const [selectedPackage, setSelectedPackage] = useState("");
  const pdfUrlRef = useRef<string | null>(null);
  const [packages, setPackages] = useState(DEFAULT_PRINT_PACKAGES);
  const [pageMap, setPageMap] = useState<{ form: string; page: number }[]>([]);
  const [activePage, setActivePage] = useState(1);
  const [goToPageNum, setGoToPageNum] = useState(0);

  const formCode = returnData.form_code;
  const entityName = returnData.entity_name;
  const year = returnData.year;

  // Fetch print packages from API
  useEffect(() => {
    get("/print-packages/").then((res) => {
      if (res.ok && Array.isArray(res.data)) {
        const apiPkgs = (res.data as { code: string; name: string; is_active: boolean }[])
          .filter((p) => p.is_active)
          .map((p) => ({ value: p.code === "all" ? "" : p.code, label: p.name }));
        if (apiPkgs.length > 0) setPackages(apiPkgs);
      }
    });
  }, []);

  // Load the complete return PDF (all forms combined)
  async function loadComplete(pkg?: string) {
    const pkgName = pkg ?? selectedPackage;
    if (pdfUrlRef.current) {
      URL.revokeObjectURL(pdfUrlRef.current);
      pdfUrlRef.current = null;
    }
    setPdfUrl(null);
    setLoading(true);
    setError(null);

    // Fetch PDF and page map in parallel
    const [pdfRes, mapRes] = await Promise.all([
      renderComplete(taxReturnId, pkgName || undefined, true),
      getPageMap(taxReturnId, pkgName || undefined),
    ]);
    setLoading(false);

    if (pdfRes.ok && pdfRes.pdfBase64) {
      const binary = atob(pdfRes.pdfBase64);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      setPdfData(bytes);
      // Also keep blob URL for download fallback
      const blob = new Blob([bytes], { type: "application/pdf" });
      const url = URL.createObjectURL(blob);
      pdfUrlRef.current = url;
      setPdfUrl(url);
    } else {
      setError(pdfRes.error || "Failed to generate PDF.");
    }

    if (mapRes.ok && Array.isArray(mapRes.data)) {
      setPageMap(mapRes.data as { form: string; page: number }[]);
    }
    setActivePage(1);
  }

  useEffect(() => {
    loadComplete("");
    return () => {
      if (pdfUrlRef.current) URL.revokeObjectURL(pdfUrlRef.current);
    };
  }, [taxReturnId]);

  function handlePackageChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const pkg = e.target.value;
    setSelectedPackage(pkg);
    loadComplete(pkg);
  }

  function handleDownload() {
    if (!pdfUrl) return;
    const match = packages.find((p) => p.value === selectedPackage);
    const label = (match?.label || "Complete").replace(/\s+/g, "");
    const safeName = entityName.replace(/\s+/g, "_");
    const a = document.createElement("a");
    a.href = pdfUrl;
    a.download = `${formCode}_${label}_${safeName}_${year}.pdf`;
    a.click();
  }

  function goToPage(page: number) {
    setActivePage(page);
    setGoToPageNum(page);
  }

  return (
    <div className="flex flex-col -mx-4 -mb-3" style={{ height: "calc(100vh - 6.5rem)" }}>
      {/* Main content: sidebar + PDF viewer */}
      <div className="flex flex-1 min-h-0">
        {/* Form name sidebar */}
        {pageMap.length > 0 && !loading && (
          <div className="w-48 shrink-0 overflow-y-auto border-r border-border bg-surface-alt">
            {/* Sidebar header with controls */}
            <div className="sticky top-0 z-10 bg-surface-alt border-b border-border px-2 py-1.5 space-y-1">
              <div className="flex items-center gap-1">
                <select
                  value={selectedPackage}
                  onChange={handlePackageChange}
                  disabled={loading}
                  className="flex-1 min-w-0 rounded border border-border bg-card px-1.5 py-0.5 text-xs text-tx focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50"
                >
                  {packages.map((p) => (
                    <option key={p.value} value={p.value}>
                      {p.label}
                    </option>
                  ))}
                </select>
                <button
                  onClick={() => loadComplete()}
                  disabled={loading}
                  className="shrink-0 rounded border border-border px-1.5 py-0.5 text-xs text-tx hover:bg-surface-alt-hover disabled:opacity-50"
                  title="Refresh"
                >
                  &#x21BB;
                </button>
                <button
                  onClick={handleDownload}
                  disabled={!pdfUrl}
                  className="shrink-0 rounded bg-primary px-1.5 py-0.5 text-xs text-white hover:bg-primary-hover disabled:opacity-50"
                  title="Download"
                >
                  &#x2193;
                </button>
              </div>
            </div>
            {pageMap.map((entry) => (
              <button
                key={entry.page}
                onClick={() => goToPage(entry.page)}
                className={`block w-full text-left px-3 py-1.5 text-xs truncate transition-colors ${
                  activePage === entry.page
                    ? "bg-primary/10 text-primary font-semibold"
                    : "text-tx hover:bg-surface-alt-hover"
                }`}
                title={entry.form}
              >
                {entry.form}
              </button>
            ))}
          </div>
        )}

        {/* PDF viewer area */}
        <div className="flex flex-1 flex-col min-w-0">
          {loading && (
            <div className="flex flex-1 items-center justify-center">
              <div className="text-center">
                <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-4 border-primary-subtle border-t-primary" />
                <p className="text-sm text-tx-secondary">Generating complete return...</p>
              </div>
            </div>
          )}
          {error && !loading && (
            <div className="flex flex-1 items-center justify-center">
              <p className="text-sm text-danger">{error}</p>
            </div>
          )}
          {!loading && pdfData && (
            <PdfViewer
              data={pdfData}
              goToPage={goToPageNum}
              onPageChange={(page) => setActivePage(page)}
            />
          )}
        </div>
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
      { ln: "L15d", label: "Total assets" },
      { ln: "L15d", label: "Accounts payable" },
      { ln: "L20d", label: "Loans from shareholders" },
      { ln: "L24d", label: "Retained earnings" },
      { ln: "L27d", label: "Total liabilities and shareholders' equity" },
    ],
  },
  {
    title: "Schedule M-2 (AAA)",
    lines: [
      { ln: "M2_1a", label: "Balance at beginning of year" },
      { ln: "M2_2a", label: "Ordinary income" },
      { ln: "M2_5a", label: "Other reductions" },
      { ln: "M2_7a", label: "Distributions" },
      { ln: "M2_8a", label: "Balance at end of year" },
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
  onRefresh,
}: {
  taxReturnId: string;
  fieldsBySection: Record<string, FieldValue[]>;
  priorYear: PriorYearData | null;
  currentYear: number;
  onRefresh: () => Promise<void>;
}) {
  const [interestTrend, setInterestTrend] = useState<InterestTrendData | null>(null);
  // Local PY overrides — keyed by line_number
  const [pyOverrides, setPyOverrides] = useState<Record<string, number>>({});

  useEffect(() => {
    get(`/tax-returns/${taxReturnId}/interest-trend/`).then((res) => {
      if (res.ok) setInterestTrend(res.data as InterestTrendData);
    });
    setPyOverrides({});
  }, [taxReturnId]);

  async function updatePYLine(lineNumber: string, value: string) {
    const num = parseFloat(value) || 0;
    setPyOverrides((prev) => ({ ...prev, [lineNumber]: num }));
    await patch(`/tax-returns/${taxReturnId}/prior-year/update-line/`, {
      line_number: lineNumber,
      value: num,
    });
  }

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

  const rawPyLines = priorYear.line_values ?? {};
  // Apply local overrides
  const pyLines: Record<string, number> = { ...rawPyLines, ...pyOverrides };
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
                      <td className="px-2 py-0.5 w-32">
                        <CurrencyInput
                          value={py ? String(py) : ""}
                          onValueChange={(v) => updatePYLine(l.ln, v)}
                          className="text-xs text-right text-tx-secondary"
                        />
                      </td>
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
  rule_code: string;
  rule_category: "preparer" | "internal";
}

interface DiagnosticRunData {
  id: string;
  status: string;
  finding_count: number;
  started_at: string;
  completed_at: string | null;
  findings: DiagnosticFinding[];
}

type SeverityFilter = "all" | "error" | "warning" | "info";

function DiagnosticsTab({ taxYearId }: { taxYearId: string }) {
  const [runs, setRuns] = useState<DiagnosticRunData[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>("all");
  const [showInternal, setShowInternal] = useState(() => {
    try { return localStorage.getItem("diag_show_internal") === "true"; } catch { return false; }
  });

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

  function toggleInternal() {
    const next = !showInternal;
    setShowInternal(next);
    try { localStorage.setItem("diag_show_internal", String(next)); } catch { /* noop */ }
  }

  const latestRun = runs.length > 0 ? runs[0] : null;
  const allFindings = latestRun?.findings || [];

  // Filter by category (hide internal unless toggled)
  const visibleFindings = allFindings.filter(
    (f) => showInternal || f.rule_category !== "internal"
  );

  // Filter by severity
  const filtered = severityFilter === "all"
    ? visibleFindings
    : visibleFindings.filter((f) => f.severity === severityFilter);

  // Counts for summary (based on visible findings, not severity-filtered)
  const errorCount = visibleFindings.filter((f) => f.severity === "error").length;
  const warnCount = visibleFindings.filter((f) => f.severity === "warning").length;
  const infoCount = visibleFindings.filter((f) => f.severity === "info").length;
  const internalCount = allFindings.filter((f) => f.rule_category === "internal").length;

  // Sort: errors first, then warnings, then info
  const SEVERITY_ORDER: Record<string, number> = { error: 0, warning: 1, info: 2 };
  const sorted = [...filtered].sort((a, b) =>
    (SEVERITY_ORDER[a.severity] ?? 9) - (SEVERITY_ORDER[b.severity] ?? 9)
  );

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

      {/* Summary bar + filters */}
      {latestRun && (
        <div className="flex flex-wrap items-center gap-3">
          {/* Summary count pills */}
          {errorCount > 0 && (
            <span className="rounded-full bg-danger/10 px-3 py-1 text-sm font-semibold text-danger">
              {errorCount} Error{errorCount !== 1 ? "s" : ""}
            </span>
          )}
          {warnCount > 0 && (
            <span className="rounded-full bg-warning/10 px-3 py-1 text-sm font-semibold text-warning-dark">
              {warnCount} Warning{warnCount !== 1 ? "s" : ""}
            </span>
          )}
          {infoCount > 0 && (
            <span className="rounded-full bg-primary/10 px-3 py-1 text-sm font-semibold text-primary-text">
              {infoCount} Info
            </span>
          )}

          <div className="flex-1" />

          {/* Severity filter buttons */}
          {visibleFindings.length > 0 && (
            <div className="flex rounded-lg border border-border overflow-hidden text-xs">
              {(["all", "error", "warning", "info"] as const).map((sev) => (
                <button
                  key={sev}
                  onClick={() => setSeverityFilter(sev)}
                  className={`px-3 py-1 font-medium capitalize transition ${
                    severityFilter === sev
                      ? "bg-primary text-white"
                      : "bg-card text-tx-secondary hover:bg-surface-alt"
                  }`}
                >
                  {sev}
                </button>
              ))}
            </div>
          )}

          {/* Internal toggle */}
          {internalCount > 0 && (
            <label className="flex items-center gap-1.5 text-xs text-tx-muted cursor-pointer select-none">
              <input
                type="checkbox"
                checked={showInternal}
                onChange={toggleInternal}
                className="rounded border-border"
              />
              Internal ({internalCount})
            </label>
          )}
        </div>
      )}

      {latestRun && visibleFindings.length === 0 && (
        <div className="rounded-xl border border-success/30 bg-success/5 p-6 text-center shadow-sm">
          <svg className="mx-auto mb-2 h-8 w-8 text-success" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-sm font-semibold text-success">No issues found. Return looks good!</p>
        </div>
      )}

      {/* Findings list */}
      {sorted.length > 0 && (
        <div className="rounded-xl border border-border bg-card shadow-sm divide-y divide-border-subtle">
          {sorted.map((f) => {
            const style = SEVERITY_STYLES[f.severity] || SEVERITY_STYLES.info;
            return (
              <div key={f.id} className={`flex items-start gap-3 px-5 py-3 ${f.rule_category === "internal" ? "opacity-75" : ""}`}>
                <span className={`mt-0.5 shrink-0 rounded px-2 py-0.5 text-xs font-bold uppercase ${style.bg} ${style.text}`}>
                  {style.label}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-tx">{f.message}</p>
                  {f.rule_category === "internal" && (
                    <span className="inline-block mt-0.5 rounded bg-surface-alt px-1.5 py-0.5 text-[10px] font-medium uppercase text-tx-muted">
                      internal
                    </span>
                  )}
                </div>
                <span className="shrink-0 text-xs text-tx-muted font-mono">{f.rule_code}</span>
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
