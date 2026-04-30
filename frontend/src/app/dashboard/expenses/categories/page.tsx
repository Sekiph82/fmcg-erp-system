"use client";
import { useEffect, useState } from "react";
import { expensesApi, ExpenseCategory } from "@/lib/expenses";

export default function CategoriesPage() {
  const [cats, setCats] = useState<ExpenseCategory[]>([]);
  const [form, setForm] = useState({ category_code: "", category_name: "", daily_limit_amount: "", monthly_limit_amount: "", receipt_required_flag: true });
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => { expensesApi.listCategories().then(setCats); }, []);

  const handleCreate = async () => {
    setSaving(true);
    await expensesApi.createCategory({
      ...form,
      daily_limit_amount: form.daily_limit_amount ? Number(form.daily_limit_amount) : undefined,
      monthly_limit_amount: form.monthly_limit_amount ? Number(form.monthly_limit_amount) : undefined,
    } as any);
    setCats(await expensesApi.listCategories());
    setShowForm(false);
    setSaving(false);
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Expense Categories</h1>
        <button onClick={() => setShowForm(!showForm)} className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">
          {showForm ? "Cancel" : "+ New Category"}
        </button>
      </div>

      {showForm && (
        <div className="bg-white border rounded-xl p-5 space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Code *</label>
              <input value={form.category_code} onChange={(e) => setForm({ ...form, category_code: e.target.value })}
                className="w-full border rounded p-2 text-sm" />
            </div>
            <div className="col-span-2">
              <label className="block text-xs text-gray-500 mb-1">Name *</label>
              <input value={form.category_name} onChange={(e) => setForm({ ...form, category_name: e.target.value })}
                className="w-full border rounded p-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Daily Limit</label>
              <input type="number" value={form.daily_limit_amount} onChange={(e) => setForm({ ...form, daily_limit_amount: e.target.value })}
                className="w-full border rounded p-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Monthly Limit</label>
              <input type="number" value={form.monthly_limit_amount} onChange={(e) => setForm({ ...form, monthly_limit_amount: e.target.value })}
                className="w-full border rounded p-2 text-sm" />
            </div>
            <div className="flex items-end pb-2">
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.receipt_required_flag}
                  onChange={(e) => setForm({ ...form, receipt_required_flag: e.target.checked })} />
                Receipt Required
              </label>
            </div>
          </div>
          <button onClick={handleCreate} disabled={saving}
            className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700 disabled:opacity-50">
            {saving ? "Saving…" : "Create"}
          </button>
        </div>
      )}

      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500">
            <tr>
              <th className="px-4 py-3 text-left">Code</th>
              <th className="px-4 py-3 text-left">Name</th>
              <th className="px-4 py-3 text-right">Daily Limit</th>
              <th className="px-4 py-3 text-right">Monthly Limit</th>
              <th className="px-4 py-3 text-left">Receipt Req.</th>
              <th className="px-4 py-3 text-left">Taxable</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {cats.map((c) => (
              <tr key={c.expense_category_id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-xs">{c.category_code}</td>
                <td className="px-4 py-3 font-medium">{c.category_name}</td>
                <td className="px-4 py-3 text-right">{c.daily_limit_amount ? `KES ${Number(c.daily_limit_amount).toLocaleString()}` : "—"}</td>
                <td className="px-4 py-3 text-right">{c.monthly_limit_amount ? `KES ${Number(c.monthly_limit_amount).toLocaleString()}` : "—"}</td>
                <td className="px-4 py-3">{c.receipt_required_flag ? "Yes" : "No"}</td>
                <td className="px-4 py-3">{c.taxable_flag ? "Yes" : "No"}</td>
              </tr>
            ))}
            {cats.length === 0 && <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No categories</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
