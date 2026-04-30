"use client";
import { useEffect, useState } from "react";
import { expensesApi, ExpenseAdvance, ADVANCE_STATUS_COLOR, fmtCurrency } from "@/lib/expenses";

const inputCls = "w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500";
const labelCls = "block text-[10px] text-slate-400 mb-1";

export default function AdvancesPage() {
  const [advances, setAdvances] = useState<ExpenseAdvance[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ advance_date: new Date().toISOString().slice(0, 10), advance_amount: "", currency: "KES", purpose: "", due_date: "", employee_id: "00000000-0000-0000-0000-000000000001" });
  const [saving, setSaving] = useState(false);

  const load = () => expensesApi.listAdvances().then(setAdvances);
  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    setSaving(true);
    await expensesApi.createAdvance({ ...form, advance_amount: Number(form.advance_amount) });
    await load(); setShowForm(false); setSaving(false);
  };

  const totalOpen = advances.filter((a) => a.settlement_status === "open" || a.settlement_status === "partially_settled")
    .reduce((s, a) => s + Number(a.advance_amount) - Number(a.settled_amount), 0);

  return (
    <div className="p-6 space-y-5 text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Expense Advances</h1>
          <p className="text-slate-500 text-sm mt-0.5">Unsettled balance: <span className="text-orange-400 font-semibold">{fmtCurrency(totalOpen)}</span></p>
        </div>
        <button onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium">
          {showForm ? "Cancel" : "+ New Advance"}
        </button>
      </div>

      {showForm && (
        <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-5 space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <div><label className={labelCls}>Date</label><input type="date" value={form.advance_date} onChange={(e) => setForm({ ...form, advance_date: e.target.value })} className={inputCls} /></div>
            <div><label className={labelCls}>Amount (KES)</label><input type="number" value={form.advance_amount} onChange={(e) => setForm({ ...form, advance_amount: e.target.value })} className={inputCls} /></div>
            <div><label className={labelCls}>Due Date</label><input type="date" value={form.due_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} className={inputCls} /></div>
            <div className="col-span-3"><label className={labelCls}>Purpose</label><input value={form.purpose} onChange={(e) => setForm({ ...form, purpose: e.target.value })} className={inputCls} /></div>
          </div>
          <button onClick={handleCreate} disabled={saving}
            className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm disabled:opacity-50">
            {saving ? "Saving…" : "Create Advance"}
          </button>
        </div>
      )}

      <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/[0.07]">
              {["Advance No", "Date", "Amount", "Settled", "Balance", "Status", "Due", "Purpose"].map((h) => (
                <th key={h} className={`px-4 py-3 text-[10px] text-slate-500 uppercase tracking-widest ${["Amount","Settled","Balance"].includes(h) ? "text-right" : "text-left"}`}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {advances.map((a) => {
              const balance = Number(a.advance_amount) - Number(a.settled_amount);
              return (
                <tr key={a.advance_id} className="border-b border-white/[0.05] hover:bg-white/[0.02]">
                  <td className="px-4 py-3 font-mono text-xs text-slate-400">{a.advance_no}</td>
                  <td className="px-4 py-3 text-slate-400">{a.advance_date}</td>
                  <td className="px-4 py-3 text-right text-white">{fmtCurrency(a.advance_amount)}</td>
                  <td className="px-4 py-3 text-right text-emerald-400">{fmtCurrency(a.settled_amount)}</td>
                  <td className="px-4 py-3 text-right font-semibold text-white">{fmtCurrency(balance)}</td>
                  <td className="px-4 py-3"><span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${ADVANCE_STATUS_COLOR[a.settlement_status]}`}>{a.settlement_status.replace("_", " ")}</span></td>
                  <td className="px-4 py-3 text-slate-400">{a.due_date || "—"}</td>
                  <td className="px-4 py-3 text-slate-500 text-xs">{a.purpose || "—"}</td>
                </tr>
              );
            })}
            {advances.length === 0 && <tr><td colSpan={8} className="px-4 py-8 text-center text-slate-600">No advances</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
