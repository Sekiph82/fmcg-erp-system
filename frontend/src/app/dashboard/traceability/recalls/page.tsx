"use client";
import { useEffect, useState } from "react";
import {
  traceApi, RecallHeader, RecallStatus, RecallType,
  RECALL_STATUS_BG, SEVERITY_BG,
} from "@/lib/traceability";

const STATUSES: RecallStatus[] = ["draft","under_review","active","contained","in_progress","completed","closed","cancelled"];

export default function RecallListPage() {
  const [recalls, setRecalls] = useState<RecallHeader[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState<RecallStatus | "">("");
  const [showCreate, setShowCreate] = useState(false);
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState({
    recall_type: "internal",
    recall_reason: "",
    trigger_source: "manual",
    severity_level: "medium",
    source_lot_id: "",
    target_market: "",
    country_scope: "",
    notes: "",
  });

  const load = (s?: RecallStatus) => {
    setLoading(true);
    traceApi.listRecalls(s || undefined).then(setRecalls).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    if (!form.recall_reason) return;
    setSaving(true);
    try {
      await traceApi.initiateRecall({
        recall_type: form.recall_type,
        recall_reason: form.recall_reason,
        trigger_source: form.trigger_source,
        severity_level: form.severity_level,
        source_lot_id: form.source_lot_id || undefined,
        target_market: form.target_market || undefined,
        country_scope: form.country_scope || undefined,
        notes: form.notes || undefined,
      });
      setShowCreate(false);
      load();
    } finally { setSaving(false); }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Recall Management</h1>
          <p className="text-sm text-gray-500">{recalls.length} recall records</p>
        </div>
        <button onClick={() => setShowCreate(true)}
          className="px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700">
          + Initiate Recall
        </button>
      </div>

      {/* Status filters */}
      <div className="flex flex-wrap gap-2">
        {(["", ...STATUSES] as const).map(s => (
          <button key={s} onClick={() => { setFilterStatus(s as any); load(s ? s as RecallStatus : undefined); }}
            className={`px-3 py-1.5 rounded-lg text-sm border ${filterStatus === s ? "bg-red-600 text-white border-red-600" : "border-gray-200 text-gray-600 hover:bg-gray-50"}`}>
            {s || "All"}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500">
            <tr>
              {["Recall #","Type","Severity","Status","Trigger","Affected Qty","Customers","Recovery","Initiated"].map(h => (
                <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan={9} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>
            ) : recalls.length === 0 ? (
              <tr><td colSpan={9} className="px-4 py-8 text-center text-gray-400">No recalls found</td></tr>
            ) : recalls.map(r => (
              <tr key={r.id} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  <a href={`/dashboard/traceability/recalls/${r.id}`}
                    className="font-medium text-indigo-700 hover:underline">{r.recall_no}</a>
                </td>
                <td className="px-4 py-3 capitalize">{r.recall_type.replace("_"," ")}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded text-xs ${SEVERITY_BG[r.severity_level]}`}>{r.severity_level}</span>
                </td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded text-xs ${RECALL_STATUS_BG[r.status]}`}>{r.status.replace("_"," ")}</span>
                </td>
                <td className="px-4 py-3 capitalize">{r.trigger_source.replace("_"," ")}</td>
                <td className="px-4 py-3">{r.total_affected_qty ? parseFloat(r.total_affected_qty).toLocaleString() : "—"}</td>
                <td className="px-4 py-3">{r.total_affected_customers ?? "—"}</td>
                <td className="px-4 py-3">{r.recovery_pct ? `${parseFloat(r.recovery_pct).toFixed(1)}%` : "—"}</td>
                <td className="px-4 py-3 text-gray-400">{new Date(r.initiation_datetime).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            <h3 className="font-semibold text-gray-800 text-lg">Initiate Recall</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-medium text-gray-600">Recall Type</label>
                <select className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.recall_type} onChange={e => setForm(f => ({ ...f, recall_type: e.target.value }))}>
                  {["internal","customer","market","regulatory","mock_recall"].map(t => (
                    <option key={t} value={t}>{t.replace("_"," ")}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600">Severity</label>
                <select className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.severity_level} onChange={e => setForm(f => ({ ...f, severity_level: e.target.value }))}>
                  {["low","medium","high","critical"].map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600">Trigger Source</label>
                <select className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.trigger_source} onChange={e => setForm(f => ({ ...f, trigger_source: e.target.value }))}>
                  {["qc","complaint","supplier_notice","audit","regulatory","manual"].map(t => (
                    <option key={t} value={t}>{t.replace("_"," ")}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600">Source Lot ID</label>
                <input className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.source_lot_id} onChange={e => setForm(f => ({ ...f, source_lot_id: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600">Target Market</label>
                <input className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.target_market} onChange={e => setForm(f => ({ ...f, target_market: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600">Country Scope</label>
                <input className="mt-1 w-full border rounded-lg px-3 py-2 text-sm" placeholder="e.g. KE, UG, TZ"
                  value={form.country_scope} onChange={e => setForm(f => ({ ...f, country_scope: e.target.value }))} />
              </div>
              <div className="col-span-2">
                <label className="text-xs font-medium text-gray-600">Recall Reason *</label>
                <textarea rows={3} className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.recall_reason} onChange={e => setForm(f => ({ ...f, recall_reason: e.target.value }))} />
              </div>
              <div className="col-span-2">
                <label className="text-xs font-medium text-gray-600">Notes</label>
                <input className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} />
              </div>
            </div>
            <div className="flex gap-2 justify-end pt-2">
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm border rounded-lg">Cancel</button>
              <button onClick={handleCreate} disabled={!form.recall_reason || saving}
                className="px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50">
                {saving ? "Creating…" : "Initiate Recall"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
