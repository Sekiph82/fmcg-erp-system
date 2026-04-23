"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { mfApi, FlowStage, StageType, QualityStatus } from "@/lib/materialFlow";

const STAGE_TYPE_COLORS: Record<string, string> = {
  RAW_WAREHOUSE: "bg-gray-100 text-gray-700",
  QUARANTINE_RAW: "bg-yellow-100 text-yellow-700",
  WEIGHING_ROOM: "bg-blue-100 text-blue-700",
  STAGED_LINE: "bg-cyan-100 text-cyan-700",
  MIXING: "bg-purple-100 text-purple-700",
  PREMIX: "bg-violet-100 text-violet-700",
  INTERMEDIATE_HOLD: "bg-indigo-100 text-indigo-700",
  BULK_TANK: "bg-emerald-100 text-emerald-700",
  QC_HOLD_TANK: "bg-orange-100 text-orange-700",
  RELEASED_BULK: "bg-green-100 text-green-700",
  FILLING_STAGING: "bg-teal-100 text-teal-700",
  PACKAGING_STAGING: "bg-pink-100 text-pink-700",
  SECONDARY_PACKING: "bg-rose-100 text-rose-700",
  PALLETIZATION: "bg-amber-100 text-amber-700",
  FG_QUARANTINE: "bg-yellow-200 text-yellow-800",
  FG_RELEASED: "bg-green-200 text-green-800",
  REWORK_HOLDING: "bg-orange-200 text-orange-800",
  SCRAP_HOLDING: "bg-red-100 text-red-700",
  TRANSIT: "bg-gray-200 text-gray-700",
};

const STAGE_TYPES: StageType[] = [
  "RAW_WAREHOUSE", "QUARANTINE_RAW", "WEIGHING_ROOM", "STAGED_LINE",
  "MIXING", "PREMIX", "INTERMEDIATE_HOLD", "BULK_TANK", "QC_HOLD_TANK",
  "RELEASED_BULK", "FILLING_STAGING", "PACKAGING_STAGING", "SECONDARY_PACKING",
  "PALLETIZATION", "FG_QUARANTINE", "FG_RELEASED", "REWORK_HOLDING",
  "SCRAP_HOLDING", "TRANSIT",
];

