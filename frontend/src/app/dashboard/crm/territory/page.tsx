"use client";
import { useEffect, useState } from "react";
import { crmApi, CRMTerritory, CRMTerritoryPerformance, fmtCurrency } from "@/lib/crm_pipeline";

const RISK_COLORS: Record<string, string> = {
  LOW: "#10B981",
  MEDIUM: "#F59E0B",
  HIGH: "#EF4444",
  UNKNOWN: "#6B7280",
};

export default function TerritoryPage() {
  const [territories, setTerritories] = useState<CRMTerritory[]>([]);
  const [performance, setPerformance] = useState<CRMTerritoryPerformance[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [showEdit, setShowEdit] = useState<CRMTerritory | null>(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    territory_code: "", territory_name: "", region: "", assigned_rep_ids: "", notes: "",
  });

  const load = async () => {
    setLoading(true);
    try {
      const [t, p] = await Promise.all([crmApi.getTerritories(), crmApi.getTerritoryPerformance()]);
      setTerritories(t);
      setPerformance(p);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    setSaving(true);
    try {
      await crmApi.createTerritory(form);
      setShowCreate(false);
      setForm({ territory_code: "", territory_name: "", region: "", assigned_rep_ids: "", notes: "" });
      load();
    } catch (e) { console.error(e); }
    setSaving(false);
  };

  const handleUpdate = async () => {
    if (!showEdit) return;
    setSaving(true);
    try {
      await crmApi.updateTerritory(showEdit.id, form);
      setShowEdit(null);
      load();
    } catch (e) { console.error(e); }
    setSaving(false);
  };

  const openEdit = (t: CRMTerritory) => {
    setShowEdit(t);
    setForm({
      territory_code: t.territory_code,
      territory_name: t.territory_name,
      region: t.region || "",
      assigned_rep_ids: t.assigned_rep_ids || "",
      notes: t.notes || "",
    });
  };

  const perfMap = Object.fromEntries(performance.map(p => [p.territory_id, p]));

  const winRateColor = (rate: number) =>
    rate >= 60 ? "#10B981" : rate >= 30 ? "#F59E0B" : "#EF4444";

  if (loading) return <div className="p-6 text-gray-500">Loading territories…</div>;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Territory Management</h1>
          <p className="text-sm text-gray-500 mt-0.5">Manage sales territories, rep assignments, and pipeline performance by region</p>
        </div>
        <button onClick={() => setShowCreate(true)}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700">
          + New Territory
        </button>
      </div>

      {/* Performance Cards */}
      {performance.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {performance.map(p => (
            <div key={p.territory_id} className="bg-white rounded-xl border shadow-sm p-4 space-y-3">
              <div className="flex items-start justify-between">
                <div>
                  <div className="font-semibold text-gray-800">{p.territory_name}</div>
                  <div className="text-xs text-gray-400">{p.region || "No region"}</div>
                </div>
                <span className="text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-700">
                  {p.total_records} records
                </span>
              </div>
              <div className="grid grid-cols-3 gap-2 text-center">
                <div>
                  <div className="text-lg font-bold text-blue-700">{p.open_records}</div>
                  <div className="text-xs text-gray-400">Open</div>
                </div>
                <div>
                  <div className="text-lg font-bold text-green-600">{p.won_records}</div>
                  <div className="text-xs text-gray-400">Won</div>
                </div>
                <div>
                  <div className="text-lg font-bold text-red-500">{p.lost_records}</div>
                  <div className="text-xs text-gray-400">Lost</div>
                </div>
              </div>
              <div className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Pipeline</span>
                  <span className="font-medium text-gray-800">{fmtCurrency(p.pipeline_value)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Weighted</span>
                  <span className="font-medium text-indigo-700">{fmtCurrency(p.weighted_value)}</span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-gray-500">Win Rate</span>
                  <span className="font-bold" style={{ color: winRateColor(p.win_rate_pct) }}>
                    {p.win_rate_pct}%
                  </span>
                </div>
              </div>
              {p.assigned_rep_ids && (
                <div className="text-xs text-gray-400 border-t pt-2">
                  Reps: {p.assigned_rep_ids}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Territory List */}
      <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
        <div className="px-4 py-3 border-b bg-gray-50">
          <h2 className="font-semibold text-gray-800 text-sm">All Territories ({territories.length})</h2>
        </div>
        {territories.length === 0 && (
          <div className="px-4 py-12 text-center text-gray-400 text-sm">
            No territories yet. Create one to start assigning reps and records.
          </div>
        )}
        <div className="divide-y">
          {territories.map(t => {
            const p = perfMap[t.id];
            return (
              <div key={t.id} className="px-4 py-3 flex items-center gap-4">
                <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: t.active_flag ? "#10B981" : "#D1D5DB" }} />
                <div className="flex-1">
                  <div className="font-medium text-gray-800 text-sm">{t.territory_name}</div>
                  <div className="text-xs text-gray-400">
                    {t.territory_code}
                    {t.region && ` · ${t.region}`}
                    {t.assigned_rep_ids && ` · Reps: ${t.assigned_rep_ids}`}
                  </div>
                </div>
                {p && (
                  <div className="flex gap-4 text-xs text-gray-500">
                    <span>{p.open_records} open</span>
                    <span className="text-green-600 font-medium">{p.win_rate_pct}% win</span>
                    <span>{fmtCurrency(p.pipeline_value)} pipeline</span>
                  </div>
                )}
                <button onClick={() => openEdit(t)}
                  className="text-xs text-blue-600 hover:underline">Edit</button>
              </div>
            );
          })}
        </div>
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md space-y-3">
            <h2 className="font-semibold text-lg">New Territory</h2>
            <input placeholder="Territory Code *" value={form.territory_code}
              onChange={e => setForm(f => ({ ...f, territory_code: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" />
            <input placeholder="Territory Name *" value={form.territory_name}
              onChange={e => setForm(f => ({ ...f, territory_name: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" />
            <input placeholder="Region (e.g. Nairobi, Mombasa)" value={form.region}
              onChange={e => setForm(f => ({ ...f, region: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" />
            <input placeholder="Assigned Rep IDs (comma-separated)" value={form.assigned_rep_ids}
              onChange={e => setForm(f => ({ ...f, assigned_rep_ids: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" />
            <textarea placeholder="Notes" value={form.notes}
              onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" rows={2} />
            <div className="flex gap-2 pt-1">
              <button onClick={handleCreate} disabled={saving || !form.territory_code || !form.territory_name}
                className="flex-1 bg-blue-600 text-white py-2 rounded-lg text-sm disabled:opacity-50">
                {saving ? "Creating…" : "Create Territory"}
              </button>
              <button onClick={() => setShowCreate(false)} className="flex-1 border rounded-lg py-2 text-sm">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {showEdit && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md space-y-3">
            <h2 className="font-semibold text-lg">Edit Territory</h2>
            <input placeholder="Territory Name *" value={form.territory_name}
              onChange={e => setForm(f => ({ ...f, territory_name: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" />
            <input placeholder="Region" value={form.region}
              onChange={e => setForm(f => ({ ...f, region: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" />
            <input placeholder="Assigned Rep IDs (comma-separated)" value={form.assigned_rep_ids}
              onChange={e => setForm(f => ({ ...f, assigned_rep_ids: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" />
            <textarea placeholder="Notes" value={form.notes}
              onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" rows={2} />
            <div className="flex gap-2 pt-1">
              <button onClick={handleUpdate} disabled={saving || !form.territory_name}
                className="flex-1 bg-blue-600 text-white py-2 rounded-lg text-sm disabled:opacity-50">
                {saving ? "Saving…" : "Update Territory"}
              </button>
              <button onClick={() => setShowEdit(null)} className="flex-1 border rounded-lg py-2 text-sm">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
