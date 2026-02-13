import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { get } from "../lib/api";

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
  created_at: string;
}

export default function TrialBalance() {
  const { taxYearId } = useParams<{ taxYearId: string }>();
  const [uploads, setUploads] = useState<Upload[]>([]);
  const [rows, setRows] = useState<TBRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (!taxYearId) return;
    get(`/tb-uploads/?tax_year=${taxYearId}`).then((res) => {
      if (res.ok) {
        const ups = res.data as Upload[];
        setUploads(ups);
        if (ups.length > 0) {
          // Load rows for most recent upload
          get(`/tb-rows/?upload=${ups[0].id}`).then((rowRes) => {
            if (rowRes.ok) setRows(rowRes.data as TBRow[]);
            setLoading(false);
          });
        } else {
          setLoading(false);
        }
      } else {
        setLoading(false);
      }
    });
  }, [taxYearId]);

  const filtered = rows.filter(
    (r) =>
      r.account_name.toLowerCase().includes(search.toLowerCase()) ||
      r.account_number.toLowerCase().includes(search.toLowerCase())
  );

  const totalDebit = filtered.reduce((s, r) => s + parseFloat(r.debit || "0"), 0);
  const totalCredit = filtered.reduce((s, r) => s + parseFloat(r.credit || "0"), 0);

  const fmt = (v: number) =>
    v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  if (loading) return <p className="text-sm text-slate-500">Loading...</p>;

  return (
    <div>
      {/* Breadcrumb */}
      <div className="mb-4 text-sm text-slate-500">
        <Link to="/clients" className="text-blue-600 hover:underline">Clients</Link>
        <span className="mx-2">/</span>
        <span className="text-slate-800">Trial Balance</span>
      </div>

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Trial Balance</h1>
          {uploads.length > 0 && (
            <p className="text-sm text-slate-500">
              {uploads[0].original_filename} &mdash; {uploads[0].row_count} rows
            </p>
          )}
        </div>
      </div>

      {uploads.length === 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center shadow-sm">
          <p className="text-sm text-slate-500">No trial balance uploaded yet.</p>
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
              className="w-full max-w-sm rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm placeholder:text-slate-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            />
          </div>

          {/* Table */}
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                    #
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                    Account
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">
                    Debit
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">
                    Credit
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filtered.map((r) => {
                  const dr = parseFloat(r.debit || "0");
                  const cr = parseFloat(r.credit || "0");
                  const isZero = dr === 0 && cr === 0;
                  return (
                    <tr
                      key={r.id}
                      className={`hover:bg-slate-50 ${isZero ? "text-slate-400" : ""}`}
                    >
                      <td className="px-4 py-2 text-xs text-slate-400">{r.row_number}</td>
                      <td className="px-4 py-2 text-sm font-medium">
                        {r.account_name || r.account_number}
                        {r.account_number && r.account_name && (
                          <span className="ml-2 text-xs text-slate-400">{r.account_number}</span>
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
              <tfoot className="border-t-2 border-slate-300 bg-slate-50 font-semibold">
                <tr>
                  <td className="px-4 py-3" />
                  <td className="px-4 py-3 text-sm text-slate-900">TOTAL</td>
                  <td className="px-4 py-3 text-right text-sm tabular-nums text-slate-900">
                    {fmt(totalDebit)}
                  </td>
                  <td className="px-4 py-3 text-right text-sm tabular-nums text-slate-900">
                    {fmt(totalCredit)}
                  </td>
                </tr>
                <tr>
                  <td className="px-4 py-1" />
                  <td className="px-4 py-1 text-xs text-slate-500">Difference</td>
                  <td colSpan={2} className="px-4 py-1 text-right text-xs tabular-nums">
                    {Math.abs(totalDebit - totalCredit) < 0.01 ? (
                      <span className="text-green-600">Balanced</span>
                    ) : (
                      <span className="text-red-600">
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
