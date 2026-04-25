"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { brApi, BRRule, BRRuleConditionType, BRERPTransactionType, ERP_TX_LABEL } from "@/lib/bank_reconciliation";

const CONDITION_LABELS: Record<BRRuleConditionType, string> = {
  NARRATION_CONTAINS:    "Narration contains",
  REFERENCE_STARTS_WITH: "Reference starts with",
  REFERENCE_CONTAINS:    "Reference contains",
  AMOUNT_EQUALS:         "Amount equals",
  AMOUNT_RANGE:          "Amount in range",
  PAYEE_NAME_CONTAINS:   "Payee name contains",
  ACCOUNT_SPECIFIC:      "Account-specific",
};

export default function RulesPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    rule_name: "",
    condition_type: "NARRATION_CONTAINS" as BRRuleConditionType,
    condition_value: "",
    target_transaction_type: "AR_PAYMENT" as BRERPTransactionType,
    auto_apply: true,
    confidence_weight: "0.8",
    priority: "100",
    notes: "",
  });

  const { data: rules = [], isLoading } = useQuery<BRRule[]>({
    queryKey: ["br-rules"],
    queryFn: () => brApi.listRules(),
  });

  const create = useMutation({
    mutationFn: () => brApi.createRule({
      ...form,
      confidence_weight: parseFloat(form.confidence_weight),
      priority: parseInt(form.priority),
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["br-rules"] });
      setShowForm(false);
    },
  });

  const toggle = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) => brApi.updateRule(id, { active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["br-rules"] }),
  });

  const del = useMutation({
    mutationFn: (id: string) => brApi.deleteRule(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["br-rules"] }),
  });

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Reconciliation Rules</h1>
          <p className="text-sm text-gray-500 mt-1">Auto-match pattern rules applied during reconciliation</p>
        </div>
        <button onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700">
          {showForm ? "Cancel" : "+ New Rule"}
        </button>
      </div>

      {showForm && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-5 space-y-4">
          <h2 className="text-sm font-semibold text-blue-800">New Rule</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-2">
              <label className="text-xs text-gray-500 font-medium">Rule Name *</label>
              <input type="text" value={form.rule_name} onChange={(e) => setForm({ ...form, rule_name: e.target.value })}
                className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                placeholder="e.g. Match M-Pesa collections" />
            </div>
            <div>
              <label className="text-xs text-gray-500 font-medium">Priority (lower = first)</label>
              <input type="number" value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}
                className="mt-1 w-full border rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-xs text-gray-500 font-medium">Condition Type</label>
              <select value={form.condition_type} onChange={(e) => setForm({ ...form, condition_type: e.target.value as BRRuleConditionType })}
                className="mt-1 w-full border rounded-lg px-3 py-2 text-sm">
                {Object.entries(CONDITION_LABELS).map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 font-medium">Condition Value *</label>
              <input type="text" value={form.condition_value} onChange={(e) => setForm({ ...form, condition_value: e.target.value })}
                className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                placeholder="e.g. BANK CHARGE or MPESA" />
            </div>
            <div>
              <label className="text-xs text-gray-500 font-medium">Target Transaction Type</label>
              <select value={form.target_transaction_type}
                onChange={(e) => setForm({ ...form, target_transaction_type: e.target.value as BRERPTransactionType })}
                className="mt-1 w-full border rounded-lg px-3 py-2 text-sm">
                {Object.entries(ERP_TX_LABEL).map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 font-medium">Confidence Weight (0–1)</label>
              <input type="number" step="0.05" min="0" max="1" value={form.confidence_weight}
                onChange={(e) => setForm({ ...form, confidence_weight: e.target.value })}
                className="mt-1 w-full border rounded-lg px-3 py-2 text-sm" />
            </div>
            <div className="flex items-center pt-5">
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="checkbox" checked={form.auto_apply}
                  onChange={(e) => setForm({ ...form, auto_apply: e.target.checked })} className="rounded" />
                Auto-apply
              </label>
            </div>
            <div>
              <label className="text-xs text-gray-500 font-medium">Notes</label>
              <input type="text" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })}
                className="mt-1 w-full border rounded-lg px-3 py-2 text-sm" />
            </div>
          </div>
          <button onClick={() => create.mutate()}
            disabled={create.isPending || !form.rule_name || !form.condition_value}
            className="px-5 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50">
            {create.isPending ? "Creating…" : "Create Rule"}
          </button>
        </div>
      )}

      {isLoading ? (
        <p className="text-gray-400">Loading…</p>
      ) : (
        <div className="bg-white border rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                {["Priority", "Rule Name", "Condition", "Target Type", "Confidence", "Auto", "Active", ""].map((h) => (
                  <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {rules.map((r: BRRule) => (
                <tr key={r.id} className={`hover:bg-gray-50 ${!r.active ? "opacity-50" : ""}`}>
                  <td className="px-4 py-2 font-mono text-xs">{r.priority}</td>
                  <td className="px-4 py-2 font-medium">{r.rule_name}</td>
                  <td className="px-4 py-2 text-xs text-gray-600">
                    <span className="font-medium">{CONDITION_LABELS[r.condition_type]}</span>{" "}
                    <span className="bg-gray-100 px-1 py-0.5 rounded font-mono">{r.condition_value}</span>
                  </td>
                  <td className="px-4 py-2 text-xs">{ERP_TX_LABEL[r.target_transaction_type]}</td>
                  <td className="px-4 py-2 text-xs">{(Number(r.confidence_weight) * 100).toFixed(0)}%</td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-0.5 rounded-full text-xs ${r.auto_apply ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                      {r.auto_apply ? "Auto" : "Manual"}
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    <button onClick={() => toggle.mutate({ id: r.id, active: !r.active })}
                      className={`px-2 py-0.5 rounded-full text-xs ${r.active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                      {r.active ? "Active" : "Inactive"}
                    </button>
                  </td>
                  <td className="px-4 py-2">
                    <button onClick={() => del.mutate(r.id)}
                      className="text-xs text-red-500 hover:text-red-700">
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
              {rules.length === 0 && (
                <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400 text-sm">No rules. Create one to automate matching.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
