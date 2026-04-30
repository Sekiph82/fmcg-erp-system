"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { expensesApi, ExpenseClaim, ExpenseStatus, STATUS_LABEL, STATUS_COLOR, fmtCurrency } from "@/lib/expenses";

const PENDING_STATUSES: ExpenseStatus[] = ["submitted", "manager_approved"];

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
    if (activeTab === "manager") {
      await expensesApi.managerApprove(id, { approver_id: "00000000-0000-0000-0000-000000000002" });
    } else {
      await expensesApi.financeApprove(id, { approver_id: "00000000-0000-0000-0000-000000000003" });
    }
    load();
  };

  const handleReject = async (id: string) => {
    await expensesApi.rejectClaim(id, { approver_id: "00000000-0000-0000-0000-000000000002", notes: "Rejected from queue" });
    load();
  };

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-bold">Approval Queue</h1>

      <div className="flex gap-2">
        {(["manager", "finance"] as const).map((t) => (
          <button key={t} onClick={() => setActiveTab(t)}
            className={`px-4 py-2 rounded text-sm border ${activeTab === t ? "bg-blue-600 text-white" : "bg-white"}`}>
            {t === "manager" ? "Manager Approval (Submitted)" : "Finance Approval (Manager Approved)"}
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
                <th className="px-4 py-3 text-left">Violations</th>
                <th className="px-4 py-3 text-left">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {claims.map((c) => {
                const violations = c.lines.filter((l) => l.policy_violation_flag).length;
                return (
                  <tr key={c.expense_claim_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono">
                      <Link href={`/dashboard/expenses/claims/${c.expense_claim_id}`} className="text-blue-600 hover:underline">{c.claim_no}</Link>
                    </td>
                    <td className="px-4 py-3">{c.claim_date}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLOR[c.status]}`}>{STATUS_LABEL[c.status]}</span>
                    </td>
                    <td className="px-4 py-3 text-right font-mono">{fmtCurrency(c.total_claimed_amount)}</td>
                    <td className="px-4 py-3">
                      {violations > 0 && <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full">{violations} violation(s)</span>}
                    </td>
                    <td className="px-4 py-3 space-x-2">
                      <button onClick={() => handleApprove(c.expense_claim_id)} className="text-xs text-green-600 hover:underline">Approve</button>
                      <button onClick={() => handleReject(c.expense_claim_id)} className="text-xs text-red-500 hover:underline">Reject</button>
                      <Link href={`/dashboard/expenses/claims/${c.expense_claim_id}`} className="text-xs text-gray-500 hover:underline">Detail</Link>
                    </td>
                  </tr>
                );
              })}
              {claims.length === 0 && (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No claims in queue</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
