"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { tpmApi, fmtCurrency } from "@/lib/tpm";
import Link from "next/link";

export default function TPMBudgetPage() {
  const [fiscalYear, setFiscalYear] = useState(new Date().getFullYear());

  const { data: rows = [], isLoading } = useQuery({
    queryKey: ["tpm-budget-vs-actual", fiscalYear],
    queryFn: () => tpmApi.getBudgetVsActual(fiscalYear),
  });

  const totals = rows.reduce(
    (acc: any, r: any) => ({
      planned:  acc.planned  + r.planned,
      approved: acc.approved + r.approved,
      actual:   acc.actual   + r.actual,
      accrued:  acc.accrued  + r.accrued,
    }),
    { planned: 0, approved: 0, actual: 0, accrued: 0 }
  );

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Budget vs Actual Spend</h1>
          <p className="text-sm text-gray-500">Track promotion budget utilization and remaining headroom.</p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-400">FY:</label>
          <input type="number" value={fiscalYear} onChange={(e) => setFiscalYear(Number(e.target.value))}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm w-24" />
        </div>
      </div>

      {/* Summary KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Total Planned",  value: fmtCurrency(totals.planned),  color: "text-indigo-400" },
          { label: "Total Approved", value: fmtCurrency(totals.approved), color: "text-blue-400" },
          { label: "Total Actual",   value: fmtCurrency(totals.actual),   color: "text-orange-400" },
          { label: "Total Accrued",  value: fmtCurrency(totals.accrued),  color: "text-yellow-400" },
        ].map((k) => (
          <div key={k.label} className="glow-card p-4 text-center">
            <p className="text-xs text-gray-500">{k.label}</p>
            <p className={`text-base font-bold mt-1 ${k.color}`}>{k.value}</p>
          </div>
        ))}
      </div>

      <div className="glass-table overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-blue-900/30">
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Promotion</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Type</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Planned</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Approved</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Actual</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Accrued</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Variance</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Utilization</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={8} className="text-center py-10 text-gray-400">Loading…</td></tr>
            ) : rows.length === 0 ? (
              <tr><td colSpan={8} className="text-center py-10 text-gray-400">No budget data for FY{fiscalYear}.</td></tr>
            ) : rows.map((r: any) => {
              const pct = Number(r.utilization_pct);
              return (
                <tr key={r.promotion_id} className="border-b border-blue-900/20 hover:bg-blue-950/20">
                  <td className="px-4 py-3">
                    <Link href={`/dashboard/tpm/promotions/${r.promotion_id}`} className="font-medium text-gray-200 hover:text-indigo-300">
                      {r.promotion_name}
                    </Link>
                    <p className="text-xs text-gray-500 font-mono">{r.promotion_code}</p>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-400">{r.promotion_type?.replace(/_/g, " ")}</td>
                  <td className="px-4 py-3 text-right text-gray-300">{fmtCurrency(r.planned)}</td>
                  <td className="px-4 py-3 text-right text-blue-300">{fmtCurrency(r.approved)}</td>
                  <td className="px-4 py-3 text-right text-orange-400">{fmtCurrency(r.actual)}</td>
                  <td className="px-4 py-3 text-right text-yellow-400">{fmtCurrency(r.accrued)}</td>
                  <td className={`px-4 py-3 text-right font-medium ${r.variance < 0 ? "text-red-400" : "text-green-400"}`}>
                    {fmtCurrency(r.variance)}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-gray-700 rounded-full h-1.5">
                        <div
                          className={`h-1.5 rounded-full ${pct > 100 ? "bg-red-500" : pct > 80 ? "bg-orange-500" : "bg-green-500"}`}
                          style={{ width: `${Math.min(pct, 100)}%` }}
                        />
                      </div>
                      <span className={`text-xs w-10 text-right ${pct > 100 ? "text-red-400" : "text-gray-400"}`}>
                        {pct.toFixed(0)}%
                      </span>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
