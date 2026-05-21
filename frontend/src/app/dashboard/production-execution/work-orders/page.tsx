"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { execApi, ExecWorkOrderOut, WOExecStatus, WO_STATUS_COLOR, fmtMins } from "@/lib/productionExecution";

const STATUSES: WOExecStatus[] = ["PENDING", "READY", "IN_PROGRESS", "PAUSED", "COMPLETED", "CANCELLED"];

export default function WorkOrderQueuePage() {
  const qc = useQueryClient();
  const [filterStatus, setFilterStatus] = useState("");

  const { data: wos = [], isLoading } = useQuery<ExecWorkOrderOut[]>({
    queryKey: ["exec-work-orders", filterStatus],
    queryFn: () => execApi.listWorkOrders({ status: filterStatus || undefined }),
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["exec-work-orders"] });

  const startWO = useMutation({
    mutationFn: (woId: string) => execApi.startWorkOrder(woId),
    onSuccess: invalidate,
  });

  const groupByOrder = wos.reduce<Record<string, ExecWorkOrderOut[]>>((acc, wo) => {
    const key = wo.production_order_id;
    acc[key] = acc[key] || [];
    acc[key].push(wo);
    return acc;
  }, {});

  const readyCount = wos.filter((w) => w.status === "READY").length;
  const activeCount = wos.filter((w) => w.status === "IN_PROGRESS").length;
  const pendingCount = wos.filter((w) => w.status === "PENDING").length;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <a href="/dashboard/production-execution" className="text-sm text-gray-400 hover:text-gray-600">← Production Orders</a>
          </div>
          <h1 className="text-xl font-bold text-gray-900">Work Order Queue</h1>
          <p className="text-sm text-gray-500 mt-0.5">All work orders across production orders</p>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
        {[
          { label: "Total WOs",  value: wos.length,   color: "text-gray-900" },
          { label: "Ready",      value: readyCount,    color: "text-blue-600" },
          { label: "Active",     value: activeCount,   color: "text-yellow-600" },
          { label: "Pending",    value: pendingCount,  color: "text-gray-400" },
          { label: "Completed",  value: wos.filter((w) => w.status === "COMPLETED").length, color: "text-green-600" },
          { label: "Cancelled",  value: wos.filter((w) => w.status === "CANCELLED").length, color: "text-red-500" },
        ].map((k) => (
          <div key={k.label} className="bg-white rounded-xl border border-gray-100 shadow-sm p-3 text-center">
            <p className="text-xs text-gray-400">{k.label}</p>
            <p className={`text-2xl font-bold mt-0.5 ${k.color}`}>{k.value}</p>
          </div>
        ))}
      </div>

      {/* Filter */}
      <div className="flex items-center gap-3">
        <select className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm" value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
          <option value="">All Statuses</option>
          {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <span className="text-sm text-gray-400">{wos.length} work orders</span>
      </div>

      {/* List */}
      {isLoading ? (
        <div className="text-center text-gray-400 py-8">Loading…</div>
      ) : wos.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-8 text-center text-sm text-gray-400">
          No work orders found.
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                {["Step", "Operation", "Status", "Planned", "Actual", "Completed", "Scrap", "QC", ""].map((h) => (
                  <th key={h} className="px-3 py-2.5 text-left font-medium text-gray-400 text-xs">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {wos.map((wo) => (
                <tr key={wo.id} className="hover:bg-gray-50">
                  <td className="px-3 py-2">
                    <span className="text-xs text-gray-400 font-mono">{wo.step_sequence}</span>
                  </td>
                  <td className="px-3 py-2">
                    <p className="font-medium">{wo.step_name}</p>
                    <p className="text-xs text-gray-400 font-mono">
                      <a href={`/dashboard/production-execution/${wo.production_order_id}`} className="hover:underline text-indigo-500">
                        → View Order
                      </a>
                    </p>
                  </td>
                  <td className="px-3 py-2">
                    <span className={`text-xs px-1.5 py-0.5 rounded ${WO_STATUS_COLOR[wo.status]}`}>{wo.status}</span>
                  </td>
                  <td className="px-3 py-2 text-xs">{fmtMins(Number(wo.run_time_planned))}</td>
                  <td className="px-3 py-2 text-xs">{wo.run_time_actual !== null ? fmtMins(Number(wo.run_time_actual)) : "—"}</td>
                  <td className="px-3 py-2 text-xs text-right font-mono">{Number(wo.completed_qty).toFixed(2)}</td>
                  <td className="px-3 py-2 text-xs text-right font-mono text-red-500">
                    {Number(wo.scrap_qty) > 0 ? Number(wo.scrap_qty).toFixed(2) : "—"}
                  </td>
                  <td className="px-3 py-2 text-xs">
                    {wo.qc_required_flag ? (
                      wo.qc_passed === true ? <span className="text-green-600">✓</span> :
                      wo.qc_passed === false ? <span className="text-red-600">✗</span> :
                      <span className="text-yellow-600">Pending</span>
                    ) : "—"}
                  </td>
                  <td className="px-3 py-2">
                    {wo.status === "READY" && (
                      <button onClick={() => startWO.mutate(wo.id)} disabled={startWO.isPending} className="text-xs text-yellow-600 hover:underline">Start</button>
                    )}
                    {wo.status === "IN_PROGRESS" && (
                      <a href={`/dashboard/production-execution/${wo.production_order_id}?tab=Work+Orders`} className="text-xs text-green-600 hover:underline">Complete</a>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
