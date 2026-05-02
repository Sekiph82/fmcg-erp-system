"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { financeApi, TrialBalanceRow, AccountType } from "@/lib/finance";

const today = new Date().toISOString().slice(0, 10);
const yearStart = today.slice(0, 4) + "-01-01";

function fmt(n: number) {
  if (!n) return "—";
  return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

const TYPE_COLOR: Record<AccountType, string> = {
  ASSET: "text-blue-700",
  LIABILITY: "text-red-700",
  EQUITY: "text-purple-700",
  REVENUE: "text-green-700",
  EXPENSE: "text-orange-700",
};

export default function TrialBalancePage() {
  const [fromDate, setFromDate] = useState(yearStart);
  const [toDate, setToDate] = useState(today);
  const [params, setParams] = useState({ from_date: yearStart, to_date: today });

  const { data, isLoading, isError } = useQuery<TrialBalanceRow[]>({
    queryKey: ["trial-balance", params],
    queryFn: () => financeApi.trialBalance(params),
    staleTime: 30_000,
  });

  const totalDebit = (data ?? []).reduce((s, r) => s + r.total_debit, 0);
  const totalCredit = (data ?? []).reduce((s, r) => s + r.total_credit, 0);
  const isBalanced = Math.abs(totalDebit - totalCredit) < 0.01;

  return (
    <div className="max-w-6xl mx-auto space-y-5 pb-10">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Trial Balance</h1>
        <p className="text-sm text-gray-400 mt-0.5">
          Debit and credit totals per account from posted journal entries
        </p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">From Date</label>
          <input
            type="date"
            value={fromDate}
            onChange={(e) => setFromDate(e.target.value)}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">To Date</label>
          <input
            type="date"
            value={toDate}
            onChange={(e) => setToDate(e.target.value)}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
          />
        </div>
        <button
          onClick={() => setParams({ from_date: fromDate, to_date: toDate })}
          className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
        >
          Run
        </button>
        <div className="ml-auto text-sm">
          {isBalanced ? (
            <span className="bg-green-100 text-green-700 px-3 py-1.5 rounded-full font-semibold">
              ✓ Balanced
            </span>
          ) : (
            <span className="bg-red-100 text-red-700 px-3 py-1.5 rounded-full font-semibold">
              ✗ Unbalanced — difference: {fmt(Math.abs(totalDebit - totalCredit))}
            </span>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-100">
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Code</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Account Name</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Type</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Debit</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Credit</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Net Balance</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {isLoading && (
              <tr><td colSpan={6} className="text-center py-8 text-gray-400">Loading…</td></tr>
            )}
            {isError && (
              <tr><td colSpan={6} className="text-center py-8 text-red-500">Failed to load trial balance.</td></tr>
            )}
            {!isLoading && (data ?? []).length === 0 && (
              <tr><td colSpan={6} className="text-center py-8 text-gray-400">No posted journal entries found for this period.</td></tr>
            )}
            {(data ?? []).map((row) => (
              <tr key={row.account_id} className="hover:bg-gray-50">
                <td className="px-4 py-2.5 font-mono text-xs text-gray-500">{row.account_code}</td>
                <td className="px-4 py-2.5 font-medium text-gray-800">{row.account_name}</td>
                <td className={`px-4 py-2.5 text-xs font-semibold ${TYPE_COLOR[row.account_type]}`}>
                  {row.account_type}
                </td>
                <td className="px-4 py-2.5 text-right text-gray-700">{fmt(row.total_debit)}</td>
                <td className="px-4 py-2.5 text-right text-gray-700">{fmt(row.total_credit)}</td>
                <td className={`px-4 py-2.5 text-right font-semibold ${row.net_balance < 0 ? "text-red-600" : "text-gray-900"}`}>
                  {fmt(row.net_balance)}
                </td>
              </tr>
            ))}
          </tbody>
          {data && data.length > 0 && (
            <tfoot>
              <tr className="bg-gray-50 border-t-2 border-gray-200 font-bold">
                <td colSpan={3} className="px-4 py-3 text-sm text-gray-700">TOTALS</td>
                <td className="px-4 py-3 text-right text-gray-900">{fmt(totalDebit)}</td>
                <td className="px-4 py-3 text-right text-gray-900">{fmt(totalCredit)}</td>
                <td className={`px-4 py-3 text-right ${isBalanced ? "text-green-700" : "text-red-700"}`}>
                  {fmt(totalDebit - totalCredit)}
                </td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>
    </div>
  );
}
