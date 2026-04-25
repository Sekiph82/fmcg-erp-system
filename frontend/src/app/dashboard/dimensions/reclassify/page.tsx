"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { dimApi } from "@/lib/dimensions";

export default function ReclassifyPage() {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    transaction_type: "", transaction_id: "", dim_type_id: "",
    new_dim_value_id: "", reason: "", journal_entry_ref: "",
  });
  const [done, setDone] = useState(false);

  const { data: types = [] } = useQuery({ queryKey: ["dim-types"], queryFn: () => dimApi.getTypes() });
  const { data: values = [] } = useQuery({ queryKey: ["dim-values-all"], queryFn: () => dimApi.getValues() });
  const { data: history = [] } = useQuery({
    queryKey: ["dim-reclassifications"],
    queryFn: () => dimApi.getReclassifications(),
  });

  const submit = useMutation({
    mutationFn: () => dimApi.reclassify({
      transaction_type: form.transaction_type,
      transaction_id: form.transaction_id,
      dim_type_id: form.dim_type_id,
      new_dim_value_id: form.new_dim_value_id,
      reason: form.reason,
      journal_entry_ref: form.journal_entry_ref || undefined,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["dim-reclassifications"] });
      setDone(true);
      setForm({ transaction_type: "", transaction_id: "", dim_type_id: "", new_dim_value_id: "", reason: "", journal_entry_ref: "" });
      setTimeout(() => setDone(false), 3000);
    },
  });

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));
  const filteredValues = values.filter((v) => v.dim_type_id === form.dim_type_id);

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dimension Reclassification</h1>
        <p className="text-sm text-gray-500">Correct dimension tags on previously posted transactions with full audit trail.</p>
      </div>

      {done && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-sm text-green-700">
          ✓ Reclassification recorded successfully.
        </div>
      )}

      <div className="liquid-glass p-5 space-y-4 max-w-2xl">
        <h2 className="text-sm font-semibold text-gray-700">Reclassify Transaction</h2>
        <div className="grid grid-cols-2 gap-4">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Transaction Type *</label>
            <input type="text" value={form.transaction_type} onChange={(e) => set("transaction_type", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" placeholder="e.g. journal_entry" />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Transaction ID *</label>
            <input type="text" value={form.transaction_id} onChange={(e) => set("transaction_id", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" placeholder="UUID or ref number" />
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
            <label className="text-xs text-gray-500">New Dimension Value *</label>
            <select value={form.new_dim_value_id} onChange={(e) => set("new_dim_value_id", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
              <option value="">— Select —</option>
              {filteredValues.map((v) => <option key={v.id} value={v.id}>{v.dim_name}</option>)}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Journal Entry Ref</label>
            <input type="text" value={form.journal_entry_ref} onChange={(e) => set("journal_entry_ref", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          </div>
          <div className="flex flex-col gap-1 col-span-2">
            <label className="text-xs text-gray-500">Reason for Reclassification *</label>
            <textarea value={form.reason} onChange={(e) => set("reason", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" rows={2}
              placeholder="Explain why this reclassification is needed" />
          </div>
        </div>
        <button
          onClick={() => submit.mutate()}
          disabled={submit.isPending || !form.transaction_type || !form.transaction_id || !form.dim_type_id || !form.new_dim_value_id || !form.reason}
          className="glow-button"
        >
          {submit.isPending ? "Recording…" : "Record Reclassification"}
        </button>
      </div>

      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-gray-700">Reclassification History</h2>
        {history.length === 0 ? (
          <div className="liquid-glass p-8 text-center text-gray-400">No reclassifications recorded yet.</div>
        ) : (
          <div className="glass-table overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-blue-900/30">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Tx Type</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Tx ID</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Dimension</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Old Value</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">New Value</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Reason</th>
                </tr>
              </thead>
              <tbody>
                {history.map((r) => (
                  <tr key={r.id} className="border-b border-blue-900/20 hover:bg-blue-950/20 transition-colors">
                    <td className="px-4 py-3 text-xs font-mono text-indigo-300">{r.transaction_type}</td>
                    <td className="px-4 py-3 text-xs text-gray-400">{r.transaction_id.slice(0, 12)}…</td>
                    <td className="px-4 py-3 text-xs text-gray-300">{r.dim_type_name}</td>
                    <td className="px-4 py-3 text-xs text-red-400">{r.old_dim_value_name ?? "—"}</td>
                    <td className="px-4 py-3 text-xs text-green-400">{r.new_dim_value_name}</td>
                    <td className="px-4 py-3 text-xs text-gray-400 max-w-xs truncate">{r.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
