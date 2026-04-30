"use client";
import { useEffect, useState } from "react";
import { expensesApi, ExpensePolicy, ExpenseCategory } from "@/lib/expenses";

export default function PoliciesPage() {
  const [policies, setPolicies] = useState<ExpensePolicy[]>([]);
  const [categories, setCategories] = useState<ExpenseCategory[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    policy_name: "", category_id: "", max_amount_per_line: "", max_amount_per_day: "",
    max_amount_per_month: "", receipt_required_above_amount: "", approval_level_required: "1",
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    expensesApi.listPolicies().then(setPolicies);
    expensesApi.listCategories().then(setCategories);
  }, []);

  const handleCreate = async () => {
    setSaving(true);
    await expensesApi.createPolicy({
      policy_name: form.policy_name,
      category_id: form.category_id as any,
      max_amount_per_line: form.max_amount_per_line ? Number(form.max_amount_per_line) : undefined,
      max_amount_per_day: form.max_amount_per_day ? Number(form.max_amount_per_day) : undefined,
      max_amount_per_month: form.max_amount_per_month ? Number(form.max_amount_per_month) : undefined,
      receipt_required_above_amount: form.receipt_required_above_amount ? Number(form.receipt_required_above_amount) : undefined,
      approval_level_required: Number(form.approval_level_required),
    } as any);
    setPolicies(await expensesApi.listPolicies());
    setShowForm(false);
    setSaving(false);
  };

  const catName = (id: string) => categories.find((c) => c.expense_category_id === id)?.category_name ?? id;

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Expense Policies</h1>
        <button onClick={() => setShowForm(!showForm)} className="bg-blue-600 text-white px-4 py-2 rounded text-sm">
          {showForm ? "Cancel" : "+ New Policy"}
        </button>
      </div>

      {showForm && (
        <div className="bg-white border rounded-xl p-5 space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Policy Name</label>
              <input value={form.policy_name} onChange={(e) => setForm({ ...form, policy_name: e.target.value })} className="w-full border rounded p-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Category</label>
              <select value={form.category_id} onChange={(e) => setForm({ ...form, category_id: e.target.value })} className="w-full border rounded p-2 text-sm">
                <option value="">Select…</option>
                {categories.map((c) => <option key={c.expense_category_id} value={c.expense_category_id}>{c.category_name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Max Per Line</label>
              <input type="number" value={form.max_amount_per_line} onChange={(e) => setForm({ ...form, max_amount_per_line: e.target.value })} className="w-full border rounded p-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Max Per Day</label>
              <input type="number" value={form.max_amount_per_day} onChange={(e) => setForm({ ...form, max_amount_per_day: e.target.value })} className="w-full border rounded p-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Max Per Month</label>
              <input type="number" value={form.max_amount_per_month} onChange={(e) => setForm({ ...form, max_amount_per_month: e.target.value })} className="w-full border rounded p-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Receipt Required Above</label>
              <input type="number" value={form.receipt_required_above_amount} onChange={(e) => setForm({ ...form, receipt_required_above_amount: e.target.value })} className="w-full border rounded p-2 text-sm" />
            </div>
          </div>
          <button onClick={handleCreate} disabled={saving} className="bg-blue-600 text-white px-4 py-2 rounded text-sm disabled:opacity-50">
            {saving ? "Saving…" : "Create"}
          </button>
        </div>
      )}

      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500">
            <tr>
              <th className="px-4 py-3 text-left">Policy Name</th>
              <th className="px-4 py-3 text-left">Category</th>
              <th className="px-4 py-3 text-right">Max / Line</th>
              <th className="px-4 py-3 text-right">Max / Day</th>
              <th className="px-4 py-3 text-right">Max / Month</th>
              <th className="px-4 py-3 text-right">Receipt Above</th>
              <th className="px-4 py-3 text-left">Approval Level</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {policies.map((p) => (
              <tr key={p.expense_policy_id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium">{p.policy_name}</td>
                <td className="px-4 py-3">{catName(p.category_id)}</td>
                <td className="px-4 py-3 text-right">{p.max_amount_per_line ? `KES ${Number(p.max_amount_per_line).toLocaleString()}` : "—"}</td>
                <td className="px-4 py-3 text-right">{p.max_amount_per_day ? `KES ${Number(p.max_amount_per_day).toLocaleString()}` : "—"}</td>
                <td className="px-4 py-3 text-right">{p.max_amount_per_month ? `KES ${Number(p.max_amount_per_month).toLocaleString()}` : "—"}</td>
                <td className="px-4 py-3 text-right">{p.receipt_required_above_amount ? `KES ${Number(p.receipt_required_above_amount).toLocaleString()}` : "—"}</td>
                <td className="px-4 py-3">{p.approval_level_required}</td>
              </tr>
            ))}
            {policies.length === 0 && <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No policies</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
