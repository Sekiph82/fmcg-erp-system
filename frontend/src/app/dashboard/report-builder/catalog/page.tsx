"use client";
import { useEffect, useState } from "react";
import { reportBuilderApi, DataSource } from "@/lib/report_builder";

const TYPE_COLOR: Record<string, string> = {
  string: "bg-blue-100 text-blue-700",
  number: "bg-green-100 text-green-700",
  date: "bg-orange-100 text-orange-700",
  boolean: "bg-purple-100 text-purple-700",
  datetime: "bg-indigo-100 text-indigo-700",
};

const MODULE_COLOR: Record<string, string> = {
  sales: "bg-blue-50 border-blue-200",
  procurement: "bg-orange-50 border-orange-200",
  inventory: "bg-green-50 border-green-200",
  expenses: "bg-red-50 border-red-200",
  timesheets: "bg-yellow-50 border-yellow-200",
  appraisals: "bg-purple-50 border-purple-200",
  crm: "bg-teal-50 border-teal-200",
  kanban: "bg-indigo-50 border-indigo-200",
  training: "bg-pink-50 border-pink-200",
  notifications: "bg-gray-50 border-gray-200",
};

export default function DataCatalogPage() {
  const [catalog, setCatalog] = useState<Record<string, DataSource>>({});
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const [preview, setPreview] = useState<{ columns: unknown[]; rows: unknown[]; total: number } | null>(null);
  const [previewing, setPreviewing] = useState(false);

  useEffect(() => {
    reportBuilderApi.getCatalog().then(setCatalog).finally(() => setLoading(false));
  }, []);

  const runPreview = async (dsKey: string) => {
    setPreviewing(true);
    setPreview(null);
    try {
      const result = await reportBuilderApi.preview(dsKey, 5);
      setPreview(result);
    } catch {
      setPreview(null);
    } finally {
      setPreviewing(false);
    }
  };

  const filtered = Object.entries(catalog).filter(([key, ds]) =>
    !search || ds.label.toLowerCase().includes(search.toLowerCase()) ||
    ds.module.toLowerCase().includes(search.toLowerCase()) ||
    ds.fields.some(f => f.label.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-bold text-gray-900">Data Catalog</h1>
      <p className="text-sm text-gray-500">Browse available data sources and their fields. Click a source to preview data.</p>

      <input className="w-full border rounded px-3 py-2 text-sm max-w-sm" placeholder="Search data sources or fields…"
        value={search} onChange={(e) => setSearch(e.target.value)} />

      {loading ? <p className="text-gray-500 text-sm">Loading…</p> : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map(([key, ds]) => (
            <div key={key} className={`border rounded-lg p-4 shadow-sm cursor-pointer hover:shadow-md transition-shadow ${MODULE_COLOR[ds.module] ?? "bg-white border-gray-200"} ${selected === key ? "ring-2 ring-blue-500" : ""}`}
              onClick={() => { setSelected(key === selected ? null : key); if (key !== selected) runPreview(key); }}>
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-semibold text-gray-800">{ds.label}</p>
                  <p className="text-xs text-gray-500 capitalize mt-0.5">{ds.module} module · {ds.field_count} fields</p>
                </div>
                <span className="text-xs font-mono text-gray-400">{key}</span>
              </div>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {ds.fields.map(f => (
                  <span key={f.path} className="flex items-center gap-1 text-xs">
                    <span className="text-gray-700">{f.label}</span>
                    <span className={`rounded px-1 ${TYPE_COLOR[f.type] ?? "bg-gray-100 text-gray-500"}`}>{f.type}</span>
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {selected && (
        <div className="bg-white border rounded-lg p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">
            Preview: {catalog[selected]?.label}
            {previewing && <span className="ml-2 text-gray-400 text-xs">Loading…</span>}
          </h2>
          {preview && (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    {(preview.columns as { path: string }[]).map(c => (
                      <th key={c.path} className="px-3 py-1.5 text-left font-semibold text-gray-600">{c.path}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {(preview.rows as Record<string, string | null>[]).map((row, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      {(preview.columns as { path: string }[]).map(c => (
                        <td key={c.path} className="px-3 py-1.5 text-gray-600 max-w-[150px] truncate">{row[c.path] ?? "—"}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="text-xs text-gray-400 mt-2">Total: {preview.total.toLocaleString()} rows · Showing 5</p>
            </div>
          )}
          {!previewing && !preview && <p className="text-gray-400 text-xs">No preview available.</p>}
        </div>
      )}
    </div>
  );
}
