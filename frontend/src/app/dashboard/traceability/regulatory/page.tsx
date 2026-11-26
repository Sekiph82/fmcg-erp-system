"use client";
import { useSearchParams } from "next/navigation";
import { useState, useEffect, Suspense } from "react";
import { traceApi, RecallRegulatoryReport, RecallHeader, SEVERITY_BG } from "@/lib/traceability";
import { tx } from "@/lib/i18n/core";

function RegulatoryContent() {
  const params = useSearchParams();
  const initialRecallId = params.get("recall_id") || "";
  const [recallId, setRecallId] = useState(initialRecallId);
  const [recalls, setRecalls] = useState<RecallHeader[]>([]);
  const [report, setReport] = useState<RecallRegulatoryReport | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    traceApi.listRecalls().then(setRecalls).catch(console.error);
    if (initialRecallId) handleLoad(initialRecallId);
  }, []);

  const handleLoad = async (id?: string) => {
    const rid = id || recallId;
    if (!rid) return;
    setLoading(true);
    setReport(null);
    try {
      const r = await traceApi.getRegulatoryReport(rid);
      setReport(r);
    } catch (e: any) { alert(e.message); }
    finally { setLoading(false); }
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">{tx("Regulatory Report Export")}</h1>
        <p className="text-sm text-gray-500">{tx("Generate regulator-ready recall summary for authorities, audits, and customer communications")}</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-5 flex gap-3">
        <div className="flex-1">
          <label className="text-xs font-medium text-gray-600">{tx("Select Recall")}</label>
          <select className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
            value={recallId} onChange={e => setRecallId(e.target.value)}>
            <option value="">{tx("— Select a recall —")}</option>
            {recalls.map(r => (
              <option key={r.id} value={r.id}>{r.recall_no} — {r.recall_type} — {r.status}</option>
            ))}
          </select>
        </div>
        <div className="flex items-end">
          <button onClick={() => handleLoad()} disabled={!recallId || loading}
            className="px-5 py-2 bg-teal-600 text-white text-sm rounded-lg hover:bg-teal-700 disabled:opacity-50">
            {loading ? tx("Loading…") : tx("Generate Report")}
          </button>
        </div>
      </div>

      {report && (
        <div className="space-y-5">
          {/* Report Header */}
          <div className="bg-white rounded-xl border border-teal-200 p-6">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">{tx("RECALL NOTICE")}</h2>
                <p className="text-sm text-gray-500 mt-0.5">{tx("Reference:")} {report.recall_no}</p>
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
                [tx("Recall Type"), report.recall_type.replace("_"," ")],
                [tx("Trigger"), report.trigger_source.replace("_"," ")],
                [tx("Status"), report.status.replace("_"," ")],
                [tx("Source Lot"), report.source_lot_number || "Multiple"],
                [tx("Markets"), report.affected_markets],
                [tx("Lots Affected"), report.affected_lots.length],
              ].map(([k, v]) => (
                <div key={k} className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500 uppercase">{k}</p>
                  <p className="text-sm font-semibold text-gray-800 mt-0.5 capitalize">{String(v)}</p>
                </div>
              ))}
            </div>

            {/* Narrative */}
            <div className="bg-teal-50 border border-teal-200 rounded-lg p-4">
              <p className="text-xs font-semibold text-teal-700 uppercase mb-2">{tx("Executive Summary")}</p>
              <p className="text-sm text-gray-800 leading-relaxed">{report.summary_narrative}</p>
            </div>
          </div>

          {/* Recall Reason */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="font-semibold text-gray-800 mb-2">{tx("Recall Reason")}</h3>
            <p className="text-sm text-gray-700">{report.recall_reason}</p>
          </div>

          {/* Quantity & Customer Data */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: tx("Total Affected Qty"), value: report.total_affected_qty ? Number(report.total_affected_qty).toLocaleString() : "—" },
              { label: tx("Customers Affected"), value: report.total_affected_customers ?? "—" },
              { label: tx("Recovery Rate"), value: report.recovery_pct ? `${parseFloat(report.recovery_pct).toFixed(1)}%` : "—" },
              { label: tx("Lots in Scope"), value: report.affected_lots.length },
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
              <h3 className="font-semibold text-gray-800 mb-3">{tx("Affected Lot/Batch Numbers")}</h3>
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
              <h3 className="font-semibold text-gray-800 mb-3">{tx("Actions Taken")}</h3>
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
            <h3 className="font-semibold text-gray-800 mb-3">{tx("Performance Metrics")}</h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-500">{tx("Time to Trace")}</p>
                <p className="text-lg font-bold text-gray-800">
                  {report.time_to_trace_hours ? `${parseFloat(report.time_to_trace_hours).toFixed(2)}h` : "—"}
                </p>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-500">{tx("Time to Contain")}</p>
                <p className="text-lg font-bold text-gray-800">
                  {report.time_to_contain_hours ? `${parseFloat(report.time_to_contain_hours).toFixed(2)}h` : "—"}
                </p>
              </div>
            </div>
          </div>

          <button
            onClick={() => window.print()}
            className="px-6 py-2 bg-teal-600 text-white text-sm rounded-lg hover:bg-teal-700">
            {tx("Print / Export Report")}
          </button>
        </div>
      )}
    </div>
  );
}

export default function RegulatoryPage() {
  return <Suspense fallback={<div className="p-8 text-gray-400">{tx("Loading…")}</div>}><RegulatoryContent /></Suspense>;
}
