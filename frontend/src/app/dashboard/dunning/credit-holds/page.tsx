"use client";
import { useState, useEffect } from "react";
import { dunningApi, DunningCase } from "@/lib/dunning";

export default function CreditHoldsPage() {
  const [holds, setHolds] = useState<DunningCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [releasing, setReleasing] = useState<string | null>(null);
  const [releaseForm, setReleaseForm] = useState({ released_by: "", notes: "" });

  const load = () => {
    setLoading(true);
    dunningApi.listCases({ credit_hold: true, limit: 200 }).then(setHolds).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const release = async (caseId: string) => {
    await dunningApi.releaseCreditHold(caseId, releaseForm.released_by || "manual", releaseForm.notes);
    setReleasing(null);
    load();
  };

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Credit Hold Management</h1>
        <p className="text-sm text-gray-500 mt-1">All customers currently under credit hold — review and release where appropriate</p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white border border-red-300 rounded-xl p-4">
          <div className="text-2xl font-bold text-red-700">{holds.length}</div>
          <div className="text-xs text-gray-500 mt-1">Active Credit Holds</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-xl p-4">
          <div className="text-2xl font-bold text-gray-900">
            {holds.reduce((s, h) => s + Number(h.total_overdue_amount), 0).toLocaleString()}
          </div>
          <div className="text-xs text-gray-500 mt-1">Total Held Amount</div>
        </div>
        <div className="bg-white border border-orange-200 rounded-xl p-4">
          <div className="text-2xl font-bold text-orange-700">{holds.filter((h) => h.case_status === "ESCALATED").length}</div>
          <div className="text-xs text-gray-500 mt-1">Escalated</div>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-red-50 border-b border-red-200">
            <tr>
              {["Case #", "Customer", "Total Overdue", "Hold Date", "Hold Reason", "Level", "Priority", "Actions"].map((h) => (
                <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-red-800 uppercase tracking-wide">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>
            ) : holds.length === 0 ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">No credit holds active.</td></tr>
            ) : holds.map((c) => (
              <tr key={c.id} className="hover:bg-red-50/30">
                <td className="px-4 py-3 font-medium text-blue-700">
                  <a href={`/dashboard/dunning/cases/${c.id}`} className="hover:underline">{c.case_no}</a>
                </td>
                <td className="px-4 py-3 text-gray-500 font-mono text-xs">{c.customer_id.slice(0, 12)}…</td>
                <td className="px-4 py-3 font-mono font-bold text-red-700">{Number(c.total_overdue_amount).toLocaleString()}</td>
                <td className="px-4 py-3 text-gray-600">{c.credit_hold_date || "—"}</td>
                <td className="px-4 py-3 text-gray-600 text-xs max-w-xs truncate">{c.credit_hold_reason || "—"}</td>
                <td className="px-4 py-3 text-center">
                  <span className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-xs font-bold">L{c.current_level_no}</span>
                </td>
                <td className="px-4 py-3 text-center text-xs font-bold">{c.priority_score}</td>
                <td className="px-4 py-3">
                  <button onClick={() => setReleasing(c.id)}
                    className="px-3 py-1.5 bg-green-600 text-white rounded-lg text-xs font-medium hover:bg-green-700">
                    Release Hold
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {releasing && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-md space-y-4">
            <h2 className="text-lg font-bold text-gray-900">Release Credit Hold</h2>
            <div>
              <label className="text-xs font-medium text-gray-700">Released By</label>
              <input value={releaseForm.released_by} onChange={(e) => setReleaseForm({ ...releaseForm, released_by: e.target.value })}
                className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700">Release Notes</label>
              <textarea value={releaseForm.notes} onChange={(e) => setReleaseForm({ ...releaseForm, notes: e.target.value })}
                rows={2} className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div className="flex justify-end gap-3">
              <button onClick={() => setReleasing(null)} className="px-4 py-2 border border-gray-300 rounded-lg text-sm">Cancel</button>
              <button onClick={() => release(releasing)} className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium">Confirm Release</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
