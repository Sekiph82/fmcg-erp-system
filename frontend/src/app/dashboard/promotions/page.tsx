"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { promoApi, PromoDashboard, fmtCurrency } from "@/lib/promotions";
import Link from "next/link";

const QUICK_LINKS = [
  { label: "Scheme List",       href: "/dashboard/promotions/schemes",      desc: "All promotional schemes" },
  { label: "New Scheme",        href: "/dashboard/promotions/schemes/new",  desc: "Create promotion" },
  { label: "Order Simulator",   href: "/dashboard/promotions/simulate",     desc: "Test promo on sample order" },
  { label: "Override Approvals",href: "/dashboard/promotions/overrides",    desc: "Pending approval queue" },
  { label: "Usage Analytics",   href: "/dashboard/promotions/analytics",    desc: "Cost & coverage report" },
  { label: "AI Agents",         href: "/dashboard/promotions/ai",           desc: "Conflict & cost insights" },
];

export default function PromotionsDashboard() {
  const qc = useQueryClient();
  const { data: summary, isLoading } = useQuery({
    queryKey: ["promo-dashboard"],
    queryFn: () => promoApi.getDashboard(),
  });

  const runAgents = useMutation({
    mutationFn: () => promoApi.runAgents(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["promo-dashboard"] }),
  });

  const kpis = summary ? [
    { label: "Active Schemes",       value: summary.active_schemes,            color: "text-green-400" },
    { label: "Expiring Soon (30d)",  value: summary.expiring_soon,             color: "text-yellow-400" },
    { label: "Applications (Month)", value: summary.total_applications_month,  color: "text-blue-400" },
    { label: "Discount (Month)",     value: fmtCurrency(summary.total_discount_month),    color: "text-orange-400" },
    { label: "Free Goods (Month)",   value: fmtCurrency(summary.total_free_value_month),  color: "text-purple-400" },
    { label: "Pending Overrides",    value: summary.pending_override_requests,  color: "text-red-400" },
    { label: "Pending AI Recs",      value: summary.pending_ai_recs,            color: "text-indigo-400" },
  ] : [];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Promotional Schemes</h1>
          <p className="text-sm text-gray-500">Auto-Apply Engine · Free Goods · Discounts · Tiers · Bundles</p>
        </div>
        <button onClick={() => runAgents.mutate()} disabled={runAgents.isPending} className="glow-button">
          {runAgents.isPending ? "Running…" : "Run AI Agents"}
        </button>
      </div>

      {runAgents.isSuccess && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-sm text-green-700">
          ✓ AI agents completed.
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
        {isLoading
          ? Array.from({ length: 7 }).map((_, i) => <div key={i} className="glow-card p-4 animate-pulse h-20" />)
          : kpis.map((k) => (
              <div key={k.label} className="glow-card p-4 text-center">
                <p className="text-xs text-gray-500">{k.label}</p>
                <p className={`text-lg font-bold mt-1 ${k.color}`}>{k.value}</p>
              </div>
            ))}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {QUICK_LINKS.map((l) => (
          <Link key={l.href} href={l.href} className="liquid-glass p-4 space-y-1 glow-hover block">
            <p className="text-sm font-semibold text-indigo-300">{l.label}</p>
            <p className="text-xs text-gray-400">{l.desc}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
