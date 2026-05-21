"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { dimApi, DimValidationRule, ValidationSeverity } from "@/lib/dimensions";

export default function ValidationRulesPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    rule_name: "", transaction_type: "", gl_account_pattern: "",
    module: "", dim_type_id: "", severity: "WARN" as ValidationSeverity,
    active: true, notes: "",
  });

  const { data: rules = [], isLoading } = useQuery({
    queryKey: ["dim-validation-rules"],
    queryFn: () => dimApi.getValidationRules(),
  });

  const { data: types = [] } = useQuery({
    queryKey: ["dim-types"],
    queryFn: () => dimApi.getTypes(),
  });

  const create = useMutation({
    mutationFn: () => dimApi.createValidationRule({
      ...form,
      transaction_type: form.transaction_type || undefined,
      gl_account_pattern: form.gl_account_pattern || undefined,
      module: form.module || undefined,
      notes: form.notes || undefined,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["dim-validation-rules"] });
      setShowForm(false);
    },
  });

  const set = (k: string, v: any) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dimension Validation Rules</h1>
          <p className="text-sm text-gray-500">Define which dimensions are required for specific transaction types, GL accounts, or modules.</p>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="glow-button">
          {showForm ? "Cancel" : "+ New Rule"}
        </button>
      </div>

      {showForm && (
        <div className="liquid-glass p-5 space-y-4">
          <h2 className="text-sm font-semibold text-gray-700">New Validation Rule</h2>
          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1 col-span-2">
              <label className="text-xs text-gray-500">Rule Name *</label>
              <input type="text" value={form.rule_name} onChange={(e) => set("rule_name", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Required Dimension *</label>
              <select value={form.dim_type_id} onChange={(e) => set("dim_type_id", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
                <option value="">— Select Dimension —</option>
                {types.map((t) => <option key={t.id} value={t.id}>{t.type_name}</option>)}
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Severity</label>
              <select value={form.severity} onChange={(e) => set("severity", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
                <option value="WARN">Warning (allow proceed)</option>
                <option value="BLOCK">Block (prevent save)</option>
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Transaction Type (optional)</label>
              <input type="text" value={form.transaction_type} onChange={(e) => set("transaction_type", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm" placeholder="e.g. journal_entry" />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Module (optional)</label>
              <input type="text" value={form.module} onChange={(e) => set("module", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm" placeholder="e.g. payroll" />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">GL Account Pattern (optional)</label>
              <input type="text" value={form.gl_account_pattern} onChange={(e) => set("gl_account_pattern", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm" placeholder="e.g. 6%" />
            </div>
          </div>
          <button onClick={() => create.mutate()}
            disabled={create.isPending || !form.rule_name || !form.dim_type_id}
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
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Required Dimension</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Tx Type</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Module</th>
              <th className="text-center px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Severity</th>
              <th className="text-center px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Active</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={6} className="text-center py-10 text-gray-400">Loading…</td></tr>
            ) : rules.length === 0 ? (
              <tr><td colSpan={6} className="text-center py-10 text-gray-400">No validation rules. Create one above.</td></tr>
            ) : rules.map((r) => (
              <tr key={r.id} className="border-b border-blue-900/20 hover:bg-blue-950/20 transition-colors">
                <td className="px-4 py-3 font-medium text-gray-200">{r.rule_name}</td>
                <td className="px-4 py-3 text-indigo-300">{r.dim_type_name}</td>
                <td className="px-4 py-3 text-xs text-gray-400">{r.transaction_type ?? "—"}</td>
                <td className="px-4 py-3 text-xs text-gray-400">{r.module ?? "—"}</td>
                <td className="px-4 py-3 text-center">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${r.severity === "BLOCK" ? "bg-red-100 text-red-700" : "bg-yellow-100 text-yellow-700"}`}>
                    {r.severity}
                  </span>
                </td>
                <td className="px-4 py-3 text-center">
                  <span className={`px-2 py-0.5 rounded-full text-xs ${r.active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                    {r.active ? "Active" : "Inactive"}
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
