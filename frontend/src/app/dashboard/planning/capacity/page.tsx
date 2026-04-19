"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { planningApi, ScenarioSummary, CapacityBoard, utilColor } from "@/lib/planning";

function UtilBar({ pct }: { pct: number }) {
  const w = Math.min(100, pct);
  const color = utilColor(pct);
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${w}%` }} />
      </div>
      <span className={`text-xs font-medium w-10 text-right ${pct >= 100 ? "text-red-600" : pct >= 85 ? "text-orange-500" : "text-gray-500"}`}>
        {pct.toFixed(0)}%
      </span>
    </div>
  );
}

export default function PlanningCapacityPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data: scenarios = [] } = useQuery<ScenarioSummary[]>({
    queryKey: ["planning-scenarios"],
    queryFn: () => planningApi.listScenarios(),
  });

  const { data: board, isLoading } = useQuery<CapacityBoard>({
    queryKey: ["planning-capacity", selectedId],
    queryFn: () => planningApi.capacityBoard(selectedId!),
    enabled: !!selectedId,
  });

  // Collect all unique dates
  const allDates = Array.from(
    new Set(board?.rows.flatMap((r) => r.slots.map((s) => s.slot_date)).sort() || [])
  ).slice(0, 30);

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Capacity Board</h1>
        <a href="/dashboard/planning" className="text-xs text-blue-600 hover:underline">← Planning Dashboard</a>
      </div>

      {/* Selector */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 flex flex-wrap items-center gap-3">
        <select
          className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm min-w-64"
          value={selectedId || ""}
          onChange={(e) => setSelectedId(e.target.value || null)}
        >
          <option value="">-- select scenario --</option>
          {scenarios.map((s) => (
            <option key={s.id} value={s.id}>{s.scenario_no} — {s.scenario_name}</option>
          ))}
        </select>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 text-xs text-gray-500">
        <span>Utilization:</span>
        {[["< 60%", "bg-green-400"], ["60–85%", "bg-yellow-400"], ["85–100%", "bg-orange-400"], ["> 100%", "bg-red-500"]].map(([label, c]) => (
          <div key={label} className="flex items-center gap-1">
            <div className={`w-3 h-3 rounded ${c}`} />
            <span>{label}</span>
          </div>
        ))}
      </div>

      {selectedId && (
        <>
          {/* Summary */}
          {board && (
            <div className="grid grid-cols-3 gap-4">
              {[
                { label: "Work Centers", value: board.rows.length },
                { label: "Total Operations", value: board.total_ops },
                { label: "Avg Utilization", value: `${board.avg_utilization_pct.toFixed(1)}%` },
              ].map((k) => (
                <div key={k.label} className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
                  <p className="text-xs text-gray-400 font-medium">{k.label}</p>
                  <p className="text-2xl font-bold mt-1 text-gray-900">{k.value}</p>
                </div>
              ))}
            </div>
          )}

          {/* Overload Alerts */}
          {board && board.overload_alerts.length > 0 && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4">
              <h2 className="text-sm font-semibold text-red-700 mb-2">
                Overload Alerts ({board.overload_alerts.length})
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                {board.overload_alerts.map((a, i) => (
                  <div key={i} className="bg-white border border-red-100 rounded-lg p-3">
                    <p className="text-xs font-medium text-gray-700">{a.work_center}</p>
                    <p className="text-xs text-gray-400">{a.date}</p>
                    <p className="text-sm font-bold text-red-600 mt-1">+{a.overload_hours.toFixed(1)} hrs</p>
                    <p className="text-xs text-orange-600">{a.utilization_pct.toFixed(0)}% utilization</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Heatmap Grid */}
          {isLoading ? (
            <div className="text-center text-gray-400 py-8">Loading capacity board…</div>
          ) : !board || board.rows.length === 0 ? (
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-8 text-center text-sm text-gray-400">
              No capacity data. Run the scheduling engine on a scenario first.
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr>
                      <th className="px-4 py-2 text-left font-medium text-gray-500 whitespace-nowrap min-w-[180px]">Work Center</th>
                      <th className="px-3 py-2 text-left font-medium text-gray-400 min-w-[120px]">Peak</th>
                      <th className="px-3 py-2 text-left font-medium text-gray-400">Over</th>
                      <th className="px-3 py-2 text-left font-medium text-gray-400">Co.Hrs</th>
                      {allDates.map((d) => (
                        <th key={d} className="px-1 py-2 text-center font-medium text-gray-400 min-w-[44px]">
                          {d.slice(5)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {board.rows.map((row) => {
                      const slotMap = Object.fromEntries(row.slots.map((s) => [s.slot_date, s]));
                      return (
                        <tr key={row.work_center_id} className="hover:bg-gray-50">
                          <td className="px-4 py-2 font-medium text-gray-800 whitespace-nowrap">{row.work_center_name}</td>
                          <td className="px-3 py-2 min-w-[120px]">
                            <UtilBar pct={row.peak_utilization_pct} />
                          </td>
                          <td className="px-3 py-2 text-center">
                            {row.overloaded_days > 0
                              ? <span className="text-red-600 font-medium">{row.overloaded_days}d</span>
                              : <span className="text-green-500">✓</span>}
                          </td>
                          <td className="px-3 py-2 text-center text-orange-500">
                            {row.total_overload_hrs > 0 ? `${row.total_overload_hrs.toFixed(1)}h` : "—"}
                          </td>
                          {allDates.map((d) => {
                            const slot = slotMap[d];
                            if (!slot) return <td key={d} className="px-1 py-2 text-center text-gray-200">—</td>;
                            const pct = Number(slot.utilization_pct);
                            const color = utilColor(pct);
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
