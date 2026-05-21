"use client";
import { useEffect, useState } from "react";
import { qmsApi, QCTemplate } from "@/lib/qms";

export default function QCTemplatesPage() {
  const [templates, setTemplates] = useState<QCTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<QCTemplate | null>(null);
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState<Record<string, unknown>>({
    name: "", qc_type: "INCOMING", sampling_method: "FIXED",
    is_mandatory: true, blocks_progression: true, release_required: true, is_active: true,
    parameters: [],
  });

  const load = () => {
    setLoading(true);
    qmsApi.listTemplates({ active_only: false }).then(setTemplates).finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleCreate = async () => {
    await qmsApi.createTemplate(form);
    setShowNew(false);
    setForm({ name: "", qc_type: "INCOMING", sampling_method: "FIXED",
              is_mandatory: true, blocks_progression: true, release_required: true, is_active: true, parameters: [] });
    load();
  };

  const TYPE_COLORS: Record<string, string> = {
    INCOMING: "bg-sky-100 text-sky-800",
    IN_PROCESS: "bg-purple-100 text-purple-800",
    FINISHED_GOODS: "bg-emerald-100 text-emerald-800",
    RETEST: "bg-amber-100 text-amber-800",
  };

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">QC Templates</h1>
          <p className="text-sm text-gray-500 mt-0.5">Reusable inspection templates per product/material/stage</p>
        </div>
        <button
          onClick={() => setShowNew(true)}
          className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700"
        >
          + New Template
        </button>
      </div>

      {showNew && (
        <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
          <h3 className="font-semibold text-gray-800">Create QC Template</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-gray-500 block mb-1">Template Name *</label>
              <input className="border rounded-lg px-3 py-2 text-sm w-full"
                value={form.name as string} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">QC Type *</label>
              <select className="border rounded-lg px-3 py-2 text-sm w-full"
                value={form.qc_type as string} onChange={e => setForm(p => ({ ...p, qc_type: e.target.value }))}>
                <option value="INCOMING">Incoming (IQC)</option>
                <option value="IN_PROCESS">In-Process (IPQC)</option>
                <option value="FINISHED_GOODS">Final (FQC)</option>
                <option value="RETEST">Retest</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Sub-Type (optional)</label>
              <input className="border rounded-lg px-3 py-2 text-sm w-full" placeholder="MIXING / BULK / PACKAGING…"
                value={(form.qc_sub_type as string) || ""}
                onChange={e => setForm(p => ({ ...p, qc_sub_type: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Sampling Method</label>
              <select className="border rounded-lg px-3 py-2 text-sm w-full"
                value={form.sampling_method as string}
                onChange={e => setForm(p => ({ ...p, sampling_method: e.target.value }))}>
                <option value="FIXED">Fixed Size</option>
                <option value="PERCENTAGE">Percentage</option>
                <option value="FREQUENCY">Frequency (every N batches)</option>
                <option value="TIME_BASED">Time-Based</option>
                <option value="CCP_TRIGGERED">CCP Triggered</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Sample Size / %</label>
              <input type="number" className="border rounded-lg px-3 py-2 text-sm w-full"
                value={(form.sample_size as number) || ""}
                onChange={e => setForm(p => ({ ...p, sample_size: parseFloat(e.target.value) }))} />
            </div>
            <div className="flex items-center gap-4 pt-4">
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.is_mandatory as boolean}
                  onChange={e => setForm(p => ({ ...p, is_mandatory: e.target.checked }))} />
                Mandatory
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.blocks_progression as boolean}
                  onChange={e => setForm(p => ({ ...p, blocks_progression: e.target.checked }))} />
                Blocks Progression
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.release_required as boolean}
                  onChange={e => setForm(p => ({ ...p, release_required: e.target.checked }))} />
                Release Required
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.is_ccp_template as boolean || false}
                  onChange={e => setForm(p => ({ ...p, is_ccp_template: e.target.checked }))} />
                CCP Template
              </label>
            </div>
          </div>
          <div className="flex gap-3">
            <button onClick={handleCreate}
              className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700">
              Create
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
        ) : templates.length === 0 ? (
          <p className="px-5 py-8 text-gray-400 text-sm">No templates defined yet</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                {["Name", "QC Type", "Sub-Type", "Sampling", "Parameters", "Flags", "Status"].map(h => (
                  <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {templates.map(t => (
                <tr key={t.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => setSelected(selected?.id === t.id ? null : t)}>
                  <td className="px-4 py-3 font-medium text-gray-800">{t.name}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs ${TYPE_COLORS[t.qc_type] || "bg-gray-100"}`}>
                      {t.qc_type.replace("_", " ")}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500">{t.qc_sub_type || "—"}</td>
                  <td className="px-4 py-3 text-gray-500">{t.sampling_method.replace("_", " ")}</td>
                  <td className="px-4 py-3 text-gray-500">{t.parameters.length}</td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1 flex-wrap">
                      {t.is_mandatory && <span className="px-1.5 py-0.5 bg-red-50 text-red-700 text-xs rounded">Mandatory</span>}
                      {t.blocks_progression && <span className="px-1.5 py-0.5 bg-orange-50 text-orange-700 text-xs rounded">Blocks</span>}
                      {t.is_ccp_template && <span className="px-1.5 py-0.5 bg-teal-50 text-teal-700 text-xs rounded">CCP</span>}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs ${t.is_active ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-500"}`}>
                      {t.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {selected && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="font-semibold text-gray-800 mb-4">{selected.name} — Parameters</h3>
          {selected.parameters.length === 0 ? (
            <p className="text-gray-400 text-sm">No parameters defined for this template</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs uppercase text-gray-500">
                <tr>
                  {["#", "Parameter", "Type", "Unit", "Min", "Max", "Target", "Critical", "CCP"].map(h => (
                    <th key={h} className="px-3 py-2 text-left font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {selected.parameters.map((p, i) => (
                  <tr key={p.id}>
                    <td className="px-3 py-2 text-gray-400">{i + 1}</td>
                    <td className="px-3 py-2 font-medium text-gray-800">{p.parameter_name}</td>
                    <td className="px-3 py-2 text-gray-500">{p.parameter_type}</td>
                    <td className="px-3 py-2 text-gray-500">{p.unit || "—"}</td>
                    <td className="px-3 py-2 text-gray-500">{p.min_value ?? "—"}</td>
                    <td className="px-3 py-2 text-gray-500">{p.max_value ?? "—"}</td>
                    <td className="px-3 py-2 text-gray-500">{p.target_value || "—"}</td>
                    <td className="px-3 py-2">{p.is_critical ? "✓" : "—"}</td>
                    <td className="px-3 py-2">{p.is_ccp_parameter ? "✓" : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
