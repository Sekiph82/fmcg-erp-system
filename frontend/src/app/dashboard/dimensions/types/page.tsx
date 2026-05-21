"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { dimApi, DimType, DimensionScope } from "@/lib/dimensions";

const SCOPE_LABEL: Record<DimensionScope, string> = {
  FINANCIAL:   "Financial",
  OPERATIONAL: "Operational",
  BOTH:        "Both",
};

export default function DimTypesPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    type_code: "", type_name: "", dimension_scope: "BOTH" as DimensionScope,
    hierarchy_enabled: true, is_mandatory: false, notes: "",
  });

  const { data: types = [], isLoading } = useQuery({
    queryKey: ["dim-types"],
    queryFn: () => dimApi.getTypes(),
  });

  const create = useMutation({
    mutationFn: () => dimApi.createType(form),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["dim-types"] }); setShowForm(false); setForm({ type_code: "", type_name: "", dimension_scope: "BOTH", hierarchy_enabled: true, is_mandatory: false, notes: "" }); },
  });

  const set = (k: string, v: any) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dimension Type Manager</h1>
          <p className="text-sm text-gray-500">Define analysis axes — cost center, department, region, brand, etc.</p>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="glow-button">
          {showForm ? "Cancel" : "+ New Type"}
        </button>
      </div>

      {showForm && (
        <div className="liquid-glass p-5 space-y-4">
          <h2 className="text-sm font-semibold text-gray-700">New Dimension Type</h2>
          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Type Code *</label>
              <input type="text" value={form.type_code} onChange={(e) => set("type_code", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm" placeholder="e.g. COST_CENTER" />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Type Name *</label>
              <input type="text" value={form.type_name} onChange={(e) => set("type_name", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm" placeholder="e.g. Cost Center" />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Scope</label>
              <select value={form.dimension_scope} onChange={(e) => set("dimension_scope", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
                {(["FINANCIAL","OPERATIONAL","BOTH"] as DimensionScope[]).map(s => (
                  <option key={s} value={s}>{SCOPE_LABEL[s]}</option>
                ))}
              </select>
            </div>
            <div className="col-span-2 flex flex-col gap-1">
              <label className="text-xs text-gray-500">Notes</label>
              <input type="text" value={form.notes} onChange={(e) => set("notes", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            </div>
            <div className="flex items-center gap-4 col-span-2">
              <label className="flex items-center gap-2 cursor-pointer text-sm text-gray-700">
                <input type="checkbox" checked={form.hierarchy_enabled} onChange={(e) => set("hierarchy_enabled", e.target.checked)} className="rounded" />
                Hierarchy Enabled
              </label>
              <label className="flex items-center gap-2 cursor-pointer text-sm text-gray-700">
                <input type="checkbox" checked={form.is_mandatory} onChange={(e) => set("is_mandatory", e.target.checked)} className="rounded" />
                Mandatory
              </label>
            </div>
          </div>
          <button onClick={() => create.mutate()} disabled={create.isPending || !form.type_code || !form.type_name}
            className="glow-button">
            {create.isPending ? "Creating…" : "Create Type"}
          </button>
        </div>
      )}

      <div className="glass-table overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-blue-900/30">
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Code</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Name</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Scope</th>
              <th className="text-center px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Hierarchy</th>
              <th className="text-center px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Mandatory</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Values</th>
              <th className="text-center px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Active</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={7} className="text-center py-10 text-gray-400">Loading…</td></tr>
            ) : types.length === 0 ? (
              <tr><td colSpan={7} className="text-center py-10 text-gray-400">No dimension types yet. Create one above.</td></tr>
            ) : types.map((t) => (
              <tr key={t.id} className="border-b border-blue-900/20 hover:bg-blue-950/20 transition-colors">
                <td className="px-4 py-3 font-mono text-xs text-indigo-300">{t.type_code}</td>
                <td className="px-4 py-3 font-medium text-gray-200">{t.type_name}</td>
                <td className="px-4 py-3 text-gray-400">{SCOPE_LABEL[t.dimension_scope]}</td>
                <td className="px-4 py-3 text-center">{t.hierarchy_enabled ? "✓" : "—"}</td>
                <td className="px-4 py-3 text-center">
                  {t.is_mandatory ? <span className="px-2 py-0.5 rounded-full text-xs bg-red-100 text-red-700">Required</span> : "—"}
                </td>
                <td className="px-4 py-3 text-right text-gray-300">{t.value_count}</td>
                <td className="px-4 py-3 text-center">
                  <span className={`px-2 py-0.5 rounded-full text-xs ${t.active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                    {t.active ? "Active" : "Inactive"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
