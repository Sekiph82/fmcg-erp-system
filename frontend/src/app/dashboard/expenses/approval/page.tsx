"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { expensesApi, ExpenseClaim, ExpenseStatus, STATUS_LABEL, STATUS_COLOR, fmtCurrency } from "@/lib/expenses";

export default function ApprovalQueuePage() {
  const [activeTab, setActiveTab] = useState<"manager" | "finance">("manager");
  const [claims, setClaims] = useState<ExpenseClaim[]>([]);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    const status = activeTab === "manager" ? "submitted" : "manager_approved";
    const data = await expensesApi.listClaims({ status: status as ExpenseStatus });
    setClaims(data);
    setLoading(false);
  };
  useEffect(() => { load(); }, [activeTab]);

  const handleApprove = async (id: string) => {
    if (activeTab === "manager") await expensesApi.managerApprove(id, { approver_id: "00000000-0000-0000-0000-000000000002" });
    else await expensesApi.financeApprove(id, { approver_id: "00000000-0000-0000-0000-000000000003" });
    load();
  };
  const handleReject = async (id: string) => {
    await expensesApi.rejectClaim(id, { approver_id: "00000000-0000-0000-0000-000000000002", notes: "Rejected from queue" });
    load();
  };

  return (
    <div className="p-6 space-y-5 min-h-screen bg-[#060d18] text-slate-200">
      <h1 className="text-xl font-bold text-white">Approval Queue</h1>

      <div className="flex gap-2">
        {(["manager", "finance"] as const).map((t) => (
          <button key={t} onClick={() => setActiveTab(t)}
            className={`px-4 py-2 rounded-lg text-sm font-medium border transition-colors ${activeTab === t ? "bg-indigo-600 border-indigo-500 text-white" : "border-white/[0.08] text-slate-400 hover:border-white/20"}`}>
            {t === "manager" ? "Manager Approval (Submitted)" : "Finance Approval (Manager Approved)"}
          </button>
        ))}
      </div>

      {loading ? <p className="text-slate-500 text-sm">Loading…</p> : (
        <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/[0.07]">
                {["Claim No", "Date", "Status", "Claimed", "Violations", "Actions"].map((h) => (
                  <th key={h} className={`px-4 py-3 text-[10px] text-slate-500 uppercase tracking-widest ${h === "Claimed" ? "text-right" : "text-left"}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {claims.map((c) => {
                const violations = c.lines.filter((l) => l.policy_violation_flag).length;
                return (
                  <tr key={c.expense_claim_id} className="border-b border-white/[0.05] hover:bg-white/[0.02]">
                    <td className="px-4 py-3 font-mono text-xs">
                      <Link href={`/dashboard/expenses/claims/${c.expense_claim_id}`} className="text-indigo-400 hover:text-indigo-300">{c.claim_no}</Link>
                    </td>
                    <td className="px-4 py-3 text-slate-400">{c.claim_date}</td>
                    <td className="px-4 py-3"><span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${STATUS_COLOR[c.status]}`}>{STATUS_LABEL[c.status]}</span></td>
                    <td className="px-4 py-3 text-right text-white font-medium">{fmtCurrency(c.total_claimed_amount)}</td>
                    <td className="px-4 py-3">
                      {violations > 0 && <span className="text-[10px] bg-red-500/20 text-red-300 px-2 py-0.5 rounded-full">{violations} violation(s)</span>}
                    </td>
                    <td className="px-4 py-3 space-x-3">
                      <button onClick={() => handleApprove(c.expense_claim_id)} className="text-xs text-emerald-400 hover:text-emerald-300">Approve</button>
                      <button onClick={() => handleReject(c.expense_claim_id)} className="text-xs text-red-400 hover:text-red-300">Reject</button>
                      <Link href={`/dashboard/expenses/claims/${c.expense_claim_id}`} className="text-xs text-slate-500 hover:text-slate-400">Detail</Link>
                    </td>
                  </tr>
                );
              })}
              {claims.length === 0 && <tr><td colSpan={6} className="px-4 py-8 text-center text-slate-600">No claims in queue</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
