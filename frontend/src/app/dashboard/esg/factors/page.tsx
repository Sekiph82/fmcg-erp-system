"use client";

import { useState, useEffect } from "react";
import { esgApi, EmissionFactor, SourceType, EmissionScope, SOURCE_TYPE_LABELS } from "@/lib/esg";

const SCOPE_COLORS: Record<EmissionScope, string> = {
  SCOPE1: "bg-red-100 text-red-700",
  SCOPE2: "bg-orange-100 text-orange-700",
  SCOPE3: "bg-yellow-100 text-yellow-700",
};

export default function EmissionFactorsPage() {
  const [factors, setFactors] = useState<EmissionFactor[]>([]);
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [editFactor, setEditFactor] = useState<EmissionFactor | null>(null);
  const [form, setForm] = useState({
    factor_code: "",
    source_type: "FUEL_DIESEL" as SourceType,
    region: "KE",
    valid_from: "2024-01-01",
    factor_value: "",
    unit: "kgCO2e/liter",
    scope: "SCOPE1" as EmissionScope,
    source_reference: "",
    is_active: true,
    notes: "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      setFactors(await esgApi.listFactors());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const openCreate = () => {
    setEditFactor(null);
    setForm({ factor_code: "", source_type: "FUEL_DIESEL", region: "KE", valid_from: "2024-01-01", factor_value: "", unit: "kgCO2e/liter", scope: "SCOPE1", source_reference: "", is_active: true, notes: "" });
    setError("");
    setShowModal(true);
  };

  const openEdit = (f: EmissionFactor) => {
    setEditFactor(f);
    setForm({
      factor_code: f.factor_code,
      source_type: f.source_type,
      region: f.region,
      valid_from: f.valid_from,
      factor_value: String(f.factor_value),
      unit: f.unit,
      scope: f.scope,
      source_reference: f.source_reference || "",
      is_active: f.is_active,
      notes: f.notes || "",
    });
    setError("");
    setShowModal(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const payload = { ...form, factor_value: parseFloat(form.factor_value) };
      if (editFactor) {
        await esgApi.updateFactor(editFactor.id, { factor_value: payload.factor_value, source_reference: payload.source_reference, is_active: payload.is_active, notes: payload.notes || undefined });
      } else {
        await esgApi.createFactor(payload as any);
      }
      setShowModal(false);
      load();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const handleSeed = async () => {
    const res = await esgApi.seedFactors();
    alert(res.message);
    load();
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Emission Factors</h1>
          <p className="text-sm text-gray-500 mt-1">Manage GHG emission conversion factors</p>
        </div>
        <div className="flex gap-2">
          <button onClick={handleSeed} className="px-4 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg">
            Seed Defaults
          </button>
          <button onClick={openCreate} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            + New Factor
          </button>
        </div>
      </div>

      <div className="bg-white rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
            <tr>
              <th className="px-4 py-3 text-left">Code</th>
              <th className="px-4 py-3 text-left">Source</th>
              <th className="px-4 py-3 text-right">Factor Value</th>
              <th className="px-4 py-3 text-left">Unit</th>
              <th className="px-4 py-3 text-left">Scope</th>
              <th className="px-4 py-3 text-left">Region</th>
              <th className="px-4 py-3 text-left">Valid From</th>
              <th className="px-4 py-3 text-left">Source Ref</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan={10} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>
            ) : factors.length === 0 ? (
              <tr><td colSpan={10} className="px-4 py-8 text-center text-gray-400">No factors. Click &quot;Seed Defaults&quot; to load GHG Protocol factors.</td></tr>
            ) : (
              factors.map((f) => (
                <tr key={f.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 font-mono text-xs font-semibold">{f.factor_code}</td>
                  <td className="px-4 py-2 text-xs">{SOURCE_TYPE_LABELS[f.source_type] || f.source_type}</td>
                  <td className="px-4 py-2 text-right font-semibold">{Number(f.factor_value).toFixed(6)}</td>
                  <td className="px-4 py-2 text-xs text-gray-500">{f.unit}</td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-0.5 rounded-full text-xs ${SCOPE_COLORS[f.scope]}`}>{f.scope}</span>
                  </td>
                  <td className="px-4 py-2 text-xs">{f.region}</td>
                  <td className="px-4 py-2 text-xs text-gray-500">{f.valid_from}</td>
                  <td className="px-4 py-2 text-xs text-gray-400">{f.source_reference || "—"}</td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-0.5 rounded-full text-xs ${f.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-400"}`}>
                      {f.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    <button onClick={() => openEdit(f)} className="text-blue-600 hover:underline text-xs">Edit</button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6">
            <h2 className="text-lg font-semibold mb-4">{editFactor ? "Edit Factor" : "New Emission Factor"}</h2>
            <form onSubmit={handleSave} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium mb-1">Factor Code *</label>
                  <input required disabled={!!editFactor} value={form.factor_code} onChange={(e) => setForm({ ...form, factor_code: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm disabled:bg-gray-50" placeholder="KE-DIESEL-S1" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Region</label>
                  <input value={form.region} onChange={(e) => setForm({ ...form, region: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
              {!editFactor && (
                <>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-sm font-medium mb-1">Source Type *</label>
                      <select required value={form.source_type} onChange={(e) => setForm({ ...form, source_type: e.target.value as SourceType })} className="w-full border rounded-lg px-3 py-2 text-sm">
                        {(Object.keys(SOURCE_TYPE_LABELS) as SourceType[]).map((s) => (<option key={s} value={s}>{SOURCE_TYPE_LABELS[s]}</option>))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">Scope *</label>
                      <select required value={form.scope} onChange={(e) => setForm({ ...form, scope: e.target.value as EmissionScope })} className="w-full border rounded-lg px-3 py-2 text-sm">
                        {(["SCOPE1", "SCOPE2", "SCOPE3"] as EmissionScope[]).map((s) => (<option key={s} value={s}>{s}</option>))}
                      </select>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Valid From *</label>
                    <input required type="date" value={form.valid_from} onChange={(e) => setForm({ ...form, valid_from: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
                  </div>
                </>
              )}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium mb-1">Factor Value (kgCO₂e/unit) *</label>
                  <input required type="number" step="0.00000001" value={form.factor_value} onChange={(e) => setForm({ ...form, factor_value: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Unit</label>
                  <input value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Source Reference</label>
                <input value={form.source_reference} onChange={(e) => setForm({ ...form, source_reference: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="GHG Protocol 2023, IPCC AR6…" />
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="factor_active" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} className="rounded" />
                <label htmlFor="factor_active" className="text-sm">Active</label>
              </div>
              {error && <p className="text-red-600 text-sm">{error}</p>}
              <div className="flex gap-2 pt-1">
                <button type="button" onClick={() => setShowModal(false)} className="flex-1 py-2 border rounded-lg text-sm hover:bg-gray-50">Cancel</button>
                <button type="submit" disabled={saving} className="flex-1 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50">
                  {saving ? "Saving…" : editFactor ? "Update" : "Create"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
