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
    setMsg(`Claim ${id.slice(-6)} marked as paid`);
    load();
    setTimeout(() => setMsg(""), 2500);
  };

  const total = claims.reduce((s, c) => s + Number(c.total_approved_amount), 0);

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Reimbursement — Finance Approved</h1>
        <div className="text-right">
          <p className="text-xs text-gray-500">Total to Reimburse</p>
          <p className="text-xl font-bold text-purple-600">{fmtCurrency(total)}</p>
        </div>
      </div>

      {msg && <div className="bg-green-50 text-green-700 text-sm px-4 py-2 rounded">{msg}</div>}

      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500">
            <tr>
              <th className="px-4 py-3 text-left">Claim No</th>
              <th className="px-4 py-3 text-left">Date</th>
              <th className="px-4 py-3 text-right">Approved Amount</th>
              <th className="px-4 py-3 text-left">Method</th>
              <th className="px-4 py-3 text-left">Payment Reference</th>
              <th className="px-4 py-3 text-left">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {claims.map((c) => (
              <tr key={c.expense_claim_id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono">
                  <Link href={`/dashboard/expenses/claims/${c.expense_claim_id}`} className="text-blue-600 hover:underline">{c.claim_no}</Link>
                </td>
                <td className="px-4 py-3">{c.claim_date}</td>
                <td className="px-4 py-3 text-right font-mono font-semibold">{fmtCurrency(c.total_approved_amount)}</td>
                <td className="px-4 py-3 capitalize">{c.reimbursement_method}</td>
                <td className="px-4 py-3">
                  <input type="text" placeholder="Ref / txn no" value={payRef[c.expense_claim_id] || ""}
                    onChange={(e) => setPayRef({ ...payRef, [c.expense_claim_id]: e.target.value })}
                    className="border rounded p-1 text-xs w-36" />
                </td>
                <td className="px-4 py-3">
                  <button onClick={() => handlePay(c.expense_claim_id)}
                    className="bg-emerald-600 text-white text-xs px-3 py-1 rounded hover:bg-emerald-700">Mark Paid</button>
                </td>
              </tr>
            ))}
            {claims.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No claims ready for payment</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
