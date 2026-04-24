"use client";
import { useEffect, useState } from "react";
import {
  traceApi, RecallDashboard, RECALL_STATUS_BG, SEVERITY_BG,
} from "@/lib/traceability";

function KPI({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${color || "text-gray-800"}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

export default function TraceabilityDashboardPage() {
  const [dash, setDash] = useState<RecallDashboard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    traceApi.getRecallDashboard().then(setDash).catch(console.error).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-8 text-gray-500">Loading traceability dashboard…</div>;
  if (!dash) return <div className="p-8 text-red-500">Failed to load</div>;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Lot Traceability + Recall Management</h1>
          <p className="text-sm text-gray-500 mt-0.5">Forward/backward traceability, genealogy, recall execution, regulatory reporting</p>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-5 gap-4">
        <KPI label="Total Recalls" value={dash.total_recalls} />
        <KPI label="Active" value={dash.active_recalls} color={dash.active_recalls > 0 ? "text-blue-700" : "text-gray-700"} />
        <KPI label="Critical" value={dash.critical_recalls} color={dash.critical_recalls > 0 ? "text-red-700" : "text-gray-700"} />
        <KPI label="Completed" value={dash.completed_recalls} color="text-green-700" />
        <KPI label="Pending Actions" value={dash.pending_actions} color={dash.pending_actions > 0 ? "text-amber-700" : "text-gray-700"} />
        <KPI label="Open Scope Lines" value={dash.open_scope_lines} />
        <KPI label="Avg Trace Time" value={dash.avg_time_to_trace_h ? `${parseFloat(dash.avg_time_to_trace_h).toFixed(1)}h` : "—"} />
        <KPI label="Avg Recovery %" value={dash.avg_recovery_pct ? `${parseFloat(dash.avg_recovery_pct).toFixed(1)}%` : "—"} />
      </div>

      {/* Recent Recalls */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
          <h2 className="font-semibold text-gray-800">Recent Recalls</h2>
          <a href="/dashboard/traceability/recalls" className="text-sm text-indigo-600 hover:underline">View all →</a>
        </div>
        {dash.recent_recalls.length === 0 ? (
          <p className="px-5 py-8 text-gray-400 text-sm">No recalls recorded</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                {["Recall #","Type","Severity","Status","Affected Qty","Recovery %","Initiated"].map(h => (
                  <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {dash.recent_recalls.map(r => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <a href={`/dashboard/traceability/recalls/${r.id}`} className="font-medium text-indigo-700 hover:underline">
                      {r.recall_no}
                    </a>
                  </td>
                  <td className="px-4 py-3 capitalize">{r.recall_type.replace("_"," ")}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs ${SEVERITY_BG[r.severity_level]}`}>{r.severity_level}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs ${RECALL_STATUS_BG[r.status]}`}>{r.status.replace("_"," ")}</span>
                  </td>
                  <td className="px-4 py-3">{r.total_affected_qty ? parseFloat(r.total_affected_qty).toLocaleString() : "—"}</td>
                  <td className="px-4 py-3">{r.recovery_pct ? `${parseFloat(r.recovery_pct).toFixed(1)}%` : "—"}</td>
                  <td className="px-4 py-3 text-gray-400">{new Date(r.initiation_datetime).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Quick Navigation */}
      <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-6 gap-3">
        {[
          { label: "Trace Search", href: "/dashboard/traceability/search", color: "border-indigo-200 hover:bg-indigo-50" },
          { label: "Backward Trace", href: "/dashboard/traceability/backward", color: "border-gray-200 hover:bg-gray-50" },
          { label: "Forward Trace", href: "/dashboard/traceability/forward", color: "border-green-200 hover:bg-green-50" },
          { label: "Genealogy Graph", href: "/dashboard/traceability/genealogy", color: "border-purple-200 hover:bg-purple-50" },
          { label: "Recall List", href: "/dashboard/traceability/recalls", color: "border-red-200 hover:bg-red-50" },
          { label: "Mock Recall Drill", href: "/dashboard/traceability/mock-recall", color: "border-amber-200 hover:bg-amber-50" },
          { label: "Regulatory Reports", href: "/dashboard/traceability/regulatory", color: "border-teal-200 hover:bg-teal-50" },
        ].map(n => (
          <a key={n.href} href={n.href}
            className={`block border rounded-xl p-3 text-center text-sm font-medium text-gray-700 ${n.color} transition-colors`}>
            {n.label}
          </a>
        ))}
      </div>
    </div>
  );
}
