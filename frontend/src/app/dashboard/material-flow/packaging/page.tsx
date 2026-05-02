"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { mfApi, FlowTransaction, FLOW_STATUS_COLORS } from "@/lib/materialFlow";

const PKG_MATERIALS = ["Bottles", "Jars", "Caps", "Pumps", "Labels", "Cartons", "Sleeves", "Shrink Film", "Inserts", "Pallets"];

export default function PackagingIssuePage() {
  const qc = useQueryClient();
  const [lines, setLines] = useState([{ material_id: "", qty: "", uom: "PCS", pkg_type: "Bottles" }]);
  const [orderId, setOrderId] = useState("");
  const [notes, setNotes] = useState("");
  const [success, setSuccess] = useState("");

  const { data: txList } = useQuery<FlowTransaction[]>({
    queryKey: ["mf-transactions", "pkg"],
    queryFn: () => mfApi.listTransactions({ flow_type: "PKG_ISSUE" }),
  });

  const create = useMutation({
    mutationFn: () =>
      mfApi.issueMaterials({
        flow_type: "PKG_ISSUE",
        production_order_id: orderId || undefined,
        notes,
        lines: lines.map((l, i) => ({
          line_no: i + 1,
          item_type: "material",
          material_id: l.material_id || undefined,
          quantity: parseFloat(l.qty),
          uom: l.uom,
          quality_status: "RELEASED" as any,
          issue_flag: true,
          notes: l.pkg_type,
        })),
      }),
    onSuccess: (r) => {
      setSuccess(`Packaging issue ${r.flow_no} posted.`);
      qc.invalidateQueries({ queryKey: ["mf-transactions", "pkg"] });
      qc.invalidateQueries({ queryKey: ["mf-dashboard"] });
      setLines([{ material_id: "", qty: "", uom: "PCS", pkg_type: "Bottles" }]);
      setTimeout(() => setSuccess(""), 4000);
    },
  });

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <a href="/dashboard/material-flow" className="text-sm text-indigo-600 hover:underline">← Dashboard</a>
        <h1 className="text-xl font-bold text-gray-900">Packaging Material Issue</h1>
      </div>

      {success && <div className="bg-green-50 border border-green-200 text-green-700 p-3 rounded-lg text-sm">{success}</div>}

      <div className="bg-white rounded-lg border p-5 space-y-4">
        <h2 className="font-semibold text-gray-800">Issue Packaging Materials</h2>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Production Order ID</label>
            <input value={orderId} onChange={(e) => setOrderId(e.target.value)} className="w-full border rounded px-3 py-2 text-sm" placeholder="UUID" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
            <input value={notes} onChange={(e) => setNotes(e.target.value)} className="w-full border rounded px-3 py-2 text-sm" placeholder="Packaging run notes" />
          </div>
        </div>

        <div>
          <div className="flex justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-700">Packaging Lines</h3>
            <button onClick={() => setLines((p) => [...p, { material_id: "", qty: "", uom: "PCS", pkg_type: "Bottles" }])} className="text-xs text-indigo-600 hover:underline">+ Add Line</button>
          </div>
          <table className="w-full text-sm border-collapse">
            <thead className="bg-gray-50">
              <tr>
                {["Pkg Type", "Material ID", "Quantity", "UOM", ""].map((h) => (
                  <th key={h} className="border px-3 py-1.5 text-left text-xs font-medium text-gray-600">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {lines.map((l, i) => (
                <tr key={i}>
                  <td className="border px-2 py-1">
                    <select value={l.pkg_type} onChange={(e) => setLines((p) => p.map((x, idx) => idx === i ? { ...x, pkg_type: e.target.value } : x))} className="text-xs w-full border-0 bg-transparent">
                      {PKG_MATERIALS.map((m) => <option key={m}>{m}</option>)}
                    </select>
                  </td>
                  <td className="border px-2 py-1">
                    <input value={l.material_id} onChange={(e) => setLines((p) => p.map((x, idx) => idx === i ? { ...x, material_id: e.target.value } : x))} className="w-full text-xs border-0 focus:ring-0" placeholder="UUID" />
                  </td>
                  <td className="border px-2 py-1">
                    <input type="number" value={l.qty} onChange={(e) => setLines((p) => p.map((x, idx) => idx === i ? { ...x, qty: e.target.value } : x))} className="w-24 text-xs border-0 focus:ring-0" placeholder="0" />
                  </td>
                  <td className="border px-2 py-1">
                    <select value={l.uom} onChange={(e) => setLines((p) => p.map((x, idx) => idx === i ? { ...x, uom: e.target.value } : x))} className="text-xs border-0 bg-transparent">
                      {["PCS", "CTN", "KG", "ROLL"].map((u) => <option key={u}>{u}</option>)}
                    </select>
                  </td>
                  <td className="border px-2 py-1">
                    {lines.length > 1 && <button onClick={() => setLines((p) => p.filter((_, idx) => idx !== i))} className="text-red-400 hover:text-red-600 text-xs">✕</button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="flex justify-end">
          <button onClick={() => create.mutate()} disabled={create.isPending || lines.every((l) => !l.qty)} className="bg-teal-600 text-white px-5 py-2 rounded-lg text-sm hover:bg-teal-700 disabled:opacity-50">
            {create.isPending ? "Posting…" : "Post Packaging Issue"}
          </button>
        </div>
      </div>

      <div className="bg-white rounded-lg border overflow-x-auto">
        <div className="px-4 py-3 border-b"><h2 className="font-semibold text-gray-900">Recent Packaging Issues</h2></div>
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
                <td className="px-4 py-2"><span className={`text-xs px-2 py-0.5 rounded-full font-medium ${FLOW_STATUS_COLORS[t.status] || ""}`}>{t.status}</span></td>
              </tr>
            ))}
            {!(txList?.length) && <tr><td colSpan={5} className="px-4 py-6 text-center text-gray-400 text-sm">No packaging issues recorded.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
