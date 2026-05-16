"use client";

import dynamic from "next/dynamic";
import { ModuleWorkspace } from "@/components/workspace";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { sfApi, SFDashboard, LIVE_STATUS_COLOR, IMPACT_COLOR, DOWNTIME_CAT_LABEL } from "@/lib/shopFloor";

function ShopFloorDashboardTab() {
  const qc = useQueryClient();

  const { data: dash, isLoading } = useQuery<SFDashboard>({
    queryKey: ["sf-dashboard"],
    queryFn: () => sfApi.getDashboard(),
    refetchInterval: 30_000,
  });

  const { data: alerts = [] } = useQuery({
    queryKey: ["sf-alerts"],
    queryFn: () => sfApi.getAlerts(),
    refetchInterval: 30_000,
  });

  const runAI = useMutation({
    mutationFn: sfApi.runAI,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sf-dashboard"] }),
  });

  const kpis = dash ? [
    { label: "Active Sessions",    value: dash.active_sessions,         color: "text-indigo-600" },
    { label: "Running WOs",        value: dash.running_work_orders,      color: "text-green-600" },
    { label: "Paused WOs",         value: dash.paused_work_orders,       color: "text-yellow-600" },
    { label: "QC Holds",           value: dash.qc_hold_count,            color: "text-purple-600" },
    { label: "Active Downtime",    value: dash.active_downtime_count,    color: "text-red-600" },
    { label: "Help Requests",      value: dash.help_requests_open,       color: "text-orange-600" },
    { label: "Good Qty Today",     value: dash.total_good_qty_today.toFixed(0), color: "text-teal-600" },
    { label: "Scrap Today",        value: dash.total_scrap_today.toFixed(0),    color: "text-red-400" },
    { label: "Pending AI Recs",    value: dash.pending_ai_recs,          color: "text-blue-600" },
    { label: "Overrides Today",    value: dash.supervisor_overrides_today, color: "text-gray-600" },
  ] : [];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Shop Floor Dashboard</h1>
          <p className="text-sm text-gray-500 mt-0.5">Real-time factory execution overview</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => runAI.mutate()}
            disabled={runAI.isPending}
            className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
          >
            {runAI.isPending ? "Running AI…" : "Run AI Agents"}
          </button>
          <a href="/dashboard/shop-floor/terminal" className="px-3 py-1.5 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700">
            Operator Terminal
          </a>
          <a href="/dashboard/shop-floor/supervisor" className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            Supervisor Console
          </a>
        </div>
      </div>

      {/* KPI Grid */}
      {isLoading ? (
        <div className="text-center text-gray-400 py-8">Loading…</div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {kpis.map((k) => (
            <div key={k.label} className="bg-white rounded-xl border border-gray-100 shadow-sm p-3 text-center">
              <p className="text-xs text-gray-400">{k.label}</p>
              <p className={`text-2xl font-bold mt-0.5 ${k.color}`}>{k.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Alerts */}
      {alerts.length > 0 && (
        <div className="bg-white rounded-xl border border-orange-200 shadow-sm p-4">
          <h2 className="text-sm font-semibold text-orange-700 mb-3">Active Alerts ({alerts.length})</h2>
          <div className="space-y-2">
            {(alerts as any[]).map((a, i) => (
              <div key={i} className={`flex items-start gap-3 p-2.5 rounded-lg text-sm ${
                a.severity === "HIGH" || a.severity === "CRITICAL"
                  ? "bg-red-50 text-red-800"
                  : "bg-yellow-50 text-yellow-800"
              }`}>
                <span className="font-medium text-xs px-1.5 py-0.5 rounded bg-white/60">{a.type}</span>
                <span>{a.message}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Active Downtime */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-gray-700">Active Downtime</h2>
            <a href="/dashboard/shop-floor/downtime" className="text-xs text-indigo-500 hover:underline">View All →</a>
          </div>
          {!dash || dash.active_downtimes.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-4">No active downtime</p>
          ) : (
            <div className="space-y-2">
              {dash.active_downtimes.map((dt) => {
                const elapsed = Math.floor((Date.now() - new Date(dt.start_time).getTime()) / 60000);
                return (
                  <div key={dt.id} className="flex items-center justify-between p-2.5 bg-red-50 rounded-lg">
                    <div>
                      <p className="text-sm font-medium text-red-800">{DOWNTIME_CAT_LABEL[dt.downtime_category] || dt.downtime_category}</p>
                      <p className="text-xs text-red-600">{dt.line_id || "No line"} • {dt.machine_name || ""}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-bold text-red-700">{elapsed} min</p>
                      <span className={`text-xs px-1.5 py-0.5 rounded ${IMPACT_COLOR[dt.impact_level]}`}>{dt.impact_level}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Recent Handovers */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-gray-700">Recent Handovers</h2>
            <a href="/dashboard/shop-floor/handover" className="text-xs text-indigo-500 hover:underline">View All →</a>
          </div>
          {!dash || dash.recent_handovers.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-4">No recent handovers</p>
          ) : (
            <div className="space-y-2">
              {dash.recent_handovers.slice(0, 4).map((h) => (
                <div key={h.id} className="flex items-center justify-between p-2.5 rounded-lg bg-gray-50">
                  <div>
                    <p className="text-sm font-medium text-gray-800">
                      {h.shift_from_name || "?"} → {h.shift_to_name || "?"}
                    </p>
                    <p className="text-xs text-gray-400">{h.line_id || "All lines"} • {h.outgoing_supervisor || "—"}</p>
                  </div>
                  <span className={`text-xs px-1.5 py-0.5 rounded ${h.is_approved ? "bg-green-100 text-green-700" : "bg-yellow-100 text-yellow-700"}`}>
                    {h.is_approved ? "Approved" : "Pending"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Nav Links */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { href: "/dashboard/shop-floor/terminal", label: "Operator Terminal", desc: "Start, pause, finish WOs", color: "bg-green-50 border-green-200 text-green-700" },
          { href: "/dashboard/shop-floor/queue",    label: "Work Center Queue", desc: "Live WO board by line",   color: "bg-blue-50 border-blue-200 text-blue-700" },
          { href: "/dashboard/shop-floor/downtime", label: "Downtime Board",    desc: "Track interruptions",    color: "bg-red-50 border-red-200 text-red-700" },
          { href: "/dashboard/shop-floor/handover", label: "Shift Handover",    desc: "Document shift transfers", color: "bg-indigo-50 border-indigo-200 text-indigo-700" },
        ].map((n) => (
          <a key={n.href} href={n.href} className={`block rounded-xl border p-4 hover:shadow-md transition-shadow ${n.color}`}>
            <p className="font-semibold text-sm">{n.label}</p>
            <p className="text-xs mt-0.5 opacity-70">{n.desc}</p>
          </a>
        ))}
      </div>
    </div>
  );
}

const SFTerminalPage   = dynamic(() => import("@/app/dashboard/shop-floor/terminal/page"),   { ssr: false });
const SFSupervisorPage = dynamic(() => import("@/app/dashboard/shop-floor/supervisor/page"), { ssr: false });
const SFQueuePage      = dynamic(() => import("@/app/dashboard/shop-floor/queue/page"),      { ssr: false });
const SFDowntimePage   = dynamic(() => import("@/app/dashboard/shop-floor/downtime/page"),   { ssr: false });
const SFHandoverPage   = dynamic(() => import("@/app/dashboard/shop-floor/handover/page"),   { ssr: false });

export default function ShopFloorPage() {
  const tabs = [
    { key: "overview",   label: "Overview",   permission: "production.view", content: <ShopFloorDashboardTab /> },
    { key: "terminal",   label: "Terminal",   permission: "production.view", content: <SFTerminalPage /> },
    { key: "supervisor", label: "Supervisor", permission: "production.view", content: <SFSupervisorPage /> },
    { key: "queue",      label: "Queue",      permission: "production.view", content: <SFQueuePage /> },
    { key: "downtime",   label: "Downtime",   permission: "production.view", content: <SFDowntimePage /> },
    { key: "handover",   label: "Handover",   permission: "production.view", content: <SFHandoverPage /> },
  ];
  return (
    <ModuleWorkspace
      title="Shop Floor"
      description="Operator terminal, supervisor console, queue board, downtime, handover"
      permission="production.view"
      tabs={tabs}
      defaultTab="overview"
    />
  );
}
