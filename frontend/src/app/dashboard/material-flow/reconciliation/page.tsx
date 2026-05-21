"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { mfApi, Reconciliation } from "@/lib/materialFlow";

function VarianceBar({ pct }: { pct: number }) {
  const abs = Math.abs(pct);
  const color = abs > 10 ? "bg-red-500" : abs > 5 ? "bg-yellow-400" : "bg-green-500";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-100 rounded-full h-2">
        <div className={`h-2 rounded-full ${color}`} style={{ width: `${Math.min(abs * 5, 100)}%` }} />
      </div>
      <span className={`text-xs font-medium w-14 text-right ${abs > 10 ? "text-red-600" : abs > 5 ? "text-yellow-600" : "text-green-600"}`}>
        {pct > 0 ? "+" : ""}{pct.toFixed(2)}%
      </span>
    </div>
  );
}

export default function ReconciliationPage() {
  const qc = useQueryClient();
  const [orderId, setOrderId] = useState("");
  const [fetchedOrderId, setFetchedOrderId] = useState("");
  const [reason, setReason] = useState("");

  const { data: recon, isLoading } = useQuery<Reconciliation>({
    queryKey: ["mf-recon", fetchedOrderId],
    queryFn: () => mfApi.getReconciliation(fetchedOrderId),
    enabled: !!fetchedOrderId,
  });

  const close = useMutation({
    mutationFn: () => mfApi.closeReconciliation(fetchedOrderId, { variance_reason: reason }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mf-recon", fetchedOrderId] }),
  });

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <a href="/dashboard/material-flow" className="text-sm text-indigo-600 hover:underline">← Dashboard</a>
        <h1 className="text-xl font-bold text-gray-900">Batch Reconciliation</h1>
      </div>

      <div className="bg-white rounded-lg border p-5">
        <h2 className="font-semibold text-gray-800 mb-3">Load Production Order Reconciliation</h2>
        <div className="flex gap-3 items-end">
          <div className="flex-1 max-w-md">
            <label className="block text-xs font-medium text-gray-600 mb-1">Production Order ID</label>
            <input value={orderId} onChange={(e) => setOrderId(e.target.value)} className="w-full border rounded px-3 py-2 text-sm" placeholder="UUID" />
          </div>
          <button
            onClick={() => setFetchedOrderId(orderId)}
            disabled={!orderId}
            className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-indigo-700 disabled:opacity-50"
          >Load</button>
        </div>
      </div>

      {isLoading && <div className="text-sm text-gray-400">Computing reconciliation…</div>}

      {recon && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {[
              { label: "Total Issued", value: recon.total_issued, color: "text-blue-700" },
              { label: "Consumed", value: recon.total_consumed, color: "text-green-700" },
              { label: "Returned", value: recon.total_returned, color: "text-teal-700" },
              { label: "Scrapped", value: recon.total_scrapped, color: "text-orange-700" },
              { label: "Variance", value: recon.total_variance, color: Number(recon.total_variance) !== 0 ? "text-red-600" : "text-gray-700" },
            ].map((c) => (
              <div key={c.label} className="bg-white rounded-lg border p-3 text-center">
                <p className="text-xs text-gray-500">{c.label}</p>
                <p className={`text-xl font-bold ${c.color}`}>{Number(c.value).toLocaleString()}</p>
              </div>
            ))}
          </div>

          {/* Variance indicator */}
          {recon.variance_pct !== undefined && recon.variance_pct !== null && (
            <div className="bg-white rounded-lg border p-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-medium text-gray-700">Overall Variance</h3>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  recon.status === "CLOSED" ? "bg-green-100 text-green-700" :
                  recon.status === "OPEN" ? "bg-yellow-100 text-yellow-700" : "bg-blue-100 text-blue-700"
                }`}>{recon.status}</span>
              </div>
              <VarianceBar pct={Number(recon.variance_pct)} />
            </div>
          )}

          {/* Line detail */}
          {recon.lines.length > 0 && (
            <div className="bg-white rounded-lg border overflow-x-auto">
              <div className="px-4 py-3 border-b"><h2 className="font-semibold text-gray-900">Line Detail</h2></div>
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>{["#", "Material", "BOM Qty", "Issued", "Consumed", "Returned", "Scrapped", "Variance", "Var%", "UOM"].map((h) => (
                    <th key={h} className="px-3 py-2 text-left text-xs font-medium text-gray-600">{h}</th>
                  ))}</tr>
                </thead>
                <tbody className="divide-y">
                  {recon.lines.map((l) => (
                    <tr key={l.id} className="hover:bg-gray-50">
                      <td className="px-3 py-2 text-xs">{l.line_no}</td>
                      <td className="px-3 py-2 text-xs font-mono">{l.material_name || l.material_id?.slice(0, 8) || "—"}</td>
                      <td className="px-3 py-2 text-xs">{l.bom_quantity ? Number(l.bom_quantity).toLocaleString() : "—"}</td>
                      <td className="px-3 py-2 text-xs">{Number(l.issued_quantity).toLocaleString()}</td>
                      <td className="px-3 py-2 text-xs">{Number(l.consumed_quantity).toLocaleString()}</td>
                      <td className="px-3 py-2 text-xs">{Number(l.returned_quantity).toLocaleString()}</td>
                      <td className="px-3 py-2 text-xs">{Number(l.scrapped_quantity).toLocaleString()}</td>
                      <td className={`px-3 py-2 text-xs font-medium ${Number(l.variance_quantity) !== 0 ? "text-red-600" : "text-green-600"}`}>
                        {Number(l.variance_quantity) > 0 ? "+" : ""}{Number(l.variance_quantity).toLocaleString()}
                      </td>
                      <td className="px-3 py-2 text-xs">{l.variance_pct !== null && l.variance_pct !== undefined ? `${Number(l.variance_pct).toFixed(2)}%` : "—"}</td>
                      <td className="px-3 py-2 text-xs">{l.uom}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Close reconciliation */}
          {recon.status !== "CLOSED" && (
            <div className="bg-white rounded-lg border p-5 space-y-3">
              <h2 className="font-semibold text-gray-800">Close Reconciliation</h2>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Variance Reason (required if variance exists)</label>
                <textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={2} className="w-full border rounded px-3 py-2 text-sm" placeholder="Explain material variance…" />
              </div>
              <div className="flex justify-end">
                <button onClick={() => close.mutate()} disabled={close.isPending} className="bg-emerald-600 text-white px-5 py-2 rounded-lg text-sm hover:bg-emerald-700 disabled:opacity-50">
                  {close.isPending ? "Closing…" : "Close Reconciliation"}
                </button>
              </div>
            </div>
          )}

          {recon.status === "CLOSED" && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-sm text-green-700">
              Reconciliation closed on {recon.closed_at ? new Date(recon.closed_at).toLocaleString() : "—"}.
              {recon.variance_reason && <p className="mt-1 text-xs">Variance reason: {recon.variance_reason}</p>}
            </div>
          )}
        </>
      )}
    </div>
  );
}