export default function StagesPage() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    stage_code: "",
    stage_name: "",
    stage_type: "RAW_WAREHOUSE" as StageType,
    quality_default_status: "QUARANTINE" as QualityStatus,
    sequence_no: "0",
    notes: "",
  });

  const { data } = useQuery<FlowStage[]>({
    queryKey: ["mf-stages"],
    queryFn: () => mfApi.listStages().then((r) => r.data),
  });

  const create = useMutation({
    mutationFn: () =>
      mfApi.createStage({
        ...form,
        sequence_no: parseInt(form.sequence_no),
        active_flag: true,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mf-stages"] });
      setShowCreate(false);
      setForm({ stage_code: "", stage_name: "", stage_type: "RAW_WAREHOUSE", quality_default_status: "QUARANTINE", sequence_no: "0", notes: "" });
    },
  });

  const stages = data || [];
  const grouped = STAGE_TYPES.reduce((acc, t) => {
    acc[t] = stages.filter((s) => s.stage_type === t);
    return acc;
  }, {} as Record<string, FlowStage[]>);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <a href="/dashboard/material-flow" className="text-sm text-indigo-600 hover:underline">← Dashboard</a>
          <h1 className="text-xl font-bold text-gray-900">Stage Configuration</h1>
        </div>
        <button onClick={() => setShowCreate(true)} className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700">+ Add Stage</button>
      </div>

      <div className="bg-blue-50 border border-blue-100 rounded p-3 text-xs text-blue-700">
        Stages represent physical and logical checkpoints in the factory flow. Configure all stages your plant uses before recording material movements.
      </div>

      {/* Summary */}
      <div className="grid grid-cols-4 gap-3">
        <div className="bg-white rounded-lg border p-3 text-center">
          <p className="text-xs text-gray-500">Total Stages</p>
          <p className="text-2xl font-bold text-gray-900">{stages.length}</p>
        </div>
        <div className="bg-white rounded-lg border p-3 text-center">
          <p className="text-xs text-gray-500">Active</p>
          <p className="text-2xl font-bold text-green-700">{stages.filter((s) => s.active_flag).length}</p>
        </div>
        <div className="bg-white rounded-lg border p-3 text-center">
          <p className="text-xs text-gray-500">Production Stages</p>
          <p className="text-2xl font-bold text-blue-700">{stages.filter((s) => ["MIXING", "PREMIX", "BULK_TANK", "FILLING_STAGING"].includes(s.stage_type)).length}</p>
        </div>
        <div className="bg-white rounded-lg border p-3 text-center">
          <p className="text-xs text-gray-500">FG / Warehouse</p>
          <p className="text-2xl font-bold text-purple-700">{stages.filter((s) => s.stage_type.startsWith("FG") || s.stage_type === "RAW_WAREHOUSE").length}</p>
        </div>
      </div>

      {/* Stage List */}
      <div className="bg-white rounded-lg border overflow-x-auto">
        <div className="px-4 py-3 border-b"><h2 className="font-semibold text-gray-900">All Configured Stages</h2></div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>{["Seq", "Code", "Name", "Type", "Default Quality", "Active"].map((h) => (
              <th key={h} className="px-4 py-2 text-left text-xs font-medium text-gray-600">{h}</th>
            ))}</tr>
          </thead>
          <tbody className="divide-y">
            {stages.map((s) => (
              <tr key={s.id} className="hover:bg-gray-50">
                <td className="px-4 py-2 text-xs text-gray-500">{s.sequence_no}</td>
                <td className="px-4 py-2 font-mono text-xs font-medium">{s.stage_code}</td>
                <td className="px-4 py-2 text-xs">{s.stage_name}</td>
                <td className="px-4 py-2">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STAGE_TYPE_COLORS[s.stage_type] || "bg-gray-100 text-gray-600"}`}>
                    {s.stage_type.replace(/_/g, " ")}
                  </span>
                </td>
                <td className="px-4 py-2 text-xs">{s.quality_default_status}</td>
                <td className="px-4 py-2">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${s.active_flag ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                    {s.active_flag ? "Active" : "Inactive"}
                  </span>
                </td>
              </tr>
            ))}
            {stages.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400 text-sm">No stages configured yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-[500px] space-y-4">
            <h2 className="font-bold text-gray-900">Add Flow Stage</h2>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Stage Code</label>
                <input value={form.stage_code} onChange={(e) => setForm((p) => ({ ...p, stage_code: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm" placeholder="e.g. BULK-TANK-01" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Stage Name</label>
                <input value={form.stage_name} onChange={(e) => setForm((p) => ({ ...p, stage_name: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm" placeholder="Bulk Storage Tank 1" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Stage Type</label>
                <select value={form.stage_type} onChange={(e) => setForm((p) => ({ ...p, stage_type: e.target.value as StageType }))} className="w-full border rounded px-3 py-2 text-sm">
                  {STAGE_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Default Quality</label>
                <select value={form.quality_default_status} onChange={(e) => setForm((p) => ({ ...p, quality_default_status: e.target.value as QualityStatus }))} className="w-full border rounded px-3 py-2 text-sm">
                  {["QUARANTINE", "PENDING_INSPECTION", "RELEASED", "QC_HOLD"].map((s) => <option key={s}>{s}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Sequence No</label>
                <input type="number" value={form.sequence_no} onChange={(e) => setForm((p) => ({ ...p, sequence_no: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
                <input value={form.notes} onChange={(e) => setForm((p) => ({ ...p, notes: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm" placeholder="Optional" />
              </div>
            </div>
            <div className="flex gap-2 justify-end pt-2">
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm text-gray-600 border rounded-lg hover:bg-gray-50">Cancel</button>
              <button onClick={() => create.mutate()} disabled={!form.stage_code || !form.stage_name} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                {create.isPending ? "Saving…" : "Create Stage"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
