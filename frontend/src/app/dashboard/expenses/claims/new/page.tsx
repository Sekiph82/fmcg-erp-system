"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { expensesApi, ExpenseCategory } from "@/lib/expenses";

interface LineForm {
  expense_category_id: string;
  expense_date: string;
  description: string;
  vendor_name: string;
  receipt_no: string;
  claimed_amount: string;
  tax_amount: string;
  currency: string;
  payment_method_used: string;
  attachment_ref: string;
  notes: string;
}

const emptyLine = (): LineForm => ({
  expense_category_id: "",
  expense_date: new Date().toISOString().slice(0, 10),
  description: "",
  vendor_name: "",
  receipt_no: "",
  claimed_amount: "",
  tax_amount: "0",
  currency: "KES",
  payment_method_used: "",
  attachment_ref: "",
  notes: "",
});

export default function NewClaimPage() {
  const router = useRouter();
  const [categories, setCategories] = useState<ExpenseCategory[]>([]);
  const [form, setForm] = useState({
    claim_date: new Date().toISOString().slice(0, 10),
    period_start: "",
    period_end: "",
    currency: "KES",
    reimbursement_method: "bank",
    notes: "",
    employee_id: "00000000-0000-0000-0000-000000000001",
  });
  const [lines, setLines] = useState<LineForm[]>([emptyLine()]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => { expensesApi.listCategories().then(setCategories).catch(console.error); }, []);

  const addLine = () => setLines([...lines, emptyLine()]);
  const removeLine = (i: number) => setLines(lines.filter((_, idx) => idx !== i));
  const updateLine = (i: number, key: keyof LineForm, val: string) => {
    setLines(lines.map((l, idx) => idx === i ? { ...l, [key]: val } : l));
  };

  const handleSubmit = async () => {
    setSaving(true);
    setError("");
    try {
      const payload = {
        ...form,
        lines: lines.map((l) => ({
          ...l,
          claimed_amount: parseFloat(l.claimed_amount) || 0,
          tax_amount: parseFloat(l.tax_amount) || 0,
        })),
      };
      const claim = await expensesApi.createClaim(payload);
      router.push(`/dashboard/expenses/claims/${claim.expense_claim_id}`);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      <h1 className="text-xl font-bold">New Expense Claim</h1>

      <div className="bg-white border rounded-xl p-5 space-y-4">
        <h2 className="font-semibold text-sm text-gray-700">Claim Details</h2>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Claim Date</label>
            <input type="date" value={form.claim_date} onChange={(e) => setForm({ ...form, claim_date: e.target.value })}
              className="w-full border rounded p-2 text-sm" />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Reimbursement Method</label>
            <select value={form.reimbursement_method} onChange={(e) => setForm({ ...form, reimbursement_method: e.target.value })}
              className="w-full border rounded p-2 text-sm">
              {["payroll", "ap", "bank", "cash", "manual"].map((m) => <option key={m} value={m}>{m.toUpperCase()}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Period Start</label>
            <input type="date" value={form.period_start} onChange={(e) => setForm({ ...form, period_start: e.target.value })}
              className="w-full border rounded p-2 text-sm" />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Period End</label>
            <input type="date" value={form.period_end} onChange={(e) => setForm({ ...form, period_end: e.target.value })}
              className="w-full border rounded p-2 text-sm" />
          </div>
          <div className="col-span-2">
            <label className="block text-xs text-gray-500 mb-1">Notes</label>
            <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })}
              rows={2} className="w-full border rounded p-2 text-sm" />
          </div>
        </div>
      </div>

      <div className="bg-white border rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-sm text-gray-700">Expense Lines</h2>
          <button onClick={addLine} className="text-xs bg-blue-50 text-blue-600 px-3 py-1 rounded hover:bg-blue-100">+ Add Line</button>
        </div>

        {lines.map((line, i) => (
          <div key={i} className="border rounded-lg p-4 space-y-3 bg-gray-50">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-gray-600">Line {i + 1}</span>
              {lines.length > 1 && <button onClick={() => removeLine(i)} className="text-xs text-red-500 hover:underline">Remove</button>}
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-xs text-gray-500 mb-1">Category *</label>
                <select value={line.expense_category_id} onChange={(e) => updateLine(i, "expense_category_id", e.target.value)}
                  className="w-full border rounded p-2 text-sm">
                  <option value="">Select…</option>
                  {categories.map((c) => <option key={c.expense_category_id} value={c.expense_category_id}>{c.category_name}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Date *</label>
                <input type="date" value={line.expense_date} onChange={(e) => updateLine(i, "expense_date", e.target.value)}
                  className="w-full border rounded p-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Amount (KES) *</label>
                <input type="number" value={line.claimed_amount} onChange={(e) => updateLine(i, "claimed_amount", e.target.value)}
                  className="w-full border rounded p-2 text-sm" placeholder="0.00" />
              </div>
              <div className="col-span-2">
                <label className="block text-xs text-gray-500 mb-1">Description *</label>
                <input type="text" value={line.description} onChange={(e) => updateLine(i, "description", e.target.value)}
                  className="w-full border rounded p-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Vendor</label>
                <input type="text" value={line.vendor_name} onChange={(e) => updateLine(i, "vendor_name", e.target.value)}
                  className="w-full border rounded p-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Receipt No</label>
                <input type="text" value={line.receipt_no} onChange={(e) => updateLine(i, "receipt_no", e.target.value)}
                  className="w-full border rounded p-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Payment Method</label>
                <input type="text" value={line.payment_method_used} onChange={(e) => updateLine(i, "payment_method_used", e.target.value)}
                  className="w-full border rounded p-2 text-sm" placeholder="Cash / Card / M-Pesa" />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Receipt / Doc URL</label>
                <input type="text" value={line.attachment_ref} onChange={(e) => updateLine(i, "attachment_ref", e.target.value)}
                  className="w-full border rounded p-2 text-sm" placeholder="https://…" />
              </div>
            </div>
          </div>
        ))}
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="flex gap-3">
        <button onClick={handleSubmit} disabled={saving} className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm">
          {saving ? "Saving…" : "Save Claim"}
        </button>
      </div>
    </div>
  );
}
