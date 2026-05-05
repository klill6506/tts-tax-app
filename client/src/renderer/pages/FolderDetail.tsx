import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { get, del, uploadFile } from "../lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DocumentRow {
  id: string;
  filename: string;
  file_size: number;
  content_type: string;
  category: string;
  category_display: string;
  tax_year: number | null;
  notes: string;
  uploaded_by_name: string;
  download_url: string | null;
  created_at: string;
}

interface EntityInfo {
  id: string;
  name: string;
  entity_type: string;
  ein: string;
  client: string;
}

interface PaginatedDocResponse {
  count: number;
  results: DocumentRow[];
  next: string | null;
  previous: string | null;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const CATEGORY_OPTIONS = [
  { value: "", label: "All Categories" },
  { value: "w2", label: "W-2" },
  { value: "1099", label: "1099" },
  { value: "receipt", label: "Receipt" },
  { value: "bank_statement", label: "Bank Statement" },
  { value: "k1", label: "K-1" },
  { value: "engagement_letter", label: "Engagement Letter" },
  { value: "tax_return", label: "Completed Tax Return" },
  { value: "extension", label: "Extension (7004)" },
  { value: "organizer", label: "Tax Organizer" },
  { value: "correspondence", label: "IRS/State Correspondence" },
  { value: "other", label: "Other" },
];

const ENTITY_TYPE_LABELS: Record<string, string> = {
  scorp: "S-Corp",
  partnership: "Partnership",
  ccorp: "C-Corp",
  trust: "Trust",
  individual: "Individual",
};

const CATEGORY_COLORS: Record<string, string> = {
  w2: "bg-blue-50 text-blue-700",
  "1099": "bg-violet-50 text-violet-700",
  receipt: "bg-amber-50 text-amber-700",
  bank_statement: "bg-emerald-50 text-emerald-700",
  k1: "bg-indigo-50 text-indigo-700",
  engagement_letter: "bg-rose-50 text-rose-700",
  tax_return: "bg-emerald-50 text-emerald-800",
  extension: "bg-orange-50 text-orange-700",
  organizer: "bg-cyan-50 text-cyan-700",
  correspondence: "bg-red-50 text-red-700",
  other: "bg-surface-alt text-tx-secondary",
};

// ---------------------------------------------------------------------------
// Folder Detail page
// ---------------------------------------------------------------------------

export default function FolderDetail() {
  const { entityId } = useParams<{ entityId: string }>();

  const [entity, setEntity] = useState<EntityInfo | null>(null);
  const [clientName, setClientName] = useState("");
  const [docs, setDocs] = useState<PaginatedDocResponse | null>(null);
  const [loading, setLoading] = useState(true);

  // Filters
  const [categoryFilter, setCategoryFilter] = useState("");
  const [yearFilter, setYearFilter] = useState("");

  // Upload state
  const [showUpload, setShowUpload] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadCategory, setUploadCategory] = useState("other");
  const [uploadYear, setUploadYear] = useState(String(new Date().getFullYear()));
  const [uploadNotes, setUploadNotes] = useState("");
  const [selectedFiles, setSelectedFiles] = useState<FileList | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // --- Load entity info ---

  useEffect(() => {
    if (!entityId) return;
    get(`/entities/${entityId}/`).then((res) => {
      if (res.ok) {
        const e = res.data as EntityInfo;
        setEntity(e);
        // Fetch client name
        if (e.client) {
          get(`/clients/${e.client}/`).then((cr) => {
            if (cr.ok) setClientName((cr.data as { name: string }).name);
          });
        }
      }
    });
  }, [entityId]);

  // --- Load documents ---

  useEffect(() => {
    loadDocs();
  }, [entityId, categoryFilter, yearFilter]);

  async function loadDocs() {
    if (!entityId) return;
    setLoading(true);
    const params = new URLSearchParams();
    params.set("entity", entityId);
    params.set("page_size", "100");
    if (categoryFilter) params.set("category", categoryFilter);
    if (yearFilter) params.set("tax_year", yearFilter);

    const res = await get(`/documents/?${params.toString()}`);
    if (res.ok) {
      setDocs(res.data as PaginatedDocResponse);
    }
    setLoading(false);
  }

