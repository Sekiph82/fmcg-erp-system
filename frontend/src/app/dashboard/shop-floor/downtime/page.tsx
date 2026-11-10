"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { describeShopFloorError, sfApi, SFDowntimeLog, DOWNTIME_CAT_LABEL, IMPACT_COLOR } from "@/lib/shopFloor";
import { ShopFloorConnectionNotice, useShopFloorConnectionState } from "@/components/shop-floor/ShopFloorConnectionNotice";
import { useAuth } from "@/context/AuthContext";

const DOWNTIME_CATS = [
  "MACHINE_BREAKDOWN", "MATERIAL_SHORTAGE", "PACKAGING_SHORTAGE", "QC_WAITING",
  "CHANGEOVER", "CLEANING", "POWER_ISSUE", "LABOR_SHORTAGE",
  "SUPERVISOR_HOLD", "MAINTENANCE_STOP", "LABEL_MISMATCH", "IT_ISSUE", "OTHER",
];

function fmtDuration(start: string, end?: string | null): string {
  const ms = new Date(end ?? Date.now()).getTime() - new Date(start).getTime();
  const mins = Math.floor(ms / 60000);
  if (mins < 60) return `${mins}m`;
  return `${Math.floor(mins / 60)}h ${mins % 60}m`;
}

