"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { expensesApi, ExpenseClaim, STATUS_LABEL, STATUS_COLOR, fmtCurrency } from "@/lib/expenses";

export default function ClaimDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [claim, setClaim] = useState<ExpenseClaim | null>(null);
  const [approverNotes, setApproverNotes] = useState("");
  const [msg, setMsg] = useState("");

  const load = () => expensesApi.getClaim(id).then(setClaim).catch(console.error);
  useEffect(() => { load(); }, [id]);

  const action = async (fn: () => Promise<ExpenseClaim>) => {
    try {
      const updated = await fn();
      setClaim(updated);
      setMsg("Done");
      setTimeout(() => setMsg(""), 2000);
    } catch (e: any) {
      setMsg(e.message);
    }
  };

  if (!claim) return <div className="p-6 text-gray-400">Loading…</div>;

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">{claim.claim_no}</h1>
          <p className="text-sm text-gray-500">Date: {claim.claim_date}</p>
        </div>
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${STATUS_COLOR[claim.status]}`}>{STATUS_LABEL[claim.status]}</span>
      </div>

      {msg && <div className="bg-blue-50 text-blue-700 text-sm px-4 py-2 rounded">{msg}</div>}

      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white border rounded-xl p-4">
          <p className="text-xs text-gray-500">Claimed</p>
          <p className="text-xl font-bold text-blue-600">{fmtCurrency(claim.total_claimed_amount)}</p>
        </div>
        <div className="bg-white border rounded-xl p-4">
          <p className="text-xs text-gray-500">Approved</p>
          <p className="text-xl font-bold text-green-600">{fmtCurrency(claim.total_approved_amount)}</p>
        </div>
        <div className="bg-white border rounded-xl p-4">
          <p className="text-xs text-gray-500">Reimbursement</p>
          <p className="text-lg font-semibold capitalize">{claim.reimbursement_method}</p>
        </div>
      </div>

      {/* Lines */}
      <div className="bg-white border rounded-xl overflow-hidden">
        <div className="px-4 py-3 border-b bg-gray-50">
          <h2 className="text-sm font-semibold">Expense Lines ({claim.lines.length})</h2>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500">
            <tr>
              <th className="px-3 py-2 text-left">Date</th>
              <th className="px-3 py-2 text-left">Description</th>
              <th className="px-3 py-2 text-left">Vendor</th>
              <th className="px-3 py-2 text-left">Receipt</th>
              <th className="px-3 py-2 text-right">Claimed</th>
              <th className="px-3 py-2 text-right">Approved</th>
              <th className="px-3 py-2 text-left">Status</th>
              <th className="px-3 py-2 text-left">Violation</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {claim.lines.map((ln) => (
              <tr key={ln.expense_line_id} className={ln.policy_violation_flag ? "bg-red-50" : ""}>
                <td className="px-3 py-2">{ln.expense_date}</td>
                <td className="px-3 py-2">{ln.description}</td>
                <td className="px-3 py-2 text-gray-500">{ln.vendor_name}</td>
                <td className="px-3 py-2 font-mono text-xs">{ln.receipt_no}</td>
                <td className="px-3 py-2 text-right">{fmtCurrency(ln.claimed_amount)}</td>
                <td className="px-3 py-2 text-right">{ln.approved_amount ? fmtCurrency(ln.approved_amount) : "—"}</td>
                <td className="px-3 py-2"><span className="capitalize text-xs">{ln.line_status}</span></td>
                <td className="px-3 py-2">
                  {ln.policy_violation_flag && (
                    <span className={`text-xs px-2 py-0.5 rounded-full ${ln.policy_violation_severity === "block" ? "bg-red-100 text-red-700" : "bg-yellow-100 text-yellow-700"}`}>
                      {ln.policy_violation_severity} — {ln.policy_violation_note}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Actions */}
      <div className="bg-white border rounded-xl p-4 space-y-3">
        <h2 className="text-sm font-semibold">Actions</h2>
        <textarea value={approverNotes} onChange={(e) => setApproverNotes(e.target.value)}
          placeholder="Notes / rejection reason…" rows={2}
          className="w-full border rounded p-2 text-sm" />
        <div className="flex flex-wrap gap-2">
          {claim.status === "draft" && (
            <button onClick={() => action(() => expensesApi.submitClaim(id))}
              className="bg-blue-600 text-white text-sm px-4 py-2 rounded hover:bg-blue-700">Submit</button>
          )}
          {claim.status === "submitted" && (
            <>
              <button onClick={() => action(() => expensesApi.managerApprove(id, { approver_id: "00000000-0000-0000-0000-000000000002", notes: approverNotes }))}
                className="bg-green-600 text-white text-sm px-4 py-2 rounded hover:bg-green-700">Manager Approve</button>
              <button onClick={() => action(() => expensesApi.rejectClaim(id, { approver_id: "00000000-0000-0000-0000-000000000002", notes: approverNotes }))}
                className="bg-red-600 text-white text-sm px-4 py-2 rounded hover:bg-red-700">Reject</button>
              <button onClick={() => action(() => expensesApi.returnForCorrection(id, approverNotes || "Please correct and resubmit"))}
                className="bg-yellow-500 text-white text-sm px-4 py-2 rounded hover:bg-yellow-600">Return for Correction</button>
            </>
          )}
          {claim.status === "manager_approved" && (
            <button onClick={() => action(() => expensesApi.financeApprove(id, { approver_id: "00000000-0000-0000-0000-000000000003", notes: approverNotes }))}
              className="bg-purple-600 text-white text-sm px-4 py-2 rounded hover:bg-purple-700">Finance Approve</button>
          )}
          {claim.status === "finance_approved" && (
            <button onClick={() => action(() => expensesApi.payClaim(id, { payment_reference: approverNotes }))}
              className="bg-emerald-600 text-white text-sm px-4 py-2 rounded hover:bg-emerald-700">Mark Paid</button>
          )}
        </div>
      </div>

      {/* Meta */}
      {claim.rejection_reason && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
          <strong>Rejection reason:</strong> {claim.rejection_reason}
        </div>
      )}
    </div>
  );
}
