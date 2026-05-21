"use client";

import { useState, useEffect } from "react";
import { esgApi, ESGTarget, ESGMetricType, EmissionScope } from "@/lib/esg";

export default function ESGTargetsPage() {
  const [targets, setTargets] = useState<ESGTarget[]>([]);
  const [performance, setPerformance] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({
    metric_type: "EMISSIONS" as ESGMetricType,
    scope: "" as EmissionScope | "",
    baseline_year: new Date().getFullYear() - 1,
    baseline_value: "",
    target_value: "",
    unit: "kgCO2e",
    target_date: "",
    notes: "",
    is_active: true,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const [t, p] = await Promise.all([esgApi.listTargets(), esgApi.targetPerformance()]);
      setTargets(t);
      setPerformance(p);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await esgApi.createTarget({
        metric_type: form.metric_type,
        scope: form.scope || undefined,
        baseline_year: form.baseline_year,
        baseline_value: parseFloat(form.baseline_value),
        target_value: parseFloat(form.target_value),
        unit: form.unit,
        target_date: form.target_date,
        notes: form.notes || undefined,
        is_active: form.is_active,
      });
      setShowModal(false);
      load();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const METRIC_UNITS: Record<ESGMetricType, string> = {
    EMISSIONS: "kgCO2e",
    ENERGY: "kWh",
    WATER: "m³",
    WASTE: "kg",
    RECYCLING: "kg",
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">ESG Targets</h1>
          <p className="text-sm text-gray-500 mt-1">Set and track sustainability reduction targets</p>
        </div>
        <button onClick={() => setShowModal(true)} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          + New Target
        </button>
      </div>

      {/* Performance cards */}
      {performance.length > 0 && (
        <div className="space-y-3">
          <h2 className="font-semibold text-gray-800">Target vs Actual Performance</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {performance.map((p) => {
              const pct = Math.min(Math.max(p.progress_pct, 0), 100);
              return (
                <div key={p.id} className="bg-white rounded-lg border p-4">
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <p className="font-medium text-gray-800">{p.metric_type}{p.scope ? ` (${p.scope})` : ""}</p>
                      <p className="text-xs text-gray-500 mt-0.5">Target by {p.target_date} · Baseline {p.baseline_year}</p>
                    </div>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${p.on_track ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                      {p.on_track ? "On Track" : "Off Track"}
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-xs text-center mb-3">
                    <div className="bg-gray-50 rounded p-2">
                      <p className="text-gray-500">Baseline</p>
                      <p className="font-bold">{p.baseline_value.toLocaleString()}</p>
                    </div>
                    <div className="bg-blue-50 rounded p-2">
                      <p className="text-gray-500">Target</p>
                      <p className="font-bold text-blue-600">{p.target_value.toLocaleString()}</p>
                    </div>
                    <div className="bg-gray-50 rounded p-2">
                      <p className="text-gray-500">Actual</p>
                      <p className="font-bold">{p.actual_value.toLocaleString()}</p>
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-xs text-gray-500 mb-1">
                      <span>Progress toward target</span>
                      <span>{pct.toFixed(1)}%</span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full ${pct >= 100 ? "bg-green-500" : pct >= 50 ? "bg-blue-500" : "bg-red-400"}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Targets table */}
      <div className="bg-white rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
            <tr>
              <th className="px-4 py-3 text-left">Metric</th>
              <th className="px-4 py-3 text-left">Scope</th>
              <th className="px-4 py-3 text-right">Baseline</th>
              <th className="px-4 py-3 text-right">Target</th>
              <th className="px-4 py-3 text-left">Unit</th>
              <th className="px-4 py-3 text-right">Baseline Year</th>
              <th className="px-4 py-3 text-left">Target Date</th>
              <th className="px-4 py-3 text-left">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>
            ) : targets.length === 0 ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">No targets set. Create your first ESG reduction target.</td></tr>
            ) : (
              targets.map((t) => (
                <tr key={t.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 font-medium">{t.metric_type}</td>
                  <td className="px-4 py-2 text-xs text-gray-500">{t.scope || "All"}</td>
                  <td className="px-4 py-2 text-right">{Number(t.baseline_value).toLocaleString()}</td>
                  <td className="px-4 py-2 text-right text-blue-600 font-semibold">{Number(t.target_value).toLocaleString()}</td>
                  <td className="px-4 py-2 text-xs text-gray-500">{t.unit}</td>
                  <td className="px-4 py-2 text-right">{t.baseline_year}</td>
                  <td className="px-4 py-2 text-xs">{t.target_date}</td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-0.5 rounded-full text-xs ${t.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-400"}`}>
                      {t.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <h2 className="text-lg font-semibold mb-4">New ESG Target</h2>
            <form onSubmit={handleSave} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium mb-1">Metric Type *</label>
                  <select required value={form.metric_type} onChange={(e) => setForm({ ...form, metric_type: e.target.value as ESGMetricType, unit: METRIC_UNITS[e.target.value as ESGMetricType] })} className="w-full border rounded-lg px-3 py-2 text-sm">
                    {(["EMISSIONS", "ENERGY", "WATER", "WASTE", "RECYCLING"] as ESGMetricType[]).map((m) => (<option key={m} value={m}>{m}</option>))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Scope (Emissions only)</label>
                  <select value={form.scope} onChange={(e) => setForm({ ...form, scope: e.target.value as EmissionScope | "" })} className="w-full border rounded-lg px-3 py-2 text-sm">
                    <option value="">All scopes</option>
                    {(["SCOPE1", "SCOPE2", "SCOPE3"] as EmissionScope[]).map((s) => (<option key={s} value={s}>{s}</option>))}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium mb-1">Baseline Year *</label>
                  <input required type="number" value={form.baseline_year} onChange={(e) => setForm({ ...form, baseline_year: parseInt(e.target.value) })} className="w-full border rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Target Date *</label>
                  <input required type="date" value={form.target_date} onChange={(e) => setForm({ ...form, target_date: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-sm font-medium mb-1">Baseline Value *</label>
                  <input required type="number" step="0.01" value={form.baseline_value} onChange={(e) => setForm({ ...form, baseline_value: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Target Value *</label>
                  <input required type="number" step="0.01" value={form.target_value} onChange={(e) => setForm({ ...form, target_value: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Unit</label>
                  <input value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Notes</label>
                <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" rows={2} />
              </div>
              {error && <p className="text-red-600 text-sm">{error}</p>}
              <div className="flex gap-2 pt-1">
                <button type="button" onClick={() => setShowModal(false)} className="flex-1 py-2 border rounded-lg text-sm hover:bg-gray-50">Cancel</button>
                <button type="submit" disabled={saving} className="flex-1 py-2 bg-blue-600 text-white rounded-lg text-sm disabled:opacity-50">
                  {saving ? "Saving…" : "Create Target"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
