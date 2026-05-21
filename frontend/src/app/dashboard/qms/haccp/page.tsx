"use client";
import { useEffect, useState } from "react";
import { qmsApi, HazardAnalysis, RISK_BG, HazardType, RiskLevel } from "@/lib/qms";

const HAZARD_COLORS: Record<string, string> = {
  BIOLOGICAL: "bg-red-100 text-red-800",
  CHEMICAL: "bg-orange-100 text-orange-800",
  PHYSICAL: "bg-yellow-100 text-yellow-800",
  ALLERGEN: "bg-purple-100 text-purple-800",
  RADIOLOGICAL: "bg-gray-100 text-gray-800",
};

export default function HACCPPage() {
  const [hazards, setHazards] = useState<HazardAnalysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState<Record<string, unknown>>({
    process_step: "", hazard_type: "BIOLOGICAL", hazard_description: "",
    risk_level: "MEDIUM", control_measure: "", is_ccp: false, is_active: true,
  });

  const load = () => {
    setLoading(true);
    qmsApi.listHazards().then(setHazards).finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleCreate = async () => {
    const data = { ...form };
    if (data.likelihood_score && data.severity_score) {
      data.risk_score = (data.likelihood_score as number) * (data.severity_score as number);
    }
    await qmsApi.createHazard(data);
    setShowNew(false);
    load();
  };

  const total = hazards.length;
  const ccps = hazards.filter(h => h.is_ccp).length;
  const critical = hazards.filter(h => h.risk_level === "CRITICAL").length;
  const high = hazards.filter(h => h.risk_level === "HIGH").length;

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">HACCP — Hazard Analysis</h1>
          <p className="text-sm text-gray-500 mt-0.5">Identify and assess hazards at each process step</p>
        </div>
        <div className="flex gap-3">
          <a href="/dashboard/qms/ccp" className="px-4 py-2 bg-teal-600 text-white text-sm rounded-lg hover:bg-teal-700">
            CCP Monitoring →
          </a>
          <button onClick={() => setShowNew(true)}
            className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700">
            + Add Hazard
          </button>
        </div>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "Total Hazards", value: total },
          { label: "CCP-linked", value: ccps, color: "text-teal-700" },
          { label: "Critical Risk", value: critical, color: critical > 0 ? "text-red-700" : "text-green-700" },
          { label: "High Risk", value: high, color: high > 0 ? "text-orange-700" : "text-gray-800" },
        ].map(k => (
          <div key={k.label} className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide">{k.label}</p>
            <p className={`text-2xl font-bold mt-1 ${k.color || "text-gray-800"}`}>{k.value}</p>
          </div>
        ))}
      </div>

      {showNew && (
        <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
          <h3 className="font-semibold text-gray-800">New Hazard Analysis Record</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-gray-500 block mb-1">Process Step *</label>
              <input className="border rounded-lg px-3 py-2 text-sm w-full"
                placeholder="e.g. Pasteurization, Mixing, Filling…"
                value={form.process_step as string}
                onChange={e => setForm(p => ({ ...p, process_step: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Hazard Type *</label>
              <select className="border rounded-lg px-3 py-2 text-sm w-full"
                value={form.hazard_type as string}
                onChange={e => setForm(p => ({ ...p, hazard_type: e.target.value }))}>
                <option value="BIOLOGICAL">Biological</option>
                <option value="CHEMICAL">Chemical</option>
                <option value="PHYSICAL">Physical</option>
                <option value="ALLERGEN">Allergen</option>
                <option value="RADIOLOGICAL">Radiological</option>
              </select>
            </div>
            <div className="col-span-2">
              <label className="text-xs text-gray-500 block mb-1">Hazard Description *</label>
              <textarea className="border rounded-lg px-3 py-2 text-sm w-full" rows={2}
                value={form.hazard_description as string}
                onChange={e => setForm(p => ({ ...p, hazard_description: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Likelihood (1-5)</label>
              <input type="number" min={1} max={5} className="border rounded-lg px-3 py-2 text-sm w-full"
                value={(form.likelihood_score as number) || ""}
                onChange={e => setForm(p => ({ ...p, likelihood_score: parseInt(e.target.value) }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Severity (1-5)</label>
              <input type="number" min={1} max={5} className="border rounded-lg px-3 py-2 text-sm w-full"
                value={(form.severity_score as number) || ""}
                onChange={e => setForm(p => ({ ...p, severity_score: parseInt(e.target.value) }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Risk Level</label>
              <select className="border rounded-lg px-3 py-2 text-sm w-full"
                value={form.risk_level as string}
                onChange={e => setForm(p => ({ ...p, risk_level: e.target.value }))}>
                <option value="LOW">Low</option>
                <option value="MEDIUM">Medium</option>
                <option value="HIGH">High</option>
                <option value="CRITICAL">Critical</option>
              </select>
            </div>
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 text-sm mt-4">
                <input type="checkbox" checked={form.is_ccp as boolean}
                  onChange={e => setForm(p => ({ ...p, is_ccp: e.target.checked }))} />
                Is a Critical Control Point (CCP)
              </label>
            </div>
            <div className="col-span-2">
              <label className="text-xs text-gray-500 block mb-1">Control Measure *</label>
              <textarea className="border rounded-lg px-3 py-2 text-sm w-full" rows={2}
                value={form.control_measure as string}
                onChange={e => setForm(p => ({ ...p, control_measure: e.target.value }))} />
            </div>
          </div>
          <div className="flex gap-3">
            <button onClick={handleCreate}
              className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700">
              Save Hazard
            </button>
            <button onClick={() => setShowNew(false)}
              className="px-4 py-2 bg-gray-100 text-gray-700 text-sm rounded-lg hover:bg-gray-200">
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {loading ? (
          <p className="px-5 py-8 text-gray-400 text-sm">Loading…</p>
        ) : hazards.length === 0 ? (
          <p className="px-5 py-8 text-gray-400 text-sm">No hazard analyses recorded yet</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                {["Hazard #", "Process Step", "Hazard Type", "Description", "Risk", "Score", "Control Measure", "CCP"].map(h => (
                  <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {hazards.map(h => (
                <tr key={h.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-700">{h.hazard_no}</td>
                  <td className="px-4 py-3 text-gray-800">{h.process_step}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs ${HAZARD_COLORS[h.hazard_type] || "bg-gray-100"}`}>
                      {h.hazard_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-600 max-w-xs truncate">{h.hazard_description}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs ${RISK_BG[h.risk_level]}`}>
                      {h.risk_level}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500">{h.risk_score ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-600 max-w-xs truncate">{h.control_measure}</td>
                  <td className="px-4 py-3">
                    {h.is_ccp
                      ? <span className="px-2 py-0.5 bg-teal-100 text-teal-800 rounded text-xs font-semibold">CCP</span>
                      : <span className="text-gray-400">—</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
