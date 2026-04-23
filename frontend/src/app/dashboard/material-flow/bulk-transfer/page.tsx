"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { mfApi, TankOccupancy, FlowTransaction, TANK_STATUS_COLORS, FLOW_STATUS_COLORS } from "@/lib/materialFlow";

export default function BulkTransferPage() {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    source_tank_id: "",
    destination_tank_id: "",
    quantity: "",
    uom: "KG",
    production_order_id: "",
    notes: "",
  });
  const [successMsg, setSuccessMsg] = useState("");

  const { data: tanks } = useQuery<TankOccupancy[]>({
    queryKey: ["mf-tanks"],
    queryFn: () => mfApi.listTanks().then((r) => r.data),
  });

  const { data: txList } = useQuery<FlowTransaction[]>({
    queryKey: ["mf-transactions", "bulk"],
    queryFn: () => mfApi.listTransactions({ flow_type: "BULK_TRANSFER" }).then((r) => r.data),
  });

  const create = useMutation({
    mutationFn: () =>
      mfApi.transferMaterials({
        flow_type: "BULK_TRANSFER",
        production_order_id: form.production_order_id || undefined,
        notes: form.notes,
        lines: [{
          line_no: 1,
          item_type: "material",
          quantity: parseFloat(form.quantity),
          uom: form.uom,
          source_stage_id: form.source_tank_id || undefined,
          destination_stage_id: form.destination_tank_id || undefined,
          quality_status: "RELEASED" as any,
        }],
      }),
    onSuccess: (r) => {
      setSuccessMsg(`Bulk transfer ${r.data.flow_no} posted.`);
      qc.invalidateQueries({ queryKey: ["mf-transactions", "bulk"] });
      qc.invalidateQueries({ queryKey: ["mf-tanks"] });
      qc.invalidateQueries({ queryKey: ["mf-dashboard"] });
      setForm({ source_tank_id: "", destination_tank_id: "", quantity: "", uom: "KG", production_order_id: "", notes: "" });
      setTimeout(() => setSuccessMsg(""), 4000);
    },
  });

  const tankList = tanks || [];
  const sourceTank = tankList.find((t) => t.id === form.source_tank_id);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <a href="/dashboard/material-flow" className="text-sm text-indigo-600 hover:underline">← Dashboard</a>
        <h1 className="text-xl font-bold text-gray-900">Bulk Transfer</h1>
        <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full">Tank-to-Tank</span>
      </div>

      {successMsg && <div className="bg-green-50 border border-green-200 text-green-700 p-3 rounded-lg text-sm">{successMsg}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Form */}
        <div className="lg:col-span-2 bg-white rounded-lg border p-5 space-y-4">
          <h2 className="font-semibold text-gray-800">Bulk Transfer Form</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Source Tank</label>
              <select value={form.source_tank_id} onChange={(e) => setForm((p) => ({ ...p, source_tank_id: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">— select source tank —</option>
                {tankList.filter((t) => t.quantity_current > 0).map((t) => (
                  <option key={t.id} value={t.id}>{t.tank_code} — {Number(t.quantity_current).toLocaleString()} {t.uom}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Destination Tank</label>
              <select value={form.destination_tank_id} onChange={(e) => setForm((p) => ({ ...p, destination_tank_id: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">— select destination tank —</option>
                {tankList.filter((t) => t.id !== form.source_tank_id).map((t) => (
                  <option key={t.id} value={t.id}>{t.tank_code} — {t.tank_status}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Transfer Quantity</label>
              <div className="flex gap-1">
                <input type="number" value={form.quantity} onChange={(e) => setForm((p) => ({ ...p, quantity: e.target.value }))} className="flex-1 border rounded px-3 py-2 text-sm" placeholder="0" />
                <select value={form.uom} onChange={(e) => setForm((p) => ({ ...p, uom: e.target.value }))} className="border rounded px-2 py-2 text-sm">
                  {["KG", "L", "MT"].map((u) => <option key={u}>{u}</option>)}
                </select>
              </div>
              {sourceTank && form.quantity && parseFloat(form.quantity) > sourceTank.quantity_current && (
                <p className="text-xs text-red-500 mt-1">⚠ Quantity exceeds available stock ({Number(sourceTank.quantity_current).toLocaleString()} {sourceTank.uom})</p>
              )}
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Production Order</label>
              <input value={form.production_order_id} onChange={(e) => setForm((p) => ({ ...p, production_order_id: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm" placeholder="UUID (optional)" />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
            <textarea value={form.notes} onChange={(e) => setForm((p) => ({ ...p, notes: e.target.value }))} rows={2} className="w-full border rounded px-3 py-2 text-sm" placeholder="Reason for transfer" />
          </div>
          <div className="flex justify-end">
            <button onClick={() => create.mutate()} disabled={create.isPending || !form.source_tank_id || !form.destination_tank_id || !form.quantity} className="bg-purple-600 text-white px-5 py-2 rounded-lg text-sm hover:bg-purple-700 disabled:opacity-50">
              {create.isPending ? "Posting…" : "Post Bulk Transfer"}
            </button>
          </div>
        </div>

        {/* Tank Summary */}
        <div className="bg-white rounded-lg border p-4 space-y-3">
          <h2 className="font-semibold text-gray-800">Tank Status</h2>
          {tankList.length === 0 && <p className="text-xs text-gray-400">No tanks configured.</p>}
          {tankList.map((t) => (
            <div key={t.id} className="border rounded p-2 space-y-1">
              <div className="flex justify-between items-center">
                <span className="text-xs font-medium text-gray-800">{t.tank_code}</span>
                <span className={`text-xs px-1.5 py-0.5 rounded-full ${TANK_STATUS_COLORS[t.tank_status]}`}>{t.tank_status}</span>
              </div>
              {t.capacity_max && (
                <div className="w-full bg-gray-100 rounded-full h-1.5">
                  <div
                    className="h-1.5 rounded-full bg-emerald-400"
                    style={{ width: `${Math.min((t.quantity_current / t.capacity_max) * 100, 100)}%` }}
                  />
                </div>
              )}
              <p className="text-xs text-gray-500">{Number(t.quantity_current).toLocaleString()} {t.uom}</p>
            </div>
          ))}
        </div>
      </div>

      {/* History */}
      <div className="bg-white rounded-lg border overflow-x-auto">
        <div className="px-4 py-3 border-b"><h2 className="font-semibold text-gray-900">Recent Bulk Transfers</h2></div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>{["Flow No", "Date", "Lines", "Status"].map((h) => <th key={h} className="px-4 py-2 text-left text-xs font-medium text-gray-600">{h}</th>)}</tr>
          </thead>
          <tbody className="divide-y">
            {(txList || []).map((t) => (
              <tr key={t.id} className="hover:bg-gray-50">
                <td className="px-4 py-2 font-mono text-xs">{t.flow_no}</td>
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
