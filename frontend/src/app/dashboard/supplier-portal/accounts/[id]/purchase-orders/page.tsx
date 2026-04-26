"use client";
import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { spApi, SPPOResponseStatus, SP_PO_RESPONSE_COLORS } from "@/lib/supplier_portal";

export default function SPPurchaseOrders() {
  const { id } = useParams<{ id: string }>();
  const [pos, setPOs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [selected, setSelected] = useState<any>(null);
  const [acknowledging, setAcknowledging] = useState(false);
  const [ackForm, setAckForm] = useState({
    response_status: "ACCEPTED" as SPPOResponseStatus,
    supplier_comment: "",
    rejection_reason: "",
    proposed_eta: "",
  });

  const load = () => {
    setLoading(true);
    spApi.listPOs(id, statusFilter || undefined).then(setPOs).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [id, statusFilter]);

  const ackPO = async () => {
    if (!selected) return;
    await spApi.acknowledgePO(id, selected.po_id, {
      response_status: ackForm.response_status,
      supplier_comment: ackForm.supplier_comment || undefined,
      rejection_reason: ackForm.rejection_reason || undefined,
      proposed_eta: ackForm.proposed_eta || undefined,
    });
    setAcknowledging(false);
    load();
  };

  const badge = (s: string) => {
    const col = SP_PO_RESPONSE_COLORS[s as SPPOResponseStatus] || "bg-gray-100 text-gray-700";
    return <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${col}`}>{s?.replace(/_/g, " ")}</span>;
  };

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center gap-4">
        <a href={`/dashboard/supplier-portal/accounts/${id}`} className="text-blue-600 hover:underline text-sm">← Account</a>
        <h1 className="text-xl font-bold text-gray-900">Purchase Orders</h1>
      </div>

      <div className="flex gap-2 flex-wrap">
        {["", "draft", "issued", "confirmed", "received", "closed"].map((s) => (
          <button key={s} onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border ${statusFilter === s ? "bg-blue-600 text-white border-blue-600" : "bg-white text-gray-600 border-gray-300"}`}>
            {s || "All"}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              {["PO Number", "PO Date", "Status", "Amount", "Req. Delivery", "ACK Status", "Actions"].map((h) => (
                <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">Loading...</td></tr>
            ) : pos.length === 0 ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No purchase orders found.</td></tr>
            ) : pos.map((po) => (
              <tr key={po.po_id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-blue-700">{po.po_number}</td>
                <td className="px-4 py-3 text-gray-500">{po.po_date || "—"}</td>
                <td className="px-4 py-3">
                  <span className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded-full text-xs">{po.status}</span>
                </td>
                <td className="px-4 py-3 font-mono">{po.currency} {po.total_amount?.toLocaleString() || "—"}</td>
                <td className="px-4 py-3 text-gray-600">{po.required_date || "—"}</td>
                <td className="px-4 py-3">{badge(po.acknowledgment_status)}</td>
                <td className="px-4 py-3">
                  <button onClick={() => { setSelected(po); setAcknowledging(true); }}
                    className="text-blue-600 hover:underline text-xs mr-2">Respond</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {acknowledging && selected && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-lg space-y-4">
            <h2 className="text-lg font-bold text-gray-900">Respond to PO — {selected.po_number}</h2>
            <div>
              <label className="text-xs font-medium text-gray-700">Response</label>
              <select value={ackForm.response_status} onChange={(e) => setAckForm({ ...ackForm, response_status: e.target.value as SPPOResponseStatus })}
                className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                {["ACCEPTED", "ACCEPTED_REVISED_ETA", "PARTIALLY_ACCEPTED", "REJECTED", "UNDER_REVIEW"].map((s) => (
                  <option key={s} value={s}>{s.replace(/_/g, " ")}</option>
                ))}
              </select>
            </div>
            {(ackForm.response_status === "ACCEPTED_REVISED_ETA" || ackForm.response_status === "PARTIALLY_ACCEPTED") && (
              <div>
                <label className="text-xs font-medium text-gray-700">Proposed ETA</label>
                <input type="date" value={ackForm.proposed_eta} onChange={(e) => setAckForm({ ...ackForm, proposed_eta: e.target.value })}
                  className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
            )}
            {ackForm.response_status === "REJECTED" && (
              <div>
                <label className="text-xs font-medium text-gray-700">Rejection Reason</label>
                <textarea value={ackForm.rejection_reason} onChange={(e) => setAckForm({ ...ackForm, rejection_reason: e.target.value })}
                  rows={2} className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
            )}
            <div>
              <label className="text-xs font-medium text-gray-700">Supplier Comment</label>
              <textarea value={ackForm.supplier_comment} onChange={(e) => setAckForm({ ...ackForm, supplier_comment: e.target.value })}
                rows={2} className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div className="flex justify-end gap-3">
              <button onClick={() => setAcknowledging(false)} className="px-4 py-2 border border-gray-300 rounded-lg text-sm">Cancel</button>
              <button onClick={ackPO} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">Submit Response</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
