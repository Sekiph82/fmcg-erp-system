"use client";
import { useEffect, useState } from "react";
import { expensesApi, ExpenseCategory } from "@/lib/expenses";

const inputCls = "w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500";
const labelCls = "block text-[10px] text-slate-400 mb-1";

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
    <div className="p-6 space-y-5 min-h-screen bg-[#060d18] text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Expense Categories</h1>
          <p className="text-slate-500 text-sm mt-0.5">{cats.length} categories</p>
        </div>
        <button onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium">
          {showForm ? "Cancel" : "+ New Category"}
        </button>
      </div>

      {showForm && (
        <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-5 space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <div><label className={labelCls}>Code *</label><input value={form.category_code} onChange={(e) => setForm({ ...form, category_code: e.target.value })} className={inputCls} /></div>
            <div className="col-span-2"><label className={labelCls}>Name *</label><input value={form.category_name} onChange={(e) => setForm({ ...form, category_name: e.target.value })} className={inputCls} /></div>
            <div><label className={labelCls}>Daily Limit (KES)</label><input type="number" value={form.daily_limit_amount} onChange={(e) => setForm({ ...form, daily_limit_amount: e.target.value })} className={inputCls} /></div>
            <div><label className={labelCls}>Monthly Limit (KES)</label><input type="number" value={form.monthly_limit_amount} onChange={(e) => setForm({ ...form, monthly_limit_amount: e.target.value })} className={inputCls} /></div>
            <div className="flex items-end pb-2">
              <label className="flex items-center gap-2 text-sm text-slate-400 cursor-pointer">
                <input type="checkbox" checked={form.receipt_required_flag} onChange={(e) => setForm({ ...form, receipt_required_flag: e.target.checked })} />
                Receipt Required
              </label>
            </div>
          </div>
          <button onClick={handleCreate} disabled={saving}
            className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm disabled:opacity-50">
            {saving ? "Saving…" : "Create"}
          </button>
        </div>
      )}

      <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/[0.07]">
              {["Code", "Name", "Daily Limit", "Monthly Limit", "Receipt Req.", "Taxable"].map((h) => (
                <th key={h} className={`px-4 py-3 text-[10px] text-slate-500 uppercase tracking-widest ${h.includes("Limit") ? "text-right" : "text-left"}`}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {cats.map((c) => (
              <tr key={c.expense_category_id} className="border-b border-white/[0.05] hover:bg-white/[0.02]">
                <td className="px-4 py-3 font-mono text-xs text-slate-400">{c.category_code}</td>
                <td className="px-4 py-3 text-white font-medium">{c.category_name}</td>
                <td className="px-4 py-3 text-right text-slate-400">{c.daily_limit_amount ? `KES ${Number(c.daily_limit_amount).toLocaleString()}` : "—"}</td>
                <td className="px-4 py-3 text-right text-slate-400">{c.monthly_limit_amount ? `KES ${Number(c.monthly_limit_amount).toLocaleString()}` : "—"}</td>
                <td className="px-4 py-3 text-slate-400">{c.receipt_required_flag ? <span className="text-emerald-400">Yes</span> : "No"}</td>
                <td className="px-4 py-3 text-slate-400">{c.taxable_flag ? <span className="text-amber-400">Yes</span> : "No"}</td>
              </tr>
            ))}
            {cats.length === 0 && <tr><td colSpan={6} className="px-4 py-8 text-center text-slate-600">No categories</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
