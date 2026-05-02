"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { financeApi, PLStatement } from "@/lib/finance";

const today = new Date().toISOString().slice(0, 10);
const yearStart = today.slice(0, 4) + "-01-01";

function fmt(n: number) {
  return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function ProfitLossPage() {
  const [fromDate, setFromDate] = useState(yearStart);
  const [toDate, setToDate] = useState(today);
  const [params, setParams] = useState({ from: yearStart, to: today });

  const { data, isLoading, isError } = useQuery<PLStatement>({
    queryKey: ["profit-loss", params],
    queryFn: () => financeApi.profitAndLoss(params.from, params.to),
    staleTime: 30_000,
  });

  return (
    <div className="max-w-4xl mx-auto space-y-5 pb-10">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Profit &amp; Loss Statement</h1>
        <p className="text-sm text-gray-400 mt-0.5">Revenue and expenses from posted journal entries</p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 flex flex-wrap gap-4 items-end">
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
          onClick={() => setParams({ from: fromDate, to: toDate })}
          className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700"
        >
          Run
        </button>
      </div>

      {isLoading && <div className="text-center py-8 text-gray-400">Loading…</div>}
      {isError && <div className="text-center py-8 text-red-500">Failed to load P&L statement.</div>}

      {data && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-800">
              Period: {data.from_date} to {data.to_date}
            </h2>
          </div>

          {/* Revenue */}
          <div className="px-6 py-4">
            <h3 className="text-sm font-bold text-gray-500 uppercase tracking-widest mb-3">Revenue</h3>
            {data.revenue_lines.length === 0 && (
              <p className="text-sm text-gray-400">No revenue accounts with postings.</p>
            )}
            {data.revenue_lines.map((line) => (
              <div key={line.account_id} className="flex justify-between py-1.5 text-sm">
                <span className="text-gray-600">
                  <span className="font-mono text-xs text-gray-400 mr-2">{line.account_code}</span>
                  {line.account_name}
                </span>
                <span className="font-medium text-gray-800">{fmt(line.amount)}</span>
              </div>
            ))}
            <div className="flex justify-between py-2 mt-2 border-t border-gray-100 font-bold text-sm">
              <span className="text-gray-700">Total Revenue</span>
              <span className="text-green-700">{fmt(data.total_revenue)}</span>
            </div>
          </div>

          {/* Expenses */}
          <div className="px-6 py-4 border-t border-gray-100">
            <h3 className="text-sm font-bold text-gray-500 uppercase tracking-widest mb-3">Expenses</h3>
            {data.expense_lines.length === 0 && (
              <p className="text-sm text-gray-400">No expense accounts with postings.</p>
            )}
            {data.expense_lines.map((line) => (
              <div key={line.account_id} className="flex justify-between py-1.5 text-sm">
                <span className="text-gray-600">
                  <span className="font-mono text-xs text-gray-400 mr-2">{line.account_code}</span>
                  {line.account_name}
                </span>
                <span className="font-medium text-gray-800">{fmt(line.amount)}</span>
              </div>
            ))}
            <div className="flex justify-between py-2 mt-2 border-t border-gray-100 font-bold text-sm">
              <span className="text-gray-700">Total Expenses</span>
              <span className="text-red-700">{fmt(data.total_expenses)}</span>
            </div>
          </div>

          {/* Net Income */}
          <div className={`px-6 py-5 border-t-2 border-gray-200 ${data.net_income >= 0 ? "bg-green-50" : "bg-red-50"}`}>
            <div className="flex justify-between items-center">
              <span className="text-base font-bold text-gray-900">Net Income</span>
              <span className={`text-xl font-bold ${data.net_income >= 0 ? "text-green-700" : "text-red-700"}`}>
                {data.net_income >= 0 ? "" : "("}{fmt(Math.abs(data.net_income))}{data.net_income < 0 ? ")" : ""}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
