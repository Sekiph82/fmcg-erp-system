"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { mpsApi, MPSPlanSummary, CapacityHeatmap, utilizationColor } from "@/lib/mps";

function UtilBar({ pct }: { pct: number }) {
  const w = Math.min(100, pct);
  const color = utilizationColor(pct);
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${w}%` }} />
      </div>
      <span className={`text-xs font-medium w-10 text-right ${pct >= 100 ? "text-red-600" : pct >= 80 ? "text-orange-600" : "text-gray-500"}`}>
        {pct.toFixed(0)}%
      </span>
    </div>
  );
}

export default function CapacityPage() {
  const qc = useQueryClient();
  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null);

  const { data: plans = [] } = useQuery<MPSPlanSummary[]>({
    queryKey: ["mps-plans"],
    queryFn: () => mpsApi.listPlans(),
  });

  const { data: heatmap, isLoading } = useQuery<CapacityHeatmap>({
    queryKey: ["mps-heatmap", selectedPlanId],
    queryFn: () => mpsApi.getCapacityHeatmap(selectedPlanId!),
    enabled: !!selectedPlanId,
  });

  const runCapacity = useMutation({
    mutationFn: () => mpsApi.runCapacity(selectedPlanId!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mps-heatmap", selectedPlanId] }),
  });

  // Collect all unique dates from heatmap
  const allDates = Array.from(
    new Set(heatmap?.rows.flatMap((r) => r.slots.map((s) => s.slot_date)).sort() || [])
  ).slice(0, 30);

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Capacity Heatmap</h1>
        <a href="/dashboard/mps" className="text-xs text-blue-600 hover:underline">← MPS Dashboard</a>
      </div>

      {/* Plan selector */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 flex flex-wrap items-center gap-3">
        <select
          className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm min-w-64"
          value={selectedPlanId || ""}
          onChange={(e) => setSelectedPlanId(e.target.value || null)}
        >
          <option value="">-- select plan --</option>
          {plans.map((p) => (
            <option key={p.id} value={p.id}>{p.plan_no} — {p.plan_name}</option>
          ))}
        </select>
        {selectedPlanId && (
          <button
            onClick={() => runCapacity.mutate()}
            disabled={runCapacity.isPending}
            className="px-3 py-1.5 text-xs font-medium bg-orange-100 text-orange-700 hover:bg-orange-200 rounded-lg"
          >
            {runCapacity.isPending ? "Scheduling…" : "Re-run Capacity Scheduling"}
          </button>
        )}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 text-xs text-gray-500">
        <span>Utilization:</span>
        {[["< 60%", "bg-green-400"], ["60–80%", "bg-yellow-400"], ["80–100%", "bg-orange-400"], ["> 100%", "bg-red-500"]].map(([label, c]) => (
          <div key={label} className="flex items-center gap-1">
            <div className={`w-3 h-3 rounded ${c}`} />
            <span>{label}</span>
          </div>
        ))}
      </div>

      {selectedPlanId && (
        <>
          {/* Overload Alerts */}
          {heatmap && heatmap.overload_alerts.length > 0 && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4">
              <h2 className="text-sm font-semibold text-red-700 mb-2">
                Overload Alerts ({heatmap.overload_alerts.length})
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                {heatmap.overload_alerts.map((a, i) => (
                  <div key={i} className="bg-white border border-red-100 rounded-lg p-3">
                    <p className="text-xs font-medium text-gray-700">{a.work_center}</p>
                    <p className="text-xs text-gray-400">{a.date}</p>
                    <p className="text-sm font-bold text-red-600 mt-1">
                      +{a.overload_hours.toFixed(1)} hrs
                    </p>
                    <p className="text-xs text-orange-600">{a.utilization_pct.toFixed(0)}% utilization</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Heatmap Grid */}
          {isLoading ? (
            <div className="text-center text-gray-400 py-8">Loading heatmap…</div>
          ) : !heatmap || heatmap.rows.length === 0 ? (
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-8 text-center text-sm text-gray-400">
              No capacity data. Run capacity scheduling first.
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr>
                      <th className="px-4 py-2 text-left font-medium text-gray-500 whitespace-nowrap min-w-[160px]">
                        Work Center
                      </th>
                      <th className="px-3 py-2 text-left font-medium text-gray-400">Peak</th>
                      <th className="px-3 py-2 text-left font-medium text-gray-400">Over</th>
                      {allDates.map((d) => (
                        <th key={d} className="px-1 py-2 text-center font-medium text-gray-400 min-w-[48px]">
                          {d.slice(5)} {/* MM-DD */}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {heatmap.rows.map((row) => {
                      const slotMap = Object.fromEntries(row.slots.map((s) => [s.slot_date, s]));
                      return (
                        <tr key={row.work_center_id} className="hover:bg-gray-50">
                          <td className="px-4 py-2 font-medium text-gray-800 whitespace-nowrap">
                            {row.work_center_name}
                          </td>
                          <td className="px-3 py-2 whitespace-nowrap">
                            <UtilBar pct={row.peak_utilization_pct} />
                          </td>
                          <td className="px-3 py-2 text-center">
                            {row.overloaded_days > 0 ? (
                              <span className="text-red-600 font-medium">{row.overloaded_days}d</span>
                            ) : (
                              <span className="text-green-500">✓</span>
                            )}
                          </td>
                          {allDates.map((d) => {
                            const slot = slotMap[d];
                            if (!slot) {
                              return <td key={d} className="px-1 py-2 text-center text-gray-200">—</td>;
                            }
                            const pct = Number(slot.utilization_pct);
                            const color = utilizationColor(pct);
                            return (
                              <td key={d} className="px-1 py-2 text-center" title={`${pct.toFixed(0)}% (${slot.allocated_hours}/${slot.available_hours}h)`}>
                                <div
                                  className={`mx-auto rounded ${color} text-white text-center`}
                                  style={{ width: 36, height: 20, lineHeight: "20px", fontSize: 9 }}
                                >
                                  {pct.toFixed(0)}%
                                </div>
                              </td>
                            );
                          })}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
