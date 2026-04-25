"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { dimApi, CostCenter, CostCenterType, CC_TYPE_LABEL } from "@/lib/dimensions";

export default function CostCentersPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [filter, setFilter] = useState<CostCenterType | "">("");
  const [form, setForm] = useState({
    cost_center_code: "", cost_center_name: "",
    cost_center_type: "ADMIN" as CostCenterType,
    parent_id: "", department: "", notes: "", active: true,
  });

  const { data: costCenters = [], isLoading } = useQuery({
    queryKey: ["cost-centers"],
    queryFn: () => dimApi.getCostCenters(),
  });

  const create = useMutation({
    mutationFn: () => dimApi.createCostCenter({
      ...form,
      parent_id: form.parent_id || undefined,
      department: form.department || undefined,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cost-centers"] });
      setShowForm(false);
      setForm({ cost_center_code: "", cost_center_name: "", cost_center_type: "ADMIN", parent_id: "", department: "", notes: "", active: true });
    },
  });

  const set = (k: string, v: any) => setForm((f) => ({ ...f, [k]: v }));

  const filtered = filter ? costCenters.filter((cc) => cc.cost_center_type === filter) : costCenters;

  const TYPE_COLORS: Record<CostCenterType, string> = {
    PRODUCTION:  "bg-green-100 text-green-700",
    WAREHOUSE:   "bg-blue-100 text-blue-700",
    ADMIN:       "bg-gray-100 text-gray-700",
    SALES:       "bg-purple-100 text-purple-700",
    UTILITIES:   "bg-yellow-100 text-yellow-700",
    MAINTENANCE: "bg-orange-100 text-orange-700",
    CORPORATE:   "bg-indigo-100 text-indigo-700",
    PROJECT:     "bg-pink-100 text-pink-700",
    OTHER:       "bg-gray-100 text-gray-500",
  };

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Cost Center Master</h1>
          <p className="text-sm text-gray-500">Primary management accounting dimension with hierarchical structure.</p>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="glow-button">
          {showForm ? "Cancel" : "+ New Cost Center"}
        </button>
      </div>

      {showForm && (
        <div className="liquid-glass p-5 space-y-4">
          <h2 className="text-sm font-semibold text-gray-700">New Cost Center</h2>
          <div className="grid grid-cols-2 gap-4">
            {[
              ["cost_center_code", "Code *", "text"],
              ["cost_center_name", "Name *", "text"],
              ["department", "Department", "text"],
            ].map(([k, l, t]) => (
              <div key={k} className="flex flex-col gap-1">
                <label className="text-xs text-gray-500">{l}</label>
                <input type={t} value={(form as any)[k]} onChange={(e) => set(k, e.target.value)}
                  className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
              </div>
            ))}
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Type *</label>
              <select value={form.cost_center_type} onChange={(e) => set("cost_center_type", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
                {Object.entries(CC_TYPE_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Parent Cost Center</label>
              <select value={form.parent_id} onChange={(e) => set("parent_id", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
                <option value="">— Root Level —</option>
                {costCenters.map((cc) => <option key={cc.id} value={cc.id}>{cc.cost_center_code} — {cc.cost_center_name}</option>)}
              </select>
            </div>
            <div className="col-span-2 flex flex-col gap-1">
              <label className="text-xs text-gray-500">Notes</label>
              <input type="text" value={form.notes} onChange={(e) => set("notes", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            </div>
          </div>
          <button onClick={() => create.mutate()}
            disabled={create.isPending || !form.cost_center_code || !form.cost_center_name}
            className="glow-button">
            {create.isPending ? "Creating…" : "Create Cost Center"}
          </button>
        </div>
      )}

      <div className="liquid-glass p-3 flex items-center gap-3">
        <label className="text-xs text-gray-500">Filter by Type:</label>
        <select value={filter} onChange={(e) => setFilter(e.target.value as CostCenterType | "")}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
          <option value="">All Types</option>
          {Object.entries(CC_TYPE_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <span className="text-xs text-gray-400">{filtered.length} cost centers</span>
      </div>

      <div className="glass-table overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-blue-900/30">
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Code</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Name</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Type</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Parent</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Department</th>
              <th className="text-center px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Children</th>
              <th className="text-center px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Status</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={7} className="text-center py-10 text-gray-400">Loading…</td></tr>
            ) : filtered.length === 0 ? (
              <tr><td colSpan={7} className="text-center py-10 text-gray-400">No cost centers found.</td></tr>
            ) : filtered.map((cc) => (
              <tr key={cc.id} className="border-b border-blue-900/20 hover:bg-blue-950/20 transition-colors">
                <td className="px-4 py-3 font-mono text-xs text-indigo-300">{cc.cost_center_code}</td>
                <td className="px-4 py-3 font-medium text-gray-200">{cc.cost_center_name}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${TYPE_COLORS[cc.cost_center_type]}`}>
                    {CC_TYPE_LABEL[cc.cost_center_type]}
                  </span>
                </td>
                <td className="px-4 py-3 text-xs text-gray-400">{cc.parent_name ?? "—"}</td>
                <td className="px-4 py-3 text-xs text-gray-400">{cc.department ?? "—"}</td>
                <td className="px-4 py-3 text-center text-gray-300">{cc.children_count}</td>
                <td className="px-4 py-3 text-center">
                  <span className={`px-2 py-0.5 rounded-full text-xs ${cc.active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                    {cc.active ? "Active" : "Inactive"}
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
