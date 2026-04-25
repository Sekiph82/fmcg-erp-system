"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { dimApi, DimValue } from "@/lib/dimensions";

export default function DimValuesPage() {
  const qc = useQueryClient();
  const [selectedTypeId, setSelectedTypeId] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    dim_code: "", dim_name: "", parent_id: "", notes: "",
    start_date: "", end_date: "", active: true,
  });

  const { data: types = [] } = useQuery({
    queryKey: ["dim-types"],
    queryFn: () => dimApi.getTypes(),
  });

  const { data: values = [], isLoading } = useQuery({
    queryKey: ["dim-values", selectedTypeId],
    queryFn: () => dimApi.getValues(selectedTypeId || undefined),
    enabled: true,
  });

  const create = useMutation({
    mutationFn: () => dimApi.createValue({
      dim_type_id: selectedTypeId,
      dim_code: form.dim_code,
      dim_name: form.dim_name,
      parent_id: form.parent_id || undefined,
      active: form.active,
      start_date: form.start_date || undefined,
      end_date: form.end_date || undefined,
      notes: form.notes || undefined,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["dim-values"] });
      setShowForm(false);
      setForm({ dim_code: "", dim_name: "", parent_id: "", notes: "", start_date: "", end_date: "", active: true });
    },
  });

  const set = (k: string, v: any) => setForm((f) => ({ ...f, [k]: v }));

  const rootValues = values.filter((v) => !v.parent_id);
  const getChildren = (parentId: string) => values.filter((v) => v.parent_id === parentId);

  const renderTree = (parentId: string | null, depth = 0): JSX.Element[] => {
    const items = parentId ? getChildren(parentId) : rootValues;
    return items.flatMap((v) => [
      <tr key={v.id} className="border-b border-blue-900/20 hover:bg-blue-950/20 transition-colors">
        <td className="px-4 py-3">
          <span style={{ paddingLeft: depth * 20 }} className="font-mono text-xs text-indigo-300">{v.dim_code}</span>
        </td>
        <td className="px-4 py-3 text-gray-200" style={{ paddingLeft: 16 + depth * 20 }}>
          {depth > 0 && <span className="text-gray-600 mr-2">└─</span>}{v.dim_name}
        </td>
        <td className="px-4 py-3 text-xs text-gray-400">{v.dim_type_name}</td>
        <td className="px-4 py-3 text-center text-xs text-gray-400">L{v.level_no}</td>
        <td className="px-4 py-3 text-center text-xs text-gray-400">{v.children_count}</td>
        <td className="px-4 py-3 text-center">
          <span className={`px-2 py-0.5 rounded-full text-xs ${v.active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
            {v.active ? "Active" : "Inactive"}
          </span>
        </td>
      </tr>,
      ...renderTree(v.id, depth + 1),
    ]);
  };

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dimension Value Tree Manager</h1>
          <p className="text-sm text-gray-500">Hierarchical values for each dimension axis.</p>
        </div>
        <button onClick={() => setShowForm(!showForm)} disabled={!selectedTypeId}
          className="glow-button disabled:opacity-50">
          {showForm ? "Cancel" : "+ Add Value"}
        </button>
      </div>

      <div className="liquid-glass p-4 flex items-end gap-4">
        <div className="flex flex-col gap-1 flex-1 max-w-xs">
          <label className="text-xs text-gray-500">Filter by Dimension Type</label>
          <select value={selectedTypeId} onChange={(e) => setSelectedTypeId(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
            <option value="">— All Types —</option>
            {types.map((t) => <option key={t.id} value={t.id}>{t.type_name}</option>)}
          </select>
        </div>
      </div>

      {showForm && selectedTypeId && (
        <div className="liquid-glass p-5 space-y-4">
          <h2 className="text-sm font-semibold text-gray-700">New Value</h2>
          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Code *</label>
              <input type="text" value={form.dim_code} onChange={(e) => set("dim_code", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Name *</label>
              <input type="text" value={form.dim_name} onChange={(e) => set("dim_name", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Parent (optional)</label>
              <select value={form.parent_id} onChange={(e) => set("parent_id", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
                <option value="">— Root Level —</option>
                {values.filter((v) => v.dim_type_id === selectedTypeId).map((v) => (
                  <option key={v.id} value={v.id}>{v.dim_name}</option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Notes</label>
              <input type="text" value={form.notes} onChange={(e) => set("notes", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            </div>
          </div>
          <button onClick={() => create.mutate()} disabled={create.isPending || !form.dim_code || !form.dim_name}
            className="glow-button">
            {create.isPending ? "Creating…" : "Create Value"}
          </button>
        </div>
      )}

      <div className="glass-table overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-blue-900/30">
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Code</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Name</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Type</th>
              <th className="text-center px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Level</th>
              <th className="text-center px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Children</th>
              <th className="text-center px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Status</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={6} className="text-center py-10 text-gray-400">Loading…</td></tr>
            ) : values.length === 0 ? (
              <tr><td colSpan={6} className="text-center py-10 text-gray-400">No values. Select a type and add values.</td></tr>
            ) : renderTree(null)}
          </tbody>
        </table>
      </div>
    </div>
  );
}
