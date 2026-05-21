"use client";
import { useEffect, useState } from "react";
import { expensesApi, ExpensePolicy, ExpenseCategory } from "@/lib/expenses";

const inputCls = "w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500";
const selectCls = "w-full bg-[#0d1829] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none";
const labelCls = "block text-[10px] text-slate-400 mb-1";

export default function PoliciesPage() {
  const [policies, setPolicies] = useState<ExpensePolicy[]>([]);
  const [categories, setCategories] = useState<ExpenseCategory[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ policy_name: "", category_id: "", max_amount_per_line: "", max_amount_per_day: "", max_amount_per_month: "", receipt_required_above_amount: "", approval_level_required: "1" });
  const [saving, setSaving] = useState(false);

  useEffect(() => { expensesApi.listPolicies().then(setPolicies); expensesApi.listCategories().then(setCategories); }, []);

  const handleCreate = async () => {
    setSaving(true);
    await expensesApi.createPolicy({
      policy_name: form.policy_name, category_id: form.category_id as any,
      max_amount_per_line: form.max_amount_per_line ? Number(form.max_amount_per_line) : undefined,
      max_amount_per_day: form.max_amount_per_day ? Number(form.max_amount_per_day) : undefined,
      max_amount_per_month: form.max_amount_per_month ? Number(form.max_amount_per_month) : undefined,
      receipt_required_above_amount: form.receipt_required_above_amount ? Number(form.receipt_required_above_amount) : undefined,
      approval_level_required: Number(form.approval_level_required),
    } as any);
    setPolicies(await expensesApi.listPolicies());
    setShowForm(false); setSaving(false);
  };

  const catName = (id: string) => categories.find((c) => c.expense_category_id === id)?.category_name ?? id;

  return (
    <div className="p-6 space-y-5 text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Expense Policies</h1>
          <p className="text-slate-500 text-sm mt-0.5">Spending limits and receipt requirements</p>
        </div>
        <button onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium">
          {showForm ? "Cancel" : "+ New Policy"}
        </button>
      </div>

      {showForm && (
        <div className="glow-card p-5 space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <div><label className={labelCls}>Policy Name</label><input value={form.policy_name} onChange={(e) => setForm({ ...form, policy_name: e.target.value })} className={inputCls} /></div>
            <div><label className={labelCls}>Category</label>
              <select value={form.category_id} onChange={(e) => setForm({ ...form, category_id: e.target.value })} className={selectCls}>
                <option value="">Select…</option>
                {categories.map((c) => <option key={c.expense_category_id} value={c.expense_category_id}>{c.category_name}</option>)}
              </select>
            </div>
            <div><label className={labelCls}>Max Per Line</label><input type="number" value={form.max_amount_per_line} onChange={(e) => setForm({ ...form, max_amount_per_line: e.target.value })} className={inputCls} /></div>
            <div><label className={labelCls}>Max Per Day</label><input type="number" value={form.max_amount_per_day} onChange={(e) => setForm({ ...form, max_amount_per_day: e.target.value })} className={inputCls} /></div>
            <div><label className={labelCls}>Max Per Month</label><input type="number" value={form.max_amount_per_month} onChange={(e) => setForm({ ...form, max_amount_per_month: e.target.value })} className={inputCls} /></div>
            <div><label className={labelCls}>Receipt Required Above</label><input type="number" value={form.receipt_required_above_amount} onChange={(e) => setForm({ ...form, receipt_required_above_amount: e.target.value })} className={inputCls} /></div>
          </div>
          <button onClick={handleCreate} disabled={saving}
            className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm disabled:opacity-50">
            {saving ? "Saving…" : "Create"}
          </button>
        </div>
      )}

      <div className="glass-table">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/[0.07]">
              {["Policy Name", "Category", "Max / Line", "Max / Day", "Max / Month", "Receipt Above", "Approval Level"].map((h) => (
                <th key={h} className="px-4 py-3 text-[10px] text-slate-500 uppercase tracking-widest text-left">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {policies.map((p) => (
              <tr key={p.expense_policy_id} className="border-b border-white/[0.05] hover:bg-white/[0.02]">
                <td className="px-4 py-3 text-white font-medium">{p.policy_name}</td>
                <td className="px-4 py-3 text-slate-400">{catName(p.category_id)}</td>
                {[p.max_amount_per_line, p.max_amount_per_day, p.max_amount_per_month, p.receipt_required_above_amount].map((v, i) => (
                  <td key={i} className="px-4 py-3 text-slate-400">{v ? `KES ${Number(v).toLocaleString()}` : "—"}</td>
                ))}
                <td className="px-4 py-3 text-slate-400">{p.approval_level_required}</td>
              </tr>
            ))}
            {policies.length === 0 && <tr><td colSpan={7} className="px-4 py-8 text-center text-slate-600">No policies</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
