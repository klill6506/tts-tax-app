import { useEffect, useState, useRef } from "react";
import { get, post, patch, del } from "../lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Preparer {
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
  created_at: string;
  updated_at: string;
}

const EMPTY_PREPARER: Omit<Preparer, "id" | "created_at" | "updated_at"> = {
  name: "",
  ptin: "",
  is_self_employed: false,
  firm_name: "",
  firm_ein: "",
  firm_phone: "",
  firm_address: "",
  firm_city: "",
  firm_state: "",
  firm_zip: "",
  designee_name: "",
  designee_phone: "",
  designee_pin: "",
  is_active: true,
};

const US_STATES = [
  "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA",
  "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
  "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT",
  "VA","WA","WV","WI","WY","DC",
];

// ---------------------------------------------------------------------------
// Preparer Manager page
// ---------------------------------------------------------------------------

export default function PreparerManager() {
  const [preparers, setPreparers] = useState<Preparer[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState<Preparer | null>(null);
  const [creating, setCreating] = useState(false);
  const [formData, setFormData] = useState(EMPTY_PREPARER);
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const nameRef = useRef<HTMLInputElement>(null);

  // Fetch preparers
  async function fetchPreparers() {
    const res = await get("/preparers/");
    if (res.ok) setPreparers(res.data as Preparer[]);
    setLoading(false);
  }

  useEffect(() => {
    fetchPreparers();
  }, []);

  // Filter
  const filtered = preparers.filter((p) => {
    const q = search.toLowerCase();
    return (
      p.name.toLowerCase().includes(q) ||
      p.ptin.toLowerCase().includes(q) ||
      p.firm_name.toLowerCase().includes(q)
    );
  });

  // Open create form
  function startCreate() {
    setEditing(null);
    setFormData({ ...EMPTY_PREPARER });
    setCreating(true);
    setTimeout(() => nameRef.current?.focus(), 50);
  }

  // Open edit form
  function startEdit(p: Preparer) {
    setCreating(false);
    setEditing(p);
    setFormData({
      name: p.name,
      ptin: p.ptin,
      is_self_employed: p.is_self_employed,
      firm_name: p.firm_name,
      firm_ein: p.firm_ein,
      firm_phone: p.firm_phone,
      firm_address: p.firm_address,
      firm_city: p.firm_city,
      firm_state: p.firm_state,
      firm_zip: p.firm_zip,
      designee_name: p.designee_name,
      designee_phone: p.designee_phone,
      designee_pin: p.designee_pin,
      is_active: p.is_active,
    });
    setTimeout(() => nameRef.current?.focus(), 50);
  }

  // Cancel
  function cancelForm() {
    setCreating(false);
    setEditing(null);
  }

  // Save (create or update)
  async function handleSave() {
    setSaving(true);
    try {
      if (creating) {
        const res = await post("/preparers/", formData);
        if (res.ok) {
          setCreating(false);
          await fetchPreparers();
        }
      } else if (editing) {
        const res = await patch(`/preparers/${editing.id}/`, formData);
        if (res.ok) {
          setEditing(null);
          await fetchPreparers();
        }
      }
    } finally {
      setSaving(false);
    }
  }

  // Delete
  async function handleDelete(id: string) {
    await del(`/preparers/${id}/`);
    setConfirmDelete(null);
    if (editing?.id === id) setEditing(null);
    await fetchPreparers();
  }

  // Format helpers — auto-insert dashes for EIN, SSN, and phone
  function formatEIN(raw: string): string {
    const digits = raw.replace(/\D/g, "").slice(0, 9);
    if (digits.length > 2) return digits.slice(0, 2) + "-" + digits.slice(2);
    return digits;
  }

  function formatPhone(raw: string): string {
    const digits = raw.replace(/\D/g, "").slice(0, 10);
    if (digits.length > 6) return digits.slice(0, 3) + "-" + digits.slice(3, 6) + "-" + digits.slice(6);
    if (digits.length > 3) return digits.slice(0, 3) + "-" + digits.slice(3);
    return digits;
  }

  // Fields that get auto-formatted
  const FORMAT_FIELDS: Record<string, (v: string) => string> = {
    firm_ein: formatEIN,
    firm_phone: formatPhone,
    designee_phone: formatPhone,
  };

  // Form field helper
  function field(label: string, key: keyof typeof formData, opts?: { type?: string; placeholder?: string; width?: string }) {
    const val = formData[key];
    const formatter = FORMAT_FIELDS[key];
    return (
      <div className={opts?.width || "col-span-1"}>
        <label className="block text-xs font-medium text-tx-secondary mb-1">{label}</label>
        <input
          ref={key === "name" ? nameRef : undefined}
          type={opts?.type || "text"}
          value={val as string}
          onChange={(e) => {
            const v = formatter ? formatter(e.target.value) : e.target.value;
            setFormData((prev) => ({ ...prev, [key]: v }));
          }}
          placeholder={opts?.placeholder}
          className="w-full rounded-md border border-input-border bg-input px-2.5 py-1.5 text-sm text-tx outline-none focus:ring-2 focus:ring-focus-ring"
        />
      </div>
    );
  }

  const isFormOpen = creating || editing !== null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-tx">Preparer Manager</h1>
          <p className="mt-1 text-sm text-tx-secondary">
            Manage your firm's preparers. Assign them to returns from the form editor.
          </p>
        </div>
        <button
          onClick={startCreate}
          disabled={isFormOpen}
          className="rounded-lg bg-success px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-success-hover disabled:opacity-50"
        >
          + Add Preparer
        </button>
      </div>

      {/* Search */}
      <div className="flex items-center gap-3">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name, PTIN, or firm..."
          className="w-80 rounded-md border border-input-border bg-input px-3 py-2 text-sm text-tx outline-none focus:ring-2 focus:ring-focus-ring"
        />
        <span className="text-sm text-tx-muted">{filtered.length} preparer{filtered.length !== 1 ? "s" : ""}</span>
      </div>

      {/* Create / Edit Form */}
      {isFormOpen && (
        <div className="rounded-lg border border-border bg-card p-5 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-tx">
            {creating ? "Add New Preparer" : `Edit: ${editing?.name}`}
          </h2>

          <div className="grid grid-cols-4 gap-4">
            {/* Preparer Identity */}
            <div className="col-span-4">
              <p className="text-xs font-semibold text-tx-muted uppercase tracking-wide mb-2">Preparer</p>
            </div>
            {field("Name *", "name", { placeholder: "Full name", width: "col-span-2" })}
            {field("PTIN", "ptin", { placeholder: "P12345678" })}
            <div>
              <label className="block text-xs font-medium text-tx-secondary mb-1">Self-Employed</label>
              <label className="flex items-center gap-2 mt-1.5">
                <input
                  type="checkbox"
                  checked={formData.is_self_employed}
                  onChange={(e) => setFormData((prev) => ({ ...prev, is_self_employed: e.target.checked }))}
                  className="h-4 w-4 rounded border-input-border text-primary focus:ring-focus-ring"
                />
                <span className="text-sm text-tx">Yes</span>
              </label>
            </div>

            {/* Firm Info */}
            <div className="col-span-4 mt-2">
              <p className="text-xs font-semibold text-tx-muted uppercase tracking-wide mb-2">Firm Information</p>
            </div>
            {field("Firm Name", "firm_name", { width: "col-span-2" })}
            {field("Firm EIN", "firm_ein", { placeholder: "XX-XXXXXXX" })}
            {field("Firm Phone", "firm_phone", { placeholder: "555-555-5555" })}
            {field("Address", "firm_address", { width: "col-span-2" })}
            {field("City", "firm_city")}
            <div>
              <label className="block text-xs font-medium text-tx-secondary mb-1">State</label>
              <select
                value={formData.firm_state}
                onChange={(e) => setFormData((prev) => ({ ...prev, firm_state: e.target.value }))}
                className="w-full rounded-md border border-input-border bg-input px-2.5 py-1.5 text-sm text-tx outline-none focus:ring-2 focus:ring-focus-ring"
              >
                <option value="">—</option>
                {US_STATES.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
            {field("ZIP", "firm_zip", { placeholder: "75001" })}

            {/* Designee */}
            <div className="col-span-4 mt-2">
              <p className="text-xs font-semibold text-tx-muted uppercase tracking-wide mb-2">Third-Party Designee</p>
            </div>
            {field("Designee Name", "designee_name", { width: "col-span-2" })}
            {field("Phone", "designee_phone")}
            {field("PIN", "designee_pin", { placeholder: "5-digit PIN" })}

            {/* Active */}
            {!creating && (
              <div className="col-span-4 mt-2">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={formData.is_active}
                    onChange={(e) => setFormData((prev) => ({ ...prev, is_active: e.target.checked }))}
                    className="h-4 w-4 rounded border-input-border text-primary focus:ring-focus-ring"
                  />
                  <span className="text-sm text-tx">Active</span>
                </label>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="mt-5 flex gap-3">
            <button
              onClick={handleSave}
              disabled={saving || !formData.name.trim()}
              className="rounded-lg bg-primary px-5 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-primary-hover disabled:opacity-50"
            >
              {saving ? "Saving..." : creating ? "Create Preparer" : "Save Changes"}
            </button>
            <button
              onClick={cancelForm}
              className="rounded-lg border border-border bg-card px-5 py-2 text-sm font-medium text-tx transition hover:bg-surface"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Table */}
      {loading ? (
        <div className="rounded-lg border border-border bg-card p-8 text-center text-tx-muted">
          Loading preparers...
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-lg border border-border bg-card p-8 text-center">
          <p className="text-tx-muted">
            {preparers.length === 0
              ? "No preparers yet. Click \"+ Add Preparer\" to create one."
              : "No preparers match your search."}
          </p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-border shadow-sm">
          <table className="zebra-table w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="px-4 py-2.5 text-left font-semibold text-tx">Name</th>
                <th className="px-4 py-2.5 text-left font-semibold text-tx">PTIN</th>
                <th className="px-4 py-2.5 text-left font-semibold text-tx">Firm</th>
                <th className="px-4 py-2.5 text-left font-semibold text-tx">Phone</th>
                <th className="px-4 py-2.5 text-center font-semibold text-tx">Status</th>
                <th className="px-4 py-2.5 text-center font-semibold text-tx">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((p) => (
                <tr key={p.id} className="border-b border-border-subtle">
                  <td className="px-4 py-2.5 font-medium text-tx">{p.name}</td>
                  <td className="px-4 py-2.5 text-tx-secondary font-mono text-xs">{p.ptin || "—"}</td>
                  <td className="px-4 py-2.5 text-tx-secondary">{p.firm_name || "—"}</td>
                  <td className="px-4 py-2.5 text-tx-secondary">{p.firm_phone || "—"}</td>
                  <td className="px-4 py-2.5 text-center">
                    <span
                      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${
                        p.is_active
                          ? "bg-primary-subtle text-primary-text"
                          : "bg-surface-alt text-tx-muted"
                      }`}
                    >
                      {p.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-center">
                    <div className="flex items-center justify-center gap-2">
                      <button
                        onClick={() => startEdit(p)}
                        disabled={isFormOpen}
                        className="rounded px-2 py-1 text-xs font-medium text-primary transition hover:bg-primary-subtle disabled:opacity-40"
                      >
                        Edit
                      </button>
                      {confirmDelete === p.id ? (
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => handleDelete(p.id)}
                            className="rounded bg-danger px-2 py-1 text-xs font-medium text-white transition hover:bg-danger-hover"
                          >
                            Confirm
                          </button>
                          <button
                            onClick={() => setConfirmDelete(null)}
                            className="rounded px-2 py-1 text-xs text-tx-muted transition hover:text-tx"
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setConfirmDelete(p.id)}
                          disabled={isFormOpen}
                          className="rounded px-2 py-1 text-xs font-medium text-danger transition hover:bg-danger-subtle disabled:opacity-40"
                        >
                          Delete
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
