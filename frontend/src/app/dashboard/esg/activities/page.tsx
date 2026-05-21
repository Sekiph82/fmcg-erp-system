"use client";

import { useState, useEffect, useCallback } from "react";
import { esgApi, Activity, SourceType, SOURCE_TYPE_LABELS, SOURCE_UNITS } from "@/lib/esg";

const SCOPE_BADGE: Record<string, string> = {
  SCOPE1: "bg-red-100 text-red-700",
  SCOPE2: "bg-orange-100 text-orange-700",
  SCOPE3: "bg-yellow-100 text-yellow-700",
};

export default function ESGActivitiesPage() {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(false);
  const [filterSource, setFilterSource] = useState<SourceType | "">("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({
    source_type: "FUEL_DIESEL" as SourceType,
    source_reference: "",
    activity_date: new Date().toISOString().split("T")[0],
    quantity: "",
    unit: "liters",
    notes: "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await esgApi.listActivities({
        source_type: filterSource || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        limit: 300,
      });
      setActivities(data);
    } finally {
      setLoading(false);
    }
  }, [filterSource, dateFrom, dateTo]);

  useEffect(() => { load(); }, [load]);

  const handleSourceChange = (s: SourceType) => {
    setForm((prev) => ({ ...prev, source_type: s, unit: SOURCE_UNITS[s] || "unit" }));
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await esgApi.createActivity({
        source_type: form.source_type,
        source_reference: form.source_reference || undefined,
        activity_date: form.activity_date,
        quantity: parseFloat(form.quantity),
        unit: form.unit,
        notes: form.notes || undefined,
      });
      setShowModal(false);
      load();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const totalEmission = activities.reduce((s, a) => s + (Number(a.calculated_emission_kgco2e) || 0), 0);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Activity Data</h1>
          <p className="text-sm text-gray-500 mt-1">Log emission-generating activities</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          + Log Activity
        </button>
      </div>

      {/* KPI */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-lg border p-4">
          <p className="text-xs text-gray-500">Activities Logged</p>
          <p className="text-2xl font-bold text-gray-800 mt-1">{activities.length}</p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-xs text-gray-500">Total Emissions (kgCO₂e)</p>
          <p className="text-2xl font-bold text-red-600 mt-1">{totalEmission.toLocaleString(undefined, { maximumFractionDigits: 1 })}</p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-xs text-gray-500">Auto-Imported</p>
          <p className="text-2xl font-bold text-blue-600 mt-1">{activities.filter((a) => a.is_auto_imported).length}</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap items-end">
        <select
          value={filterSource}
          onChange={(e) => setFilterSource(e.target.value as SourceType | "")}
          className="border rounded-lg px-3 py-2 text-sm"
        >
          <option value="">All Sources</option>
          {(Object.keys(SOURCE_TYPE_LABELS) as SourceType[]).map((s) => (
            <option key={s} value={s}>{SOURCE_TYPE_LABELS[s]}</option>
          ))}
        </select>
        <div>
          <label className="block text-xs text-gray-500 mb-1">From</label>
          <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="border rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">To</label>
          <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="border rounded-lg px-3 py-2 text-sm" />
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
            <tr>
              <th className="px-4 py-3 text-left">Date</th>
              <th className="px-4 py-3 text-left">Source</th>
              <th className="px-4 py-3 text-right">Quantity</th>
              <th className="px-4 py-3 text-left">Unit</th>
              <th className="px-4 py-3 text-right">kgCO₂e</th>
              <th className="px-4 py-3 text-left">Scope</th>
              <th className="px-4 py-3 text-left">Ref</th>
              <th className="px-4 py-3 text-left">Import</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>
            ) : activities.length === 0 ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">No activities logged. Use &ldquo;Log Activity&rdquo; or import fleet fuel data.</td></tr>
            ) : (
              activities.map((a) => (
                <tr key={a.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-sm">{a.activity_date}</td>
                  <td className="px-4 py-2">{SOURCE_TYPE_LABELS[a.source_type] || a.source_type}</td>
                  <td className="px-4 py-2 text-right font-medium">{Number(a.quantity).toLocaleString()}</td>
                  <td className="px-4 py-2 text-gray-500">{a.unit}</td>
                  <td className="px-4 py-2 text-right font-semibold text-red-600">
                    {a.calculated_emission_kgco2e != null ? Number(a.calculated_emission_kgco2e).toFixed(2) : <span className="text-gray-300">—</span>}
                  </td>
                  <td className="px-4 py-2">
                    {a.scope ? (
                      <span className={`px-2 py-0.5 rounded-full text-xs ${SCOPE_BADGE[a.scope]}`}>{a.scope}</span>
                    ) : <span className="text-gray-300 text-xs">No factor</span>}
                  </td>
                  <td className="px-4 py-2 text-xs text-gray-400">{a.source_reference || "—"}</td>
                  <td className="px-4 py-2 text-xs">
                    {a.is_auto_imported && <span className="px-1.5 py-0.5 rounded bg-blue-50 text-blue-600">auto</span>}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Create Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <h2 className="text-lg font-semibold mb-4">Log Activity</h2>
            <form onSubmit={handleSave} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Source Type *</label>
                <select
                  required
                  value={form.source_type}
                  onChange={(e) => handleSourceChange(e.target.value as SourceType)}
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                >
                  {(Object.keys(SOURCE_TYPE_LABELS) as SourceType[]).map((s) => (
                    <option key={s} value={s}>{SOURCE_TYPE_LABELS[s]}</option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium mb-1">Activity Date *</label>
                  <input
                    required type="date"
                    value={form.activity_date}
                    onChange={(e) => setForm({ ...form, activity_date: e.target.value })}
                    className="w-full border rounded-lg px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Quantity *</label>
                  <input
                    required type="number" step="0.0001"
                    value={form.quantity}
                    onChange={(e) => setForm({ ...form, quantity: e.target.value })}
                    className="w-full border rounded-lg px-3 py-2 text-sm"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium mb-1">Unit</label>
                  <input
                    value={form.unit}
                    onChange={(e) => setForm({ ...form, unit: e.target.value })}
                    className="w-full border rounded-lg px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Reference</label>
                  <input
                    value={form.source_reference}
                    onChange={(e) => setForm({ ...form, source_reference: e.target.value })}
                    className="w-full border rounded-lg px-3 py-2 text-sm"
                    placeholder="Vehicle ID, meter ID…"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Notes</label>
                <textarea
                  value={form.notes}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm" rows={2}
                />
              </div>
              {error && <p className="text-red-600 text-sm">{error}</p>}
              <div className="flex gap-2 pt-1">
                <button type="button" onClick={() => setShowModal(false)} className="flex-1 py-2 border rounded-lg text-sm hover:bg-gray-50">Cancel</button>
                <button type="submit" disabled={saving} className="flex-1 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50">
                  {saving ? "Saving…" : "Log Activity"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
