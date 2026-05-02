"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { imApi, ToleranceRule } from "@/lib/invoice_match";

const blank = () => ({
  rule_name: "", supplier_id: "", item_category: "",
  quantity_tolerance_pct: "1", price_tolerance_pct: "2", tax_tolerance_pct: "0",
  auto_approve_within_tolerance: true, block_payment_beyond_tolerance: true,
  approval_role_required: "", is_active: true, priority: "10", notes: "",
});

export default function ToleranceRulesPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(blank());
  const [error, setError] = useState("");

  const { data: rules = [], isLoading } = useQuery<ToleranceRule[]>({
    queryKey: ["im-tolerance-rules"],
    queryFn: () => imApi.listToleranceRules(),
  });

  const create = useMutation({
    mutationFn: () => imApi.createToleranceRule({
      ...form,
      supplier_id: form.supplier_id || null,
      item_category: form.item_category || null,
      approval_role_required: form.approval_role_required || null,
      quantity_tolerance_pct: parseFloat(form.quantity_tolerance_pct),
      price_tolerance_pct: parseFloat(form.price_tolerance_pct),
      tax_tolerance_pct: parseFloat(form.tax_tolerance_pct),
      priority: parseInt(form.priority),
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["im-tolerance-rules"] }); setShowForm(false); setForm(blank()); },
    onError: (e: Error) => setError(e.message),
  });

  const toggleActive = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      imApi.updateToleranceRule(id, { is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["im-tolerance-rules"] }),
  });

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Tolerance Rules</h1>
        <button onClick={() => setShowForm((v) => !v)}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700">
          + New Rule
        </button>
      </div>

      {/* Create form */}
      {showForm && (
        <div className="bg-white border rounded-xl p-5 space-y-4">
          <h2 className="font-semibold text-gray-700">New Tolerance Rule</h2>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {[
              { field: "rule_name", label: "Rule Name", type: "text", required: true },
              { field: "item_category", label: "Item Category (optional)", type: "text" },
              { field: "quantity_tolerance_pct", label: "Qty Tolerance %", type: "number" },
              { field: "price_tolerance_pct", label: "Price Tolerance %", type: "number" },
              { field: "tax_tolerance_pct", label: "Tax Tolerance %", type: "number" },
              { field: "approval_role_required", label: "Approval Role", type: "text" },
              { field: "priority", label: "Priority (lower=higher)", type: "number" },
              { field: "notes", label: "Notes", type: "text" },
            ].map(({ field, label, type }) => (
              <div key={field}>
                <label className="block text-xs text-gray-500 mb-1">{label}</label>
                <input type={type} className="border rounded-lg px-3 py-2 text-sm w-full"
                  value={(form as unknown as Record<string, string>)[field] ?? ""}
                  onChange={(e) => setForm({ ...form, [field]: e.target.value })} />
              </div>
            ))}
            <div className="flex items-center gap-4 mt-2">
              <label className="flex items-center gap-2 text-xs text-gray-600 cursor-pointer">
                <input type="checkbox" checked={form.auto_approve_within_tolerance}
                  onChange={(e) => setForm({ ...form, auto_approve_within_tolerance: e.target.checked })} />
                Auto-approve within tolerance
              </label>
              <label className="flex items-center gap-2 text-xs text-gray-600 cursor-pointer">
                <input type="checkbox" checked={form.block_payment_beyond_tolerance}
                  onChange={(e) => setForm({ ...form, block_payment_beyond_tolerance: e.target.checked })} />
                Block payment beyond tolerance
              </label>
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={() => create.mutate()} disabled={!form.rule_name || create.isPending}
              className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50">
              {create.isPending ? "Saving…" : "Save Rule"}
            </button>
            <button onClick={() => setShowForm(false)}
              className="px-3 py-2 border rounded-lg text-sm hover:bg-gray-50">Cancel</button>
          </div>
        </div>
      )}

      {/* Rules table */}
      <div className="bg-white border rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              {["Rule Name", "Category", "Qty Tol%", "Price Tol%", "Tax Tol%", "Auto Approve", "Block Payment", "Priority", "Active", ""].map((h) => (
                <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y">
            {isLoading ? (
              <tr><td colSpan={10} className="px-4 py-6 text-center text-gray-400">Loading…</td></tr>
            ) : rules.length === 0 ? (
              <tr><td colSpan={10} className="px-4 py-6 text-center text-gray-400">No tolerance rules configured.</td></tr>
            ) : (
              rules.map((r) => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 font-medium">{r.rule_name}</td>
                  <td className="px-4 py-2 text-gray-600 text-xs">{r.item_category ?? "All"}</td>
                  <td className="px-4 py-2">±{r.quantity_tolerance_pct}%</td>
                  <td className="px-4 py-2">±{r.price_tolerance_pct}%</td>
                  <td className="px-4 py-2">±{r.tax_tolerance_pct}%</td>
                  <td className="px-4 py-2">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${r.auto_approve_within_tolerance ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                      {r.auto_approve_within_tolerance ? "Yes" : "No"}
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${r.block_payment_beyond_tolerance ? "bg-red-100 text-red-700" : "bg-gray-100 text-gray-500"}`}>
                      {r.block_payment_beyond_tolerance ? "Yes" : "No"}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-gray-600">{r.priority}</td>
                  <td className="px-4 py-2">
                    <button onClick={() => toggleActive.mutate({ id: r.id, is_active: !r.is_active })}
                      className={`text-xs px-2 py-0.5 rounded-full cursor-pointer ${r.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                      {r.is_active ? "Active" : "Inactive"}
                    </button>
                  </td>
                  <td className="px-4 py-2 text-xs text-gray-400">
                    {r.notes ?? "—"}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
