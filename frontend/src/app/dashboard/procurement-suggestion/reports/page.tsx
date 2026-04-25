"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { psApi, ShortageReportRow, fmt } from "@/lib/procurement_suggestion";

const URGENCY_ORDER = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };

export default function PSReportsPage() {
  const [runId, setRunId] = useState("");
  const [activeRunId, setActiveRunId] = useState("");

  const { data: runs } = useQuery({
    queryKey: ["ps-runs-reports"],
    queryFn: () => psApi.listRuns(0, 20),
  });

  const { data: shortages, isLoading } = useQuery({
    queryKey: ["ps-shortage-report", activeRunId],
    queryFn: () => psApi.shortageReport(activeRunId),
    enabled: !!activeRunId,
  });

  const sorted = [...(shortages ?? [])].sort(
    (a, b) => (URGENCY_ORDER[a.urgency_level as keyof typeof URGENCY_ORDER] ?? 99) -
               (URGENCY_ORDER[b.urgency_level as keyof typeof URGENCY_ORDER] ?? 99)
  );

  const totalShortage = sorted.reduce((s, r) => s + Number(r.shortage_qty), 0);
  const totalCost     = sorted.reduce((s, r) => s + Number(r.estimated_cost ?? 0), 0);

  const urgencyColor = (u: string) => ({
    CRITICAL: "text-red-700 bg-red-50",
    HIGH:     "text-orange-700 bg-orange-50",
    MEDIUM:   "text-yellow-700 bg-yellow-50",
    LOW:      "text-green-700 bg-green-50",
  }[u] ?? "text-gray-600 bg-gray-50");

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-xl font-semibold text-gray-900">Procurement Reports</h1>
        <p className="text-sm text-gray-500">Shortage analysis · Cost projections · Risk summary</p>
      </div>

      {/* Run selector */}
      <div className="flex gap-3 items-end">
        <div className="flex-1">
          <label className="text-sm text-gray-600 block mb-1">Select Run</label>
          <select
            value={runId}
            onChange={(e) => setRunId(e.target.value)}
            className="w-full border rounded px-3 py-2 text-sm"
          >
            <option value="">— Select a run —</option>
            {(runs ?? []).filter((r) => r.status === "COMPLETED").map((r) => (
              <option key={r.id} value={r.id}>{r.run_no} ({r.suggestion_date})</option>
            ))}
          </select>
        </div>
        <button
          onClick={() => setActiveRunId(runId)}
          disabled={!runId}
          className="px-4 py-2 border rounded text-sm hover:bg-gray-50 disabled:opacity-50"
        >
          Load Report
        </button>
      </div>

      {isLoading && <div className="text-gray-400">Loading shortage report…</div>}

      {activeRunId && !isLoading && sorted.length === 0 && (
        <div className="text-center py-12 text-gray-400">No shortages found in this run.</div>
      )}

      {activeRunId && !isLoading && sorted.length > 0 && (
        <>
          {/* Summary */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-white border rounded-lg p-4">
              <p className="text-xs text-gray-500 uppercase">Total Items in Shortage</p>
              <p className="text-2xl font-bold mt-1">{sorted.length}</p>
            </div>
            <div className="bg-white border border-red-200 rounded-lg p-4">
              <p className="text-xs text-gray-500 uppercase">Critical</p>
              <p className="text-2xl font-bold text-red-600 mt-1">
                {sorted.filter((r) => r.urgency_level === "CRITICAL").length}
              </p>
            </div>
            <div className="bg-white border rounded-lg p-4">
              <p className="text-xs text-gray-500 uppercase">Risk Flagged</p>
              <p className="text-2xl font-bold text-orange-600 mt-1">
                {sorted.filter((r) => r.risk_flag).length}
              </p>
            </div>
            <div className="bg-white border rounded-lg p-4">
              <p className="text-xs text-gray-500 uppercase">Est. Procurement Cost</p>
              <p className="text-2xl font-bold mt-1">KES {fmt(totalCost, 0)}</p>
            </div>
          </div>

          {/* Shortage table */}
          <div className="bg-white border border-gray-200 rounded-lg overflow-x-auto">
            <div className="px-4 py-3 border-b border-gray-100">
              <h2 className="font-semibold text-gray-700 text-sm">Shortage Report</h2>
            </div>
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                <tr>
                  <th className="text-left px-4 py-2">Material</th>
                  <th className="text-left px-4 py-2">UOM</th>
                  <th className="text-right px-4 py-2">Available</th>
                  <th className="text-right px-4 py-2">Required</th>
                  <th className="text-right px-4 py-2">Shortage</th>
                  <th className="text-right px-4 py-2">Safety Stock</th>
                  <th className="text-left px-4 py-2">Urgency</th>
                  <th className="text-left px-4 py-2">Order Date</th>
                  <th className="text-left px-4 py-2">Req. Date</th>
                  <th className="text-left px-4 py-2">Supplier</th>
                  <th className="text-right px-4 py-2">Est. Cost</th>
                  <th className="text-left px-4 py-2">Risk</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((r) => (
                  <tr key={r.material_id} className="border-t border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-2">
                      <p className="font-medium">{r.material_name}</p>
                      <p className="text-xs font-mono text-gray-400">{r.material_code}</p>
                    </td>
                    <td className="px-4 py-2 text-gray-500">{r.uom ?? "—"}</td>
                    <td className="px-4 py-2 text-right">{fmt(r.available_qty)}</td>
                    <td className="px-4 py-2 text-right">{fmt(r.required_qty)}</td>
                    <td className="px-4 py-2 text-right font-bold text-red-600">{fmt(r.shortage_qty)}</td>
                    <td className="px-4 py-2 text-right text-gray-500">{fmt(r.safety_stock_qty)}</td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-0.5 rounded text-xs font-semibold ${urgencyColor(r.urgency_level)}`}>
                        {r.urgency_level}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-xs">{r.suggested_order_date ?? "—"}</td>
                    <td className="px-4 py-2 text-xs">{r.required_date ?? "—"}</td>
                    <td className="px-4 py-2 text-xs">{r.supplier_name ?? <span className="text-red-500">No supplier!</span>}</td>
                    <td className="px-4 py-2 text-right text-xs">
                      {r.estimated_cost ? `KES ${fmt(r.estimated_cost, 0)}` : "—"}
                    </td>
                    <td className="px-4 py-2 text-xs">
                      {r.risk_flag && <span className="text-orange-500">⚠ Risk</span>}
                    </td>
                  </tr>
                ))}
                {/* Totals */}
                <tr className="border-t-2 border-gray-300 bg-gray-50 font-semibold">
                  <td className="px-4 py-2" colSpan={4}>TOTAL ({sorted.length} items)</td>
                  <td className="px-4 py-2 text-right text-red-600">{fmt(totalShortage)}</td>
                  <td colSpan={5} />
                  <td className="px-4 py-2 text-right">KES {fmt(totalCost, 0)}</td>
                  <td />
                </tr>
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
