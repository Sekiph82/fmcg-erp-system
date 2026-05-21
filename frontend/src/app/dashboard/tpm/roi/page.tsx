"use client";
import { useQuery } from "@tanstack/react-query";
import { tpmApi, fmtCurrency } from "@/lib/tpm";
import Link from "next/link";

export default function TPMROIPage() {
  const { data: rows = [], isLoading } = useQuery({
    queryKey: ["tpm-roi"],
    queryFn: () => tpmApi.getROIReport(),
  });

  const avgExpectedROI = rows.length > 0
    ? rows.reduce((s: number, r: any) => s + r.expected_roi_pct, 0) / rows.length
    : 0;
  const avgActualROI = rows.length > 0
    ? rows.reduce((s: number, r: any) => s + r.actual_roi_pct, 0) / rows.length
    : 0;
  const positiveROI = rows.filter((r: any) => r.actual_roi_pct > 0).length;
  const totalActualSpend = rows.reduce((s: number, r: any) => s + r.actual_spend, 0);

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">ROI / Post-Event Analysis</h1>
        <p className="text-sm text-gray-500">Compare expected vs actual return on investment for completed promotions.</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Avg Expected ROI",  value: `${avgExpectedROI.toFixed(1)}%`,  color: "text-blue-400" },
          { label: "Avg Actual ROI",    value: `${avgActualROI.toFixed(1)}%`,    color: avgActualROI >= avgExpectedROI ? "text-green-400" : "text-red-400" },
          { label: "Positive ROI Count",value: positiveROI,                       color: "text-teal-400" },
          { label: "Total Actual Spend",value: fmtCurrency(totalActualSpend),    color: "text-orange-400" },
        ].map((k) => (
          <div key={k.label} className="glow-card p-4 text-center">
            <p className="text-xs text-gray-500">{k.label}</p>
            <p className={`text-lg font-bold mt-1 ${k.color}`}>{k.value}</p>
          </div>
        ))}
      </div>

      <div className="glass-table overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-blue-900/30">
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Promotion</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Objective</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Actual Spend</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Expected Uplift %</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Actual Uplift %</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Expected ROI %</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Actual ROI %</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase">ROI vs Plan</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={8} className="text-center py-10 text-gray-400">Loading…</td></tr>
            ) : rows.length === 0 ? (
              <tr><td colSpan={8} className="text-center py-10 text-gray-400">No completed promotions with performance data.</td></tr>
            ) : rows.map((r: any) => (
              <tr key={r.promotion_id} className="border-b border-blue-900/20 hover:bg-blue-950/20">
                <td className="px-4 py-3">
                  <Link href={`/dashboard/tpm/promotions/${r.promotion_id}`} className="font-medium text-gray-200 hover:text-indigo-300">
                    {r.promotion_name}
                  </Link>
                  <p className="text-xs text-gray-500 font-mono">{r.promotion_code}</p>
                </td>
                <td className="px-4 py-3 text-xs text-gray-400">{r.objective_type?.replace(/_/g, " ")}</td>
                <td className="px-4 py-3 text-right text-orange-400">{fmtCurrency(r.actual_spend)}</td>
                <td className="px-4 py-3 text-right text-blue-300">{r.expected_uplift_pct.toFixed(1)}%</td>
                <td className={`px-4 py-3 text-right font-medium ${r.actual_uplift_pct >= r.expected_uplift_pct ? "text-green-400" : "text-red-400"}`}>
                  {r.actual_uplift_pct.toFixed(1)}%
                </td>
                <td className="px-4 py-3 text-right text-blue-300">{r.expected_roi_pct.toFixed(1)}%</td>
                <td className={`px-4 py-3 text-right font-bold ${r.actual_roi_pct >= r.expected_roi_pct ? "text-green-400" : "text-red-400"}`}>
                  {r.actual_roi_pct.toFixed(1)}%
                </td>
                <td className={`px-4 py-3 text-right font-medium ${r.roi_vs_plan >= 0 ? "text-green-400" : "text-red-400"}`}>
                  {r.roi_vs_plan >= 0 ? "+" : ""}{r.roi_vs_plan.toFixed(1)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {rows.length > 0 && (
        <div className="liquid-glass p-5 space-y-3">
          <h2 className="text-sm font-semibold text-gray-700">Learnings Summary</h2>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-xs text-gray-500 mb-2">Top Performers (actual ROI)</p>
              {rows.slice(0, 3).map((r: any) => (
                <div key={r.promotion_id} className="flex justify-between py-1 border-b border-blue-900/20">
                  <span className="text-gray-300 text-xs truncate max-w-[200px]">{r.promotion_name}</span>
                  <span className={`text-xs font-bold ml-2 ${r.actual_roi_pct >= 0 ? "text-green-400" : "text-red-400"}`}>
                    {r.actual_roi_pct.toFixed(1)}%
                  </span>
                </div>
              ))}
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-2">Underperformers</p>
              {[...rows].reverse().slice(0, 3).map((r: any) => (
                <div key={r.promotion_id} className="flex justify-between py-1 border-b border-blue-900/20">
                  <span className="text-gray-300 text-xs truncate max-w-[200px]">{r.promotion_name}</span>
                  <span className="text-xs font-bold ml-2 text-red-400">{r.actual_roi_pct.toFixed(1)}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
