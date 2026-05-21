"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { scApi, SCYieldOut, yieldBadge, fmt } from "@/lib/subcontracting";

export default function YieldPage() {
  const [abnormalOnly, setAbnormalOnly] = useState(false);
  const { data, isLoading } = useQuery({
    queryKey: ["sc-yield-report", abnormalOnly],
    queryFn: () => scApi.yieldReport(abnormalOnly),
  });

  const avgYield = data?.length
    ? data.reduce((s, r) => s + Number(r.actual_yield_pct ?? 0), 0) / data.length
    : null;

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Yield Analysis</h1>
          <p className="text-sm text-gray-500">Actual vs expected yield · Scrap tracking · Variance</p>
        </div>
        <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
          <input type="checkbox" checked={abnormalOnly} onChange={(e) => setAbnormalOnly(e.target.checked)} />
          Abnormal Only
        </label>
      </div>

      {avgYield != null && (
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-white border rounded-lg p-4">
            <p className="text-xs text-gray-500 uppercase">Avg Yield</p>
            <p className={`text-2xl font-bold mt-1 ${avgYield < 90 ? "text-red-600" : "text-green-600"}`}>{fmt(avgYield, 1)}%</p>
          </div>
          <div className="bg-white border rounded-lg p-4">
            <p className="text-xs text-gray-500 uppercase">Abnormal Records</p>
            <p className="text-2xl font-bold mt-1 text-orange-600">{data?.filter((r) => r.is_abnormal).length ?? 0}</p>
          </div>
          <div className="bg-white border rounded-lg p-4">
            <p className="text-xs text-gray-500 uppercase">Total Scrap Cost</p>
            <p className="text-2xl font-bold mt-1 text-red-600">
              KES {fmt(data?.reduce((s, r) => s + Number(r.scrap_cost ?? 0), 0) ?? 0, 0)}
            </p>
          </div>
        </div>
      )}

      {isLoading && <div className="text-gray-400">Loading…</div>}
      {!isLoading && !data?.length && (
        <div className="text-center py-12 text-gray-400">No yield records found.</div>
      )}

      <div className="bg-white border border-gray-200 rounded-lg overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              <th className="text-left px-4 py-2">Order Line</th>
              <th className="text-right px-4 py-2">Ordered</th>
              <th className="text-right px-4 py-2">Received</th>
              <th className="text-right px-4 py-2">Mat. Issued</th>
              <th className="text-right px-4 py-2">Exp. Yield</th>
              <th className="text-right px-4 py-2">Act. Yield</th>
              <th className="text-right px-4 py-2">Variance</th>
              <th className="text-right px-4 py-2">Scrapped</th>
              <th className="text-left px-4 py-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {(data ?? []).map((r) => (
              <tr key={r.id} className={`border-t border-gray-100 hover:bg-gray-50 ${r.is_abnormal ? "bg-red-50" : ""}`}>
                <td className="px-4 py-2">
                  <a href={`/dashboard/subcontracting/orders?id=${r.order_id}`} className="text-blue-600 hover:underline text-xs font-mono">
                    {r.order_id.slice(0, 8)}…
                  </a>
                </td>
                <td className="px-4 py-2 text-right">{fmt(r.quantity_ordered)}</td>
                <td className="px-4 py-2 text-right">{fmt(r.quantity_received)}</td>
                <td className="px-4 py-2 text-right">{fmt(r.total_material_issued)}</td>
                <td className="px-4 py-2 text-right">{r.expected_yield_pct != null ? `${r.expected_yield_pct}%` : "—"}</td>
                <td className={`px-4 py-2 text-right font-bold ${Number(r.actual_yield_pct ?? 0) < 90 ? "text-red-600" : "text-green-600"}`}>
                  {r.actual_yield_pct != null ? `${fmt(r.actual_yield_pct, 1)}%` : "—"}
                </td>
                <td className={`px-4 py-2 text-right ${Number(r.yield_variance_pct ?? 0) < 0 ? "text-red-600" : "text-green-600"}`}>
                  {r.yield_variance_pct != null ? `${Number(r.yield_variance_pct) >= 0 ? "+" : ""}${fmt(r.yield_variance_pct, 1)}%` : "—"}
                </td>
                <td className={`px-4 py-2 text-right ${Number(r.total_scrapped) > 0 ? "text-orange-600" : ""}`}>{fmt(r.total_scrapped)}</td>
                <td className="px-4 py-2">
                  <span className={`px-2 py-0.5 rounded text-xs ${yieldBadge(r.yield_status)}`}>{r.yield_status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
