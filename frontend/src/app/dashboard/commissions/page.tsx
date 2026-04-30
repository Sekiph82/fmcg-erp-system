"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { commissionsApi, TXN_STATUS_COLORS, PAYOUT_STATUS_COLORS } from "@/lib/commissions";
import Link from "next/link";

function KpiCard({ label, value, color = "text-white", sub }: { label: string; value: string | number; color?: string; sub?: string }) {
  return (
    <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-5">
      <p className="text-[10px] text-slate-500 uppercase tracking-widest mb-1">{label}</p>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
      {sub && <p className="text-xs text-slate-600 mt-0.5">{sub}</p>}
    </div>
  );
}

export default function CommissionsDashboard() {
  const qc = useQueryClient();
  const { data: summary } = useQuery({ queryKey: ["cm-summary"], queryFn: () => commissionsApi.reportSummary() });
  const { data: txns = [] } = useQuery({ queryKey: ["cm-txns-pending"], queryFn: () => commissionsApi.listTransactions({ status: "PENDING", limit: 10 }) });
  const { data: payouts = [] } = useQuery({ queryKey: ["cm-payouts"], queryFn: () => commissionsApi.listPayouts({ status: "DRAFT" }) });
  const { data: aiRecs = [] } = useQuery({ queryKey: ["cm-ai-recs"], queryFn: () => commissionsApi.aiRecs({ status: "PENDING" }) });

  const aiMut = useMutation({
    mutationFn: () => commissionsApi.runAI(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cm-ai-recs"] }),
  });

  const s = summary as any;

  return (
    <div className="p-6 space-y-6 text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Sales Commission Tracking</h1>
          <p className="text-slate-500 text-sm mt-0.5">Incentive engine — rules, calculations, payouts</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => aiMut.mutate()} disabled={aiMut.isPending}
            className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium disabled:opacity-50">
            {aiMut.isPending ? "Running AI…" : "Run AI"}
          </button>
          <Link href="/dashboard/commissions/rules"
            className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium">
            Manage Rules
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <KpiCard label="Total Transactions" value={s?.total_txns ?? 0} />
        <KpiCard label="Pending Approval" value={s?.pending ?? 0} color="text-amber-400" />
        <KpiCard label="Approved" value={s?.approved ?? 0} color="text-blue-400" />
        <KpiCard label="Total Commission" value={`KES ${(s?.total_commission ?? 0).toLocaleString()}`} color="text-emerald-400" />
        <KpiCard label="Paid Out" value={`KES ${(s?.paid_commission ?? 0).toLocaleString()}`} color="text-white" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Pending approvals */}
        <div className="lg:col-span-2 rounded-xl border border-white/[0.07] bg-[#0d1829] p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-white">Pending Approval</h2>
            <Link href="/dashboard/commissions/transactions" className="text-xs text-indigo-400 hover:text-indigo-300">All transactions</Link>
          </div>
          <div className="space-y-2">
            {txns.map((t) => (
              <div key={t.id} className="flex items-center justify-between p-3 rounded-lg bg-white/[0.025]">
                <div>
                  <p className="text-xs text-white font-medium font-mono">{t.id.slice(0, 8)}…</p>
                  <p className="text-[10px] text-slate-500">{t.period} · {t.calculation_date}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-sm font-bold text-emerald-400">KES {Number(t.commission_amount).toLocaleString()}</span>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${TXN_STATUS_COLORS[t.status]}`}>{t.status}</span>
                </div>
              </div>
            ))}
            {txns.length === 0 && <p className="text-slate-600 text-sm text-center py-4">No pending transactions</p>}
          </div>
        </div>

        <div className="space-y-4">
          {/* Payouts */}
          <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-white">Draft Payouts</h2>
              <Link href="/dashboard/commissions/payouts" className="text-xs text-indigo-400">View all</Link>
            </div>
            <div className="space-y-2">
              {payouts.slice(0, 4).map((p) => (
                <div key={p.id} className="flex items-center justify-between p-2 rounded-lg bg-white/[0.03]">
                  <div>
                    <p className="text-xs text-slate-400 font-mono">{p.entity_id.slice(0, 8)}…</p>
                    <p className="text-[10px] text-slate-600">{p.period}</p>
                  </div>
                  <span className="text-xs text-emerald-400 font-medium">KES {Number(p.net_commission).toLocaleString()}</span>
                </div>
              ))}
              {payouts.length === 0 && <p className="text-slate-600 text-xs">No draft payouts</p>}
            </div>
          </div>

          {/* AI */}
          <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-white">AI Insights</h2>
              <Link href="/dashboard/commissions/ai" className="text-xs text-indigo-400">View all</Link>
            </div>
            <div className="space-y-2">
              {aiRecs.slice(0, 3).map((r) => (
                <div key={r.id} className="p-2 rounded-lg bg-white/[0.03]">
                  <p className="text-xs text-white font-medium line-clamp-1">{r.title}</p>
                  <p className="text-[10px] text-slate-500 mt-0.5 line-clamp-1">{r.body}</p>
                </div>
              ))}
              {aiRecs.length === 0 && <p className="text-slate-600 text-xs">No alerts</p>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
