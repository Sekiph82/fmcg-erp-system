"use client";
// M47.S01.T011 report-builder datasets: upload a CSV (e.g. a distributor sell-out sheet), blend it with a catalog
// source by a key column, preview; the dataset then appears in the report builder as "<name> (dataset)".
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";

type Field = { path: string; label: string; type: string };
type Dataset = { id: string; name: string; columns: Field[]; row_count: number; join: { source: string; local: string; remote: string } | null; source_key: string };
type Catalog = Record<string, { label: string; fields: Field[] }>;
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : "Something went wrong."; };

export default function DatasetsPage() {
  const [list, setList] = useState<Dataset[]>([]);
  const [cat, setCat] = useState<Catalog>({});
  const [f, setF] = useState({ name: "", csv: "", join_source: "", join_local: "", join_remote: "" });
  const [preview, setPreview] = useState<{ columns: { path: string }[]; rows: Record<string, string | null>[]; total: number } | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const load = useCallback(() => apiClient.get("/api/v1/report-datasets").then((r) => setList(r.data)).catch((e) => setMsg(err(e))), []);
  useEffect(() => { load(); apiClient.get("/api/v1/reports-builder/catalog").then((r) => setCat(r.data)).catch(() => {}); }, [load]);
  const head = f.csv.split("\n")[0]?.split(",").map((h) => h.trim().toLowerCase().replace(/[^a-z0-9_]/g, "_").replace(/^_+|_+$/g, "")).filter(Boolean) ?? [];
  const sources = Object.entries(cat).filter(([k]) => !k.startsWith("ds:"));
  const create = () => apiClient.post("/api/v1/report-datasets", { name: f.name, csv: f.csv, ...(f.join_source ? { join_source: f.join_source, join_local: f.join_local, join_remote: f.join_remote } : {}) })
    .then(() => { setMsg("Dataset created — it is now a source in the report builder."); setF({ name: "", csv: "", join_source: "", join_local: "", join_remote: "" }); load(); }).catch((e) => setMsg(err(e)));
  return (
    <div className="p-4 space-y-3 text-sm">
      <h2 className="text-lg font-semibold">Report datasets</h2>
      <p className="text-xs text-gray-500">Upload a table (CSV, first row = column names, up to 20 000 rows) and optionally blend it with an ERP source by a shared column. Blended columns start with “src.”.</p>
      {msg && <p role="status" className="text-xs bg-amber-50 border rounded p-2">{msg}</p>}
      <section className="border rounded p-3 space-y-2 text-xs">
        <input aria-label="Dataset name" placeholder="Name, e.g. Distributor sell-out W47" className="border rounded px-1 w-full" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />
        <input aria-label="CSV file" type="file" accept=".csv,text/csv" onChange={(e) => e.target.files?.[0]?.text().then((t) => setF((x) => ({ ...x, csv: t })))} />
        <textarea aria-label="CSV text" rows={4} className="border rounded w-full font-mono" placeholder="customer_code,units,week" value={f.csv} onChange={(e) => setF({ ...f, csv: e.target.value })} />
        <div className="flex flex-wrap gap-2 items-center">Blend with
          <select aria-label="Source" className="border rounded" value={f.join_source} onChange={(e) => setF({ ...f, join_source: e.target.value, join_remote: "" })}>
            <option value="">(no blending)</option>{sources.map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}</select>
          {f.join_source && <>where dataset column
            <select aria-label="Dataset column" className="border rounded" value={f.join_local} onChange={(e) => setF({ ...f, join_local: e.target.value })}><option value="">…</option>{head.map((h) => <option key={h}>{h}</option>)}</select>
            equals
            <select aria-label="Source field" className="border rounded" value={f.join_remote} onChange={(e) => setF({ ...f, join_remote: e.target.value })}><option value="">…</option>{(cat[f.join_source]?.fields ?? []).map((x) => <option key={x.path} value={x.path}>{x.label}</option>)}</select></>}
          <button className="bg-indigo-600 text-white rounded px-3 py-1" onClick={create} disabled={!f.name || !f.csv}>Create dataset</button></div>
      </section>
      <ul className="divide-y border rounded">{list.length === 0 ? <li className="p-2 text-xs text-gray-500">No datasets yet.</li> : list.map((d) =>
        <li key={d.id} className="p-2 text-xs flex flex-wrap justify-between gap-2"><span><b>{d.name}</b> · {d.row_count} rows · {d.columns.length} columns{d.join ? ` · blended with ${cat[d.join.source]?.label ?? d.join.source} on ${d.join.local} = ${d.join.remote}` : ""}</span>
          <span className="flex gap-2"><button className="underline" onClick={() => apiClient.get(`/api/v1/report-datasets/${d.id}/preview`).then((r) => setPreview(r.data)).catch((e) => setMsg(err(e)))}>Preview</button>
            <button className="text-red-600" onClick={() => apiClient.delete(`/api/v1/report-datasets/${d.id}`).then(load).catch((e) => setMsg(err(e)))}>Delete</button></span></li>)}</ul>
      {preview && <div className="overflow-x-auto"><p className="text-xs">{preview.total} rows (first 50)</p><table className="text-xs border min-w-full"><thead><tr>{preview.columns.map((c) => <th key={c.path} className="p-1 border-b text-left">{c.path}</th>)}</tr></thead>
        <tbody>{preview.rows.map((r, i) => <tr key={i}>{preview.columns.map((c) => <td key={c.path} className="p-1 border-b">{r[c.path] ?? "—"}</td>)}</tr>)}</tbody></table></div>}
    </div>
  );
}
