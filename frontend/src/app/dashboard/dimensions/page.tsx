"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { dimApi, DimDashboard } from "@/lib/dimensions";
import Link from "next/link";
import { tx, lx } from "@/lib/i18n/core";

const QUICK_LINKS = lx(() => [
  { label: tx("Dimension Types"),     href: "/dashboard/dimensions/types",       desc: tx("Manage analysis axes") },
  { label: tx("Dimension Values"),    href: "/dashboard/dimensions/values",       desc: tx("Hierarchy tree editor") },
  { label: tx("Cost Centers"),        href: "/dashboard/dimensions/cost-centers", desc: tx("Cost center master") },
  { label: tx("Allocation Rules"),    href: "/dashboard/dimensions/allocations",  desc: tx("Overhead distribution rules") },
  { label: tx("Allocation Run"),      href: "/dashboard/dimensions/allocation-run", desc: tx("Run & preview allocations") },
  { label: tx("Validation Rules"),    href: "/dashboard/dimensions/validation",   desc: tx("Mandatory dim policies") },
  { label: tx("Default Rules"),       href: "/dashboard/dimensions/defaults",     desc: tx("Auto-derivation rules") },
  { label: tx("Reclassify"),          href: "/dashboard/dimensions/reclassify",   desc: tx("Correct dim tags") },
  { label: tx("Completeness Report"), href: "/dashboard/dimensions/completeness", desc: tx("Tagging health") },
  { label: tx("AI Agents"),           href: "/dashboard/dimensions/ai",           desc: tx("Intelligent analysis") },
]);

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
    { label: tx("Dimension Types"),      value: summary.total_dim_types,          color: "text-indigo-400" },
    { label: tx("Dimension Values"),     value: summary.total_dim_values,          color: "text-blue-400" },
    { label: tx("Active Cost Centers"),  value: summary.total_cost_centers,        color: "text-cyan-400" },
    { label: tx("Allocation Rules"),     value: summary.active_allocation_rules,   color: "text-purple-400" },
    { label: tx("Pending AI Recs"),      value: summary.pending_ai_recs,           color: "text-yellow-400" },
    { label: tx("Untagged Today"),       value: summary.untagged_transactions_today, color: "text-red-400" },
  ] : [];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{tx("Accounting Dimensions")}</h1>
          <p className="text-sm text-gray-500">{tx("Cost Centers · Allocation · Profitability Analysis")}</p>
        </div>
        <button
          onClick={() => runAgents.mutate()}
          disabled={runAgents.isPending}
          className="glow-button"
        >
          {runAgents.isPending ? tx("Running…") : tx("Run AI Agents")}
        </button>
      </div>

      {runAgents.isSuccess && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-sm text-green-700">
          {tx("✓ AI agents completed. New recommendations generated.")}
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
