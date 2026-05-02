"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { financeApi, BalanceSheetStatement, BSLineItem } from "@/lib/finance";

const today = new Date().toISOString().slice(0, 10);

function fmt(n: number) {
  return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function Section({
  title, lines, total, colorClass,
}: {
  title: string;
  lines: BSLineItem[];
  total: number;
  colorClass: string;
}) {
  return (
    <div className="px-6 py-4">
      <h3 className="text-sm font-bold text-gray-500 uppercase tracking-widest mb-3">{title}</h3>
      {lines.length === 0 && <p className="text-sm text-gray-400">No accounts with postings.</p>}
      {lines.map((line) => (
        <div key={line.account_id} className="flex justify-between py-1.5 text-sm">
          <span className="text-gray-600">
            <span className="font-mono text-xs text-gray-400 mr-2">{line.account_code}</span>
            {line.account_name}
          </span>
          <span className="font-medium text-gray-800">{fmt(line.balance)}</span>
        </div>
      ))}
      <div className={`flex justify-between py-2 mt-2 border-t border-gray-100 font-bold text-sm ${colorClass}`}>
        <span>Total {title}</span>
        <span>{fmt(total)}</span>
      </div>
    </div>
  );
}

export default function BalanceSheetPage() {
  const [asOfDate, setAsOfDate] = useState(today);
  const [query, setQuery] = useState(today);

  const { data, isLoading, isError } = useQuery<BalanceSheetStatement>({
    queryKey: ["balance-sheet", query],
    queryFn: () => financeApi.balanceSheet(query),
    staleTime: 30_000,
  });

  return (
    <div className="max-w-4xl mx-auto space-y-5 pb-10">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Balance Sheet</h1>
        <p className="text-sm text-gray-400 mt-0.5">Assets, liabilities, and equity as of a date</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 flex gap-4 items-end">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">As of Date</label>
          <input type="date" value={asOfDate} onChange={(e) => setAsOfDate(e.target.value)}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300" />
        </div>
        <button
          onClick={() => setQuery(asOfDate)}
          className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700"
        >
          Run
        </button>
        {data && (
          <div className="ml-auto">
            {data.is_balanced ? (
              <span className="bg-green-100 text-green-700 px-3 py-1.5 rounded-full text-sm font-semibold">✓ Balanced</span>
            ) : (
              <span className="bg-red-100 text-red-700 px-3 py-1.5 rounded-full text-sm font-semibold">
                ✗ Out of balance: {fmt(Math.abs(data.total_assets - data.total_liabilities - data.total_equity))}
              </span>
            )}
          </div>
        )}
      </div>

      {isLoading && <div className="text-center py-8 text-gray-400">Loading…</div>}
      {isError && <div className="text-center py-8 text-red-500">Failed to load balance sheet.</div>}

      {data && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-800">As of {data.as_of_date}</h2>
          </div>

          <Section title="Assets" lines={data.asset_lines} total={data.total_assets} colorClass="text-blue-700" />

          <div className="border-t border-gray-100">
            <Section title="Liabilities" lines={data.liability_lines} total={data.total_liabilities} colorClass="text-red-700" />
          </div>

          <div className="border-t border-gray-100">
            <Section title="Equity" lines={data.equity_lines} total={data.total_equity} colorClass="text-purple-700" />
          </div>

          <div className="px-6 py-4 border-t-2 border-gray-200 bg-gray-50">
            <div className="flex justify-between text-sm font-bold text-gray-700">
              <span>Total Liabilities + Equity</span>
              <span>{fmt(data.total_liabilities + data.total_equity)}</span>
            </div>
            <div className="flex justify-between text-sm font-bold text-blue-700 mt-1">
              <span>Total Assets</span>
              <span>{fmt(data.total_assets)}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
