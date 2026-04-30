"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { contractsApi, STATUS_COLORS, PARTY_COLORS, CONTRACT_TYPE_LABELS } from "@/lib/contracts";
import Link from "next/link";

function KpiCard({ label, value, color = "text-white" }: { label: string; value: number; color?: string }) {
  return (
    <div className="glow-card p-5">
      <p className="text-[10px] text-slate-500 uppercase tracking-widest mb-1">{label}</p>
      <p className={`text-3xl font-bold ${color}`}>{value}</p>
    </div>
  );
}

export default function ContractsDashboard() {
  const qc = useQueryClient();
  const { data: summary } = useQuery({ queryKey: ["ct-summary"], queryFn: () => contractsApi.reportSummary() });
  const { data: contracts = [] } = useQuery({ queryKey: ["contracts"], queryFn: () => contractsApi.list({ limit: 10 }) });
  const { data: expiring = [] } = useQuery({ queryKey: ["ct-expiring"], queryFn: () => contractsApi.reportExpiring(30) });
  const { data: aiRecs = [] } = useQuery({ queryKey: ["ct-ai-recs"], queryFn: () => contractsApi.aiRecs({ status: "PENDING" }) });

  const aiMut = useMutation({
    mutationFn: () => contractsApi.runAI(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ct-ai-recs"] }),
  });

  const s = summary as any;

  return (
    <div className="p-6 space-y-6 text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Contract Management</h1>
          <p className="text-slate-500 text-sm mt-0.5">Commercial agreements lifecycle & compliance</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => aiMut.mutate()} disabled={aiMut.isPending}
            className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium disabled:opacity-50">
            {aiMut.isPending ? "Running AI…" : "Run AI"}
          </button>
          <Link href="/dashboard/contracts/new"
            className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium">
            + New Contract
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <KpiCard label="Total" value={s?.total ?? 0} />
        <KpiCard label="Active" value={s?.active ?? 0} color="text-emerald-400" />
        <KpiCard label="Expiring 30d" value={s?.expiring_30_days ?? 0} color="text-amber-400" />
        <KpiCard label="Draft" value={s?.draft ?? 0} color="text-slate-400" />
        <KpiCard label="Under Review" value={s?.under_review ?? 0} color="text-blue-400" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent contracts */}
        <div className="lg:col-span-2 glow-card p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-white">Recent Contracts</h2>
            <Link href="/dashboard/contracts/list" className="text-xs text-indigo-400 hover:text-indigo-300">View all</Link>
          </div>
          <div className="space-y-2">
            {contracts.map((c) => (
              <Link key={c.id} href={`/dashboard/contracts/list/${c.id}`}
                className="flex items-center justify-between p-3 rounded-lg bg-white/[0.025] hover:bg-white/[0.05] transition-colors">
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-white font-medium truncate">{c.contract_code} — {c.contract_name}</p>
                  <p className="text-xs text-slate-500">
                    {CONTRACT_TYPE_LABELS[c.contract_type]} · {c.end_date ?? "No end date"}
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0 ml-3">
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${PARTY_COLORS[c.party_type]}`}>{c.party_type}</span>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[c.status]}`}>{c.status}</span>
                </div>
              </Link>
            ))}
            {contracts.length === 0 && <p className="text-slate-600 text-sm text-center py-4">No contracts</p>}
          </div>
        </div>

        <div className="space-y-4">
          {/* Expiring soon */}
          <div className="glow-card border-amber-500/20 p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-amber-300">Expiring in 30 Days</h2>
              <Link href="/dashboard/contracts/expiring" className="text-xs text-indigo-400">View all</Link>
            </div>
            <div className="space-y-2">
              {expiring.slice(0, 4).map((c) => (
                <Link key={c.id} href={`/dashboard/contracts/list/${c.id}`}
                  className="block p-2 rounded-lg bg-white/[0.03] hover:bg-white/[0.06] transition-colors">
                  <p className="text-xs text-white font-medium">{c.contract_code}</p>
                  <p className="text-[10px] text-amber-400 mt-0.5">Expires: {c.end_date}</p>
                </Link>
              ))}
              {expiring.length === 0 && <p className="text-slate-600 text-xs">None expiring soon</p>}
            </div>
          </div>

          {/* AI alerts */}
          <div className="glow-card p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-white">AI Alerts</h2>
              <Link href="/dashboard/contracts/ai" className="text-xs text-indigo-400">View all</Link>
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
