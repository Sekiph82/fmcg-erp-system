"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { mfApi, FlowType, FlowTransaction, FLOW_STATUS_COLORS, FLOW_TYPE_LABELS } from "@/lib/materialFlow";

interface IssueLine {
  item_type: string;
  material_id: string;
  lot_id: string;
  quantity: string;
  uom: string;
  destination_warehouse_id: string;
  destination_stage_id: string;
  quality_status: string;
}

const BLANK_LINE: IssueLine = {
  item_type: "material",
  material_id: "",
  lot_id: "",
  quantity: "",
  uom: "KG",
  destination_warehouse_id: "",
  destination_stage_id: "",
  quality_status: "RELEASED",
};

export default function IssuePage() {
  const qc = useQueryClient();
  const [flowType, setFlowType] = useState<FlowType>("RAW_ISSUE");
  const [orderId, setOrderId] = useState("");
  const [notes, setNotes] = useState("");
  const [lines, setLines] = useState<IssueLine[]>([{ ...BLANK_LINE }]);
  const [successMsg, setSuccessMsg] = useState("");

  const { data: txList } = useQuery<FlowTransaction[]>({
    queryKey: ["mf-transactions", "issue"],
    queryFn: () => mfApi.listTransactions({ flow_type: "RAW_ISSUE" }).then((r) => r.data),
  });

  const createIssue = useMutation({
    mutationFn: () =>
      mfApi.issueMaterials({
        flow_type: flowType,
        production_order_id: orderId || undefined,
        notes,
        lines: lines.map((l, i) => ({
          line_no: i + 1,
          item_type: l.item_type,
          material_id: l.material_id || undefined,
          lot_id: l.lot_id || undefined,
          quantity: parseFloat(l.quantity),
          uom: l.uom,
          destination_warehouse_id: l.destination_warehouse_id || undefined,
          destination_stage_id: l.destination_stage_id || undefined,
          quality_status: l.quality_status,
          issue_flag: true,
        })),
      }),
    onSuccess: (r) => {
      setSuccessMsg(`Issue transaction ${r.data.flow_no} created successfully.`);
      setLines([{ ...BLANK_LINE }]);
      setNotes("");
      qc.invalidateQueries({ queryKey: ["mf-transactions"] });
      qc.invalidateQueries({ queryKey: ["mf-dashboard"] });
      setTimeout(() => setSuccessMsg(""), 4000);
    },
  });

  const confirmTx = useMutation({
    mutationFn: (id: string) => mfApi.confirmTransaction(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mf-transactions", "issue"] }),
  });

  function updateLine(idx: number, field: keyof IssueLine, val: string) {
    setLines((prev) => prev.map((l, i) => i === idx ? { ...l, [field]: val } : l));
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <a href="/dashboard/material-flow" className="text-sm text-indigo-600 hover:underline">← Dashboard</a>
        <h1 className="text-xl font-bold text-gray-900">Issue to Production</h1>
      </div>

      {successMsg && (
        <div className="bg-green-50 border border-green-200 text-green-700 p-3 rounded-lg text-sm">{successMsg}</div>
      )}

      <div className="bg-white rounded-lg border p-5 space-y-4">
        <h2 className="font-semibold text-gray-800">New Issue Transaction</h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Flow Type</label>
            <select
              value={flowType}
              onChange={(e) => setFlowType(e.target.value as FlowType)}
              className="w-full border rounded px-3 py-2 text-sm"
            >
              <option value="RAW_ISSUE">Raw Material Issue</option>
              <option value="PKG_ISSUE">Packaging Issue</option>
              <option value="CONSUMABLE_ISSUE">Consumable Issue</option>
              <option value="WEIGHING_TRANSFER">Weighing Transfer</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Production Order ID</label>
            <input
              type="text"
              value={orderId}
              onChange={(e) => setOrderId(e.target.value)}
              placeholder="UUID of production order"
              className="w-full border rounded px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
            <input
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Optional notes"
              className="w-full border rounded px-3 py-2 text-sm"
            />
          </div>
        </div>

        {/* Lines */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-700">Issue Lines</h3>
            <button
              onClick={() => setLines((p) => [...p, { ...BLANK_LINE }])}
              className="text-xs text-indigo-600 hover:underline"
            >+ Add Line</button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead className="bg-gray-50">
                <tr>
                  {["#", "Material ID", "Lot ID", "Quantity", "UOM", "Dest Stage ID", "Quality", ""].map((h) => (
                    <th key={h} className="border px-2 py-1.5 text-left text-xs font-medium text-gray-600">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {lines.map((ln, i) => (
                  <tr key={i}>
                    <td className="border px-2 py-1 text-xs text-gray-500">{i + 1}</td>
                    <td className="border px-2 py-1">
                      <input value={ln.material_id} onChange={(e) => updateLine(i, "material_id", e.target.value)} className="w-full text-xs border-0 focus:ring-0" placeholder="material uuid" />
                    </td>
                    <td className="border px-2 py-1">
                      <input value={ln.lot_id} onChange={(e) => updateLine(i, "lot_id", e.target.value)} className="w-full text-xs border-0 focus:ring-0" placeholder="lot uuid" />
                    </td>
                    <td className="border px-2 py-1">
                      <input type="number" value={ln.quantity} onChange={(e) => updateLine(i, "quantity", e.target.value)} className="w-20 text-xs border-0 focus:ring-0" placeholder="0" />
                    </td>
                    <td className="border px-2 py-1">
                      <select value={ln.uom} onChange={(e) => updateLine(i, "uom", e.target.value)} className="text-xs border-0 bg-transparent">
                        {["KG", "L", "PCS", "CTN", "MT"].map((u) => <option key={u}>{u}</option>)}
                      </select>
                    </td>
                    <td className="border px-2 py-1">
                      <input value={ln.destination_stage_id} onChange={(e) => updateLine(i, "destination_stage_id", e.target.value)} className="w-full text-xs border-0 focus:ring-0" placeholder="stage uuid" />
                    </td>
                    <td className="border px-2 py-1">
                      <select value={ln.quality_status} onChange={(e) => updateLine(i, "quality_status", e.target.value)} className="text-xs border-0 bg-transparent">
                        {["RELEASED", "QUARANTINE", "QC_HOLD"].map((s) => <option key={s}>{s}</option>)}
                      </select>
                    </td>
                    <td className="border px-2 py-1">
                      {lines.length > 1 && (
                        <button onClick={() => setLines((p) => p.filter((_, idx) => idx !== i))} className="text-red-400 hover:text-red-600 text-xs">✕</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="flex justify-end">
          <button
            onClick={() => createIssue.mutate()}
            disabled={createIssue.isPending || lines.every((l) => !l.quantity)}
            className="bg-blue-600 text-white px-5 py-2 rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
          >
            {createIssue.isPending ? "Posting…" : "Post Issue Transaction"}
          </button>
        </div>
      </div>

      {/* Recent issue transactions */}
      <div className="bg-white rounded-lg border">
        <div className="px-4 py-3 border-b">
          <h2 className="font-semibold text-gray-900">Recent Issue Transactions</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                {["Flow No", "Type", "Production Order", "Date", "Status", "Lines", "Actions"].map((h) => (
                  <th key={h} className="px-4 py-2 text-left text-xs font-medium text-gray-600">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {(txList || []).map((t) => (
                <tr key={t.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 font-mono text-xs">{t.flow_no}</td>
                  <td className="px-4 py-2 text-xs">{FLOW_TYPE_LABELS[t.flow_type]}</td>
                  <td className="px-4 py-2 text-xs font-mono">{t.production_order_id?.slice(0, 8) || "—"}</td>
                  <td className="px-4 py-2 text-xs">{new Date(t.transaction_datetime).toLocaleString()}</td>
                  <td className="px-4 py-2">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${FLOW_STATUS_COLORS[t.status] || ""}`}>{t.status}</span>
                  </td>
                  <td className="px-4 py-2 text-xs">{t.lines?.length || 0}</td>
                  <td className="px-4 py-2">
                    {t.status === "DRAFT" && (
                      <button onClick={() => confirmTx.mutate(t.id)} className="text-xs text-green-600 hover:underline">Confirm</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
