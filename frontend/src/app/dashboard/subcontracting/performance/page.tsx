"use client";
import { useQuery } from "@tanstack/react-query";
import { scApi, fmt } from "@/lib/subcontracting";

function ScoreBadge({ score }: { score: number|null }) {
  if (score == null) return <span className="text-gray-400">—</span>;
  const cls = score >= 80 ? "text-green-600" : score >= 60 ? "text-yellow-600" : "text-red-600";
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 bg-gray-200 rounded-full h-2">
        <div className={`h-2 rounded-full ${score >= 80 ? "bg-green-500" : score >= 60 ? "bg-yellow-500" : "bg-red-500"}`}
          style={{ width: `${Math.min(score, 100)}%` }} />
      </div>
      <span className={`font-mono font-bold ${cls}`}>{fmt(score, 0)}</span>
    </div>
  );
}

export default function PerformancePage() {
  const { data, isLoading } = useQuery({ queryKey: ["sc-performance"], queryFn: () => scApi.getPerformance() });

  const onTimeCount = data?.filter((r) => r.on_time).length ?? 0;
  const avgScore = data?.length ? data.reduce((s, r) => s + Number(r.performance_score ?? 0), 0) / data.length : null;

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-xl font-semibold text-gray-900">Subcontractor Performance</h1>
        <p className="text-sm text-gray-500">Delivery · Quality · Yield · Cost KPIs per completed order</p>
      </div>

      {data && data.length > 0 && (
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-white border rounded-lg p-4">
            <p className="text-xs text-gray-500 uppercase">Avg Performance Score</p>
            <p className={`text-2xl font-bold mt-1 ${(avgScore ?? 0) >= 80 ? "text-green-600" : "text-orange-600"}`}>
              {avgScore != null ? `${fmt(avgScore, 0)}/100` : "—"}
            </p>
          </div>
          <div className="bg-white border rounded-lg p-4">
            <p className="text-xs text-gray-500 uppercase">On-Time Deliveries</p>
            <p className="text-2xl font-bold mt-1">{onTimeCount} / {data.length}</p>
          </div>
          <div className="bg-white border rounded-lg p-4">
            <p className="text-xs text-gray-500 uppercase">Avg Rejection Rate</p>
            <p className="text-2xl font-bold mt-1 text-red-600">
              {data.length ? fmt(data.reduce((s, r) => s + Number(r.rejection_rate_pct ?? 0), 0) / data.length, 1) : "—"}%
            </p>
          </div>
        </div>
      )}

      {isLoading && <div className="text-gray-400">Loading…</div>}
      {!isLoading && !data?.length && (
        <div className="text-center py-12 text-gray-400">No performance records yet. Complete orders to generate KPI data.</div>
      )}

      <div className="bg-white border border-gray-200 rounded-lg overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              <th className="text-left px-4 py-2">Order / Supplier</th>
              <th className="text-left px-4 py-2">Planned</th>
              <th className="text-left px-4 py-2">Actual</th>
              <th className="text-right px-4 py-2">Delay</th>
              <th className="text-right px-4 py-2">Qty Ordered</th>
              <th className="text-right px-4 py-2">Rejection %</th>
              <th className="text-right px-4 py-2">Avg Yield</th>
              <th className="text-right px-4 py-2">Cost Variance</th>
              <th className="text-left px-4 py-2">Score</th>
            </tr>
          </thead>
          <tbody>
            {(data ?? []).map((r) => (
              <tr key={r.id} className="border-t border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-2">
                  <p className="font-mono font-medium text-blue-700">{r.order_no}</p>
                  <p className="text-xs text-gray-500">{r.supplier_name}</p>
                </td>
                <td className="px-4 py-2 text-gray-500">{r.planned_completion ?? "—"}</td>
                <td className="px-4 py-2 text-gray-500">{r.actual_completion ?? "—"}</td>
                <td className={`px-4 py-2 text-right ${(r.delay_days ?? 0) > 0 ? "text-red-600 font-medium" : "text-green-600"}`}>
                  {r.delay_days != null ? (r.delay_days > 0 ? `+${r.delay_days}d` : r.delay_days === 0 ? "On time" : `${r.delay_days}d early`) : "—"}
                </td>
                <td className="px-4 py-2 text-right">{fmt(r.total_qty_ordered, 0)}</td>
                <td className={`px-4 py-2 text-right ${Number(r.rejection_rate_pct ?? 0) > 5 ? "text-red-600" : ""}`}>
                  {r.rejection_rate_pct != null ? `${fmt(r.rejection_rate_pct, 1)}%` : "—"}
                </td>
                <td className="px-4 py-2 text-right">{r.avg_yield_pct != null ? `${fmt(r.avg_yield_pct, 1)}%` : "—"}</td>
                <td className={`px-4 py-2 text-right ${Number(r.cost_variance_pct ?? 0) > 5 ? "text-red-600" : "text-gray-600"}`}>
                  {r.cost_variance_pct != null ? `${Number(r.cost_variance_pct) >= 0 ? "+" : ""}${fmt(r.cost_variance_pct, 1)}%` : "—"}
                </td>
                <td className="px-4 py-2"><ScoreBadge score={r.performance_score} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
