"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { expensesApi, ExpenseCategory } from "@/lib/expenses";

interface LineForm {
  expense_category_id: string; expense_date: string; description: string;
  vendor_name: string; receipt_no: string; claimed_amount: string;
  tax_amount: string; currency: string; payment_method_used: string; attachment_ref: string; notes: string;
}
const emptyLine = (): LineForm => ({
  expense_category_id: "", expense_date: new Date().toISOString().slice(0, 10),
  description: "", vendor_name: "", receipt_no: "", claimed_amount: "",
  tax_amount: "0", currency: "KES", payment_method_used: "", attachment_ref: "", notes: "",
});

const inputCls = "w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500";
const selectCls = "w-full bg-[#0d1829] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none";
const labelCls = "block text-[10px] text-slate-400 mb-1";

export default function NewClaimPage() {
  const router = useRouter();
  const [categories, setCategories] = useState<ExpenseCategory[]>([]);
  const [form, setForm] = useState({
    claim_date: new Date().toISOString().slice(0, 10), period_start: "", period_end: "",
    currency: "KES", reimbursement_method: "bank", notes: "",
    employee_id: "00000000-0000-0000-0000-000000000001",
  });
  const [lines, setLines] = useState<LineForm[]>([emptyLine()]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => { expensesApi.listCategories().then(setCategories).catch(console.error); }, []);

  const addLine = () => setLines([...lines, emptyLine()]);
  const removeLine = (i: number) => setLines(lines.filter((_, idx) => idx !== i));
  const updateLine = (i: number, key: keyof LineForm, val: string) =>
    setLines(lines.map((l, idx) => idx === i ? { ...l, [key]: val } : l));

  const handleSubmit = async () => {
    setSaving(true); setError("");
    try {
      const payload = { ...form, lines: lines.map((l) => ({ ...l, claimed_amount: parseFloat(l.claimed_amount) || 0, tax_amount: parseFloat(l.tax_amount) || 0 })) };
      const claim = await expensesApi.createClaim(payload);
      router.push(`/dashboard/expenses/claims/${claim.expense_claim_id}`);
    } catch (e: any) { setError(e.message); }
    finally { setSaving(false); }
  };

  return (
    <div className="p-6 space-y-6 text-slate-200 max-w-4xl">
      <h1 className="text-xl font-bold text-white">New Expense Claim</h1>

      <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-5 space-y-4">
        <h2 className="text-sm font-semibold text-white">Claim Details</h2>
        <div className="grid grid-cols-2 gap-4">
          <div><label className={labelCls}>Claim Date</label><input type="date" value={form.claim_date} onChange={(e) => setForm({ ...form, claim_date: e.target.value })} className={inputCls} /></div>
          <div><label className={labelCls}>Reimbursement Method</label>
            <select value={form.reimbursement_method} onChange={(e) => setForm({ ...form, reimbursement_method: e.target.value })} className={selectCls}>
              {["payroll", "ap", "bank", "cash", "manual"].map((m) => <option key={m} value={m}>{m.toUpperCase()}</option>)}
            </select>
          </div>
          <div><label className={labelCls}>Period Start</label><input type="date" value={form.period_start} onChange={(e) => setForm({ ...form, period_start: e.target.value })} className={inputCls} /></div>
          <div><label className={labelCls}>Period End</label><input type="date" value={form.period_end} onChange={(e) => setForm({ ...form, period_end: e.target.value })} className={inputCls} /></div>
          <div className="col-span-2"><label className={labelCls}>Notes</label>
            <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} rows={2} className={inputCls} />
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white">Expense Lines</h2>
          <button onClick={addLine} className="px-3 py-1.5 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-slate-300 text-xs">+ Add Line</button>
        </div>

        {lines.map((line, i) => (
          <div key={i} className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-500">Line {i + 1}</span>
              {lines.length > 1 && <button onClick={() => removeLine(i)} className="text-xs text-red-400 hover:text-red-300">Remove</button>}
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div><label className={labelCls}>Category *</label>
                <select value={line.expense_category_id} onChange={(e) => updateLine(i, "expense_category_id", e.target.value)} className={selectCls}>
                  <option value="">Select…</option>
                  {categories.map((c) => <option key={c.expense_category_id} value={c.expense_category_id}>{c.category_name}</option>)}
                </select>
              </div>
              <div><label className={labelCls}>Date *</label><input type="date" value={line.expense_date} onChange={(e) => updateLine(i, "expense_date", e.target.value)} className={inputCls} /></div>
              <div><label className={labelCls}>Amount (KES) *</label><input type="number" value={line.claimed_amount} onChange={(e) => updateLine(i, "claimed_amount", e.target.value)} placeholder="0.00" className={inputCls} /></div>
              <div className="col-span-2"><label className={labelCls}>Description *</label><input type="text" value={line.description} onChange={(e) => updateLine(i, "description", e.target.value)} className={inputCls} /></div>
              <div><label className={labelCls}>Vendor</label><input type="text" value={line.vendor_name} onChange={(e) => updateLine(i, "vendor_name", e.target.value)} className={inputCls} /></div>
              <div><label className={labelCls}>Receipt No</label><input type="text" value={line.receipt_no} onChange={(e) => updateLine(i, "receipt_no", e.target.value)} className={inputCls} /></div>
              <div><label className={labelCls}>Payment Method</label><input type="text" value={line.payment_method_used} onChange={(e) => updateLine(i, "payment_method_used", e.target.value)} placeholder="Cash / Card / M-Pesa" className={inputCls} /></div>
              <div><label className={labelCls}>Receipt / Doc URL</label><input type="text" value={line.attachment_ref} onChange={(e) => updateLine(i, "attachment_ref", e.target.value)} placeholder="https://…" className={inputCls} /></div>
            </div>
          </div>
        ))}
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}
      <button onClick={handleSubmit} disabled={saving}
        className="px-6 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium disabled:opacity-50">
        {saving ? "Saving…" : "Save Claim"}
      </button>
    </div>
  );
}
