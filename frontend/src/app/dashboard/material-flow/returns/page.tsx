"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { mfApi, FlowTransaction, FLOW_STATUS_COLORS } from "@/lib/materialFlow";

export default function ReturnsPage() {
  const qc = useQueryClient();
  const [mode, setMode] = useState<"RETURN" | "REVERSAL">("RETURN");
  const [form, setForm] = useState({
    production_order_id: "",
    item_type: "material",
    material_id: "",
    lot_id: "",
    quantity: "",
    uom: "KG",
    return_reason: "RETURN_UNUSED",
    destination: "original",
    notes: "",
  });
  const [successMsg, setSuccessMsg] = useState("");
  const [reversalId, setReversalId] = useState("");

  const { data: txList } = useQuery<FlowTransaction[]>({
    queryKey: ["mf-transactions", "returns"],
    queryFn: () => mfApi.listTransactions({ flow_type: "RETURN" }).then((r) => r.data),
  });

  const create = useMutation({
    mutationFn: () =>
      mfApi.returnMaterials({
        flow_type: mode,
        production_order_id: form.production_order_id || undefined,
        notes: form.notes,
        lines: [{
          line_no: 1,
          item_type: form.item_type,
          material_id: form.material_id || undefined,
          lot_id: form.lot_id || undefined,
          quantity: parseFloat(form.quantity),
          uom: form.uom,
          movement_reason: form.return_reason as any,
          return_flag: true,
          quality_status: "QUARANTINE" as any,
        }],
      }),
    onSuccess: (r) => {
      setSuccessMsg(`Return transaction ${r.data.flow_no} created.`);
      qc.invalidateQueries({ queryKey: ["mf-transactions", "returns"] });
      qc.invalidateQueries({ queryKey: ["mf-dashboard"] });
      setForm({ ...form, quantity: "", material_id: "", lot_id: "", notes: "" });
      setTimeout(() => setSuccessMsg(""), 4000);
    },
  });

  const reverse = useMutation({
    mutationFn: () => mfApi.reverseTransaction(reversalId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mf-transactions", "returns"] });
      setSuccessMsg("Transaction reversed.");
      setReversalId("");
      setTimeout(() => setSuccessMsg(""), 4000);
    },
  });

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <a href="/dashboard/material-flow" className="text-sm text-indigo-600 hover:underline">← Dashboard</a>
        <h1 className="text-xl font-bold text-gray-900">Returns & Reversals</h1>
      </div>

      {successMsg && <div className="bg-green-50 border border-green-200 text-green-700 p-3 rounded-lg text-sm">{successMsg}</div>}

      {/* Mode Toggle */}
      <div className="flex gap-2">
        {(["RETURN", "REVERSAL"] as const).map((m) => (
          <button key={m} onClick={() => setMode(m)} className={`px-4 py-2 text-sm rounded-lg ${mode === m ? "bg-blue-600 text-white" : "bg-white text-gray-600 border"}`}>
            {m === "RETURN" ? "Material Return" : "Transaction Reversal"}
          </button>
        ))}
      </div>

      {mode === "RETURN" && (
        <div className="bg-white rounded-lg border p-5 space-y-4">
          <h2 className="font-semibold text-gray-800">Return Unused Material</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Production Order</label>
              <input value={form.production_order_id} onChange={(e) => setForm((p) => ({ ...p, production_order_id: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm" placeholder="UUID" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Item Type</label>
              <select value={form.item_type} onChange={(e) => setForm((p) => ({ ...p, item_type: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm">
                <option value="material">Material</option>
                <option value="product">Product</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Material ID</label>
              <input value={form.material_id} onChange={(e) => setForm((p) => ({ ...p, material_id: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm" placeholder="UUID" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Lot ID</label>
              <input value={form.lot_id} onChange={(e) => setForm((p) => ({ ...p, lot_id: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm" placeholder="UUID" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Return Quantity</label>
              <div className="flex gap-1">
                <input type="number" value={form.quantity} onChange={(e) => setForm((p) => ({ ...p, quantity: e.target.value }))} className="flex-1 border rounded px-3 py-2 text-sm" placeholder="0" />
                <select value={form.uom} onChange={(e) => setForm((p) => ({ ...p, uom: e.target.value }))} className="border rounded px-2 py-2 text-sm">
                  {["KG", "L", "PCS", "CTN"].map((u) => <option key={u}>{u}</option>)}
                </select>
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Return Reason</label>
              <select value={form.return_reason} onChange={(e) => setForm((p) => ({ ...p, return_reason: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm">
                <option value="RETURN_UNUSED">Unused Material</option>
                <option value="RETURN_FROM_REWORK">From Rework</option>
                <option value="REVERSAL">Mistaken Issue</option>
                <option value="RECONCILIATION">Reconciliation</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
            <textarea value={form.notes} onChange={(e) => setForm((p) => ({ ...p, notes: e.target.value }))} rows={2} className="w-full border rounded px-3 py-2 text-sm" placeholder="Return reason details" />
          </div>
          <div className="bg-yellow-50 border border-yellow-200 rounded p-2 text-xs text-yellow-700">
            Returned material will be placed in <strong>QUARANTINE</strong> status pending quality reassessment.
          </div>
          <div className="flex justify-end">
            <button onClick={() => create.mutate()} disabled={create.isPending || !form.quantity} className="bg-rose-600 text-white px-5 py-2 rounded-lg text-sm hover:bg-rose-700 disabled:opacity-50">
              {create.isPending ? "Posting…" : "Post Return"}
            </button>
          </div>
        </div>
      )}

      {mode === "REVERSAL" && (
        <div className="bg-white rounded-lg border p-5 space-y-4">
          <h2 className="font-semibold text-gray-800">Reverse Transaction</h2>
          <div className="bg-orange-50 border border-orange-200 rounded p-2 text-xs text-orange-700">
            Reversals can only be applied to POSTED transactions that have not yet been consumed. The system will auto-generate a mirror transaction.
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Transaction ID to Reverse</label>
            <input value={reversalId} onChange={(e) => setReversalId(e.target.value)} className="w-full border rounded px-3 py-2 text-sm max-w-sm" placeholder="Flow Transaction UUID" />
          </div>
          <div className="flex justify-end">
            <button onClick={() => reverse.mutate()} disabled={reverse.isPending || !reversalId} className="bg-orange-600 text-white px-5 py-2 rounded-lg text-sm hover:bg-orange-700 disabled:opacity-50">
              {reverse.isPending ? "Reversing…" : "Reverse Transaction"}
            </button>
          </div>
        </div>
      )}

      {/* History */}
      <div className="bg-white rounded-lg border overflow-x-auto">
        <div className="px-4 py-3 border-b"><h2 className="font-semibold text-gray-900">Return History</h2></div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>{["Flow No", "Type", "Production Order", "Date", "Status"].map((h) => <th key={h} className="px-4 py-2 text-left text-xs font-medium text-gray-600">{h}</th>)}</tr>
          </thead>
          <tbody className="divide-y">
            {(txList || []).map((t) => (
              <tr key={t.id} className="hover:bg-gray-50">
                <td className="px-4 py-2 font-mono text-xs">{t.flow_no}</td>
                <td className="px-4 py-2 text-xs">{t.flow_type.replace("_", " ")}</td>
                <td className="px-4 py-2 font-mono text-xs">{t.production_order_id?.slice(0, 8) || "—"}</td>
                <td className="px-4 py-2 text-xs">{new Date(t.transaction_datetime).toLocaleString()}</td>
                <td className="px-4 py-2"><span className={`text-xs px-2 py-0.5 rounded-full font-medium ${FLOW_STATUS_COLORS[t.status] || ""}`}>{t.status}</span></td>
              </tr>
            ))}
            {!(txList?.length) && <tr><td colSpan={5} className="px-4 py-6 text-center text-gray-400 text-sm">No return transactions.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
