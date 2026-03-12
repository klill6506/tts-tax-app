import { useEffect, useState } from "react";
import { get, post, patch, del } from "../lib/api";

interface PrintPackage {
  id: string;
  name: string;
  code: string;
  description: string;
  sort_order: number;
  is_active: boolean;
}

const EMPTY_PACKAGE: Omit<PrintPackage, "id"> = {
  name: "",
  code: "",
  description: "",
  sort_order: 0,
  is_active: true,
};

export default function PrintPackageManager() {
  const [packages, setPackages] = useState<PrintPackage[]>([]);
  const [editing, setEditing] = useState<PrintPackage | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState(EMPTY_PACKAGE);

  async function load() {
    const res = await get("/print-packages/");
    if (res.ok && Array.isArray(res.data)) {
      setPackages(res.data as PrintPackage[]);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function startCreate() {
    setEditing(null);
    setCreating(true);
    setForm({ ...EMPTY_PACKAGE, sort_order: (packages.length + 1) * 10 });
  }

  function startEdit(pkg: PrintPackage) {
    setCreating(false);
    setEditing(pkg);
    setForm({
      name: pkg.name,
      code: pkg.code,
      description: pkg.description,
      sort_order: pkg.sort_order,
      is_active: pkg.is_active,
    });
  }

  function cancel() {
    setEditing(null);
    setCreating(false);
  }

  async function save() {
    if (creating) {
      await post("/print-packages/", form);
    } else if (editing) {
      await patch(`/print-packages/${editing.id}/`, form);
    }
    setEditing(null);
    setCreating(false);
    load();
  }

  async function remove(id: string) {
    await del(`/print-packages/${id}/`);
    load();
  }

  const isEditing = creating || editing !== null;

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-tx">Print Packages</h1>
          <p className="text-sm text-tx-secondary">
            Configure which print packages appear in the Forms tab dropdown.
          </p>
        </div>
        <button
          onClick={startCreate}
          disabled={isEditing}
          className="rounded-lg bg-success px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-success-hover disabled:opacity-50"
        >
          Add Package
        </button>
      </div>

      {isEditing && (
        <div className="mb-4 rounded-xl border border-border bg-card p-4 shadow-sm">
          <h2 className="mb-3 text-sm font-bold text-tx">
            {creating ? "New Package" : `Edit: ${editing!.name}`}
          </h2>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-tx-secondary mb-1">Name</label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full rounded-lg border border-border bg-card px-3 py-1.5 text-sm text-tx"
                placeholder="Client Copy"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-tx-secondary mb-1">Code</label>
              <input
                type="text"
                value={form.code}
                onChange={(e) => setForm({ ...form, code: e.target.value })}
                className="w-full rounded-lg border border-border bg-card px-3 py-1.5 text-sm text-tx"
                placeholder="client"
                disabled={!creating}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-tx-secondary mb-1">Description</label>
              <input
                type="text"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                className="w-full rounded-lg border border-border bg-card px-3 py-1.5 text-sm text-tx"
                placeholder="Letter + Invoice + all forms"
              />
            </div>
            <div className="flex items-end gap-4">
              <div>
                <label className="block text-xs font-medium text-tx-secondary mb-1">Sort Order</label>
                <input
                  type="number"
                  value={form.sort_order}
                  onChange={(e) => setForm({ ...form, sort_order: parseInt(e.target.value) || 0 })}
                  className="w-24 rounded-lg border border-border bg-card px-3 py-1.5 text-sm text-tx"
                />
              </div>
              <label className="flex items-center gap-2 text-sm text-tx pb-1">
                <input
                  type="checkbox"
                  checked={form.is_active}
                  onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                />
                Active
              </label>
            </div>
          </div>
          <div className="mt-3 flex gap-2">
            <button
              onClick={save}
              className="rounded-lg bg-primary px-4 py-1.5 text-sm font-semibold text-white hover:bg-primary-hover"
            >
              Save
            </button>
            <button
              onClick={cancel}
              className="rounded-lg border border-border px-4 py-1.5 text-sm font-medium text-tx hover:bg-surface-alt"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="rounded-xl border border-border bg-card shadow-sm">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-surface-alt text-left text-xs font-semibold uppercase tracking-wider text-tx-secondary">
              <th className="px-4 py-2">Order</th>
              <th className="px-4 py-2">Name</th>
              <th className="px-4 py-2">Code</th>
              <th className="px-4 py-2">Description</th>
              <th className="px-4 py-2">Active</th>
              <th className="px-4 py-2 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {packages.map((pkg) => (
              <tr key={pkg.id} className="border-b border-border-subtle last:border-0 hover:bg-surface-alt/50">
                <td className="px-4 py-2 text-tx-secondary">{pkg.sort_order}</td>
                <td className="px-4 py-2 font-medium text-tx">{pkg.name}</td>
                <td className="px-4 py-2 font-mono text-xs text-tx-secondary">{pkg.code}</td>
                <td className="px-4 py-2 text-tx-secondary">{pkg.description}</td>
                <td className="px-4 py-2">
                  {pkg.is_active ? (
                    <span className="text-success">Yes</span>
                  ) : (
                    <span className="text-tx-muted">No</span>
                  )}
                </td>
                <td className="px-4 py-2 text-right">
                  <button
                    onClick={() => startEdit(pkg)}
                    disabled={isEditing}
                    className="mr-2 text-primary-text hover:underline disabled:opacity-50"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => remove(pkg.id)}
                    disabled={isEditing}
                    className="text-danger hover:underline disabled:opacity-50"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
            {packages.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-tx-muted">
                  No print packages configured. Click "Add Package" to create one.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
