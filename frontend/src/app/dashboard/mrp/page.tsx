"use client";
import React, { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { mrpApi, STATUS_COLOR, fmtQty, SUGGESTION_TYPE_COLOR } from "@/lib/mrp";
import { PageHelpTooltip } from "@/components/help/PageHelpTooltip";

const StatusBadge = ({ s }: { s: string }) => (
  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLOR[s] ?? "bg-gray-100 text-gray-600"}`}>{s}</span>
);

export default function MRPDashboardPage() {
  const qc = useQueryClient();
  const [running, setRunning] = useState(false);

  const { data: dash, isLoading } = useQuery({
    queryKey: ["mrp-dashboard"],
    queryFn: () => mrpApi.getDashboard(),
    refetchInterval: running ? 3000 : false,
  });

  const { data: alerts = [] } = useQuery({
    queryKey: ["mrp-alerts"],
    queryFn: () => mrpApi.getShortageAlerts(),
  });

  const runMutation = useMutation({
    mutationFn: () => mrpApi.triggerRun({ planning_horizon_days: 90, include_forecast: true, include_safety_stock: true }),
    onSuccess: () => {
      setRunning(false);
      qc.invalidateQueries({ queryKey: ["mrp-dashboard"] });
      qc.invalidateQueries({ queryKey: ["mrp-alerts"] });
    },
    onMutate: () => setRunning(true),
    onError: () => setRunning(false),
  });

  const kpis = [
    { label: "Last Run Status", value: dash?.last_run ? <StatusBadge s={dash.last_run.status} /> : "—", sub: dash?.last_run?.run_no },
    { label: "Shortage Products", value: dash?.shortage_products ?? "—", color: "text-red-600", sub: "in last run" },
    { label: "Open Suggestions", value: dash?.open_suggestions ?? "—", color: "text-orange-600", sub: "pending action" },
    { label: "Pending Approval", value: dash?.pending_approval ?? "—", color: "text-yellow-600", sub: "need review" },
    { label: "Active Forecasts", value: dash?.active_forecasts ?? "—", color: "text-blue-600", sub: "demand plans" },
    { label: "Total MRP Runs", value: dash?.total_runs ?? "—", sub: "all time" },
  ];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white" style={{ borderLeft: "4px solid #6366f1", paddingLeft: 12 }}>
            MRP & Planning
          </h1>
          <p className="text-sm text-gray-500 mt-1">Material Requirements Planning · Demand Forecasting · Planning Engine</p>
        </div>
        <div className="flex gap-3 flex-wrap items-center">
          <PageHelpTooltip topic="planning-mrp" />
          <Link href="/dashboard/mrp/forecast" className="px-4 py-2 rounded-lg text-sm bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-50">
            📈 Forecasts
          </Link>
          <Link href="/dashboard/mrp/suggestions" className="px-4 py-2 rounded-lg text-sm bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-50">
            📋 Suggestions
          </Link>
          <Link href="/dashboard/mrp/run" className="px-4 py-2 rounded-lg text-sm bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-50">
            🗂 Run History
          </Link>
          <button
            onClick={() => runMutation.mutate()}
            disabled={running || runMutation.isPending}
            className="px-5 py-2 rounded-lg text-sm font-semibold bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-60 flex items-center gap-2"
          >
            {running || runMutation.isPending ? (
              <><span className="animate-spin">⟳</span> Running MRP...</>
            ) : "▶ Run MRP Now"}
          </button>
        </div>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        {kpis.map((k, i) => (
          <div key={i} className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
            <p className="text-xs text-gray-500 font-medium">{k.label}</p>
            <p className={`text-2xl font-bold mt-1 ${k.color ?? "text-gray-900 dark:text-white"}`}>{k.value}</p>
            {k.sub && <p className="text-xs text-gray-400 mt-0.5">{k.sub}</p>}
          </div>
        ))}
      </div>

      {/* Last run details */}
      {dash?.last_run && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Last MRP Run</h3>
            <Link href={`/dashboard/mrp/run?id=${dash.last_run.id}`} className="text-xs text-indigo-600 hover:underline">View Results →</Link>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
            <div><p className="text-xs text-gray-500">Run No</p><p className="font-mono font-semibold">{dash.last_run.run_no}</p></div>
            <div><p className="text-xs text-gray-500">Run Date</p><p className="font-semibold">{dash.last_run.run_date}</p></div>
            <div><p className="text-xs text-gray-500">Horizon</p><p className="font-semibold">{dash.last_run.planning_horizon_days} days</p></div>
            <div><p className="text-xs text-gray-500">Products Analysed</p><p className="font-semibold">{dash.last_run.product_count ?? "—"}</p></div>
          </div>
          {dash.last_run.error_message && (
            <div className="mt-3 p-3 bg-red-50 dark:bg-red-950/20 rounded-lg text-sm text-red-700">
              ⚠ Error: {dash.last_run.error_message}
            </div>
          )}
        </div>
      )}

      {/* Shortage alerts */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
        <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-700 flex justify-between items-center">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">🚨 Shortage Alerts</h3>
          <span className="text-xs text-gray-400">From latest completed run</span>
        </div>
        {alerts.length === 0 ? (
          <div className="px-5 py-8 text-center text-gray-400 text-sm">No shortages detected — stock levels are healthy ✓</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-700 text-xs uppercase text-gray-500">
                <tr>
                  {["SKU", "Product", "Net Required", "Suggested Qty", "Required By", "Run"].map(h => (
                    <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {alerts.map((a, i) => (
                  <tr key={i} className="hover:bg-red-50/40 dark:hover:bg-red-950/10">
                    <td className="px-4 py-3 font-mono text-xs">{a.product_sku ?? "—"}</td>
                    <td className="px-4 py-3 font-medium">{a.product_name ?? "—"}</td>
                    <td className="px-4 py-3 text-right font-bold text-red-600">{fmtQty(a.net_requirement)}</td>
                    <td className="px-4 py-3 text-right text-orange-600">{fmtQty(a.suggested_qty)}</td>
                    <td className="px-4 py-3 text-xs font-mono">{a.required_date ?? "—"}</td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-400">{a.run_no}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Recent runs */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
        <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-700 flex justify-between items-center">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Recent MRP Runs</h3>
          <Link href="/dashboard/mrp/run" className="text-xs text-indigo-600 hover:underline">View all →</Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-700 text-xs uppercase text-gray-500">
              <tr>
                {["Run No", "Date", "Status", "Horizon", "Products", "Shortages", "Suggestions"].map(h => (
                  <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {(dash?.recent_runs ?? []).map((r, i) => (
                <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-750">
                  <td className="px-4 py-3 font-mono text-xs">
                    <Link href={`/dashboard/mrp/run?id=${r.id}`} className="text-indigo-600 hover:underline">{r.run_no}</Link>
                  </td>
                  <td className="px-4 py-3 text-xs font-mono">{r.run_date}</td>
                  <td className="px-4 py-3"><StatusBadge s={r.status} /></td>
                  <td className="px-4 py-3">{r.planning_horizon_days}d</td>
                  <td className="px-4 py-3 text-center">{r.product_count ?? "—"}</td>
                  <td className="px-4 py-3 text-center text-red-600 font-semibold">{r.shortage_count ?? "—"}</td>
                  <td className="px-4 py-3 text-center">{r.suggestion_count ?? "—"}</td>
                </tr>
              ))}
              {!dash?.recent_runs?.length && (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No MRP runs yet. Click &quot;Run MRP Now&quot; to start.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
