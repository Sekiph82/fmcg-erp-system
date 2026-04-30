"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { expensesApi, ExpenseClaim, ExpenseStatus, STATUS_LABEL, STATUS_COLOR, fmtCurrency } from "@/lib/expenses";

const STATUSES: ExpenseStatus[] = ["draft", "submitted", "manager_approved", "finance_approved", "rejected", "paid", "cancelled"];

export default function ClaimsPage() {
  const [claims, setClaims] = useState<ExpenseClaim[]>([]);
  const [filter, setFilter] = useState<ExpenseStatus | "">("");
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    const data = await expensesApi.listClaims(filter ? { status: filter as ExpenseStatus } : undefined);
    setClaims(data);
    setLoading(false);
  };
  useEffect(() => { load(); }, [filter]);

  const handleSubmit = async (id: string) => {
    await expensesApi.submitClaim(id);
    load();
  };

  return (
    <div className="p-6 space-y-5 min-h-screen bg-[#060d18] text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Expense Claims</h1>
          <p className="text-slate-500 text-sm mt-0.5">{claims.length} claims</p>
        </div>
        <Link href="/dashboard/expenses/claims/new"
          className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium">+ New Claim</Link>
      </div>

      <div className="flex gap-2 flex-wrap">
        <button onClick={() => setFilter("")}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${filter === "" ? "bg-indigo-600 border-indigo-500 text-white" : "border-white/[0.08] text-slate-400 hover:border-white/20"}`}>All</button>
        {STATUSES.map((s) => (
          <button key={s} onClick={() => setFilter(s)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${filter === s ? "bg-indigo-600 border-indigo-500 text-white" : "border-white/[0.08] text-slate-400 hover:border-white/20"}`}>
            {STATUS_LABEL[s]}
          </button>
        ))}
      </div>

      {loading ? <p className="text-slate-500 text-sm">Loading…</p> : (
        <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/[0.07]">
                {["Claim No", "Date", "Status", "Claimed", "Approved", "Method", "Actions"].map((h) => (
                  <th key={h} className={`px-4 py-3 text-[10px] text-slate-500 uppercase tracking-widest ${h === "Claimed" || h === "Approved" ? "text-right" : "text-left"}`}>{h}</th>
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
                  <td className="px-4 py-3">
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${STATUS_COLOR[c.status]}`}>{STATUS_LABEL[c.status]}</span>
                  </td>
                  <td className="px-4 py-3 text-right text-white font-medium">{fmtCurrency(c.total_claimed_amount)}</td>
                  <td className="px-4 py-3 text-right text-emerald-400">{fmtCurrency(c.total_approved_amount)}</td>
                  <td className="px-4 py-3 text-slate-400 capitalize">{c.reimbursement_method}</td>
                  <td className="px-4 py-3 space-x-3">
                    {c.status === "draft" && (
                      <button onClick={() => handleSubmit(c.expense_claim_id)} className="text-xs text-blue-400 hover:text-blue-300">Submit</button>
                    )}
                    <Link href={`/dashboard/expenses/claims/${c.expense_claim_id}`} className="text-xs text-slate-500 hover:text-slate-400">View</Link>
                  </td>
                </tr>
              ))}
              {claims.length === 0 && (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-slate-600">No claims found</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
