"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { financeApi, GLAccountDrillDown, COA } from "@/lib/finance";

const today = new Date().toISOString().slice(0, 10);
const monthStart = today.slice(0, 7) + "-01";

function fmt(n: number) {
  return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function GeneralLedgerPage() {
  const [accountId, setAccountId] = useState("");
  const [fromDate, setFromDate] = useState(monthStart);
  const [toDate, setToDate] = useState(today);
  const [query, setQuery] = useState<{ accountId: string; from: string; to: string } | null>(null);

  const { data: accounts } = useQuery<COA[]>({
    queryKey: ["coa"],
    queryFn: () => financeApi.listCOA(false),
    staleTime: 60_000,
  });

  const { data, isLoading, isError } = useQuery<GLAccountDrillDown>({
    queryKey: ["gl-drilldown", query],
    queryFn: () => financeApi.generalLedger(query!.accountId, query!.from, query!.to),
    enabled: !!query,
    staleTime: 30_000,
  });

  return (
    <div className="max-w-6xl mx-auto space-y-5 pb-10">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">General Ledger</h1>
        <p className="text-sm text-gray-400 mt-0.5">Per-account transaction drill-down with running balance</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Account</label>
          <select
            value={accountId}
            onChange={(e) => setAccountId(e.target.value)}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300 min-w-[260px]"
          >
            <option value="">Select account…</option>
            {(accounts ?? []).map((a) => (
              <option key={a.id} value={a.id}>
                {a.code} — {a.name} ({a.account_type})
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">From Date</label>
          <input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300" />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">To Date</label>
          <input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300" />
        </div>
        <button
          onClick={() => accountId && setQuery({ accountId, from: fromDate, to: toDate })}
          disabled={!accountId}
          className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Run
        </button>
      </div>

      {isLoading && <div className="text-center py-8 text-gray-400">Loading…</div>}
      {isError && <div className="text-center py-8 text-red-500">Failed to load general ledger.</div>}

      {data && (
        <>
          {/* Account summary */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: "Opening Balance", value: data.opening_balance, color: "text-gray-800" },
              { label: "Total Debit", value: data.total_debit, color: "text-blue-700" },
              { label: "Total Credit", value: data.total_credit, color: "text-red-700" },
              { label: "Closing Balance", value: data.closing_balance, color: data.closing_balance >= 0 ? "text-green-700" : "text-red-700" },
            ].map((kpi) => (
              <div key={kpi.label} className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
                <p className="text-xs font-semibold text-gray-400 uppercase">{kpi.label}</p>
                <p className={`text-xl font-bold mt-1 ${kpi.color}`}>{fmt(kpi.value)}</p>
              </div>
            ))}
          </div>

          {/* Transactions table */}
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-100">
              <h2 className="font-semibold text-gray-800">
                {data.account_code} — {data.account_name}
                <span className="ml-2 text-xs text-gray-400 font-normal">{data.account_type}</span>
              </h2>
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Date</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Entry No</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Description</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Module</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Debit</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Credit</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Balance</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                <tr className="bg-blue-50">
                  <td colSpan={6} className="px-4 py-2 text-xs font-semibold text-blue-700">Opening Balance</td>
                  <td className="px-4 py-2 text-right text-xs font-bold text-blue-700">{fmt(data.opening_balance)}</td>
                </tr>
                {data.transactions.length === 0 && (
                  <tr><td colSpan={7} className="text-center py-6 text-gray-400">No transactions in this period.</td></tr>
                )}
                {data.transactions.map((tx) => (
                  <tr key={tx.entry_id} className="hover:bg-gray-50">
                    <td className="px-4 py-2.5 text-gray-500">{tx.entry_date}</td>
                    <td className="px-4 py-2.5 font-mono text-xs text-gray-600">{tx.entry_no}</td>
                    <td className="px-4 py-2.5 text-gray-700">{tx.description}</td>
                    <td className="px-4 py-2.5 text-xs text-gray-400">{tx.source_module ?? "—"}</td>
                    <td className="px-4 py-2.5 text-right text-gray-700">{tx.debit ? fmt(tx.debit) : "—"}</td>
                    <td className="px-4 py-2.5 text-right text-gray-700">{tx.credit ? fmt(tx.credit) : "—"}</td>
                    <td className={`px-4 py-2.5 text-right font-semibold ${tx.running_balance < 0 ? "text-red-600" : "text-gray-900"}`}>
                      {fmt(tx.running_balance)}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="bg-gray-50 border-t-2 border-gray-200">
                  <td colSpan={6} className="px-4 py-3 text-sm font-bold text-gray-700">Closing Balance</td>
                  <td className={`px-4 py-3 text-right font-bold ${data.closing_balance < 0 ? "text-red-700" : "text-gray-900"}`}>
                    {fmt(data.closing_balance)}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