export default function DowntimeBoardPage() {
  const qc = useQueryClient();
  const { refreshUser } = useAuth();
  const connection = useShopFloorConnectionState();
  const [showClosed, setShowClosed] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [lineId, setLineId] = useState("");
  const [filterLineId, setFilterLineId] = useState("");
  const [category, setCategory] = useState("MACHINE_BREAKDOWN");
  const [reason, setReason] = useState("");
  const [machineName, setMachineName] = useState("");
  const [operatorName, setOperatorName] = useState("");
  const [impactLevel, setImpactLevel] = useState<"LOW" | "MEDIUM" | "HIGH" | "CRITICAL">("MEDIUM");
  const [requestError, setRequestError] = useState<{ message: string; requiresRefresh: boolean } | null>(null);
  const [requiresStateRefresh, setRequiresStateRefresh] = useState(false);
  const [refreshingState, setRefreshingState] = useState(false);

  const { data: logs = [], isLoading, isError } = useQuery<SFDowntimeLog[]>({
    queryKey: ["sf-downtime", showClosed, filterLineId],
    queryFn: () => sfApi.listDowntime({ is_closed: showClosed, line_id: filterLineId || undefined }),
    refetchInterval: 20_000,
  });

  const reportRequestError = (error: unknown) => {
    const detail = describeShopFloorError(error);
    if (detail.requiresRefresh) setRequiresStateRefresh(true);
    setRequestError(detail);
  };
  const writesBlocked = connection.state !== "online" || requiresStateRefresh || isLoading || isError;
  const refreshShopFloorState = async () => {
    setRefreshingState(true);
    try {
      await refreshUser();
      await qc.invalidateQueries({ queryKey: ["sf-downtime"] }, { throwOnError: true });
      connection.acknowledgeRefresh();
      setRequiresStateRefresh(false);
      setRequestError(null);
    } catch (error) {
      reportRequestError(error);
    } finally {
      setRefreshingState(false);
    }
  };

  const stopMut = useMutation({
    mutationFn: ({ id, comments }: { id: string; comments?: string }) =>
      sfApi.stopDowntime(id, comments),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sf-downtime"] }),
    onError: reportRequestError,
  });

  const createMut = useMutation({
    mutationFn: () => sfApi.startDowntime({
      line_id: lineId || null,
      machine_name: machineName || null,
      operator_name: operatorName || null,
      downtime_category: category,
      root_reason: reason || null,
      impact_level: impactLevel,
    }),
    onSuccess: () => {
      setShowModal(false);
      setReason(""); setMachineName(""); setLineId(""); setOperatorName("");
      setRequestError(null);
      setRequiresStateRefresh(false);
      qc.invalidateQueries({ queryKey: ["sf-downtime"] });
    },
    onError: reportRequestError,
  });

  const active = logs.filter((l) => !l.is_closed);
  const closed = logs.filter((l) => l.is_closed);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <a href="/dashboard/shop-floor" className="text-sm text-gray-400 hover:text-gray-600">← Dashboard</a>
          </div>
          <h1 className="text-xl font-bold text-gray-900">Downtime Board</h1>
          <p className="text-sm text-gray-500 mt-0.5">Track production interruptions</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowClosed(!showClosed)}
            className={`px-3 py-1.5 text-sm rounded-lg border ${showClosed ? "bg-gray-100 border-gray-300" : "border-gray-200"}`}
          >
            {showClosed ? "Active Only" : "Show Closed"}
          </button>
          <button
            onClick={() => setShowModal(true)}
            className="px-3 py-1.5 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700"
          >
            + Log Downtime
          </button>
        </div>
      </div>

      {!showModal && (
        <ShopFloorConnectionNotice
          state={connection.state}
          onRefresh={() => void refreshShopFloorState()}
          refreshing={refreshingState}
          forceRefresh={requiresStateRefresh}
        />
      )}

      {requestError && (
        <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
          <p>{requestError.message}</p>
          {requestError.requiresRefresh && (
            <button type="button" onClick={() => void refreshShopFloorState()} disabled={refreshingState} className="mt-2 min-h-11 rounded-md border border-red-500 px-3 font-semibold disabled:opacity-50">
              {refreshingState ? "Refreshing Shop Floor state…" : "Refresh Shop Floor state"}
            </button>
          )}
        </div>
      )}

      <div className="max-w-sm">
        <label htmlFor="shop-floor-downtime-line-filter" className="text-xs text-gray-500">Production line filter</label>
        <input id="shop-floor-downtime-line-filter" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm mt-0.5" value={filterLineId} onChange={(event) => setFilterLineId(event.target.value)} placeholder="Enter an assigned line for scoped access" />
      </div>

      {/* Active KPIs */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "Active Events", value: active.length, color: "text-red-600" },
          { label: "Avg Duration (min)", value: active.length ? Math.round(active.reduce((s, l) => s + (Date.now() - new Date(l.start_time).getTime()) / 60000, 0) / active.length) : 0, color: "text-orange-600" },
          { label: "Closed Today", value: closed.length, color: "text-gray-600" },
        ].map((k) => (
          <div key={k.label} className="bg-white rounded-xl border border-gray-100 shadow-sm p-3 text-center">
            <p className="text-xs text-gray-400">{k.label}</p>
            <p className={`text-2xl font-bold mt-0.5 ${k.color}`}>{k.value}</p>
          </div>
        ))}
      </div>

      {/* Active Downtime */}
      {active.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="px-4 py-3 bg-red-50 border-b border-red-100">
            <h2 className="text-sm font-semibold text-red-700">Active Downtime ({active.length})</h2>
          </div>
          <div className="divide-y divide-gray-50">
            {active.map((dt) => (
              <div key={dt.id} className="px-4 py-3 flex items-center gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-sm">{DOWNTIME_CAT_LABEL[dt.downtime_category] || dt.downtime_category}</p>
                    <span className={`text-xs px-1.5 py-0.5 rounded ${IMPACT_COLOR[dt.impact_level]}`}>{dt.impact_level}</span>
                  </div>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {dt.line_id || "No line"} · {dt.machine_name || ""} · {dt.operator_name || ""}
                  </p>
                  {dt.root_reason && <p className="text-xs text-gray-500 mt-0.5 italic">{dt.root_reason}</p>}
                </div>
                <div className="text-right flex-shrink-0">
                  <p className="text-lg font-bold text-red-600">{fmtDuration(dt.start_time)}</p>
                  <button
                    onClick={() => stopMut.mutate({ id: dt.id })}
                    disabled={stopMut.isPending || writesBlocked}
                    className="mt-1 text-xs px-2 py-1 bg-gray-800 text-white rounded hover:bg-gray-900 disabled:opacity-40"
                  >
                    Stop
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Log List */}
      {isError ? (
        <div role="alert" className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          <p>Downtime records could not be loaded. If your access is line-scoped, enter an assigned line in the filter above.</p>
          <button type="button" onClick={() => void refreshShopFloorState()} disabled={refreshingState} className="mt-2 min-h-11 rounded-md border border-amber-500 px-3 font-semibold disabled:opacity-50">
            {refreshingState ? "Refreshing Shop Floor state…" : "Refresh Shop Floor state"}
          </button>
        </div>
      ) : isLoading ? (
        <div className="text-center text-gray-400 py-8">Loading…</div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100">
            <h2 className="text-sm font-semibold text-gray-700">
              {showClosed ? "All Records" : "Open Records"} ({logs.length})
            </h2>
          </div>
          {logs.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-8">No downtime records</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[42rem] text-sm">
              <thead className="bg-gray-50 text-xs text-gray-400">
                <tr>
                  {["Category", "Line", "Machine", "Start", "Duration", "Impact", "Status"].map((h) => (
                    <th key={h} className="px-3 py-2.5 text-left font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {logs.map((dt) => (
                  <tr key={dt.id} className="hover:bg-gray-50">
                    <td className="px-3 py-2 text-xs font-medium">
                      {DOWNTIME_CAT_LABEL[dt.downtime_category] || dt.downtime_category}
                    </td>
                    <td className="px-3 py-2 text-xs text-gray-500">{dt.line_id || "—"}</td>
                    <td className="px-3 py-2 text-xs text-gray-500">{dt.machine_name || "—"}</td>
                    <td className="px-3 py-2 text-xs text-gray-400">{new Date(dt.start_time).toLocaleTimeString()}</td>
                    <td className="px-3 py-2 text-xs font-mono">
                      {dt.is_closed && dt.duration_minutes ? `${Number(dt.duration_minutes).toFixed(0)}m` : fmtDuration(dt.start_time, dt.end_time)}
                    </td>
                    <td className="px-3 py-2">
                      <span className={`text-xs px-1.5 py-0.5 rounded ${IMPACT_COLOR[dt.impact_level]}`}>{dt.impact_level}</span>
                    </td>
                    <td className="px-3 py-2">
                      <span className={`text-xs px-1.5 py-0.5 rounded ${dt.is_closed ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                        {dt.is_closed ? "Closed" : "Active"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Create Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-end sm:items-center justify-center z-50 p-2 sm:p-4">
          <div role="dialog" aria-modal="true" aria-labelledby="shop-floor-downtime-create-title" className="bg-white rounded-2xl p-4 sm:p-6 w-full max-w-md max-h-[calc(100dvh-1rem)] overflow-y-auto shadow-xl space-y-4">
            <h2 id="shop-floor-downtime-create-title" className="text-lg font-bold text-gray-900">Log Downtime Event</h2>
            <ShopFloorConnectionNotice
              state={connection.state}
              onRefresh={() => void refreshShopFloorState()}
              refreshing={refreshingState}
              forceRefresh={requiresStateRefresh}
            />
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label htmlFor="shop-floor-downtime-create-line" className="text-xs text-gray-500">Line ID</label>
                <input id="shop-floor-downtime-create-line" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm mt-0.5" value={lineId} onChange={(e) => setLineId(e.target.value)} placeholder="e.g. LINE-1" />
                <p className="mt-1 text-xs text-gray-500">Scoped users must enter a line in their edit scope.</p>
              </div>
              <div>
                <label className="text-xs text-gray-500">Machine Name</label>
                <input className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm mt-0.5" value={machineName} onChange={(e) => setMachineName(e.target.value)} placeholder="Optional" />
              </div>
              <div>
                <label className="text-xs text-gray-500">Operator label (context only)</label>
                <input className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm mt-0.5" value={operatorName} onChange={(e) => setOperatorName(e.target.value)} />
              </div>
              <div>
                <label className="text-xs text-gray-500">Impact Level</label>
                <select className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm mt-0.5" value={impactLevel} onChange={(e) => setImpactLevel(e.target.value as any)}>
                  {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((l) => <option key={l} value={l}>{l}</option>)}
                </select>
              </div>
            </div>
            <div>
              <label className="text-xs text-gray-500">Category</label>
              <select className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm mt-0.5" value={category} onChange={(e) => setCategory(e.target.value)}>
                {DOWNTIME_CATS.map((c) => <option key={c} value={c}>{DOWNTIME_CAT_LABEL[c as keyof typeof DOWNTIME_CAT_LABEL] || c}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor="shop-floor-downtime-create-reason" className="text-xs text-gray-500">Root Reason</label>
              <textarea id="shop-floor-downtime-create-reason" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm mt-0.5" rows={2} value={reason} onChange={(e) => setReason(e.target.value)} />
            </div>
            <div className="flex gap-2">
              <button onClick={() => setShowModal(false)} className="flex-1 min-h-12 py-2 border border-gray-200 rounded-lg text-sm">Cancel</button>
            <button onClick={() => createMut.mutate()} disabled={createMut.isPending || writesBlocked} className="flex-1 min-h-12 py-2 bg-red-600 text-white rounded-lg text-sm font-medium disabled:opacity-40">
                Start Downtime
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
