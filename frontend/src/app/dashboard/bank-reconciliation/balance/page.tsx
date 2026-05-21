"use client";
import { useQuery } from "@tanstack/react-query";
import { brApi, BRBalanceSummary } from "@/lib/bank_reconciliation";

export default function BalanceSummaryPage() {
  const { data: rows = [], isLoading } = useQuery<BRBalanceSummary[]>({
    queryKey: ["br-balance"],
    queryFn: () => brApi.getBalanceSummary(),
  });

  const totalVariance = rows.reduce((s, r) => s + r.variance, 0);

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Bank vs Ledger Balance</h1>
          <p className="text-sm text-gray-500 mt-1">Statement closing vs ERP cash book — real-time variance view</p>
        </div>
        <div className="text-right">
          <p className={`text-2xl font-bold ${Math.abs(totalVariance) < 1 ? "text-green-600" : "text-red-600"}`}>
            {totalVariance.toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </p>
          <p className="text-xs text-gray-500">Total variance</p>
        </div>
      </div>

      {isLoading ? (
        <p className="text-gray-400">Loading…</p>
      ) : rows.length === 0 ? (
        <div className="bg-gray-50 border rounded-xl p-8 text-center">
          <p className="text-gray-500">No bank accounts configured. Create bank accounts and import statements first.</p>
        </div>
      ) : (
        <div className="bg-white border rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                {["Account", "Currency", "Last Statement", "Statement Closing", "ERP Book Balance", "Variance", "Status"].map((h) => (
                  <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {rows.map((r: BRBalanceSummary) => {
                const hasVar = Math.abs(r.variance) >= 1;
                return (
                  <tr key={r.bank_account_id} className="hover:bg-gray-50">
                    <td className="px-4 py-2 font-medium">{r.bank_account_name}</td>
                    <td className="px-4 py-2 text-xs">{r.currency}</td>
                    <td className="px-4 py-2 font-mono text-xs">{r.last_statement_no || "—"}</td>
                    <td className="px-4 py-2 font-medium">{r.statement_closing.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                    <td className="px-4 py-2">{r.erp_book_balance.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                    <td className={`px-4 py-2 font-semibold ${hasVar ? "text-red-700" : "text-green-700"}`}>
                      {r.variance > 0 ? "+" : ""}{r.variance.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${hasVar ? "bg-red-100 text-red-700" : "bg-green-100 text-green-700"}`}>
                        {r.status}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-sm text-blue-800">
        <p className="font-semibold mb-1">Variance Interpretation</p>
        <ul className="space-y-1 text-xs list-disc list-inside text-blue-700">
          <li>Positive variance = Statement closing higher than ERP book (unposted credits)</li>
          <li>Negative variance = ERP book higher than statement (outstanding debits / uncleared cheques)</li>
          <li>Variance ≤ 1.00 is treated as matched</li>
        </ul>
      </div>
    </div>
  );
}