  // --- Upload ---

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedFiles || selectedFiles.length === 0 || !entityId) return;

    setUploading(true);
    for (let i = 0; i < selectedFiles.length; i++) {
      const file = selectedFiles[i];
      const fields: Record<string, string> = {
        entity: entityId,
        category: uploadCategory,
        notes: uploadNotes,
      };
      if (uploadYear) fields.tax_year = uploadYear;
      await uploadFile("/documents/upload/", fields, file);
    }
    setUploading(false);
    setShowUpload(false);
    setSelectedFiles(null);
    setUploadNotes("");
    if (fileInputRef.current) fileInputRef.current.value = "";
    loadDocs();
  }

  // --- Delete ---

  async function handleDelete(docId: string, filename: string) {
    if (!confirm(`Delete "${filename}"? This cannot be undone.`)) return;
    const res = await del(`/documents/${docId}/`);
    if (res.ok) loadDocs();
    else alert("Failed to delete document.");
  }

  // --- Download ---

  function handleDownload(url: string | null, filename: string) {
    if (!url) return;
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    a.click();
  }

  // --- Drag & drop ---

  const [dragOver, setDragOver] = useState(false);

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length > 0) {
      setSelectedFiles(e.dataTransfer.files);
      setShowUpload(true);
    }
  }

  // --- Helpers ---

  function relativeTime(iso: string): string {
    const d = new Date(iso);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return "just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHrs = Math.floor(diffMins / 60);
    if (diffHrs < 24) return `${diffHrs}h ago`;
    const diffDays = Math.floor(diffHrs / 24);
    if (diffDays < 7) return `${diffDays}d ago`;
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }

  function formatSize(bytes: number): string {
    if (!bytes) return "—";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  const documents = docs?.results ?? [];
  const currentYear = new Date().getFullYear();
  const yearOptions = Array.from({ length: 6 }, (_, i) => currentYear - i);

  // --- Render ---

  return (
    <div>
      {/* Header */}
      <div className="mb-5 flex items-center gap-3">
        <Link to="/folders" className="text-sm text-primary-text hover:underline">
          ← Folders
        </Link>
        <span className="text-tx-muted">/</span>
        <h1 className="text-lg font-semibold text-tx">
          {entity?.name ?? "Loading..."}
        </h1>
        {entity && (
          <span className="rounded bg-surface-alt px-2 py-0.5 text-xs font-medium text-tx-secondary">
            {ENTITY_TYPE_LABELS[entity.entity_type] || entity.entity_type}
          </span>
        )}
        {clientName && (
          <span className="text-sm text-tx-muted">({clientName})</span>
        )}
      </div>

      {/* Action bar */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <button
          onClick={() => setShowUpload(!showUpload)}
          className="rounded-lg bg-success px-4 py-2 text-sm font-medium text-white transition hover:bg-success-hover"
        >
          Upload Document
        </button>
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="rounded-md border border-input-border bg-input px-3 py-1.5 text-sm text-tx shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring"
        >
          {CATEGORY_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
        <select
          value={yearFilter}
          onChange={(e) => setYearFilter(e.target.value)}
          className="rounded-md border border-input-border bg-input px-3 py-1.5 text-sm text-tx shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring"
        >
          <option value="">All Years</option>
          {yearOptions.map((y) => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
        {(categoryFilter || yearFilter) && (
          <button
            onClick={() => { setCategoryFilter(""); setYearFilter(""); }}
            className="text-xs text-primary-text hover:underline"
          >
            Clear filters
          </button>
        )}
        <span className="ml-auto text-sm text-tx-muted">
          {docs?.count ?? 0} document{(docs?.count ?? 0) !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Upload form */}
      {showUpload && (
        <form onSubmit={handleUpload} className="mb-4 rounded-lg border border-border bg-card p-4 shadow-sm">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
            <div className="sm:col-span-2">
              <label className="mb-1 block text-xs font-medium text-tx-secondary">File(s)</label>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                onChange={(e) => setSelectedFiles(e.target.files)}
                className="w-full rounded-md border border-input-border bg-input px-3 py-1.5 text-sm text-tx file:mr-3 file:rounded file:border-0 file:bg-primary file:px-3 file:py-1 file:text-xs file:font-medium file:text-white"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-tx-secondary">Category</label>
              <select
                value={uploadCategory}
                onChange={(e) => setUploadCategory(e.target.value)}
                className="w-full rounded-md border border-input-border bg-input px-3 py-1.5 text-sm text-tx shadow-sm"
              >
                {CATEGORY_OPTIONS.filter((o) => o.value).map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-tx-secondary">Tax Year</label>
              <select
                value={uploadYear}
                onChange={(e) => setUploadYear(e.target.value)}
                className="w-full rounded-md border border-input-border bg-input px-3 py-1.5 text-sm text-tx shadow-sm"
              >
                {yearOptions.map((y) => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="mt-3">
            <label className="mb-1 block text-xs font-medium text-tx-secondary">Notes (optional)</label>
            <input
              type="text"
              value={uploadNotes}
              onChange={(e) => setUploadNotes(e.target.value)}
              placeholder="e.g., W-2 from employer"
              className="w-full rounded-md border border-input-border bg-input px-3 py-1.5 text-sm text-tx shadow-sm placeholder:text-tx-muted"
            />
          </div>
          <div className="mt-3 flex items-center gap-2">
            <button
              type="submit"
              disabled={uploading || !selectedFiles || selectedFiles.length === 0}
              className="rounded-lg bg-success px-4 py-2 text-sm font-medium text-white transition hover:bg-success-hover disabled:opacity-50"
            >
              {uploading ? "Uploading..." : "Upload"}
            </button>
            <button
              type="button"
              onClick={() => { setShowUpload(false); setSelectedFiles(null); if (fileInputRef.current) fileInputRef.current.value = ""; }}
              className="rounded-lg px-3 py-2 text-sm font-medium text-tx-secondary transition hover:bg-surface-alt"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Drop zone + Document table */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        className={`overflow-hidden rounded-xl border bg-card shadow-sm transition ${
          dragOver ? "border-primary border-2 bg-primary-subtle" : "border-border"
        }`}
      >
        {loading && !docs ? (
          <p className="p-6 text-sm text-tx-secondary">Loading documents...</p>
        ) : documents.length === 0 ? (
          <div className="p-8 text-center">
            <svg className="mx-auto mb-3 h-10 w-10 text-tx-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m6.75 12l-3-3m0 0l-3 3m3-3v6m-1.5-15H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
            <p className="text-sm text-tx-secondary">
              No documents yet. Drag files here or click "Upload Document" to get started.
            </p>
          </div>
        ) : (
          <table className="min-w-full divide-y divide-border">
            <thead className="bg-surface-alt">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-tx-secondary">Filename</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-tx-secondary">Category</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-tx-secondary">Tax Year</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-tx-secondary">Size</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-tx-secondary">Uploaded By</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-tx-secondary">Date</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-tx-secondary">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle">
              {documents.map((doc) => (
                <tr key={doc.id} className="transition hover:bg-primary-subtle">
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleDownload(doc.download_url, doc.filename)}
                      className="text-sm font-medium text-primary-text hover:underline"
                    >
                      {doc.filename}
                    </button>
                    {doc.notes && (
                      <p className="mt-0.5 text-xs text-tx-muted">{doc.notes}</p>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${
                      CATEGORY_COLORS[doc.category] || CATEGORY_COLORS.other
                    }`}>
                      {doc.category_display}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-tx-secondary">{doc.tax_year || "—"}</td>
                  <td className="px-4 py-3 text-sm text-tx-secondary">{formatSize(doc.file_size)}</td>
                  <td className="px-4 py-3 text-sm text-tx-secondary">{doc.uploaded_by_name || "—"}</td>
                  <td className="px-4 py-3 text-sm text-tx-secondary" title={new Date(doc.created_at).toLocaleString()}>
                    {relativeTime(doc.created_at)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => handleDownload(doc.download_url, doc.filename)}
                        className="rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-white transition hover:bg-primary-hover"
                      >
                        Download
                      </button>
                      <button
                        onClick={() => handleDelete(doc.id, doc.filename)}
                        className="rounded-md px-2.5 py-1.5 text-xs font-medium text-danger transition hover:bg-danger-subtle"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
