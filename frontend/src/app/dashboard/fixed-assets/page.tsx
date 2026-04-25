"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { faApi, fmtCurrency, FADashboardSummary } from "@/lib/fixed_assets";

export default function FADashboardPage() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["fa-dashboard"],
    queryFn: () => faApi.getDashboard(),
  });

  const runAI = useMutation({
    mutationFn: () => faApi.runAIAgents(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["fa-dashboard"] }),
  });

  if (isLoading || !data) return (
    <div className="p-6 flex items-center gap-3 text-gray-400">
      <div className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
      Loading…
    </div>
  );

  const kpis = [
    { label: "Total Assets",          value: data.total_assets,                        color: "text-blue-700" },
    { label: "Active Assets",         value: data.active_assets,                       color: "text-green-700" },
    { label: "Total Cost (KES)",       value: fmtCurrency(data.total_cost),             color: "text-indigo-600" },
    { label: "Accumulated Depr.",      value: fmtCurrency(data.total_accumulated_depreciation), color: "text-orange-600" },
    { label: "Net Book Value",         value: fmtCurrency(data.total_nbv),             color: "text-cyan-600" },
    { label: "Pending Depr. Lines",   value: data.pending_depreciation_lines,          color: "text-yellow-600" },
    { label: "AI Recommendations",    value: data.ai_pending_recommendations,          color: "text-purple-600" },
  ];

  const quickLinks = [
    { href: "/dashboard/fixed-assets/assets",       label: "Asset Register",        icon: "🏭" },
    { href: "/dashboard/fixed-assets/categories",   label: "Asset Categories",      icon: "📂" },
    { href: "/dashboard/fixed-assets/depreciation", label: "Depreciation Schedules",icon: "📅" },
    { href: "/dashboard/fixed-assets/posting",      label: "Posting Run",           icon: "⚡" },
    { href: "/dashboard/fixed-assets/disposal",     label: "Disposals",             icon: "🗑️" },
    { href: "/dashboard/fixed-assets/transfer",     label: "Transfers",             icon: "🔄" },
    { href: "/dashboard/fixed-assets/import",       label: "Legacy Import",         icon: "📥" },
    { href: "/dashboard/fixed-assets/ai",           label: "AI Agents",             icon: "🤖", badge: data.ai_pending_recommendations },
  ];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Fixed Asset Accounting</h1>
          <p className="text-sm text-gray-500 mt-0.5">Full financial lifecycle — acquisition · depreciation · disposal</p>
        </div>
        <div className="flex gap-2">
          <Link href="/dashboard/fixed-assets/assets/new" className="glow-button">
            + New Asset
          </Link>
          <button
            onClick={() => runAI.mutate()}
            disabled={runAI.isPending}
            className="glow-button-secondary"
          >
            {runAI.isPending ? "Running…" : "Run AI Agents"}
          </button>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
        {kpis.map((k) => (
          <div key={k.label} className="glow-card p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide leading-tight">{k.label}</p>
            <p className={`text-xl font-bold mt-1 ${k.color} leading-none`}>{k.value}</p>
          </div>
        ))}
      </div>

      {/* Quick links */}
      <div>
        <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wide mb-3">Module Navigation</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {quickLinks.map((q) => (
            <Link key={q.href} href={q.href} className="liquid-glass glow-hover p-4 flex items-center gap-3">
              <span className="text-2xl">{q.icon}</span>
              <div className="min-w-0">
                <p className="text-sm font-medium text-gray-800 truncate">{q.label}</p>
                {q.badge ? <p className="text-xs text-yellow-600">{q.badge} pending</p> : null}
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* NBV summary */}
      <div className="glass-panel p-5 space-y-3">
        <h2 className="text-sm font-semibold text-gray-700">Book Value Summary</h2>
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: "Gross Cost",             value: data.total_cost,                        color: "text-blue-600" },
            { label: "Accumulated Depreciation",value: data.total_accumulated_depreciation,   color: "text-orange-600" },
            { label: "Net Book Value",          value: data.total_nbv,                        color: "text-green-600" },
          ].map((row) => (
            <div key={row.label} className="text-center">
              <p className="text-xs text-gray-500 uppercase tracking-wide">{row.label}</p>
              <p className={`text-lg font-bold mt-1 ${row.color}`}>{fmtCurrency(row.value)}</p>
            </div>
          ))}
        </div>
        <div className="relative h-3 rounded-full bg-gray-100 overflow-hidden mt-2">
          <div
            className="absolute inset-y-0 left-0 rounded-full"
            style={{
              width: `${data.total_cost > 0 ? (data.total_accumulated_depreciation / data.total_cost) * 100 : 0}%`,
              background: "linear-gradient(90deg, rgba(249,115,22,0.7) 0%, rgba(239,68,68,0.6) 100%)",
            }}
          />
        </div>
        <p className="text-xs text-gray-400 text-center">
          {data.total_cost > 0
            ? `${((data.total_accumulated_depreciation / data.total_cost) * 100).toFixed(1)}% of total cost depreciated`
            : "No active assets"}
        </p>
      </div>
    </div>
  );
}
