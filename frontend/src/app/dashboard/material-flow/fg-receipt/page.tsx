"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { mfApi, FlowTransaction, FlowStage, FLOW_STATUS_COLORS } from "@/lib/materialFlow";

export default function FGReceiptPage() {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    production_order_id: "",
    product_id: "",
    lot_id: "",
    quantity: "",
    uom: "KG",
    destination_stage: "FG_QUARANTINE",
    destination_warehouse_id: "",
    destination_stage_id: "",
    quality_status: "QUARANTINE",
    notes: "",
  });
  const [successMsg, setSuccessMsg] = useState("");

  const { data: stages } = useQuery<FlowStage[]>({
    queryKey: ["mf-stages"],
    queryFn: () => mfApi.listStages(),
  });

  const { data: txList } = useQuery<FlowTransaction[]>({
    queryKey: ["mf-transactions", "fg"],
    queryFn: () => mfApi.listTransactions({ flow_type: "FG_RECEIPT" }),
  });

  const create = useMutation({
    mutationFn: () =>
      mfApi.fgReceipt({
        flow_type: "FG_RECEIPT",
        production_order_id: form.production_order_id || undefined,
        notes: form.notes,
        lines: [{
          line_no: 1,
          item_type: "product",
          product_id: form.product_id || undefined,
          lot_id: form.lot_id || undefined,
          quantity: parseFloat(form.quantity),
          uom: form.uom,
          destination_warehouse_id: form.destination_warehouse_id || undefined,
          destination_stage_id: form.destination_stage_id || undefined,
          quality_status: form.quality_status as any,
        }],
      }),
    onSuccess: (r) => {
      setSuccessMsg(`FG Receipt ${r.flow_no} created. Product moved to ${form.destination_stage}.`);
      qc.invalidateQueries({ queryKey: ["mf-transactions", "fg"] });
      qc.invalidateQueries({ queryKey: ["mf-dashboard"] });
      setForm({ ...form, quantity: "", lot_id: "", notes: "" });
      setTimeout(() => setSuccessMsg(""), 5000);
    },
  });

  const fgStages = (stages || []).filter((s) => ["FG_QUARANTINE", "FG_RELEASED", "PALLETIZATION"].includes(s.stage_type));

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <a href="/dashboard/material-flow" className="text-sm text-indigo-600 hover:underline">← Dashboard</a>
        <h1 className="text-xl font-bold text-gray-900">Finished Goods Receipt</h1>
      </div>

      {successMsg && <div className="bg-green-50 border border-green-200 text-green-700 p-3 rounded-lg text-sm">{successMsg}</div>}

      <div className="bg-white rounded-lg border p-5 space-y-4">
        <h2 className="font-semibold text-gray-800">Receive Finished Goods</h2>

        {/* QC flow notice */}
        <div className="bg-blue-50 border border-blue-100 rounded p-3 text-xs text-blue-700">
          FG receipts default to <strong>FG Quarantine</strong> unless explicitly routed to a released warehouse. QC approval required to release.
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Production Order ID</label>
            <input value={form.production_order_id} onChange={(e) => setForm((p) => ({ ...p, production_order_id: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm" placeholder="UUID" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Product ID</label>
            <input value={form.product_id} onChange={(e) => setForm((p) => ({ ...p, product_id: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm" placeholder="UUID" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">FG Lot / Batch No</label>
            <input value={form.lot_id} onChange={(e) => setForm((p) => ({ ...p, lot_id: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm" placeholder="Lot UUID" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Received Quantity</label>
            <div className="flex gap-1">
              <input type="number" value={form.quantity} onChange={(e) => setForm((p) => ({ ...p, quantity: e.target.value }))} className="flex-1 border rounded px-3 py-2 text-sm" placeholder="0" />
              <select value={form.uom} onChange={(e) => setForm((p) => ({ ...p, uom: e.target.value }))} className="border rounded px-2 py-2 text-sm">
                {["KG", "PCS", "CTN", "L", "MT"].map((u) => <option key={u}>{u}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Destination Stage</label>
            <select value={form.destination_stage_id} onChange={(e) => setForm((p) => ({ ...p, destination_stage_id: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm">
              <option value="">— select FG stage —</option>
              {fgStages.map((s) => <option key={s.id} value={s.id}>{s.stage_name} ({s.stage_type})</option>)}
              {fgStages.length === 0 && <option disabled>No FG stages configured</option>}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Quality Status</label>
            <select value={form.quality_status} onChange={(e) => setForm((p) => ({ ...p, quality_status: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm">
              <option value="QUARANTINE">QUARANTINE (default)</option>
              <option value="PENDING_INSPECTION">PENDING INSPECTION</option>
              <option value="RELEASED">RELEASED</option>
              <option value="QC_HOLD">QC HOLD</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
          <textarea value={form.notes} onChange={(e) => setForm((p) => ({ ...p, notes: e.target.value }))} rows={2} className="w-full border rounded px-3 py-2 text-sm" placeholder="FG receipt notes, shift, operator, etc." />
        </div>

        <div className="flex justify-end">
          <button onClick={() => create.mutate()} disabled={create.isPending || !form.quantity || !form.product_id} className="bg-orange-600 text-white px-5 py-2 rounded-lg text-sm hover:bg-orange-700 disabled:opacity-50">
            {create.isPending ? "Receiving…" : "Receive Finished Goods"}
          </button>
        </div>
      </div>

      {/* Recent FG Receipts */}
      <div className="bg-white rounded-lg border overflow-x-auto">
        <div className="px-4 py-3 border-b"><h2 className="font-semibold text-gray-900">Recent FG Receipts</h2></div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>{["Flow No", "Production Order", "Date", "Lines", "Status"].map((h) => <th key={h} className="px-4 py-2 text-left text-xs font-medium text-gray-600">{h}</th>)}</tr>
          </thead>
          <tbody className="divide-y">
            {(txList || []).map((t) => (
              <tr key={t.id} className="hover:bg-gray-50">
                <td className="px-4 py-2 font-mono text-xs">{t.flow_no}</td>
                <td className="px-4 py-2 font-mono text-xs">{t.production_order_id?.slice(0, 8) || "—"}</td>
                <td className="px-4 py-2 text-xs">{new Date(t.transaction_datetime).toLocaleString()}</td>
                <td className="px-4 py-2 text-xs">{t.lines.length}</td>
                <td className="px-4 py-2">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${FLOW_STATUS_COLORS[t.status] || ""}`}>{t.status}</span>
                </td>
              </tr>
            ))}
            {!(txList?.length) && <tr><td colSpan={5} className="px-4 py-6 text-center text-gray-400 text-sm">No FG receipts recorded.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
