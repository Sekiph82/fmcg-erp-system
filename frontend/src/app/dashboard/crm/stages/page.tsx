"use client";
import { useEffect, useState } from "react";
import { crmApi, CRMStage, STAGE_TYPE_LABELS, CRMStageType } from "@/lib/crm_pipeline";

export default function StageConfigPage() {
  const [stages, setStages] = useState<CRMStage[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [form, setForm] = useState({
    stage_code: "", stage_name: "", stage_type: "LEAD" as CRMStageType,
    default_probability: 0, sequence_no: 10, color_code: "#6B7280", active_flag: true,
  });
  const [saving, setSaving] = useState(false);

  const load = () => {
    setLoading(true);
    crmApi.getStages().then(setStages).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleSeed = async () => {
    setSeeding(true);
    try { await crmApi.seedDefaultStages(); load(); } catch (e) { console.error(e); }
    setSeeding(false);
  };

  const handleCreate = async () => {
    setSaving(true);
    try { await crmApi.createStage(form as Partial<CRMStage>); setShowCreate(false); load(); }
    catch (e) { console.error(e); }
    setSaving(false);
  };

  const handleToggle = async (stage: CRMStage) => {
    try { await crmApi.updateStage(stage.id, { active_flag: !stage.active_flag }); load(); }
    catch (e) { console.error(e); }
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Pipeline Stage Configuration</h1>
        <div className="flex gap-2">
          <button onClick={handleSeed} disabled={seeding}
            className="px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50 disabled:opacity-50">
            {seeding ? "Seeding…" : "Seed Defaults"}
          </button>
          <button onClick={() => setShowCreate(true)}
            className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            + New Stage
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl border shadow-sm overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-gray-50 text-xs text-gray-600">
              <th className="px-3 py-2 text-left">Seq</th>
              <th className="px-3 py-2 text-left">Color</th>
              <th className="px-3 py-2 text-left">Code</th>
              <th className="px-3 py-2 text-left">Name</th>
              <th className="px-3 py-2 text-left">Type</th>
              <th className="px-3 py-2 text-left">Default Prob %</th>
              <th className="px-3 py-2 text-left">Active</th>
              <th className="px-3 py-2 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading && <tr><td colSpan={8} className="px-3 py-6 text-center text-gray-400">Loading…</td></tr>}
            {!loading && stages.length === 0 && (
              <tr><td colSpan={8} className="px-3 py-6 text-center text-gray-400">
                No stages configured. Click "Seed Defaults" to add default stages.
              </td></tr>
            )}
            {stages.map(stage => (
              <tr key={stage.id} className="border-b hover:bg-gray-50">
                <td className="px-3 py-2 text-gray-500 font-mono text-xs">{stage.sequence_no}</td>
                <td className="px-3 py-2">
                  <div className="w-4 h-4 rounded-full" style={{ background: stage.color_code || "#6B7280" }} />
                </td>
                <td className="px-3 py-2 font-mono text-xs text-gray-600">{stage.stage_code}</td>
                <td className="px-3 py-2 font-medium text-gray-800">{stage.stage_name}</td>
                <td className="px-3 py-2 text-xs text-gray-500">{STAGE_TYPE_LABELS[stage.stage_type]}</td>
                <td className="px-3 py-2 text-gray-700">{stage.default_probability}%</td>
                <td className="px-3 py-2">
                  <span className={`px-2 py-0.5 rounded-full text-xs ${stage.active_flag ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                    {stage.active_flag ? "Active" : "Inactive"}
                  </span>
                </td>
                <td className="px-3 py-2">
                  <button onClick={() => handleToggle(stage)}
                    className="text-xs text-blue-600 hover:underline">
                    {stage.active_flag ? "Deactivate" : "Activate"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md space-y-3">
            <h2 className="font-semibold text-lg">New Pipeline Stage</h2>
            <input placeholder="Stage Code (e.g. QUALIFIED)" value={form.stage_code}
              onChange={e => setForm(f => ({ ...f, stage_code: e.target.value.toUpperCase() }))}
              className="w-full border rounded-lg px-3 py-2 text-sm font-mono" />
            <input placeholder="Stage Name" value={form.stage_name}
              onChange={e => setForm(f => ({ ...f, stage_name: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" />
            <select value={form.stage_type} onChange={e => setForm(f => ({ ...f, stage_type: e.target.value as CRMStageType }))}
              className="w-full border rounded-lg px-3 py-2 text-sm">
              {Object.entries(STAGE_TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <div className="flex gap-2">
              <input type="number" placeholder="Default Probability %" value={form.default_probability}
                onChange={e => setForm(f => ({ ...f, default_probability: +e.target.value }))}
                className="flex-1 border rounded-lg px-3 py-2 text-sm" min={0} max={100} />
              <input type="number" placeholder="Sequence No" value={form.sequence_no}
                onChange={e => setForm(f => ({ ...f, sequence_no: +e.target.value }))}
                className="flex-1 border rounded-lg px-3 py-2 text-sm" />
            </div>
            <div className="flex items-center gap-2">
              <label className="text-sm text-gray-600">Color:</label>
              <input type="color" value={form.color_code}
                onChange={e => setForm(f => ({ ...f, color_code: e.target.value }))}
                className="h-8 w-16 border rounded cursor-pointer" />
            </div>
            <div className="flex gap-2 pt-1">
              <button onClick={handleCreate} disabled={saving || !form.stage_code || !form.stage_name}
                className="flex-1 bg-blue-600 text-white py-2 rounded-lg text-sm disabled:opacity-50">
                {saving ? "Saving…" : "Create Stage"}
              </button>
              <button onClick={() => setShowCreate(false)} className="flex-1 border rounded-lg py-2 text-sm">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
