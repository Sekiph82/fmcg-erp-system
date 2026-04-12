"use client";

import { useQuery } from "@tanstack/react-query";
import { maintenanceApi } from "@/lib/maintenance";
import { Badge } from "@/components/ui/Badge";

export default function MaintenanceReportsPage() {
  const { data: mtbfData = [], isLoading: mtbfLoading } = useQuery({
    queryKey: ["maint-mtbf"],
    queryFn: () => maintenanceApi.reportMtbfMttr(),
  });

  const { data: downtimeData = [], isLoading: dtLoading } = useQuery({
    queryKey: ["maint-downtime"],
    queryFn: () => maintenanceApi.reportDowntimeByMachine(),
  });

  const { data: overduePM = [], isLoading: odLoading } = useQuery({
    queryKey: ["maint-overdue-pm"],
    queryFn: () => maintenanceApi.reportOverduePM(),
  });

  const totalDowntimeMin = downtimeData.reduce((s, r) => s + r.total_downtime_minutes, 0);
  const totalBreakdowns = downtimeData.reduce((s, r) => s + r.breakdown_count, 0);
  const worstAsset = downtimeData[0];
  const bestMtbf = mtbfData.reduce((best, r) => (!best || (r.mtbf_days ?? 0) > (best.mtbf_days ?? 0) ? r : best), mtbfData[0] as typeof mtbfData[0] | undefined);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Maintenance Reports</h1>
        <p className="text-sm text-gray-500 mt-1">MTBF, MTTR, downtime analysis and overdue PMs</p>
      </div>

      {/* Summary tiles */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border p-5">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Total Downtime</p>
          <p className="text-2xl font-bold mt-1 text-red-600">{(totalDowntimeMin / 60).toFixed(1)} hrs</p>
          <p className="text-xs text-gray-400 mt-1">{totalDowntimeMin.toLocaleString()} minutes</p>
        </div>
        <div className="bg-white rounded-lg border p-5">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Total Breakdowns</p>
          <p className="text-2xl font-bold mt-1 text-orange-600">{totalBreakdowns}</p>
          <p className="text-xs text-gray-400 mt-1">across {downtimeData.length} assets</p>
        </div>
        <div className="bg-white rounded-lg border p-5">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Worst Asset</p>
          <p className="text-xl font-bold mt-1 text-gray-800 truncate">{worstAsset?.asset_name ?? "—"}</p>
          <p className="text-xs text-gray-400 mt-1">{worstAsset ? `${(worstAsset.total_downtime_minutes / 60).toFixed(1)} hrs downtime` : "No data"}</p>
        </div>
        <div className="bg-white rounded-lg border p-5">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Best MTBF</p>
          <p className="text-xl font-bold mt-1 text-green-700">{bestMtbf?.mtbf_days != null ? `${bestMtbf.mtbf_days} days` : "—"}</p>
          <p className="text-xs text-gray-400 mt-1">{bestMtbf?.asset_name ?? ""}</p>
        </div>
      </div>

      {/* MTBF / MTTR Table */}
      <div className="bg-white rounded-lg border">
        <div className="px-5 py-3 border-b">
          <h2 className="font-semibold text-gray-800">MTBF / MTTR by Asset</h2>
          <p className="text-xs text-gray-500 mt-0.5">MTBF = mean time between failures (days) · MTTR = mean time to repair (minutes)</p>
        </div>
        {mtbfLoading ? (
          <p className="px-5 py-8 text-center text-gray-400">Loading…</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-5 py-2 text-left">Asset</th>
                <th className="px-5 py-2 text-left">Line</th>
                <th className="px-5 py-2 text-right">Breakdowns</th>
                <th className="px-5 py-2 text-right">Total Downtime</th>
                <th className="px-5 py-2 text-right">MTTR (min)</th>
                <th className="px-5 py-2 text-right">MTBF (days)</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {mtbfData.map((r) => (
                <tr key={r.asset_id} className="hover:bg-gray-50">
                  <td className="px-5 py-3">
                    <p className="font-medium text-gray-900">{r.asset_name}</p>
                    <p className="text-xs text-gray-400">{r.asset_no}</p>
                  </td>
                  <td className="px-5 py-3 text-gray-500">{r.line || "—"}</td>
                  <td className="px-5 py-3 text-right font-semibold">{r.breakdown_count}</td>
                  <td className="px-5 py-3 text-right text-red-600">{r.total_downtime_minutes} min</td>
                  <td className="px-5 py-3 text-right">
                    <span className={r.avg_downtime_minutes > 120 ? "text-red-600 font-semibold" : "text-gray-700"}>
                      {r.avg_downtime_minutes.toFixed(1)}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-right">
                    {r.mtbf_days != null ? (
                      <span className={r.mtbf_days < 7 ? "text-red-600 font-semibold" : r.mtbf_days < 30 ? "text-orange-500" : "text-green-600 font-semibold"}>
                        {r.mtbf_days}d
                      </span>
                    ) : <span className="text-gray-400">—</span>}
                  </td>
                </tr>
              ))}
              {mtbfData.length === 0 && (
                <tr><td colSpan={6} className="px-5 py-8 text-center text-gray-400">No breakdown data</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      {/* Downtime by Machine */}
      <div className="bg-white rounded-lg border">
        <div className="px-5 py-3 border-b">
          <h2 className="font-semibold text-gray-800">Downtime by Machine</h2>
          <p className="text-xs text-gray-500 mt-0.5">Includes breakdowns and MES downtime logs</p>
        </div>
        {dtLoading ? (
          <p className="px-5 py-8 text-center text-gray-400">Loading…</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-5 py-2 text-left">Asset</th>
                <th className="px-5 py-2 text-left">Line</th>
                <th className="px-5 py-2 text-right">Breakdowns</th>
                <th className="px-5 py-2 text-right">Total Downtime</th>
                <th className="px-5 py-2 text-right">Hours</th>
                <th className="px-5 py-2 text-right">Open</th>
                <th className="px-5 py-2">Severity bar</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {downtimeData.map((r) => {
                const pct = totalDowntimeMin > 0 ? (r.total_downtime_minutes / totalDowntimeMin) * 100 : 0;
                return (
                  <tr key={r.asset_id} className="hover:bg-gray-50">
                    <td className="px-5 py-3">
                      <p className="font-medium text-gray-900">{r.asset_name}</p>
                      <p className="text-xs text-gray-400">{r.asset_no}</p>
                    </td>
                    <td className="px-5 py-3 text-gray-500">{r.line || "—"}</td>
                    <td className="px-5 py-3 text-right">{r.breakdown_count}</td>
                    <td className="px-5 py-3 text-right font-semibold text-red-600">{r.total_downtime_minutes} min</td>
                    <td className="px-5 py-3 text-right">{(r.total_downtime_minutes / 60).toFixed(1)}</td>
                    <td className="px-5 py-3 text-right">
                      {r.open_breakdowns > 0 ? (
                        <Badge label={`${r.open_breakdowns} open`} variant="red" />
                      ) : <span className="text-gray-400">—</span>}
                    </td>
                    <td className="px-5 py-3">
                      <div className="h-2 bg-gray-100 rounded overflow-hidden w-full min-w-24">
                        <div className="h-full bg-red-400 rounded" style={{ width: `${Math.min(pct, 100)}%` }} />
                      </div>
                      <p className="text-xs text-gray-400 mt-0.5">{pct.toFixed(0)}% of total</p>
                    </td>
                  </tr>
                );
              })}
              {downtimeData.length === 0 && (
                <tr><td colSpan={7} className="px-5 py-8 text-center text-gray-400">No downtime data</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      {/* Overdue PM */}
      <div className="bg-white rounded-lg border">
        <div className="px-5 py-3 border-b flex items-center justify-between">
          <h2 className="font-semibold text-gray-800">Overdue PM Plans</h2>
          {overduePM.length > 0 && <Badge label={`${overduePM.length} overdue`} variant="red" />}
        </div>
        {odLoading ? (
          <p className="px-5 py-8 text-center text-gray-400">Loading…</p>
        ) : overduePM.length === 0 ? (
          <p className="px-5 py-8 text-center text-gray-400">All PM plans are up to date</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-5 py-2 text-left">Asset</th>
                <th className="px-5 py-2 text-left">Plan</th>
                <th className="px-5 py-2 text-left">Frequency</th>
                <th className="px-5 py-2 text-left">Due Date</th>
                <th className="px-5 py-2 text-right">Days Overdue</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {overduePM.map((r) => (
                <tr key={r.plan_id} className="hover:bg-gray-50">
                  <td className="px-5 py-3">
                    <p className="font-medium text-gray-900">{r.asset_name}</p>
                    <p className="text-xs text-gray-400">{r.asset_no}</p>
                  </td>
                  <td className="px-5 py-3 text-gray-700">{r.plan_name}</td>
                  <td className="px-5 py-3"><Badge label={r.frequency} variant="blue" /></td>
                  <td className="px-5 py-3 text-gray-500">{r.next_due_date || "—"}</td>
                  <td className="px-5 py-3 text-right">
                    <span className={`font-semibold ${r.days_overdue > 14 ? "text-red-600" : "text-orange-500"}`}>
                      {r.days_overdue}d
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
