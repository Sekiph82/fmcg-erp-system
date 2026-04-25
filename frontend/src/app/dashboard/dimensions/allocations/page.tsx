"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { dimApi, AllocationRule, AllocationBasis, AllocationFrequency, ALLOC_BASIS_LABEL } from "@/lib/dimensions";

export default function AllocationRulesPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [form, setForm] = useState({
    rule_code: "", rule_name: "",
    source_dim_type_id: "", source_dim_value_id: "", target_dim_type_id: "",
    allocation_basis: "FIXED_PCT" as AllocationBasis,
    frequency: "MONTHLY" as AllocationFrequency,
    gl_account_cost_pool: "", notes: "",
  });
  const [lines, setLines] = useState([{ target_dim_value_id: "", fixed_pct: "", weight_value: "" }]);

  const { data: rules = [], isLoading } = useQuery({
    queryKey: ["allocation-rules"],
    queryFn: () => dimApi.getAllocationRules(),
  });

  const { data: types = [] } = useQuery({ queryKey: ["dim-types"], queryFn: () => dimApi.getTypes() });
  const { data: values = [] } = useQuery({ queryKey: ["dim-values-all"], queryFn: () => dimApi.getValues() });

  const create = useMutation({
    mutationFn: () => dimApi.createAllocationRule({
      ...form,
      gl_account_cost_pool: form.gl_account_cost_pool || undefined,
      notes: form.notes || undefined,
      lines: lines.filter((l) => l.target_dim_value_id).map((l) => ({
        target_dim_value_id: l.target_dim_value_id,
        fixed_pct: l.fixed_pct ? Number(l.fixed_pct) : undefined,
        weight_value: l.weight_value ? Number(l.weight_value) : undefined,
        active: true,
      })),
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["allocation-rules"] });
      setShowForm(false);
    },
  });

  const addLine = () => setLines([...lines, { target_dim_value_id: "", fixed_pct: "", weight_value: "" }]);
  const setLine = (i: number, k: string, v: string) =>
    setLines(lines.map((l, idx) => idx === i ? { ...l, [k]: v } : l));
  const set = (k: string, v: any) => setForm((f) => ({ ...f, [k]: v }));

  const sourceValues = values.filter((v) => v.dim_type_id === form.source_dim_type_id);
  const targetValues = values.filter((v) => v.dim_type_id === form.target_dim_type_id);

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Allocation Rule Manager</h1>
          <p className="text-sm text-gray-500">Define how shared costs are distributed across dimensions.</p>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="glow-button">
          {showForm ? "Cancel" : "+ New Rule"}
        </button>
      </div>

      {showForm && (
        <div className="liquid-glass p-5 space-y-4">
          <h2 className="text-sm font-semibold text-gray-700">New Allocation Rule</h2>
          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Rule Code *</label>
              <input type="text" value={form.rule_code} onChange={(e) => set("rule_code", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Rule Name *</label>
              <input type="text" value={form.rule_name} onChange={(e) => set("rule_name", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Source Pool Dimension Type *</label>
              <select value={form.source_dim_type_id} onChange={(e) => set("source_dim_type_id", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
                <option value="">— Select —</option>
                {types.map((t) => <option key={t.id} value={t.id}>{t.type_name}</option>)}
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Source Pool Value *</label>
              <select value={form.source_dim_value_id} onChange={(e) => set("source_dim_value_id", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
                <option value="">— Select —</option>
                {sourceValues.map((v) => <option key={v.id} value={v.id}>{v.dim_name}</option>)}
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Target Dimension Type *</label>
              <select value={form.target_dim_type_id} onChange={(e) => set("target_dim_type_id", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
                <option value="">— Select —</option>
                {types.map((t) => <option key={t.id} value={t.id}>{t.type_name}</option>)}
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Allocation Basis</label>
              <select value={form.allocation_basis} onChange={(e) => set("allocation_basis", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
                {Object.entries(ALLOC_BASIS_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Frequency</label>
              <select value={form.frequency} onChange={(e) => set("frequency", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
                <option value="MONTHLY">Monthly</option>
                <option value="QUARTERLY">Quarterly</option>
                <option value="MANUAL">Manual</option>
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Cost Pool GL Account</label>
              <input type="text" value={form.gl_account_cost_pool} onChange={(e) => set("gl_account_cost_pool", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold text-gray-500 uppercase">Target Lines</h3>
              <button type="button" onClick={addLine} className="glow-button-secondary text-xs !py-1">+ Add Line</button>
            </div>
            {lines.map((line, i) => (
              <div key={i} className="grid grid-cols-3 gap-3 items-end">
                <div className="flex flex-col gap-1">
                  <label className="text-xs text-gray-500">Target Value</label>
                  <select value={line.target_dim_value_id} onChange={(e) => setLine(i, "target_dim_value_id", e.target.value)}
                    className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
                    <option value="">— Select —</option>
                    {targetValues.map((v) => <option key={v.id} value={v.id}>{v.dim_name}</option>)}
                  </select>
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-xs text-gray-500">Fixed % {form.allocation_basis === "FIXED_PCT" ? "*" : ""}</label>
                  <input type="number" value={line.fixed_pct} onChange={(e) => setLine(i, "fixed_pct", e.target.value)}
                    className="rounded-lg border border-gray-300 px-3 py-2 text-sm" min="0" max="100" />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-xs text-gray-500">Weight Value</label>
                  <input type="number" value={line.weight_value} onChange={(e) => setLine(i, "weight_value", e.target.value)}
                    className="rounded-lg border border-gray-300 px-3 py-2 text-sm" min="0" />
                </div>
              </div>
            ))}
          </div>

          <button onClick={() => create.mutate()}
            disabled={create.isPending || !form.rule_code || !form.rule_name || !form.source_dim_value_id || !form.target_dim_type_id}
            className="glow-button">
            {create.isPending ? "Creating…" : "Create Allocation Rule"}
          </button>
        </div>
      )}

      <div className="space-y-3">
        {isLoading ? (
          <div className="text-gray-400 text-sm text-center py-10">Loading…</div>
        ) : rules.length === 0 ? (
          <div className="liquid-glass p-8 text-center text-gray-400">No allocation rules. Create one above.</div>
        ) : rules.map((rule) => (
          <div key={rule.id} className="liquid-glass p-4 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="font-mono text-xs text-indigo-300">{rule.rule_code}</span>
                <span className="font-medium text-gray-200">{rule.rule_name}</span>
                <span className="px-2 py-0.5 rounded-full text-xs bg-blue-100 text-blue-700">
                  {ALLOC_BASIS_LABEL[rule.allocation_basis]}
                </span>
                <span className="text-xs text-gray-400">{rule.frequency}</span>
              </div>
              <button onClick={() => setExpanded(expanded === rule.id ? null : rule.id)}
                className="glow-button-secondary text-xs !py-1">
                {expanded === rule.id ? "Collapse" : "View Lines"}
              </button>
            </div>
            <div className="text-xs text-gray-400">
              Pool: <span className="text-gray-300">{rule.source_dim_value_name}</span>
              {" → "}Target Type: <span className="text-gray-300">{rule.target_dim_type_name}</span>
            </div>
            {expanded === rule.id && rule.lines.length > 0 && (
              <div className="mt-2 overflow-x-auto">
                <table className="w-full text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-blue-900/30">
                      <th className="text-left py-1 px-2 text-gray-400">Target</th>
                      <th className="text-right py-1 px-2 text-gray-400">Fixed %</th>
                      <th className="text-right py-1 px-2 text-gray-400">Weight</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rule.lines.map((l) => (
                      <tr key={l.id} className="border-b border-blue-900/10">
                        <td className="py-1 px-2 text-gray-300">{l.target_dim_value_name}</td>
                        <td className="py-1 px-2 text-right text-gray-300">{l.fixed_pct ?? "—"}%</td>
                        <td className="py-1 px-2 text-right text-gray-300">{l.weight_value ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
