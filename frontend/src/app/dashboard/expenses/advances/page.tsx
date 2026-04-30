"use client";
import { useEffect, useState } from "react";
import { expensesApi, ExpenseAdvance, AdvanceSettlementStatus, ADVANCE_STATUS_COLOR, fmtCurrency } from "@/lib/expenses";

export default function AdvancesPage() {
  const [advances, setAdvances] = useState<ExpenseAdvance[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    advance_date: new Date().toISOString().slice(0, 10),
    advance_amount: "",
    currency: "KES",
    purpose: "",
    due_date: "",
    employee_id: "00000000-0000-0000-0000-000000000001",
  });
  const [saving, setSaving] = useState(false);

  const load = () => expensesApi.listAdvances().then(setAdvances);
  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    setSaving(true);
    await expensesApi.createAdvance({ ...form, advance_amount: Number(form.advance_amount) });
    await load();
    setShowForm(false);
    setSaving(false);
  };

  const totalOpen = advances.filter((a) => a.settlement_status === "open" || a.settlement_status === "partially_settled")
    .reduce((s, a) => s + Number(a.advance_amount) - Number(a.settled_amount), 0);

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Expense Advances</h1>
          <p className="text-sm text-gray-500">Unsettled balance: <strong className="text-orange-600">{fmtCurrency(totalOpen)}</strong></p>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="bg-blue-600 text-white px-4 py-2 rounded text-sm">
          {showForm ? "Cancel" : "+ New Advance"}
        </button>
      </div>

      {showForm && (
        <div className="bg-white border rounded-xl p-5 space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Date</label>
              <input type="date" value={form.advance_date} onChange={(e) => setForm({ ...form, advance_date: e.target.value })} className="w-full border rounded p-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Amount (KES)</label>
              <input type="number" value={form.advance_amount} onChange={(e) => setForm({ ...form, advance_amount: e.target.value })} className="w-full border rounded p-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Due Date</label>
              <input type="date" value={form.due_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} className="w-full border rounded p-2 text-sm" />
            </div>
            <div className="col-span-3">
              <label className="block text-xs text-gray-500 mb-1">Purpose</label>
              <input value={form.purpose} onChange={(e) => setForm({ ...form, purpose: e.target.value })} className="w-full border rounded p-2 text-sm" />
            </div>
          </div>
          <button onClick={handleCreate} disabled={saving} className="bg-blue-600 text-white px-4 py-2 rounded text-sm disabled:opacity-50">
            {saving ? "Saving…" : "Create Advance"}
          </button>
        </div>
      )}

      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500">
            <tr>
              <th className="px-4 py-3 text-left">Advance No</th>
              <th className="px-4 py-3 text-left">Date</th>
              <th className="px-4 py-3 text-right">Amount</th>
              <th className="px-4 py-3 text-right">Settled</th>
              <th className="px-4 py-3 text-right">Balance</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Due</th>
              <th className="px-4 py-3 text-left">Purpose</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {advances.map((a) => {
              const balance = Number(a.advance_amount) - Number(a.settled_amount);
              return (
                <tr key={a.advance_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs">{a.advance_no}</td>
                  <td className="px-4 py-3">{a.advance_date}</td>
                  <td className="px-4 py-3 text-right">{fmtCurrency(a.advance_amount)}</td>
                  <td className="px-4 py-3 text-right">{fmtCurrency(a.settled_amount)}</td>
                  <td className="px-4 py-3 text-right font-semibold">{fmtCurrency(balance)}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${ADVANCE_STATUS_COLOR[a.settlement_status]}`}>
                      {a.settlement_status.replace("_", " ")}
                    </span>
                  </td>
                  <td className="px-4 py-3">{a.due_date || "—"}</td>
                  <td className="px-4 py-3 text-gray-500">{a.purpose}</td>
                </tr>
              );
            })}
            {advances.length === 0 && <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">No advances</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
