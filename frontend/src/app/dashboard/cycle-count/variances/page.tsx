"use client";

import { useEffect, useState } from "react";
import { listAdjustments, approveAdjustments, rejectAdjustments, listEntries, CountAdjustment, CountEntry, AdjustmentStatus } from "@/lib/cycleCount";
import { Button } from "@/components/ui/Button";

export default function VariancesPage() {
  const [adjustments, setAdjustments] = useState<CountAdjustment[]>([]);
  const [entries, setEntries] = useState<Record<string, CountEntry>>({});
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [statusFilter, setStatusFilter] = useState<AdjustmentStatus | "all">("pending");
  const [rejectionReason, setRejectionReason] = useState("");
  const [processing, setProcessing] = useState(false);
  const [msg, setMsg] = useState("");

  useEffect(() => { load(); }, [statusFilter]);
  async function load() {
    setLoading(true);
    try {
      const adjs = await listAdjustments(statusFilter === "all" ? undefined : { status: statusFilter });
      setAdjustments(adjs);
      // Load corresponding entries
      const entriesData = await listEntries({ within_tolerance: false });
      const entryMap: Record<string, CountEntry> = {};
      entriesData.forEach((e) => { entryMap[e.id] = e; });
      setEntries(entryMap);
    } catch {}
    setLoading(false);
    setSelected(new Set());
  }

  function toggleSelect(entryId: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(entryId) ? next.delete(entryId) : next.add(entryId);
      return next;
    });
  }

  async function handleApprove() {
    if (!selected.size) return;
    setProcessing(true);
    try {
      const r = await approveAdjustments(Array.from(selected));
      setMsg(`Approved & posted ${r.approved} adjustment(s)`);
      await load();
    } catch { setMsg("Approve failed"); }
    setProcessing(false);
  }

  async function handleReject() {
    if (!selected.size || !rejectionReason) { setMsg("Enter rejection reason"); return; }
    setProcessing(true);
    try {
      const r = await rejectAdjustments(Array.from(selected), rejectionReason);
      setMsg(`Rejected ${r.rejected} adjustment(s)`);
      setRejectionReason("");
      await load();
    } catch { setMsg("Reject failed"); }
    setProcessing(false);
  }

  const STATUSES: Array<AdjustmentStatus | "all"> = ["all", "pending", "approved", "rejected", "posted"];

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Variance Review</h1>
          <p className="text-sm text-gray-500 mt-1">{adjustments.length} adjustment record(s)</p>
        </div>
        <div className="flex gap-2">
          {STATUSES.map((s) => (
            <button key={s} onClick={() => setStatusFilter(s)} className={`text-sm px-3 py-1.5 rounded-lg capitalize ${statusFilter === s ? "bg-indigo-600 text-white" : "bg-gray-100 text-gray-700"}`}>
              {s.replace("_", " ")}
            </button>
          ))}
        </div>
      </div>

      {msg && <div className="bg-blue-50 border border-blue-200 text-blue-700 text-sm rounded-lg px-4 py-2">{msg}</div>}

      {selected.size > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-center gap-4">
          <span className="text-sm text-amber-700">{selected.size} selected</span>
          <Button onClick={handleApprove} loading={processing}>Approve & Post</Button>
          <div className="flex gap-2 flex-1">
            <input
              className="flex-1 border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
              placeholder="Rejection reason..."
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
            />
            <Button variant="danger" onClick={handleReject} loading={processing}>Reject</Button>
          </div>
        </div>
      )}

      {loading ? <div className="text-gray-500 py-8 text-center">Loading...</div> : (
        <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3">
                  <input type="checkbox" onChange={(e) => {
                    if (e.target.checked) setSelected(new Set(adjustments.map((a) => a.entry_id)));
                    else setSelected(new Set());
                  }} />
                </th>
                {["Status", "Adj. Qty", "Value (KES)", "System Qty", "Counted Qty", "Variance %", "Movement Ref"].map((h) => (
                  <th key={h} className="text-left px-4 py-3 font-medium text-gray-700">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {adjustments.map((adj) => {
                const entry = entries[adj.entry_id];
                return (
                  <tr key={adj.id} className={`hover:bg-gray-50 ${selected.has(adj.entry_id) ? "bg-amber-50" : ""}`}>
                    <td className="px-4 py-3">
                      {adj.status === "pending" && (
                        <input type="checkbox" checked={selected.has(adj.entry_id)} onChange={() => toggleSelect(adj.entry_id)} />
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded font-medium capitalize ${
                        adj.status === "posted" ? "bg-green-100 text-green-700" :
                        adj.status === "approved" ? "bg-indigo-100 text-indigo-700" :
                        adj.status === "pending" ? "bg-amber-100 text-amber-700" :
                        "bg-red-100 text-red-700"
                      }`}>{adj.status}</span>
                    </td>
                    <td className={`px-4 py-3 font-medium ${Number(adj.adjustment_qty) < 0 ? "text-red-600" : "text-amber-600"}`}>
                      {Number(adj.adjustment_qty) > 0 ? "+" : ""}{Number(adj.adjustment_qty).toFixed(3)}
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {adj.adjustment_value ? Math.abs(Number(adj.adjustment_value)).toLocaleString() : "—"}
                    </td>
                    <td className="px-4 py-3 text-gray-600">{entry ? Number(entry.system_qty).toFixed(3) : "—"}</td>
                    <td className="px-4 py-3 text-gray-600">{entry ? Number(entry.counted_qty).toFixed(3) : "—"}</td>
                    <td className="px-4 py-3 text-gray-600">{entry ? `${Number(entry.variance_pct || 0).toFixed(2)}%` : "—"}</td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-400">{adj.stock_movement_ref || "—"}</td>
                  </tr>
                );
              })}
              {adjustments.length === 0 && <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">No adjustments found</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
