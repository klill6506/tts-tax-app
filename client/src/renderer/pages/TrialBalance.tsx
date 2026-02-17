import { useEffect, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { get, uploadFile } from "../lib/api";

interface TBRow {
  id: string;
  row_number: number;
  account_number: string;
  account_name: string;
  debit: string;
  credit: string;
}

interface Upload {
  id: string;
  original_filename: string;
  status: string;
  row_count: number;
  error_message?: string;
  created_at: string;
}

export default function TrialBalance() {
  const { taxYearId } = useParams<{ taxYearId: string }>();
  const [uploads, setUploads] = useState<Upload[]>([]);
  const [rows, setRows] = useState<TBRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  // Upload state
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!taxYearId) return;
    loadData();
  }, [taxYearId]);

  async function loadData() {
    if (!taxYearId) return;
    const res = await get(`/tb-uploads/?tax_year=${taxYearId}`);
    if (res.ok) {
      const ups = res.data as Upload[];
      setUploads(ups);
      if (ups.length > 0) {
        const rowRes = await get(`/tb-rows/?upload=${ups[0].id}`);
        if (rowRes.ok) setRows(rowRes.data as TBRow[]);
      }
    }
    setLoading(false);
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !taxYearId) return;

    setUploading(true);
    setUploadError("");

    const res = await uploadFile("/tb-uploads/upload/", { tax_year: taxYearId }, file);

    if (res.ok) {
      // Reload data to show new upload
      setRows([]);
      setLoading(true);
      await loadData();
    } else {
      const err = res.data as { error?: string; file?: string[]; detail?: string };
      setUploadError(err.file?.[0] || err.error || err.detail || "Upload failed.");
    }

    setUploading(false);
    // Reset file input so the same file can be re-selected
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  const filtered = rows.filter(
    (r) =>
      r.account_name.toLowerCase().includes(search.toLowerCase()) ||
      r.account_number.toLowerCase().includes(search.toLowerCase())
  );

  const totalDebit = filtered.reduce((s, r) => s + parseFloat(r.debit || "0"), 0);
  const totalCredit = filtered.reduce((s, r) => s + parseFloat(r.credit || "0"), 0);

  const fmt = (v: number) =>
    v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  if (loading) return <p className="text-sm text-tx-secondary">Loading...</p>;

  return (
    <div>
      {/* Breadcrumb */}
      <div className="mb-4 text-sm text-tx-secondary">
        <Link to="/" className="text-primary-text hover:underline">Clients</Link>
        <span className="mx-2">/</span>
        <span className="text-tx">Trial Balance</span>
      </div>

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-tx">Trial Balance</h1>
          {uploads.length > 0 && (
            <p className="text-sm text-tx-secondary">
              {uploads[0].original_filename} &mdash; {uploads[0].row_count} rows
            </p>
          )}
        </div>

        {/* Upload button */}
        <div className="flex items-center gap-3">
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.xlsx,.xls"
            onChange={handleUpload}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="rounded-lg bg-success px-4 py-2 text-sm font-medium text-white transition hover:bg-success-hover disabled:opacity-50"
          >
            {uploading ? "Uploading..." : uploads.length > 0 ? "Re-upload TB" : "Upload Trial Balance"}
          </button>
        </div>
      </div>

      {/* Upload error */}
      {uploadError && (
        <div className="mb-4 rounded-lg border border-danger bg-danger-subtle px-4 py-3 text-sm text-danger">
          {uploadError}
        </div>
      )}

      {uploads.length === 0 ? (
        <div className="rounded-xl border border-border bg-card p-8 text-center shadow-sm">
          <p className="mb-2 text-sm text-tx-secondary">No trial balance uploaded yet.</p>
          <p className="text-xs text-tx-muted">
            Upload a CSV or Excel file with Account Number, Account Name, Debit, and Credit columns.
          </p>
        </div>
      ) : (
        <>
          {/* Search */}
          <div className="mb-4">
            <input
              type="text"
              placeholder="Search accounts..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full max-w-sm rounded-md border border-input-border bg-input px-3 py-2 text-sm text-tx shadow-sm placeholder:text-tx-muted focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring"
            />
          </div>

          {/* Table */}
          <div className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
            <table className="min-w-full divide-y divide-border">
              <thead className="bg-surface">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-tx-secondary">
                    #
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-tx-secondary">
                    Account
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-tx-secondary">
                    Debit
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-tx-secondary">
                    Credit
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle">
                {filtered.map((r) => {
                  const dr = parseFloat(r.debit || "0");
                  const cr = parseFloat(r.credit || "0");
                  const isZero = dr === 0 && cr === 0;
                  return (
                    <tr
                      key={r.id}
                      className={`hover:bg-surface ${isZero ? "text-tx-muted" : ""}`}
                    >
                      <td className="px-4 py-2 text-xs text-tx-muted">{r.row_number}</td>
                      <td className="px-4 py-2 text-sm font-medium">
                        {r.account_name || r.account_number}
                        {r.account_number && r.account_name && (
                          <span className="ml-2 text-xs text-tx-muted">{r.account_number}</span>
                        )}
                      </td>
                      <td className="px-4 py-2 text-right text-sm tabular-nums">
                        {dr > 0 ? fmt(dr) : ""}
                      </td>
                      <td className="px-4 py-2 text-right text-sm tabular-nums">
                        {cr > 0 ? fmt(cr) : ""}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
              {/* Totals row */}
              <tfoot className="border-t-2 border-border bg-surface font-semibold">
                <tr>
                  <td className="px-4 py-3" />
                  <td className="px-4 py-3 text-sm text-tx">TOTAL</td>
                  <td className="px-4 py-3 text-right text-sm tabular-nums text-tx">
                    {fmt(totalDebit)}
                  </td>
                  <td className="px-4 py-3 text-right text-sm tabular-nums text-tx">
                    {fmt(totalCredit)}
                  </td>
                </tr>
                <tr>
                  <td className="px-4 py-1" />
                  <td className="px-4 py-1 text-xs text-tx-secondary">Difference</td>
                  <td colSpan={2} className="px-4 py-1 text-right text-xs tabular-nums">
                    {Math.abs(totalDebit - totalCredit) < 0.01 ? (
                      <span className="text-success">Balanced</span>
                    ) : (
                      <span className="text-danger">
                        Out of balance by {fmt(Math.abs(totalDebit - totalCredit))}
                      </span>
                    )}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
