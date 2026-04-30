"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { expensesApi, ExpenseClaim, fmtCurrency } from "@/lib/expenses";

export default function ReimbursementPage() {
  const [claims, setClaims] = useState<ExpenseClaim[]>([]);
  const [payRef, setPayRef] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState("");

  const load = () => expensesApi.listClaims({ status: "finance_approved" }).then(setClaims);
  useEffect(() => { load(); }, []);

  const handlePay = async (id: string) => {
    await expensesApi.payClaim(id, { payment_reference: payRef[id] || "" });
    setMsg(`Claim paid`);
    load();
    setTimeout(() => setMsg(""), 2500);
  };

  const total = claims.reduce((s, c) => s + Number(c.total_approved_amount), 0);

  return (
    <div className="p-6 space-y-5 min-h-screen bg-[#060d18] text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Reimbursement</h1>
          <p className="text-slate-500 text-sm mt-0.5">Finance-approved claims ready for payment</p>
        </div>
        <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] px-4 py-2 text-right">
          <p className="text-[10px] text-slate-500 uppercase tracking-widest">Total to Reimburse</p>
          <p className="text-xl font-bold text-purple-400">{fmtCurrency(total)}</p>
        </div>
      </div>

      {msg && <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-3 text-sm text-emerald-300">{msg}</div>}

      <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/[0.07]">
              {["Claim No", "Date", "Approved Amount", "Method", "Payment Reference", "Action"].map((h) => (
                <th key={h} className={`px-4 py-3 text-[10px] text-slate-500 uppercase tracking-widest ${h === "Approved Amount" ? "text-right" : "text-left"}`}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {claims.map((c) => (
              <tr key={c.expense_claim_id} className="border-b border-white/[0.05] hover:bg-white/[0.02]">
                <td className="px-4 py-3 font-mono text-xs">
                  <Link href={`/dashboard/expenses/claims/${c.expense_claim_id}`} className="text-indigo-400 hover:text-indigo-300">{c.claim_no}</Link>
                </td>
                <td className="px-4 py-3 text-slate-400">{c.claim_date}</td>
                <td className="px-4 py-3 text-right text-white font-semibold">{fmtCurrency(c.total_approved_amount)}</td>
                <td className="px-4 py-3 text-slate-400 capitalize">{c.reimbursement_method}</td>
                <td className="px-4 py-3">
                  <input type="text" placeholder="Ref / txn no" value={payRef[c.expense_claim_id] || ""}
                    onChange={(e) => setPayRef({ ...payRef, [c.expense_claim_id]: e.target.value })}
                    className="bg-white/[0.04] border border-white/[0.08] rounded-lg px-2 py-1 text-xs text-white focus:outline-none w-36" />
                </td>
                <td className="px-4 py-3">
                  <button onClick={() => handlePay(c.expense_claim_id)}
                    className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium">Mark Paid</button>
                </td>
              </tr>
            ))}
            {claims.length === 0 && <tr><td colSpan={6} className="px-4 py-8 text-center text-slate-600">No claims ready for payment</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
