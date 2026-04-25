"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { dimApi } from "@/lib/dimensions";

export default function DefaultRulesPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    rule_name: "", transaction_type: "", source_field: "",
    source_field_value: "", dim_type_id: "", dim_value_id: "", priority: "10", active: true,
  });

  const { data: rules = [], isLoading } = useQuery({
    queryKey: ["dim-default-rules"],
    queryFn: () => dimApi.getDefaultRules(),
  });
  const { data: types = [] } = useQuery({ queryKey: ["dim-types"], queryFn: () => dimApi.getTypes() });
  const { data: values = [] } = useQuery({ queryKey: ["dim-values-all"], queryFn: () => dimApi.getValues() });

  const create = useMutation({
    mutationFn: () => dimApi.createDefaultRule({
      rule_name: form.rule_name,
      transaction_type: form.transaction_type,
      source_field: form.source_field || undefined,
      source_field_value: form.source_field_value || undefined,
      dim_type_id: form.dim_type_id,
      dim_value_id: form.dim_value_id,
      priority: Number(form.priority),
      active: form.active,
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["dim-default-rules"] }); setShowForm(false); },
  });

  const set = (k: string, v: any) => setForm((f) => ({ ...f, [k]: v }));
  const filteredValues = values.filter((v) => v.dim_type_id === form.dim_type_id);

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Default Derivation Rules</h1>
          <p className="text-sm text-gray-500">Automatically assign dimensions based on transaction context.</p>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="glow-button">
          {showForm ? "Cancel" : "+ New Rule"}
        </button>
      </div>

      {showForm && (
        <div className="liquid-glass p-5 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1 col-span-2">
              <label className="text-xs text-gray-500">Rule Name *</label>
              <input type="text" value={form.rule_name} onChange={(e) => set("rule_name", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Transaction Type *</label>
              <input type="text" value={form.transaction_type} onChange={(e) => set("transaction_type", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm" placeholder="e.g. production_order" />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Priority (lower = first)</label>
              <input type="number" value={form.priority} onChange={(e) => set("priority", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm" min="1" />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Source Field (optional)</label>
              <input type="text" value={form.source_field} onChange={(e) => set("source_field", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm" placeholder="e.g. work_center" />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Source Value (optional)</label>
              <input type="text" value={form.source_field_value} onChange={(e) => set("source_field_value", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm" placeholder="e.g. LINE-2" />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Dimension Type *</label>
              <select value={form.dim_type_id} onChange={(e) => set("dim_type_id", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
                <option value="">— Select —</option>
                {types.map((t) => <option key={t.id} value={t.id}>{t.type_name}</option>)}
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Default Value *</label>
              <select value={form.dim_value_id} onChange={(e) => set("dim_value_id", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
                <option value="">— Select —</option>
                {filteredValues.map((v) => <option key={v.id} value={v.id}>{v.dim_name}</option>)}
              </select>
            </div>
          </div>
          <button onClick={() => create.mutate()}
            disabled={create.isPending || !form.rule_name || !form.transaction_type || !form.dim_type_id || !form.dim_value_id}
            className="glow-button">
            {create.isPending ? "Creating…" : "Create Rule"}
          </button>
        </div>
      )}

      <div className="glass-table overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-blue-900/30">
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Rule Name</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Tx Type</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Source Field</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Dimension</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Default Value</th>
              <th className="text-center px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Priority</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={6} className="text-center py-10 text-gray-400">Loading…</td></tr>
            ) : rules.length === 0 ? (
              <tr><td colSpan={6} className="text-center py-10 text-gray-400">No default rules yet.</td></tr>
            ) : rules.map((r) => (
              <tr key={r.id} className="border-b border-blue-900/20 hover:bg-blue-950/20 transition-colors">
                <td className="px-4 py-3 font-medium text-gray-200">{r.rule_name}</td>
                <td className="px-4 py-3 text-xs font-mono text-indigo-300">{r.transaction_type}</td>
                <td className="px-4 py-3 text-xs text-gray-400">{r.source_field ? `${r.source_field} = ${r.source_field_value}` : "Any"}</td>
                <td className="px-4 py-3 text-xs text-gray-400">{r.dim_type_name}</td>
                <td className="px-4 py-3 text-gray-300">{r.dim_value_name}</td>
                <td className="px-4 py-3 text-center text-gray-300">{r.priority}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
