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
    try { const updated = await fn(); setClaim(updated); setMsg("Done"); setTimeout(() => setMsg(""), 2000); }
    catch (e: any) { setMsg(e.message); }
  };

  if (!claim) return <div className="p-6 min-h-screen bg-[#060d18] text-slate-500">Loading…</div>;

  return (
    <div className="p-6 space-y-5 min-h-screen bg-[#060d18] text-slate-200 max-w-4xl">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">{claim.claim_no}</h1>
          <p className="text-slate-500 text-sm mt-0.5">Date: {claim.claim_date}</p>
        </div>
        <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${STATUS_COLOR[claim.status]}`}>{STATUS_LABEL[claim.status]}</span>
      </div>

      {msg && <div className="rounded-xl border border-indigo-500/20 bg-indigo-500/10 p-3 text-sm text-indigo-300">{msg}</div>}

      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Claimed", value: fmtCurrency(claim.total_claimed_amount), color: "text-blue-400" },
          { label: "Approved", value: fmtCurrency(claim.total_approved_amount), color: "text-emerald-400" },
          { label: "Reimbursement", value: claim.reimbursement_method.toUpperCase(), color: "text-white" },
        ].map((k) => (
          <div key={k.label} className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-4">
            <p className="text-[10px] text-slate-500 uppercase tracking-widest mb-1">{k.label}</p>
            <p className={`text-xl font-bold ${k.color}`}>{k.value}</p>
          </div>
        ))}
      </div>

      {/* Lines */}
      <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] overflow-hidden">
        <div className="px-4 py-3 border-b border-white/[0.07] flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white">Expense Lines ({claim.lines.length})</h2>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/[0.07]">
              {["Date", "Description", "Vendor", "Receipt", "Claimed", "Approved", "Status", "Violation"].map((h) => (
                <th key={h} className={`px-3 py-2 text-[10px] text-slate-500 uppercase tracking-widest ${h === "Claimed" || h === "Approved" ? "text-right" : "text-left"}`}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {claim.lines.map((ln) => (
              <tr key={ln.expense_line_id} className={`border-b border-white/[0.05] ${ln.policy_violation_flag ? "bg-red-500/5" : "hover:bg-white/[0.02]"}`}>
                <td className="px-3 py-2 text-slate-400">{ln.expense_date}</td>
                <td className="px-3 py-2 text-white">{ln.description}</td>
                <td className="px-3 py-2 text-slate-500">{ln.vendor_name || "—"}</td>
                <td className="px-3 py-2 font-mono text-xs text-slate-500">{ln.receipt_no || "—"}</td>
                <td className="px-3 py-2 text-right text-white">{fmtCurrency(ln.claimed_amount)}</td>
                <td className="px-3 py-2 text-right text-emerald-400">{ln.approved_amount ? fmtCurrency(ln.approved_amount) : "—"}</td>
                <td className="px-3 py-2 text-xs text-slate-500 capitalize">{ln.line_status}</td>
                <td className="px-3 py-2">
                  {ln.policy_violation_flag && (
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${ln.policy_violation_severity === "block" ? "bg-red-500/20 text-red-300" : "bg-amber-500/20 text-amber-300"}`}>
                      {ln.policy_violation_severity}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Actions */}
      <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-5 space-y-3">
        <h2 className="text-sm font-semibold text-white">Actions</h2>
        <textarea value={approverNotes} onChange={(e) => setApproverNotes(e.target.value)}
          placeholder="Notes / rejection reason…" rows={2}
          className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500" />
        <div className="flex flex-wrap gap-2">
          {claim.status === "draft" && (
            <button onClick={() => action(() => expensesApi.submitClaim(id))}
              className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm">Submit</button>
          )}
          {claim.status === "submitted" && (
            <>
              <button onClick={() => action(() => expensesApi.managerApprove(id, { approver_id: "00000000-0000-0000-0000-000000000002", notes: approverNotes }))}
                className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm">Manager Approve</button>
              <button onClick={() => action(() => expensesApi.rejectClaim(id, { approver_id: "00000000-0000-0000-0000-000000000002", notes: approverNotes }))}
                className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-white text-sm">Reject</button>
              <button onClick={() => action(() => expensesApi.returnForCorrection(id, approverNotes || "Please correct and resubmit"))}
                className="px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-sm">Return for Correction</button>
            </>
          )}
          {claim.status === "manager_approved" && (
            <button onClick={() => action(() => expensesApi.financeApprove(id, { approver_id: "00000000-0000-0000-0000-000000000003", notes: approverNotes }))}
              className="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-sm">Finance Approve</button>
          )}
          {claim.status === "finance_approved" && (
            <button onClick={() => action(() => expensesApi.payClaim(id, { payment_reference: approverNotes }))}
              className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm">Mark Paid</button>
          )}
        </div>
      </div>

      {claim.rejection_reason && (
        <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-300">
          <strong>Rejection reason:</strong> {claim.rejection_reason}
        </div>
      )}
    </div>
  );
}
