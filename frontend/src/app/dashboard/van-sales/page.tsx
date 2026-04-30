"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { vanSalesApi, VAN_STATUS_COLORS, VISIT_STATUS_COLORS, PAYMENT_STATUS_COLORS } from "@/lib/van_sales";
import Link from "next/link";

function KpiCard({ label, value, sub, color = "text-white" }: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-5">
      <p className="text-[10px] text-slate-500 uppercase tracking-widest mb-1">{label}</p>
      <p className={`text-3xl font-bold ${color}`}>{value}</p>
      {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
    </div>
  );
}

export default function VanSalesDashboard() {
  const qc = useQueryClient();
  const { data: vans = [] } = useQuery({
    queryKey: ["vans"],
    queryFn: () => vanSalesApi.listVans(),
  });
  const { data: aiRecs = [] } = useQuery({
    queryKey: ["vs-ai-recs"],
    queryFn: () => vanSalesApi.aiRecs({ status: "PENDING" }),
  });

  const aiMut = useMutation({
    mutationFn: () => vanSalesApi.runAI(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["vs-ai-recs"] }),
  });

  const active = vans.filter((v) => v.status === "ACTIVE").length;
  const onRoute = vans.filter((v) => v.status === "ON_ROUTE").length;

  return (
    <div className="p-6 space-y-6 text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Van Sales / Mobile POS</h1>
          <p className="text-slate-500 text-sm mt-0.5">Route-based field sales execution</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => aiMut.mutate()}
            disabled={aiMut.isPending}
            className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium disabled:opacity-50"
          >
            {aiMut.isPending ? "Running AI…" : "Run AI Agents"}
          </button>
          <Link href="/dashboard/van-sales/vans/new"
            className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium">
            + New Van
          </Link>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard label="Total Vans" value={vans.length} />
        <KpiCard label="Active" value={active} color="text-emerald-400" />
        <KpiCard label="On Route" value={onRoute} color="text-blue-400" />
        <KpiCard label="AI Alerts" value={aiRecs.length} color={aiRecs.length > 0 ? "text-amber-400" : "text-white"} />
      </div>

      {/* Quick nav */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { href: "/dashboard/van-sales/route", label: "Route Execution", icon: "🗺️", desc: "Today's visits & stops" },
          { href: "/dashboard/van-sales/pos", label: "Mobile POS", icon: "📱", desc: "Create sale / return" },
          { href: "/dashboard/van-sales/stock", label: "Van Stock", icon: "📦", desc: "Load & track stock" },
          { href: "/dashboard/van-sales/reconciliation", label: "Reconciliation", icon: "✅", desc: "Daily close-out" },
        ].map((card) => (
          <Link key={card.href} href={card.href}
            className="rounded-xl border border-white/[0.07] bg-[#0d1829] hover:bg-white/[0.04] p-4 transition-colors">
            <p className="text-2xl mb-2">{card.icon}</p>
            <p className="text-sm font-semibold text-white">{card.label}</p>
            <p className="text-xs text-slate-500 mt-0.5">{card.desc}</p>
          </Link>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Van list */}
        <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-white">Vans</h2>
            <Link href="/dashboard/van-sales/vans" className="text-xs text-indigo-400 hover:text-indigo-300">View all</Link>
          </div>
          <div className="space-y-2">
            {vans.slice(0, 8).map((v) => (
              <Link key={v.id} href={`/dashboard/van-sales/vans/${v.id}`}
                className="flex items-center justify-between p-3 rounded-lg bg-white/[0.025] hover:bg-white/[0.05] transition-colors">
                <div>
                  <p className="text-sm text-white font-medium">{v.van_code}</p>
                  <p className="text-xs text-slate-500">{v.plate_number ?? "No plate"}</p>
                </div>
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${VAN_STATUS_COLORS[v.status]}`}>
                  {v.status}
                </span>
              </Link>
            ))}
            {vans.length === 0 && <p className="text-sm text-slate-600 text-center py-4">No vans configured</p>}
          </div>
        </div>

        {/* AI Alerts */}
        <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-white">AI Alerts</h2>
            <Link href="/dashboard/van-sales/ai" className="text-xs text-indigo-400 hover:text-indigo-300">View all</Link>
          </div>
          <div className="space-y-2">
            {aiRecs.slice(0, 4).map((r) => (
              <div key={r.id} className="p-3 rounded-lg bg-white/[0.025] border border-white/[0.04]">
                <p className="text-xs text-white font-medium">{r.title}</p>
                <p className="text-xs text-slate-500 mt-0.5 line-clamp-1">{r.body}</p>
              </div>
            ))}
            {aiRecs.length === 0 && <p className="text-sm text-slate-600 text-center py-4">No pending alerts</p>}
          </div>
        </div>
      </div>
    </div>
  );
}
