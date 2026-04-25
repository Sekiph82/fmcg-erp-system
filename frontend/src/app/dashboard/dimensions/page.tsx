"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { dimApi, DimDashboard } from "@/lib/dimensions";
import Link from "next/link";

const QUICK_LINKS = [
  { label: "Dimension Types",     href: "/dashboard/dimensions/types",       desc: "Manage analysis axes" },
  { label: "Dimension Values",    href: "/dashboard/dimensions/values",       desc: "Hierarchy tree editor" },
  { label: "Cost Centers",        href: "/dashboard/dimensions/cost-centers", desc: "Cost center master" },
  { label: "Allocation Rules",    href: "/dashboard/dimensions/allocations",  desc: "Overhead distribution rules" },
  { label: "Allocation Run",      href: "/dashboard/dimensions/allocation-run", desc: "Run & preview allocations" },
  { label: "Validation Rules",    href: "/dashboard/dimensions/validation",   desc: "Mandatory dim policies" },
  { label: "Default Rules",       href: "/dashboard/dimensions/defaults",     desc: "Auto-derivation rules" },
  { label: "Reclassify",          href: "/dashboard/dimensions/reclassify",   desc: "Correct dim tags" },
  { label: "Completeness Report", href: "/dashboard/dimensions/completeness", desc: "Tagging health" },
  { label: "AI Agents",           href: "/dashboard/dimensions/ai",           desc: "Intelligent analysis" },
];

export default function DimensionsDashboard() {
  const qc = useQueryClient();
  const { data: summary, isLoading } = useQuery({
    queryKey: ["dim-dashboard"],
    queryFn: () => dimApi.getDashboard(),
  });

  const runAgents = useMutation({
    mutationFn: () => dimApi.runAgents(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["dim-dashboard"] }),
  });

  const kpis = summary ? [
    { label: "Dimension Types",      value: summary.total_dim_types,          color: "text-indigo-400" },
    { label: "Dimension Values",     value: summary.total_dim_values,          color: "text-blue-400" },
    { label: "Active Cost Centers",  value: summary.total_cost_centers,        color: "text-cyan-400" },
    { label: "Allocation Rules",     value: summary.active_allocation_rules,   color: "text-purple-400" },
    { label: "Pending AI Recs",      value: summary.pending_ai_recs,           color: "text-yellow-400" },
    { label: "Untagged Today",       value: summary.untagged_transactions_today, color: "text-red-400" },
  ] : [];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Accounting Dimensions</h1>
          <p className="text-sm text-gray-500">Cost Centers · Allocation · Profitability Analysis</p>
        </div>
        <button
          onClick={() => runAgents.mutate()}
          disabled={runAgents.isPending}
          className="glow-button"
        >
          {runAgents.isPending ? "Running…" : "Run AI Agents"}
        </button>
      </div>

      {runAgents.isSuccess && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-sm text-green-700">
          ✓ AI agents completed. New recommendations generated.
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {isLoading
          ? Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="glow-card p-4 animate-pulse h-20" />
            ))
          : kpis.map((k) => (
              <div key={k.label} className="glow-card p-4 text-center">
                <p className="text-xs text-gray-500">{k.label}</p>
                <p className={`text-2xl font-bold mt-1 ${k.color}`}>{k.value}</p>
              </div>
            ))}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {QUICK_LINKS.map((l) => (
          <Link key={l.href} href={l.href}
            className="liquid-glass p-4 space-y-1 glow-hover block">
            <p className="text-sm font-semibold text-indigo-300">{l.label}</p>
            <p className="text-xs text-gray-400">{l.desc}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
