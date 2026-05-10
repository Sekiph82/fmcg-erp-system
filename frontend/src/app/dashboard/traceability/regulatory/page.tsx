"use client";
import { useSearchParams } from "next/navigation";
import { useCallback, useState, useEffect, Suspense } from "react";
import { traceApi, RecallRegulatoryReport, RecallHeader, SEVERITY_BG } from "@/lib/traceability";

function RegulatoryContent() {
  const params = useSearchParams();
  const initialRecallId = params.get("recall_id") || "";
  const [recallId, setRecallId] = useState(initialRecallId);
  const [recalls, setRecalls] = useState<RecallHeader[]>([]);
  const [report, setReport] = useState<RecallRegulatoryReport | null>(null);
  const [loading, setLoading] = useState(false);

  const handleLoad = useCallback(async (rid: string) => {
    if (!rid) return;
    setLoading(true);
    setReport(null);
    try {
      const r = await traceApi.getRegulatoryReport(rid);
      setReport(r);
    } catch (e: any) { alert(e.message); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    traceApi.listRecalls().then(setRecalls).catch(console.error);
    if (initialRecallId) handleLoad(initialRecallId);
  }, [initialRecallId, handleLoad]);

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Regulatory Report Export</h1>
        <p className="text-sm text-gray-500">Generate regulator-ready recall summary for authorities, audits, and customer communications</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-5 flex gap-3">
        <div className="flex-1">
          <label className="text-xs font-medium text-gray-600">Select Recall</label>
          <select className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
            value={recallId} onChange={e => setRecallId(e.target.value)}>
            <option value="">— Select a recall —</option>
            {recalls.map(r => (
              <option key={r.id} value={r.id}>{r.recall_no} — {r.recall_type} — {r.status}</option>
            ))}
          </select>
        </div>
        <div className="flex items-end">
          <button onClick={() => handleLoad(recallId)} disabled={!recallId || loading}
            className="px-5 py-2 bg-teal-600 text-white text-sm rounded-lg hover:bg-teal-700 disabled:opacity-50">
            {loading ? "Loading…" : "Generate Report"}
          </button>
        </div>
      </div>

      {report && (
        <div className="space-y-5">
          {/* Report Header */}
          <div className="bg-white rounded-xl border border-teal-200 p-6">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">RECALL NOTICE</h2>
                <p className="text-sm text-gray-500 mt-0.5">Reference: {report.recall_no}</p>
              </div>
              <div className="text-right">
                <span className={`px-3 py-1 rounded text-sm font-semibold ${SEVERITY_BG[report.severity_level]}`}>
                  {report.severity_level.toUpperCase()} SEVERITY
                </span>
                <p className="text-xs text-gray-400 mt-1">{new Date(report.initiation_datetime).toLocaleString()}</p>
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-5">
              {[
                ["Recall Type", report.recall_type.replace("_"," ")],
                ["Trigger", report.trigger_source.replace("_"," ")],
                ["Status", report.status.replace("_"," ")],
                ["Source Lot", report.source_lot_number || "Multiple"],
                ["Markets", report.affected_markets],
                ["Lots Affected", report.affected_lots.length],
              ].map(([k, v]) => (
                <div key={k} className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500 uppercase">{k}</p>
                  <p className="text-sm font-semibold text-gray-800 mt-0.5 capitalize">{String(v)}</p>
                </div>
              ))}
            </div>

            {/* Narrative */}
            <div className="bg-teal-50 border border-teal-200 rounded-lg p-4">
              <p className="text-xs font-semibold text-teal-700 uppercase mb-2">Executive Summary</p>
              <p className="text-sm text-gray-800 leading-relaxed">{report.summary_narrative}</p>
            </div>
          </div>

          {/* Recall Reason */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="font-semibold text-gray-800 mb-2">Recall Reason</h3>
            <p className="text-sm text-gray-700">{report.recall_reason}</p>
          </div>

          {/* Quantity & Customer Data */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: "Total Affected Qty", value: report.total_affected_qty ? parseFloat(report.total_affected_qty).toLocaleString() : "—" },
              { label: "Customers Affected", value: report.total_affected_customers ?? "—" },
              { label: "Recovery Rate", value: report.recovery_pct ? `${parseFloat(report.recovery_pct).toFixed(1)}%` : "—" },
              { label: "Lots in Scope", value: report.affected_lots.length },
            ].map(s => (
              <div key={s.label} className="bg-white rounded-xl border border-gray-200 p-4 text-center">
                <p className="text-2xl font-bold text-gray-800">{s.value}</p>
                <p className="text-xs text-gray-500">{s.label}</p>
              </div>
            ))}
          </div>

          {/* Affected Lots */}
          {report.affected_lots.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-800 mb-3">Affected Lot/Batch Numbers</h3>
              <div className="flex flex-wrap gap-2">
                {report.affected_lots.map((lot, i) => (
                  <span key={i} className="px-3 py-1.5 bg-red-50 border border-red-200 rounded-lg text-xs font-mono text-red-700">
                    {lot}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Actions Taken */}
          {report.actions_taken.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-800 mb-3">Actions Taken</h3>
              <ul className="space-y-1">
                {report.actions_taken.map((a, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                    <span className="text-teal-600 mt-0.5">✓</span><span>{a}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Metrics */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="font-semibold text-gray-800 mb-3">Performance Metrics</h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-500">Time to Trace</p>
                <p className="text-lg font-bold text-gray-800">
                  {report.time_to_trace_hours ? `${parseFloat(report.time_to_trace_hours).toFixed(2)}h` : "—"}
                </p>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-500">Time to Contain</p>
                <p className="text-lg font-bold text-gray-800">
                  {report.time_to_contain_hours ? `${parseFloat(report.time_to_contain_hours).toFixed(2)}h` : "—"}
                </p>
              </div>
            </div>
          </div>

          <button
            onClick={() => window.print()}
            className="px-6 py-2 bg-teal-600 text-white text-sm rounded-lg hover:bg-teal-700">
            Print / Export Report
          </button>
        </div>
      )}
    </div>
  );
}

export default function RegulatoryPage() {
  return <Suspense fallback={<div className="p-8 text-gray-400">Loading…</div>}><RegulatoryContent /></Suspense>;
}
