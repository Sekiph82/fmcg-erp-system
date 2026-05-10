"use client";
import { useCallback, useEffect, useState } from "react";
import { voipApi, CallLog, CallStats, OUTCOME_COLORS, fmtDuration } from "@/lib/voip";

const BLANK_FORM = {
  phone_number: "", customer_id: "", direction: "OUTBOUND",
  outcome: "ANSWERED", duration_seconds: "", notes: "",
  follow_up_required: false, follow_up_date: "", tags: "",
};

export default function CallsPage() {
  const [calls, setCalls] = useState<CallLog[]>([]);
  const [stats, setStats] = useState<CallStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [filterOutcome, setFilterOutcome] = useState("");
  const [showLog, setShowLog] = useState(false);
  const [form, setForm] = useState({ ...BLANK_FORM });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [c, s] = await Promise.all([
        voipApi.listCalls(filterOutcome ? { outcome: filterOutcome } : undefined),
        voipApi.getStats(),
      ]);
      setCalls(c);
      setStats(s);
    } finally {
      setLoading(false);
    }
  }, [filterOutcome]);

  useEffect(() => { load(); }, [load]);

  const logCall = async () => {
    if (!form.phone_number) { setError("Phone number required"); return; }
    setSaving(true); setError("");
    try {
      await voipApi.createCall({
        phone_number: form.phone_number,
        customer_id: form.customer_id || null,
        direction: form.direction,
        outcome: form.outcome,
        duration_seconds: form.duration_seconds ? parseInt(form.duration_seconds) : null,
        notes: form.notes || null,
        follow_up_required: form.follow_up_required,
        follow_up_date: form.follow_up_date || null,
        tags: form.tags || null,
      });
      setShowLog(false);
      setForm({ ...BLANK_FORM });
      await load();
    } catch {
      setError("Failed to log call");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Call Center</h1>
          <p className="text-xs text-gray-500 mt-0.5">Log and track sales calls, follow-ups, and call performance.</p>
        </div>
        <button onClick={() => { setShowLog(true); setError(""); }}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          📞 Log Call
        </button>
      </div>

      {stats && (
        <div className="grid grid-cols-5 gap-3">
          {[
            { label: "Total Calls", value: stats.total_calls, color: "text-gray-700" },
            { label: "Answered", value: stats.answered_calls, color: "text-green-600" },
            { label: "Answer Rate", value: `${stats.answer_rate}%`, color: stats.answer_rate >= 70 ? "text-green-600" : "text-amber-600" },
            { label: "Follow-ups", value: stats.follow_ups_pending, color: "text-red-600" },
            { label: "Avg Duration", value: fmtDuration(stats.avg_duration_seconds), color: "text-blue-600" },
          ].map(s => (
            <div key={s.label} className="bg-white border rounded-lg p-3 shadow-sm">
              <p className="text-xs text-gray-500">{s.label}</p>
              <p className={`text-lg font-bold mt-1 ${s.color}`}>{loading ? "—" : s.value}</p>
            </div>
          ))}
        </div>
      )}

      {stats?.by_outcome && Object.keys(stats.by_outcome).length > 0 && (
        <div className="bg-white border rounded-lg p-4 shadow-sm">
          <h3 className="text-xs font-semibold text-gray-600 mb-3">Calls by Outcome</h3>
          <div className="flex gap-3 flex-wrap">
            {Object.entries(stats.by_outcome).map(([outcome, count]) => (
              <div key={outcome}
                className={`flex items-center gap-2 rounded-full px-3 py-1.5 ${OUTCOME_COLORS[outcome] ?? "bg-gray-100 text-gray-600"}`}>
                <span className="text-xs font-medium">{outcome.replace("_", " ")}</span>
                <span className="text-xs font-bold">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex gap-2 flex-wrap">
        {["", "ANSWERED", "NO_ANSWER", "BUSY", "VOICEMAIL", "FAILED"].map(o => (
          <button key={o}
            onClick={() => setFilterOutcome(o)}
            className={`rounded-full px-3 py-1 text-xs font-medium border transition-colors ${
              filterOutcome === o
                ? "bg-blue-600 text-white border-blue-600"
                : "bg-white text-gray-600 border-gray-300 hover:border-blue-400"
            }`}>
            {o || "All"}
          </button>
        ))}
        <span className="text-xs text-gray-500 self-center">{calls.length} calls</span>
      </div>

      {loading ? (
        <p className="text-sm text-gray-500">Loading…</p>
      ) : calls.length === 0 ? (
        <div className="bg-white border rounded-lg p-10 text-center text-gray-400">
          <p className="text-2xl mb-2">📞</p>
          <p className="text-sm">No calls logged yet.</p>
        </div>
      ) : (
        <div className="bg-white border rounded-lg shadow-sm overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {["Ref", "Direction", "Phone", "Customer", "Agent", "Duration", "Outcome", "Follow-up", "Notes"].map(h => (
                  <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {calls.map(c => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{c.call_ref}</td>
                  <td className="px-4 py-3 text-xs">
                    <span className={`rounded px-1.5 py-0.5 ${c.direction === "INBOUND" ? "bg-blue-50 text-blue-600" : "bg-green-50 text-green-600"}`}>
                      {c.direction === "INBOUND" ? "↓ IN" : "↑ OUT"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs font-mono text-gray-700">{c.phone_number}</td>
                  <td className="px-4 py-3 text-xs text-gray-700">{c.customer_name ?? "—"}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">{c.agent_name ?? "—"}</td>
                  <td className="px-4 py-3 text-xs text-gray-600">{fmtDuration(c.duration_seconds)}</td>
                  <td className="px-4 py-3">
                    {c.outcome ? (
                      <span className={`text-xs rounded-full px-2 py-0.5 ${OUTCOME_COLORS[c.outcome] ?? "bg-gray-100 text-gray-600"}`}>
                        {c.outcome.replace("_", " ")}
                      </span>
                    ) : "—"}
                  </td>
                  <td className="px-4 py-3 text-xs">
                    {c.follow_up_required ? (
                      <span className="text-red-600 font-medium">{c.follow_up_date ?? "Yes"}</span>
                    ) : <span className="text-gray-300">—</span>}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500 max-w-xs truncate">{c.notes ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showLog && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h2 className="text-base font-semibold">Log Call</h2>
              <button onClick={() => setShowLog(false)} className="text-gray-400 text-xl">×</button>
            </div>
            <div className="p-6 space-y-3">
              {error && <p className="text-xs text-red-500 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>}
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: "Phone Number *", key: "phone_number", placeholder: "+254712345678", col: 2 },
                  { label: "Customer ID (UUID, optional)", key: "customer_id", placeholder: "", col: 2 },
                  { label: "Duration (seconds)", key: "duration_seconds", type: "number", placeholder: "0", col: 1 },
                  { label: "Follow-up Date", key: "follow_up_date", type: "date", col: 1 },
                  { label: "Tags", key: "tags", placeholder: "sales, cold-call", col: 2 },
                ].map(f => (
                  <div key={f.key} className={f.col === 2 ? "col-span-2" : ""}>
                    <label className="block text-xs font-medium text-gray-600 mb-1">{f.label}</label>
                    <input type={f.type ?? "text"} placeholder={f.placeholder}
                      value={(form as unknown as Record<string, string>)[f.key] ?? ""}
                      onChange={e => setForm(p => ({ ...p, [f.key]: e.target.value }))}
                      className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                    />
                  </div>
                ))}
                {[
                  { label: "Direction", key: "direction", options: ["OUTBOUND", "INBOUND"] },
                  { label: "Outcome", key: "outcome", options: ["ANSWERED", "NO_ANSWER", "BUSY", "VOICEMAIL", "FAILED"] },
                ].map(f => (
                  <div key={f.key}>
                    <label className="block text-xs font-medium text-gray-600 mb-1">{f.label}</label>
                    <select value={(form as unknown as Record<string, string>)[f.key]}
                      onChange={e => setForm(p => ({ ...p, [f.key]: e.target.value }))}
                      className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none">
                      {f.options.map(o => <option key={o} value={o}>{o.replace("_", " ")}</option>)}
                    </select>
                  </div>
                ))}
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
                  <textarea value={form.notes}
                    onChange={e => setForm(p => ({ ...p, notes: e.target.value }))}
                    rows={3} placeholder="Call summary…"
                    className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none resize-none"
                  />
                </div>
              </div>
              <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                <input type="checkbox" checked={form.follow_up_required}
                  onChange={e => setForm(p => ({ ...p, follow_up_required: e.target.checked }))}
                  className="h-4 w-4 rounded border-gray-300 text-blue-600"
                />
                Follow-up required
              </label>
            </div>
            <div className="px-6 pb-5 flex gap-3">
              <button onClick={logCall} disabled={saving}
                className="flex-1 rounded bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
                {saving ? "Logging…" : "Log Call"}
              </button>
              <button onClick={() => setShowLog(false)}
                className="flex-1 rounded border py-2 text-sm text-gray-600 hover:bg-gray-50">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
