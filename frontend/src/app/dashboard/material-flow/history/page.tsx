"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { mfApi, FlowTransaction, FlowType, FLOW_TYPE_LABELS, FLOW_STATUS_COLORS } from "@/lib/materialFlow";

export default function FlowHistoryPage() {
  const [orderId, setOrderId] = useState("");
  const [flowType, setFlowType] = useState<FlowType | "">("");
  const [selected, setSelected] = useState<FlowTransaction | null>(null);

  const { data, isLoading } = useQuery<FlowTransaction[]>({
    queryKey: ["mf-history", orderId, flowType],
    queryFn: () =>
      mfApi.getHistory({
        ...(orderId ? { production_order_id: orderId } : {}),
        ...(flowType ? { flow_type: flowType } : {}),
      }),
  });

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <a href="/dashboard/material-flow" className="text-sm text-indigo-600 hover:underline">← Dashboard</a>
        <h1 className="text-xl font-bold text-gray-900">Material Flow History</h1>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg border p-4 flex flex-wrap gap-4">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Production Order ID</label>
          <input value={orderId} onChange={(e) => setOrderId(e.target.value)} className="border rounded px-3 py-2 text-sm w-64" placeholder="Filter by order UUID" />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Flow Type</label>
          <select value={flowType} onChange={(e) => setFlowType(e.target.value as FlowType)} className="border rounded px-3 py-2 text-sm">
            <option value="">All Types</option>
            {Object.entries(FLOW_TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
      </div>

      {/* History Table */}
      <div className="bg-white rounded-lg border overflow-x-auto">
        <div className="px-4 py-3 border-b flex items-center justify-between">
          <h2 className="font-semibold text-gray-900">Transactions ({data?.length || 0})</h2>
        </div>
        {isLoading && <div className="p-6 text-gray-400 text-sm">Loading…</div>}
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>{["Flow No", "Type", "Mode", "Production Order", "Date/Time", "Lines", "Status", ""].map((h) => (
              <th key={h} className="px-4 py-2 text-left text-xs font-medium text-gray-600">{h}</th>
            ))}</tr>
          </thead>
          <tbody className="divide-y">
            {(data || []).map((t) => (
              <tr key={t.id} className="hover:bg-gray-50">
                <td className="px-4 py-2.5 font-mono text-xs">{t.flow_no}</td>
                <td className="px-4 py-2.5 text-xs">{FLOW_TYPE_LABELS[t.flow_type]}</td>
                <td className="px-4 py-2.5 text-xs">{t.flow_mode.replace("_", " ")}</td>
                <td className="px-4 py-2.5 font-mono text-xs">{t.production_order_id?.slice(0, 8) || "—"}</td>
                <td className="px-4 py-2.5 text-xs">{new Date(t.transaction_datetime).toLocaleString()}</td>
                <td className="px-4 py-2.5 text-xs">{t.lines.length}</td>
                <td className="px-4 py-2.5">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${FLOW_STATUS_COLORS[t.status] || ""}`}>{t.status}</span>
                </td>
                <td className="px-4 py-2.5">
                  <button onClick={() => setSelected(selected?.id === t.id ? null : t)} className="text-xs text-indigo-600 hover:underline">
                    {selected?.id === t.id ? "Hide" : "Lines"}
                  </button>
                </td>
              </tr>
            ))}
            {!isLoading && !(data?.length) && (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400 text-sm">No flow transactions found.</td></tr>
            )}
          </tbody>
        </table>

        {/* Inline line detail */}
        {selected && (
          <div className="border-t bg-gray-50 p-4">
            <h3 className="text-sm font-semibold text-gray-800 mb-2">Lines — {selected.flow_no}</h3>
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-white">
                  {["#", "Item", "Lot", "Qty", "UOM", "Src Stage", "Dst Stage", "Quality", "Flags"].map((h) => (
                    <th key={h} className="px-2 py-1.5 text-left font-medium text-gray-600 border">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {selected.lines.map((l) => (
                  <tr key={l.id}>
                    <td className="px-2 py-1 border">{l.line_no}</td>
                    <td className="px-2 py-1 border font-mono">{l.material_name || l.product_name || l.material_id?.slice(0, 6) || "—"}</td>
                    <td className="px-2 py-1 border font-mono">{l.lot_number || l.lot_id?.slice(0, 6) || "—"}</td>
                    <td className="px-2 py-1 border">{Number(l.quantity).toLocaleString()}</td>
                    <td className="px-2 py-1 border">{l.uom}</td>
                    <td className="px-2 py-1 border">{l.source_stage_name || "—"}</td>
                    <td className="px-2 py-1 border">{l.destination_stage_name || "—"}</td>
                    <td className="px-2 py-1 border">{l.quality_status}</td>
                    <td className="px-2 py-1 border">
                      {[l.issue_flag && "ISSUE", l.return_flag && "RETURN", l.scrap_flag && "SCRAP"].filter(Boolean).join(" | ") || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
