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
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Expense Claims</h1>
        <Link href="/dashboard/expenses/claims/new" className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">
          + New Claim
        </Link>
      </div>

      <div className="flex gap-2 flex-wrap">
        <button onClick={() => setFilter("")} className={`px-3 py-1 rounded text-sm border ${filter === "" ? "bg-blue-600 text-white" : "bg-white"}`}>All</button>
        {STATUSES.map((s) => (
          <button key={s} onClick={() => setFilter(s)} className={`px-3 py-1 rounded text-sm border ${filter === s ? "bg-blue-600 text-white" : "bg-white"}`}>
            {STATUS_LABEL[s]}
          </button>
        ))}
      </div>

      {loading ? <p className="text-sm text-gray-500">Loading…</p> : (
        <div className="bg-white rounded-xl border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                <th className="px-4 py-3 text-left">Claim No</th>
                <th className="px-4 py-3 text-left">Date</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-right">Claimed</th>
                <th className="px-4 py-3 text-right">Approved</th>
                <th className="px-4 py-3 text-left">Method</th>
                <th className="px-4 py-3 text-left">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {claims.map((c) => (
                <tr key={c.expense_claim_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono">
                    <Link href={`/dashboard/expenses/claims/${c.expense_claim_id}`} className="text-blue-600 hover:underline">{c.claim_no}</Link>
                  </td>
                  <td className="px-4 py-3">{c.claim_date}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLOR[c.status]}`}>{STATUS_LABEL[c.status]}</span>
                  </td>
                  <td className="px-4 py-3 text-right">{fmtCurrency(c.total_claimed_amount)}</td>
                  <td className="px-4 py-3 text-right">{fmtCurrency(c.total_approved_amount)}</td>
                  <td className="px-4 py-3 capitalize">{c.reimbursement_method}</td>
                  <td className="px-4 py-3 space-x-2">
                    {c.status === "draft" && (
                      <button onClick={() => handleSubmit(c.expense_claim_id)} className="text-xs text-blue-600 hover:underline">Submit</button>
                    )}
                    <Link href={`/dashboard/expenses/claims/${c.expense_claim_id}`} className="text-xs text-gray-600 hover:underline">View</Link>
                  </td>
                </tr>
              ))}
              {claims.length === 0 && (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No claims found</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
