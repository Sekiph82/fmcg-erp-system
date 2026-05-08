"use client";
import { useEffect, useState } from "react";
import { qmsApi, AQLPlan } from "@/lib/qms";

const BLANK = {
  plan_code: "", plan_name: "", product_id: "", material_id: "", product_category: "",
  lot_size_min: "", lot_size_max: "", sample_size: "",
  aql_level: "II", aql_value: "1.0",
  acceptance_number: "", rejection_number: "",
  inspection_level: "Normal", applies_to_type: "INCOMING",
  notes: "",
};

const AQL_LEVELS = ["I", "II", "III", "S1", "S2", "S3", "S4"];
const AQL_VALUES = ["0.065", "0.10", "0.15", "0.25", "0.40", "0.65", "1.0", "1.5", "2.5", "4.0", "6.5", "10", "15"];
const INSPECTION_TYPES = ["INCOMING", "IN_PROCESS", "FINISHED_GOODS", "RETEST"];
const INSPECTION_LEVELS = ["Normal", "Tightened", "Reduced"];

export default function AQLPage() {
  const [plans, setPlans] = useState<AQLPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [form, setForm] = useState({ ...BLANK });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const data = await qmsApi.listAQLPlans(false);
      setPlans(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const openCreate = () => { setForm({ ...BLANK }); setEditId(null); setError(""); setShowModal(true); };

  const openEdit = (p: AQLPlan) => {
    setForm({
      plan_code: p.plan_code, plan_name: p.plan_name,
      product_id: "", material_id: "",
      product_category: "",
      lot_size_min: String(p.lot_size_min),
      lot_size_max: p.lot_size_max != null ? String(p.lot_size_max) : "",
      sample_size: String(p.sample_size),
      aql_level: p.aql_level, aql_value: String(p.aql_value),
      acceptance_number: String(p.acceptance_number),
      rejection_number: String(p.rejection_number),
      inspection_level: p.inspection_level, applies_to_type: p.applies_to_type,
      notes: p.notes ?? "",
    });
    setEditId(p.id);
    setError("");
    setShowModal(true);
  };

  const save = async () => {
    if (!form.plan_code || !form.plan_name || !form.lot_size_min || !form.sample_size || !form.acceptance_number || !form.rejection_number) {
      setError("Plan code, name, lot size min, sample size, acceptance and rejection numbers required"); return;
    }
    setSaving(true); setError("");
    try {
      const payload = {
        plan_code: form.plan_code,
        plan_name: form.plan_name,
        product_id: form.product_id || null,
        material_id: form.material_id || null,
        product_category: form.product_category || null,
        lot_size_min: parseInt(form.lot_size_min),
        lot_size_max: form.lot_size_max ? parseInt(form.lot_size_max) : null,
        sample_size: parseInt(form.sample_size),
        aql_level: form.aql_level,
        aql_value: parseFloat(form.aql_value),
        acceptance_number: parseInt(form.acceptance_number),
        rejection_number: parseInt(form.rejection_number),
        inspection_level: form.inspection_level,
        applies_to_type: form.applies_to_type,
        notes: form.notes || null,
      };
      if (editId) {
        await qmsApi.updateAQLPlan(editId, payload);
      } else {
        await qmsApi.createAQLPlan(payload);
      }
      setShowModal(false);
      await load();
    } catch {
      setError("Failed to save");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">AQL Sampling Plans</h1>
          <p className="text-xs text-gray-500 mt-0.5">
            Acceptance Quality Limit sampling plans per lot size. Define sample size, acceptance and rejection numbers.
          </p>
        </div>
        <button onClick={openCreate}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          + New Plan
        </button>
      </div>

      <div className="bg-blue-50 border border-blue-100 rounded-lg px-4 py-3">
        <p className="text-xs text-blue-700 font-medium mb-1">AQL Sampling Standard (ISO 2859 / ANSI Z1.4)</p>
        <p className="text-xs text-blue-600">
          AQL is the maximum defect rate considered acceptable. Sample size and acceptance/rejection numbers
          are determined by lot size and inspection level. Level II Normal is standard for most FMCG incoming inspections.
          Acceptance number = max defects to accept. Rejection number = min defects to reject.
        </p>
      </div>

      {loading ? (
        <p className="text-sm text-gray-500">Loading…</p>
      ) : plans.length === 0 ? (
        <div className="bg-white border rounded-lg p-10 text-center text-gray-400">
          <p className="text-2xl mb-2">📊</p>
          <p className="text-sm">No AQL sampling plans defined.</p>
        </div>
      ) : (
        <div className="bg-white border rounded-lg shadow-sm overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {["Code", "Name", "Product", "Lot Size", "Sample Size", "AQL Level", "AQL %", "Accept", "Reject", "Level", "Type", "Actions"].map(h => (
                  <th key={h} className="px-3 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {plans.map(p => (
                <tr key={p.id} className={`hover:bg-gray-50 ${!p.is_active ? "opacity-60" : ""}`}>
                  <td className="px-3 py-3 font-mono text-xs text-gray-700">{p.plan_code}</td>
                  <td className="px-3 py-3 text-xs font-medium text-gray-800">{p.plan_name}</td>
                  <td className="px-3 py-3 text-xs text-gray-600">{p.product_name ?? "Any"}</td>
                  <td className="px-3 py-3 text-xs text-gray-600">
                    {p.lot_size_min.toLocaleString()}
                    {p.lot_size_max != null ? ` – ${p.lot_size_max.toLocaleString()}` : "+"}
                  </td>
                  <td className="px-3 py-3 text-xs font-semibold text-blue-700">{p.sample_size}</td>
                  <td className="px-3 py-3 text-xs text-gray-600">{p.aql_level}</td>
                  <td className="px-3 py-3 text-xs text-gray-600">{p.aql_value}%</td>
                  <td className="px-3 py-3 text-xs font-semibold text-green-700">{p.acceptance_number}</td>
                  <td className="px-3 py-3 text-xs font-semibold text-red-600">{p.rejection_number}</td>
                  <td className="px-3 py-3 text-xs text-gray-600">{p.inspection_level}</td>
                  <td className="px-3 py-3 text-xs">
                    <span className="bg-gray-100 text-gray-600 rounded px-1.5 py-0.5">{p.applies_to_type}</span>
                  </td>
                  <td className="px-3 py-3">
                    <button onClick={() => openEdit(p)} className="text-xs text-blue-600 hover:underline">Edit</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h2 className="text-base font-semibold">{editId ? "Edit AQL Plan" : "New AQL Plan"}</h2>
              <button onClick={() => setShowModal(false)} className="text-gray-400 text-xl">×</button>
            </div>
            <div className="p-6 space-y-4">
              {error && <p className="text-xs text-red-500 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>}
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: "Plan Code *", key: "plan_code", placeholder: "AQL-FG-001", col: 1 },
                  { label: "Plan Name *", key: "plan_name", placeholder: "Finished Goods AQL", col: 1 },
                  { label: "Lot Size Min *", key: "lot_size_min", type: "number", placeholder: "1", col: 1 },
                  { label: "Lot Size Max", key: "lot_size_max", type: "number", placeholder: "empty = unlimited", col: 1 },
                  { label: "Sample Size *", key: "sample_size", type: "number", placeholder: "80", col: 1 },
                  { label: "Acceptance No. *", key: "acceptance_number", type: "number", placeholder: "3", col: 1 },
                  { label: "Rejection No. *", key: "rejection_number", type: "number", placeholder: "4", col: 1 },
                ].map(f => (
                  <div key={f.key} className={f.col === 2 ? "col-span-2" : ""}>
                    <label className="block text-xs font-medium text-gray-600 mb-1">{f.label}</label>
                    <input type={f.type ?? "text"} placeholder={f.placeholder}
                      value={(form as Record<string, string>)[f.key]}
                      onChange={e => setForm(prev => ({ ...prev, [f.key]: e.target.value }))}
                      className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                    />
                  </div>
                ))}
                {[
                  { label: "AQL Level", key: "aql_level", options: AQL_LEVELS },
                  { label: "AQL Value (%)", key: "aql_value", options: AQL_VALUES },
                  { label: "Inspection Level", key: "inspection_level", options: INSPECTION_LEVELS },
                  { label: "Applies To", key: "applies_to_type", options: INSPECTION_TYPES },
                ].map(f => (
                  <div key={f.key}>
                    <label className="block text-xs font-medium text-gray-600 mb-1">{f.label}</label>
                    <select value={(form as Record<string, string>)[f.key]}
                      onChange={e => setForm(prev => ({ ...prev, [f.key]: e.target.value }))}
                      className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none">
                      {f.options.map(o => <option key={o} value={o}>{o}</option>)}
                    </select>
                  </div>
                ))}
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
                  <textarea value={form.notes}
                    onChange={e => setForm(prev => ({ ...prev, notes: e.target.value }))}
                    rows={2} className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none resize-none"
                  />
                </div>
              </div>
            </div>
            <div className="px-6 pb-5 flex gap-3">
              <button onClick={save} disabled={saving}
                className="flex-1 rounded bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
                {saving ? "Saving…" : editId ? "Update" : "Create Plan"}
              </button>
              <button onClick={() => setShowModal(false)}
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
