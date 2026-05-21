"use client";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { reportBuilderApi, Report, RunResult } from "@/lib/report_builder";

export default function ReportViewerPage() {
  const searchParams = useSearchParams();
  const reportId = searchParams.get("id");
  const [reports, setReports] = useState<Report[]>([]);
  const [selectedId, setSelectedId] = useState(reportId ?? "");
  const [report, setReport] = useState<Report | null>(null);
  const [result, setResult] = useState<RunResult | null>(null);
  const [running, setRunning] = useState(false);
  const [limit, setLimit] = useState(50);
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState("");

  useEffect(() => { reportBuilderApi.listReports().then(setReports); }, []);

  useEffect(() => {
    if (!selectedId) return;
    reportBuilderApi.getReport(selectedId).then(setReport);
  }, [selectedId]);

  useEffect(() => {
    if (reportId && reportId !== selectedId) setSelectedId(reportId);
  }, [reportId]);

  const run = async () => {
    if (!selectedId) return;
    setRunning(true);
    setError("");
    try {
      const r = await reportBuilderApi.runReport(selectedId, { limit, offset });
      setResult(r);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error running report");
    } finally {
      setRunning(false);
    }
  };

  useEffect(() => {
    if (selectedId) run();
  }, [selectedId]);

  const exportCsv = () => {
    if (!selectedId) return;
    window.open(reportBuilderApi.getExportUrl(selectedId), "_blank");
  };

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-bold text-gray-900">Report Viewer</h1>

      <div className="flex gap-3 items-end flex-wrap">
        <div>
          <label className="text-xs text-gray-500">Report</label>
          <select className="block border rounded px-2 py-1 text-sm mt-1 w-64" value={selectedId}
            onChange={(e) => setSelectedId(e.target.value)}>
            <option value="">Select report…</option>
            {reports.map(r => <option key={r.report_id} value={r.report_id}>{r.report_name}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-500">Page Size</label>
          <select className="block border rounded px-2 py-1 text-sm mt-1" value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}>
            {[25,50,100,250].map(v => <option key={v} value={v}>{v}</option>)}
          </select>
        </div>
        <button onClick={run} disabled={running || !selectedId}
          className="rounded bg-blue-600 px-5 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
          {running ? "Running…" : "Run"}
        </button>
        <button onClick={exportCsv} disabled={!selectedId}
          className="rounded border border-green-200 px-4 py-2 text-sm text-green-700 hover:bg-green-50 disabled:opacity-50">
          Export CSV
        </button>
      </div>

      {error && <div className="bg-red-50 border border-red-200 text-red-700 rounded p-3 text-sm">{error}</div>}

      {result && (
        <div className="space-y-3">
          <div className="flex items-center gap-4 text-xs text-gray-500">
            <span>Total: <strong>{result.total_count.toLocaleString()}</strong> rows</span>
            <span>Showing: <strong>{result.rows.length}</strong></span>
            <span>Executed in: <strong>{result.execution_ms}ms</strong></span>
            <span>Source: <strong>{result.data_source}</strong></span>
          </div>

          {report && (
            <div className="flex gap-2 text-xs text-gray-400 flex-wrap">
              {report.fields.map(f => (
                <span key={f.report_field_id} className="bg-gray-100 rounded px-2 py-0.5">
                  {f.alias || f.field_path}
                  {f.aggregation !== "none" && <span className="ml-1 text-blue-600">({f.aggregation})</span>}
                  {f.is_group_by && <span className="ml-1 text-green-600">GROUP</span>}
                </span>
              ))}
            </div>
          )}

          <div className="bg-white border rounded-lg shadow-sm overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b sticky top-0">
                <tr>
                  {result.columns.map(c => (
                    <th key={c.path} className="px-3 py-2 text-left text-xs font-semibold text-gray-600 whitespace-nowrap">
                      {c.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y">
                {result.rows.map((row, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    {result.columns.map(c => (
                      <td key={c.path} className="px-3 py-2 text-gray-700 max-w-[200px] truncate whitespace-nowrap">
                        {row[c.path] ?? <span className="text-gray-300">null</span>}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {result.rows.length === 0 && <p className="text-center text-gray-400 py-8 text-sm">No data returned.</p>}
          </div>

          {result.total_count > limit && (
            <div className="flex items-center gap-3">
              <button disabled={offset === 0} onClick={() => { setOffset(Math.max(0, offset - limit)); run(); }}
                className="rounded border px-3 py-1 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-40">← Prev</button>
              <span className="text-sm text-gray-500">Page {result.page} · {result.total_count.toLocaleString()} total</span>
              <button disabled={offset + limit >= result.total_count} onClick={() => { setOffset(offset + limit); run(); }}
                className="rounded border px-3 py-1 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-40">Next →</button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
