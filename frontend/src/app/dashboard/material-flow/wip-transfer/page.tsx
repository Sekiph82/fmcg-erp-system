"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { mfApi, FlowTransaction, FlowStage, FLOW_STATUS_COLORS } from "@/lib/materialFlow";

export default function WIPTransferPage() {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    flow_type: "STAGE_TRANSFER",
    production_order_id: "",
    notes: "",
    item_type: "material",
    material_id: "",
    product_id: "",
    lot_id: "",
    quantity: "",
    uom: "KG",
    source_stage_id: "",
    destination_stage_id: "",
    quality_status: "RELEASED",
  });
  const [successMsg, setSuccessMsg] = useState("");

  const { data: stages } = useQuery<FlowStage[]>({
    queryKey: ["mf-stages"],
    queryFn: () => mfApi.listStages(),
  });

  const { data: txList } = useQuery<FlowTransaction[]>({
    queryKey: ["mf-transactions", "transfer"],
    queryFn: () => mfApi.listTransactions({ flow_type: "STAGE_TRANSFER" }),
  });

  const create = useMutation({
    mutationFn: () =>
      mfApi.transferMaterials({
        flow_type: form.flow_type as any,
        production_order_id: form.production_order_id || undefined,
        notes: form.notes,
        lines: [{
          line_no: 1,
          item_type: form.item_type,
          material_id: form.material_id || undefined,
          product_id: form.product_id || undefined,
          lot_id: form.lot_id || undefined,
          quantity: parseFloat(form.quantity),
          uom: form.uom,
          source_stage_id: form.source_stage_id || undefined,
          destination_stage_id: form.destination_stage_id || undefined,
          quality_status: form.quality_status as any,
        }],
      }),
    onSuccess: (r) => {
      setSuccessMsg(`Transfer ${r.flow_no} posted.`);
      qc.invalidateQueries({ queryKey: ["mf-transactions", "transfer"] });
      qc.invalidateQueries({ queryKey: ["mf-dashboard"] });
      setTimeout(() => setSuccessMsg(""), 4000);
    },
  });

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <a href="/dashboard/material-flow" className="text-sm text-indigo-600 hover:underline">← Dashboard</a>
        <h1 className="text-xl font-bold text-gray-900">WIP / Stage Transfer</h1>
      </div>

      {successMsg && <div className="bg-green-50 border border-green-200 text-green-700 p-3 rounded-lg text-sm">{successMsg}</div>}

      <div className="bg-white rounded-lg border p-5 space-y-4">
        <h2 className="font-semibold text-gray-800">New Stage Transfer</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Transfer Type</label>
            <select value={form.flow_type} onChange={(e) => setForm((p) => ({ ...p, flow_type: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm">
              <option value="STAGE_TRANSFER">Stage Transfer</option>
              <option value="WEIGHING_TRANSFER">Weighing Transfer</option>
              <option value="INTERMEDIATE_CREATE">Intermediate Create</option>
              <option value="LINE_TRANSFER">Line Transfer</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Item Type</label>
            <select value={form.item_type} onChange={(e) => setForm((p) => ({ ...p, item_type: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm">
              <option value="material">Material</option>
              <option value="product">Product</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Production Order ID</label>
            <input value={form.production_order_id} onChange={(e) => setForm((p) => ({ ...p, production_order_id: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm" placeholder="UUID" />
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
            <label className="block text-xs font-medium text-gray-600 mb-1">Quantity</label>
            <div className="flex gap-1">
              <input type="number" value={form.quantity} onChange={(e) => setForm((p) => ({ ...p, quantity: e.target.value }))} className="flex-1 border rounded px-3 py-2 text-sm" placeholder="0" />
              <select value={form.uom} onChange={(e) => setForm((p) => ({ ...p, uom: e.target.value }))} className="border rounded px-2 py-2 text-sm">
                {["KG", "L", "MT", "PCS"].map((u) => <option key={u}>{u}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Source Stage</label>
            <select value={form.source_stage_id} onChange={(e) => setForm((p) => ({ ...p, source_stage_id: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm">
              <option value="">— select stage —</option>
              {(stages || []).map((s) => <option key={s.id} value={s.id}>{s.stage_name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Destination Stage</label>
            <select value={form.destination_stage_id} onChange={(e) => setForm((p) => ({ ...p, destination_stage_id: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm">
              <option value="">— select stage —</option>
              {(stages || []).map((s) => <option key={s.id} value={s.id}>{s.stage_name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Quality Status</label>
            <select value={form.quality_status} onChange={(e) => setForm((p) => ({ ...p, quality_status: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm">
              {["RELEASED", "QUARANTINE", "QC_HOLD", "PENDING_INSPECTION"].map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
          <textarea value={form.notes} onChange={(e) => setForm((p) => ({ ...p, notes: e.target.value }))} rows={2} className="w-full border rounded px-3 py-2 text-sm" placeholder="Optional transfer notes" />
        </div>
        <div className="flex justify-end">
          <button onClick={() => create.mutate()} disabled={create.isPending || !form.quantity} className="bg-blue-600 text-white px-5 py-2 rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50">
            {create.isPending ? "Posting…" : "Post Transfer"}
          </button>
        </div>
      </div>

      <div className="bg-white rounded-lg border overflow-x-auto">
        <div className="px-4 py-3 border-b"><h2 className="font-semibold text-gray-900">Recent Stage Transfers</h2></div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>{["Flow No", "Type", "Date", "Lines", "Status"].map((h) => <th key={h} className="px-4 py-2 text-left text-xs font-medium text-gray-600">{h}</th>)}</tr>
          </thead>
          <tbody className="divide-y">
            {(txList || []).map((t) => (
              <tr key={t.id} className="hover:bg-gray-50">
                <td className="px-4 py-2 font-mono text-xs">{t.flow_no}</td>
                <td className="px-4 py-2 text-xs">{t.flow_type.replace("_", " ")}</td>
                <td className="px-4 py-2 text-xs">{new Date(t.transaction_datetime).toLocaleString()}</td>
                <td className="px-4 py-2 text-xs">{t.lines.length}</td>
                <td className="px-4 py-2"><span className={`text-xs px-2 py-0.5 rounded-full font-medium ${FLOW_STATUS_COLORS[t.status] || ""}`}>{t.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
