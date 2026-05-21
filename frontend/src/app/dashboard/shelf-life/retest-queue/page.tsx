"use client";
import { useEffect, useState } from "react";
import { shelfLifeApi, RetestRequest, RetestStatus } from "@/lib/shelfLife";

const STATUS_BG: Record<RetestStatus, string> = {
  pending:    "bg-gray-100 text-gray-700",
  requested:  "bg-blue-100 text-blue-700",
  in_progress:"bg-amber-100 text-amber-700",
  passed:     "bg-green-100 text-green-700",
  failed:     "bg-red-100 text-red-700",
  cancelled:  "bg-gray-100 text-gray-500",
};

export default function RetestQueuePage() {
  const [queue, setQueue] = useState<RetestRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [showResult, setShowResult] = useState<RetestRequest | null>(null);
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState({ lot_id: "", reason: "", scheduled_date: "" });
  const [resultForm, setResultForm] = useState({ result_passed: true, result_notes: "", new_expiry_date: "" });

  const load = () => {
    setLoading(true);
    shelfLifeApi.listRetestQueue().then(setQueue).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    if (!form.lot_id || !form.reason) return;
    setSaving(true);
    try {
      await shelfLifeApi.createRetestRequest({
        lot_id: form.lot_id,
        reason: form.reason,
        scheduled_date: form.scheduled_date || undefined,
      });
      setShowCreate(false);
      setForm({ lot_id: "", reason: "", scheduled_date: "" });
      load();
    } finally { setSaving(false); }
  };

  const handleResult = async () => {
    if (!showResult) return;
    setSaving(true);
    try {
      await shelfLifeApi.recordRetestResult(showResult.id, {
        result_passed: resultForm.result_passed,
        result_notes: resultForm.result_notes || undefined,
        new_expiry_date: resultForm.new_expiry_date || undefined,
      });
      setShowResult(null);
      load();
    } finally { setSaving(false); }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Retest Queue</h1>
          <p className="text-sm text-gray-500">{queue.length} lots awaiting retest or in-progress</p>
        </div>
        <button onClick={() => setShowCreate(true)}
          className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          + Create Retest Request
        </button>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500">
            <tr>
              {["Request #","Lot ID","Status","Reason","Scheduled Date","Assigned To","Action"].map(h => (
                <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>
            ) : queue.length === 0 ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No lots in retest queue</td></tr>
            ) : queue.map(r => (
              <tr key={r.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-xs font-medium text-blue-700">{r.request_number}</td>
                <td className="px-4 py-3 font-mono text-xs">{r.lot_id.slice(0,12)}…</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded text-xs ${STATUS_BG[r.status]}`}>{r.status}</span>
                </td>
                <td className="px-4 py-3 text-gray-600 max-w-xs truncate">{r.reason}</td>
                <td className="px-4 py-3">{r.scheduled_date || "—"}</td>
                <td className="px-4 py-3 text-gray-400">{r.assigned_to_id ? r.assigned_to_id.slice(0,8) : "—"}</td>
                <td className="px-4 py-3">
                  {["requested","in_progress"].includes(r.status) && (
                    <button onClick={() => setShowResult(r)}
                      className="px-3 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700">
                      Record Result
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4">
            <h3 className="font-semibold text-gray-800">New Retest Request</h3>
            <div>
              <label className="text-xs font-medium text-gray-600">Lot ID</label>
              <input className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                placeholder="Lot UUID" value={form.lot_id}
                onChange={e => setForm(f => ({ ...f, lot_id: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600">Reason</label>
              <textarea rows={3} className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                value={form.reason} onChange={e => setForm(f => ({ ...f, reason: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600">Scheduled Date</label>
              <input type="date" className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                value={form.scheduled_date} onChange={e => setForm(f => ({ ...f, scheduled_date: e.target.value }))} />
            </div>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm border rounded-lg">Cancel</button>
              <button onClick={handleCreate} disabled={saving}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                {saving ? "Creating…" : "Create"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Result Modal */}
      {showResult && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4">
            <h3 className="font-semibold text-gray-800">Record Retest Result — {showResult.request_number}</h3>
            <div className="flex gap-4">
              {[true, false].map(p => (
                <label key={String(p)} className="flex items-center gap-2 cursor-pointer">
                  <input type="radio" name="result" checked={resultForm.result_passed === p}
                    onChange={() => setResultForm(f => ({ ...f, result_passed: p }))} />
                  <span className={`text-sm font-medium ${p ? "text-green-700" : "text-red-700"}`}>
                    {p ? "Passed" : "Failed"}
                  </span>
                </label>
              ))}
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600">Result Notes</label>
              <textarea rows={3} className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                value={resultForm.result_notes}
                onChange={e => setResultForm(f => ({ ...f, result_notes: e.target.value }))} />
            </div>
            {resultForm.result_passed && (
              <div>
                <label className="text-xs font-medium text-gray-600">New Expiry Date (if extended)</label>
                <input type="date" className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                  value={resultForm.new_expiry_date}
                  onChange={e => setResultForm(f => ({ ...f, new_expiry_date: e.target.value }))} />
              </div>
            )}
            <div className="flex gap-2 justify-end">
              <button onClick={() => setShowResult(null)} className="px-4 py-2 text-sm border rounded-lg">Cancel</button>
              <button onClick={handleResult} disabled={saving}
                className={`px-4 py-2 text-sm text-white rounded-lg disabled:opacity-50 ${resultForm.result_passed ? "bg-green-600 hover:bg-green-700" : "bg-red-600 hover:bg-red-700"}`}>
                {saving ? "Saving…" : `Record ${resultForm.result_passed ? "Pass" : "Fail"}`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
