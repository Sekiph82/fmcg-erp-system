"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { brApi, BROpenItem, LINE_STATUS_COLOR } from "@/lib/bank_reconciliation";

export default function OpenItemsPage() {
  const [minDays, setMinDays] = useState(0);

  const { data: items = [], isLoading } = useQuery<BROpenItem[]>({
    queryKey: ["br-open-items", minDays],
    queryFn: () => brApi.getOpenItems({ min_days: minDays }),
  });

  const totalUnmatched = items.reduce((s, i) => s + i.unmatched_amount, 0);

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Open Items — Aging</h1>
          <p className="text-sm text-gray-500 mt-1">Unreconciled statement lines requiring action</p>
        </div>
        <div className="text-right">
          <p className="text-2xl font-bold text-red-600">
            {totalUnmatched.toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </p>
          <p className="text-xs text-gray-500">Total unmatched</p>
        </div>
      </div>

      {/* Age filter */}
      <div className="flex gap-2">
        {[
          { label: "All", days: 0 },
          { label: "7+ days", days: 7 },
          { label: "30+ days", days: 30 },
          { label: "90+ days", days: 90 },
        ].map((f) => (
          <button key={f.days} onClick={() => setMinDays(f.days)}
            className={`px-3 py-1.5 text-xs rounded-lg border ${
              minDays === f.days ? "bg-red-600 text-white border-red-600" : "bg-white text-gray-600 hover:bg-gray-50"
            }`}>
            {f.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <p className="text-gray-400">Loading…</p>
      ) : (
        <div className="bg-white border rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                {["Account", "Statement", "Date", "D/C", "Amount", "Unmatched", "Days", "Narration", "Status"].map((h) => (
                  <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {items.map((item: BROpenItem) => (
                <tr key={item.line_id} className={`hover:bg-gray-50 ${item.days_outstanding > 90 ? "bg-red-50" : item.days_outstanding > 30 ? "bg-orange-50" : ""}`}>
                  <td className="px-4 py-2 text-xs text-gray-600 max-w-xs truncate">{item.bank_account_name}</td>
                  <td className="px-4 py-2 font-mono text-xs">{item.statement_no}</td>
                  <td className="px-4 py-2 text-xs">{item.transaction_date}</td>
                  <td className="px-4 py-2">
                    <span className={`px-1.5 py-0.5 rounded text-xs font-bold ${item.debit_credit === "C" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                      {item.debit_credit === "C" ? "CR" : "DR"}
                    </span>
                  </td>
                  <td className="px-4 py-2">{item.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                  <td className="px-4 py-2 font-medium text-red-600">{item.unmatched_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                  <td className="px-4 py-2">
                    <span className={`font-semibold ${item.days_outstanding > 90 ? "text-red-700" : item.days_outstanding > 30 ? "text-orange-600" : "text-gray-700"}`}>
                      {item.days_outstanding}d
                    </span>
                  </td>
                  <td className="px-4 py-2 text-xs text-gray-600 max-w-xs truncate">{item.narration || "—"}</td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${LINE_STATUS_COLOR[item.match_status]}`}>
                      {item.match_status.replace(/_/g, " ")}
                    </span>
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <div className="p-8 text-center">
                  <p className="text-green-600 font-medium">✓ No open items in this range.</p>
                </div>
              )}
            </tbody>
          </table>
          {items.length === 0 && (
            <div className="px-4 py-8 text-center">
              <p className="text-green-600 font-medium">✓ No open items{minDays > 0 ? ` older than ${minDays} days` : ""}.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
