"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { reportBuilderApi, Report, DataSource } from "@/lib/report_builder";

export default function SavedReportsPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [catalog, setCatalog] = useState<Record<string, DataSource>>({});
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState({ template: false, ds: "" });
  const [cloning, setCloning] = useState<string | null>(null);
  const [cloneForm, setCloneForm] = useState({ code: "", name: "" });

  const load = useCallback(() =>
    Promise.all([
      reportBuilderApi.listReports({ template_only: filter.template || undefined, data_source: filter.ds || undefined }),
      reportBuilderApi.getCatalog(),
    ]).then(([r, c]) => { setReports(r); setCatalog(c); }).finally(() => setLoading(false)), [filter]);

  useEffect(() => { load(); }, [load]);

  const del = async (id: string) => {
    if (!confirm("Archive this report?")) return;
    await reportBuilderApi.deleteReport(id);
    load();
  };

  const clone = async (id: string) => {
    if (!cloneForm.code || !cloneForm.name) { alert("Code and Name required"); return; }
    await reportBuilderApi.cloneReport(id, cloneForm.code, cloneForm.name);
    setCloning(null);
    setCloneForm({ code: "", name: "" });
    load();
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Saved Reports</h1>
        <div className="flex gap-2">
          <button onClick={() => reportBuilderApi.seedTemplates().then(() => load())}
            className="rounded border border-gray-300 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50">
            Seed Templates
          </button>
          <Link href="/dashboard/report-builder/builder"
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
            + New Report
          </Link>
        </div>
      </div>

      <div className="flex gap-3 flex-wrap">
        <select className="border rounded px-2 py-1 text-sm" value={filter.ds}
          onChange={(e) => setFilter({ ...filter, ds: e.target.value })}>
          <option value="">All Data Sources</option>
          {Object.entries(catalog).map(([k, ds]) => <option key={k} value={k}>{ds.label}</option>)}
        </select>
        <label className="flex items-center gap-2 text-sm text-gray-600">
          <input type="checkbox" checked={filter.template} onChange={(e) => setFilter({ ...filter, template: e.target.checked })} />
          Templates only
        </label>
        <span className="text-xs text-gray-400 self-center">{reports.length} reports</span>
      </div>

      {loading ? <p className="text-gray-500 text-sm">Loading…</p> : (
        <div className="bg-white border rounded-lg shadow-sm overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {["Code","Name","Data Source","Visibility","Fields","Runs","Last Run","Actions"].map(h=>(
                  <th key={h} className="px-3 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {reports.map(r => (
                <tr key={r.report_id} className="hover:bg-gray-50">
                  <td className="px-3 py-2 font-mono text-xs text-gray-400">{r.report_code}</td>
                  <td className="px-3 py-2">
                    <span className="font-medium text-gray-800">{r.report_name}</span>
                    {r.is_template && <span className="ml-2 rounded bg-blue-100 text-blue-700 px-1.5 py-0.5 text-xs">Template</span>}
                  </td>
                  <td className="px-3 py-2 text-gray-600">{catalog[r.data_source]?.label ?? r.data_source}</td>
                  <td className="px-3 py-2 capitalize text-gray-500">{r.visibility}</td>
                  <td className="px-3 py-2 text-center">{r.fields.length}</td>
                  <td className="px-3 py-2 text-center font-semibold">{r.run_count}</td>
                  <td className="px-3 py-2 text-gray-400 text-xs">{r.last_run_at ? new Date(r.last_run_at).toLocaleDateString() : "—"}</td>
                  <td className="px-3 py-2 flex gap-2">
                    <Link href={`/dashboard/report-builder/viewer?id=${r.report_id}`}
                      className="text-xs text-blue-600 hover:underline">Run</Link>
                    <button onClick={() => { setCloning(r.report_id); setCloneForm({ code: "", name: r.report_name + " Copy" }); }}
                      className="text-xs text-gray-600 hover:underline">Clone</button>
                    <a href={reportBuilderApi.getExportUrl(r.report_id)} download
                      className="text-xs text-green-600 hover:underline">CSV</a>
                    <button onClick={() => del(r.report_id)} className="text-xs text-red-500 hover:underline">Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {reports.length === 0 && <p className="text-center text-gray-400 py-8 text-sm">No reports. Build one or seed templates.</p>}
        </div>
      )}

      {cloning && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-sm p-6 space-y-3">
            <h2 className="font-bold text-gray-900">Clone Report</h2>
            <div><label className="text-xs text-gray-500">New Code</label>
              <input className="w-full border rounded px-2 py-1 text-sm mt-1" value={cloneForm.code}
                onChange={(e) => setCloneForm({ ...cloneForm, code: e.target.value })} /></div>
            <div><label className="text-xs text-gray-500">New Name</label>
              <input className="w-full border rounded px-2 py-1 text-sm mt-1" value={cloneForm.name}
                onChange={(e) => setCloneForm({ ...cloneForm, name: e.target.value })} /></div>
            <div className="flex gap-2">
              <button onClick={() => clone(cloning)} className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700">Clone</button>
              <button onClick={() => setCloning(null)} className="rounded border px-4 py-1.5 text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
