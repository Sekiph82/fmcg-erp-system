"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { sfApi, LiveWOItem, LIVE_STATUS_COLOR } from "@/lib/shopFloor";

export default function WorkCenterQueuePage() {
  const [lineFilter, setLineFilter] = useState("");

  const { data: queue = [], isLoading } = useQuery<LiveWOItem[]>({
    queryKey: ["sf-queue-board", lineFilter],
    queryFn: () => sfApi.getLiveQueue(lineFilter ? { line_id: lineFilter } : undefined),
    refetchInterval: 20_000,
  });

  // Group by line
  const byLine = queue.reduce<Record<string, LiveWOItem[]>>((acc, wo) => {
    const key = wo.line_id || "No Line";
    acc[key] = acc[key] || [];
    acc[key].push(wo);
    return acc;
  }, {});

  const lines = Object.keys(byLine).sort();

  const completionPct = (wo: LiveWOItem) =>
    wo.planned_qty > 0 ? Math.min(100, Math.round((wo.completed_qty / wo.planned_qty) * 100)) : 0;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <a href="/dashboard/shop-floor" className="text-sm text-gray-400 hover:text-gray-600">← Dashboard</a>
          </div>
          <h1 className="text-xl font-bold text-gray-900">Work Center Queue Board</h1>
          <p className="text-sm text-gray-500 mt-0.5">Live view by production line</p>
        </div>
        <div className="flex gap-2">
          <input
            className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm"
            placeholder="Filter by line…"
            value={lineFilter}
            onChange={(e) => setLineFilter(e.target.value)}
          />
          <span className="text-sm text-gray-400 self-center">{queue.length} WOs</span>
        </div>
      </div>

      {isLoading ? (
        <div className="text-center text-gray-400 py-12">Loading…</div>
      ) : queue.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-8 text-center text-sm text-gray-400">
          No active work orders
        </div>
      ) : (
        <div className="space-y-6">
          {lines.map((line) => (
            <div key={line} className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
              <div className="px-4 py-3 bg-gray-50 border-b border-gray-100 flex items-center justify-between">
                <h2 className="font-semibold text-gray-700">{line}</h2>
                <div className="flex gap-2 text-xs text-gray-400">
                  {(["RUNNING", "PAUSED", "BLOCKED", "QC_HOLD"] as const).map((s) => {
                    const count = byLine[line].filter((w) => w.live_status === s).length;
                    if (!count) return null;
                    return (
                      <span key={s} className={`px-1.5 py-0.5 rounded-full font-medium ${LIVE_STATUS_COLOR[s]}`}>
                        {count} {s}
                      </span>
                    );
                  })}
                </div>
              </div>
              <div className="divide-y divide-gray-50">
                {byLine[line].map((wo) => {
                  const pct = completionPct(wo);
                  return (
                    <div key={wo.id} className="px-4 py-3 flex items-center gap-4">
                      <div className="w-6 h-6 rounded-full flex items-center justify-center bg-gray-100 text-xs text-gray-500 font-mono flex-shrink-0">
                        {wo.step_sequence}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="font-medium text-sm truncate">{wo.step_name}</p>
                          <span className={`text-xs px-1.5 py-0.5 rounded-full flex-shrink-0 ${LIVE_STATUS_COLOR[wo.live_status]}`}>
                            {wo.live_status}
                          </span>
                          {wo.qc_required_flag && (
                            <span className="text-xs text-purple-500 flex-shrink-0">QC req.</span>
                          )}
                        </div>
                        <p className="text-xs text-gray-400 truncate">
                          {wo.product_name || "—"} · {wo.batch_no || "—"} · {wo.operator_name || "No operator"}
                        </p>
                        <div className="mt-1.5 flex items-center gap-2">
                          <div className="flex-1 bg-gray-100 rounded-full h-1.5">
                            <div
                              className={`h-1.5 rounded-full ${pct >= 100 ? "bg-teal-500" : "bg-indigo-500"}`}
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                          <span className="text-xs text-gray-400 flex-shrink-0 font-mono">
                            {wo.completed_qty.toFixed(0)} / {wo.planned_qty.toFixed(0)}
                          </span>
                        </div>
                      </div>
                      <div className="text-right flex-shrink-0">
                        {wo.scrap_qty > 0 && (
                          <p className="text-xs text-red-500">Scrap: {wo.scrap_qty.toFixed(0)}</p>
                        )}
                        {wo.has_active_downtime && (
                          <p className="text-xs text-red-600 font-medium">⚠ Downtime</p>
                        )}
                        {wo.last_event && (
                          <p className="text-xs text-gray-400">{wo.last_event}</p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
