"use client";
import { useEffect, useState } from "react";
import {
  shelfLifeApi, FEFOComplianceReport, FEFOAuditLog, FEFOContext,
} from "@/lib/shelfLife";

const CONTEXT_LABEL: Record<FEFOContext, string> = {
  production_issue:  "Production Issue",
  warehouse_pick:    "Warehouse Pick",
  sales_shipment:    "Sales Shipment",
  internal_transfer: "Internal Transfer",
  line_side_issue:   "Line-Side Issue",
};

export default function FEFOCompliancePage() {
  const [report, setReport] = useState<FEFOComplianceReport | null>(null);
  const [auditLog, setAuditLog] = useState<FEFOAuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [tab, setTab] = useState<"report" | "log">("report");

  const loadReport = (from?: string, to?: string) => {
    setLoading(true);
    Promise.all([
      shelfLifeApi.getComplianceReport(from || undefined, to || undefined),
      shelfLifeApi.listAuditLog(200),
    ]).then(([r, l]) => { setReport(r); setAuditLog(l); })
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadReport(); }, []);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">FEFO Compliance Audit</h1>
          <p className="text-sm text-gray-500">Track FEFO override frequency, compliance %, and non-compliant picks</p>
        </div>
        <div className="flex gap-2 items-center">
          <input type="date" className="border rounded-lg px-3 py-2 text-sm"
            value={dateFrom} onChange={e => setDateFrom(e.target.value)} />
          <span className="text-gray-400 text-sm">to</span>
          <input type="date" className="border rounded-lg px-3 py-2 text-sm"
            value={dateTo} onChange={e => setDateTo(e.target.value)} />
          <button onClick={() => loadReport(dateFrom, dateTo)}
            className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">
            Apply Filter
          </button>
        </div>
      </div>

      {/* Overall Compliance */}
      {report && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-800">Overall FEFO Compliance</h2>
            <span className={`text-3xl font-bold ${parseFloat(report.overall_compliance_pct) >= 90 ? "text-green-700" : parseFloat(report.overall_compliance_pct) >= 70 ? "text-amber-700" : "text-red-700"}`}>
              {report.overall_compliance_pct}%
            </span>
          </div>
          <div className="w-full h-4 bg-gray-200 rounded-full overflow-hidden">
            <div className={`h-full rounded-full ${parseFloat(report.overall_compliance_pct) >= 90 ? "bg-green-500" : parseFloat(report.overall_compliance_pct) >= 70 ? "bg-amber-500" : "bg-red-500"}`}
              style={{ width: `${report.overall_compliance_pct}%` }} />
          </div>
          <p className="text-xs text-gray-500 mt-2 text-right">Target: 95%</p>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
        {(["report","log"] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded text-sm font-medium ${tab === t ? "bg-white shadow text-gray-800" : "text-gray-500"}`}>
            {t === "report" ? "By Warehouse" : "Audit Log"}
          </button>
        ))}
      </div>

      {tab === "report" && report && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                {["Warehouse","Total Picks","Compliant","Non-Compliant","Compliance %","Overrides"].map(h => (
                  <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>
              ) : report.rows.length === 0 ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No picks recorded yet</td></tr>
              ) : report.rows.map((row, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs">{row.warehouse_id ? row.warehouse_id.slice(0,8) : "Unknown"}…</td>
                  <td className="px-4 py-3">{row.total_picks}</td>
                  <td className="px-4 py-3 text-green-700 font-medium">{row.compliant_picks}</td>
                  <td className="px-4 py-3 text-red-700 font-medium">{row.non_compliant_picks}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-20 h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div className={`h-full rounded-full ${parseFloat(row.compliance_pct) >= 90 ? "bg-green-500" : "bg-amber-500"}`}
                          style={{ width: `${row.compliance_pct}%` }} />
                      </div>
                      <span className="font-semibold">{row.compliance_pct}%</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">{row.override_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "log" && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                {["Date","Context","FEFO Compliant","Rec. Expiry","Actual Expiry","Override Reason","Qty"].map(h => (
                  <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {auditLog.length === 0 ? (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No audit log entries</td></tr>
              ) : auditLog.map(l => (
                <tr key={l.id} className={`hover:bg-gray-50 ${!l.is_fefo_compliant ? "bg-red-50" : ""}`}>
                  <td className="px-4 py-3 text-xs text-gray-400">{new Date(l.created_at).toLocaleDateString()}</td>
                  <td className="px-4 py-3">{CONTEXT_LABEL[l.context] || l.context}</td>
                  <td className="px-4 py-3">
                    {l.is_fefo_compliant
                      ? <span className="text-green-700 font-medium">✓ Yes</span>
                      : <span className="text-red-700 font-medium">✗ No</span>}
                  </td>
                  <td className="px-4 py-3 text-xs font-mono">{l.recommended_expiry || "—"}</td>
                  <td className="px-4 py-3 text-xs font-mono">{l.actual_expiry || "—"}</td>
                  <td className="px-4 py-3 text-xs text-gray-500 max-w-xs truncate">{l.override_reason || "—"}</td>
                  <td className="px-4 py-3">{l.quantity || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
