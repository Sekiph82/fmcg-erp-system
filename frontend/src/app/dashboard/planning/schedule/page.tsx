"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  planningApi, ScenarioSummary, ScenarioOut, OpQueueOut,
  SCENARIO_STATUS_COLOR, OP_STATUS_COLOR, fmtMins,
} from "@/lib/planning";

export default function SchedulePage() {
  const qc = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [viewOp, setViewOp] = useState<OpQueueOut | null>(null);

  const { data: scenarios = [] } = useQuery<ScenarioSummary[]>({
    queryKey: ["planning-scenarios"],
    queryFn: () => planningApi.listScenarios(),
  });

  const { data: scenario } = useQuery<ScenarioOut>({
    queryKey: ["planning-scenario", selectedId],
    queryFn: () => planningApi.getScenario(selectedId!),
    enabled: !!selectedId,
  });

  const { data: ops = [], isLoading: opsLoading } = useQuery<OpQueueOut[]>({
    queryKey: ["planning-ops", selectedId, statusFilter],
    queryFn: () => planningApi.listOps(selectedId!, statusFilter || undefined),
    enabled: !!selectedId,
  });

  const calculate = useMutation({
    mutationFn: () => planningApi.calculate(selectedId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["planning-ops", selectedId] });
      qc.invalidateQueries({ queryKey: ["planning-scenario", selectedId] });
      qc.invalidateQueries({ queryKey: ["planning-dashboard"] });
    },
  });

  const activate = useMutation({
    mutationFn: () => planningApi.activateScenario(selectedId!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["planning-scenario", selectedId] }),
  });

  // Group ops by work center for Gantt-like display
  const byWC: Record<string, OpQueueOut[]> = {};
  for (const op of ops) {
    const wc = op.work_center_name || "Unassigned";
    if (!byWC[wc]) byWC[wc] = [];
    byWC[wc].push(op);
  }

  const statusCounts = {
    SCHEDULED: ops.filter((o) => o.status === "SCHEDULED").length,
    BLOCKED: ops.filter((o) => o.status === "BLOCKED").length,
    PENDING: ops.filter((o) => o.status === "PENDING").length,
  };

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Schedule Board</h1>
        <a href="/dashboard/planning" className="text-xs text-blue-600 hover:underline">← Planning Dashboard</a>
      </div>

      {/* Scenario selector */}
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

        {selectedId && (
          <>
            <button
              onClick={() => calculate.mutate()}
              disabled={calculate.isPending}
              className="px-3 py-1.5 text-xs font-medium bg-indigo-100 text-indigo-700 hover:bg-indigo-200 rounded-lg"
            >
              {calculate.isPending ? "Scheduling…" : "Run Scheduling Engine"}
            </button>
            {scenario?.status === "DRAFT" && (
              <button
                onClick={() => activate.mutate()}
                disabled={activate.isPending}
                className="px-3 py-1.5 text-xs font-medium bg-green-100 text-green-700 hover:bg-green-200 rounded-lg"
              >
                Activate Scenario
              </button>
            )}
            {scenario && (
              <span className={`text-xs px-2 py-1 rounded ${SCENARIO_STATUS_COLOR[scenario.status]}`}>
                {scenario.status}
              </span>
            )}
          </>
        )}
      </div>

      {selectedId && scenario && (
        <>
          {/* Summary KPIs */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {[
              { label: "Total Ops", value: scenario.total_ops },
              { label: "Scheduled", value: statusCounts.SCHEDULED, color: "text-green-600" },
              { label: "Blocked", value: statusCounts.BLOCKED, color: statusCounts.BLOCKED > 0 ? "text-red-600" : "text-gray-900" },
              { label: "Avg Utilization", value: `${Number(scenario.avg_utilization_pct || 0).toFixed(1)}%` },
              { label: "Changeover Hours", value: `${Number(scenario.total_changeover_hrs || 0).toFixed(1)}h`, color: "text-orange-600" },
            ].map((k) => (
              <div key={k.label} className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
                <p className="text-xs text-gray-400 font-medium">{k.label}</p>
                <p className={`text-2xl font-bold mt-1 ${k.color || "text-gray-900"}`}>{k.value}</p>
              </div>
            ))}
          </div>

          {/* Status filter */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">Filter:</span>
            {["", "SCHEDULED", "BLOCKED", "PENDING"].map((s) => (
              <button
                key={s}
                onClick={() => setStatusFilter(s)}
                className={`px-2 py-1 text-xs rounded ${statusFilter === s ? "bg-indigo-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}
              >
                {s || "All"}
              </button>
            ))}
          </div>

          {/* Gantt-style table */}
          {opsLoading ? (
            <div className="text-center text-gray-400 py-8">Loading schedule…</div>
          ) : ops.length === 0 ? (
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-8 text-center text-sm text-gray-400">
              No operations. Run the scheduling engine first.
            </div>
          ) : (
            <div className="space-y-4">
              {Object.entries(byWC).map(([wcName, wcOps]) => (
                <div key={wcName} className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
                  <div className="px-4 py-2 bg-gradient-to-r from-indigo-50 to-purple-50 border-b border-gray-100">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-semibold text-indigo-800">{wcName}</p>
                      <span className="text-xs text-gray-400">{wcOps.length} ops</span>
                    </div>
                  </div>
                  <table className="w-full text-xs">
                    <thead className="bg-gray-50">
                      <tr>
                        {["Op No", "Product", "Step", "Qty", "Setup", "Run", "CO", "Total", "Start", "End", "Status"].map((h) => (
                          <th key={h} className="px-2 py-2 text-left font-medium text-gray-400">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      {wcOps.map((op) => (
                        <tr
                          key={op.id}
                          className="hover:bg-gray-50 cursor-pointer"
                          onClick={() => setViewOp(op)}
                        >
                          <td className="px-2 py-2 font-mono text-gray-500">{op.op_no}</td>
                          <td className="px-2 py-2">
                            <p className="font-medium text-gray-700 truncate max-w-[120px]">{op.product_name || "—"}</p>
                            {op.product_code && <p className="text-gray-400">{op.product_code}</p>}
                          </td>
                          <td className="px-2 py-2 text-gray-500">{op.step_name || "—"}</td>
                          <td className="px-2 py-2 font-medium text-right">{Number(op.planned_qty).toLocaleString()}</td>
                          <td className="px-2 py-2 text-right text-gray-500">{fmtMins(op.setup_minutes)}</td>
                          <td className="px-2 py-2 text-right text-gray-500">{fmtMins(op.run_minutes)}</td>
                          <td className="px-2 py-2 text-right text-orange-500">{op.changeover_minutes > 0 ? fmtMins(op.changeover_minutes) : "—"}</td>
                          <td className="px-2 py-2 text-right font-medium">{fmtMins(op.total_minutes)}</td>
                          <td className="px-2 py-2 text-gray-400">{op.scheduled_start ? new Date(op.scheduled_start).toLocaleDateString() : "—"}</td>
                          <td className="px-2 py-2 text-gray-400">{op.scheduled_end ? new Date(op.scheduled_end).toLocaleDateString() : "—"}</td>
                          <td className="px-2 py-2">
                            <span className={`px-1.5 py-0.5 rounded font-medium ${OP_STATUS_COLOR[op.status]}`}>
                              {op.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Op detail modal */}
      {viewOp && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">{viewOp.op_no}</h2>
              <button onClick={() => setViewOp(null)} className="text-gray-400 hover:text-gray-600 text-xl">×</button>
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              {[
                ["Product", viewOp.product_name || "—"],
                ["Code", viewOp.product_code || "—"],
                ["Work Center", viewOp.work_center_name || "—"],
                ["Step", viewOp.step_name || "—"],
                ["Qty", Number(viewOp.planned_qty).toLocaleString()],
                ["Rate/hr", viewOp.rate_per_hour ? `${viewOp.rate_per_hour} units/hr` : "—"],
                ["Setup", fmtMins(viewOp.setup_minutes)],
                ["Run", fmtMins(viewOp.run_minutes)],
                ["Changeover", fmtMins(viewOp.changeover_minutes)],
                ["Total", fmtMins(viewOp.total_minutes)],
                ["Sched Start", viewOp.scheduled_start ? new Date(viewOp.scheduled_start).toLocaleString() : "—"],
                ["Sched End", viewOp.scheduled_end ? new Date(viewOp.scheduled_end).toLocaleString() : "—"],
                ["Priority", String(viewOp.priority)],
                ["Critical Path", viewOp.is_critical_path ? "Yes" : "No"],
              ].map(([k, v]) => (
                <div key={k}>
                  <p className="text-xs text-gray-400">{k}</p>
                  <p className="font-medium text-gray-800">{v}</p>
                </div>
              ))}
            </div>
            {viewOp.block_reason && (
              <div className="mt-3 bg-red-50 border border-red-100 rounded-lg p-3">
                <p className="text-xs font-semibold text-red-600">Block reason</p>
                <p className="text-sm text-red-700">{viewOp.block_reason}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
