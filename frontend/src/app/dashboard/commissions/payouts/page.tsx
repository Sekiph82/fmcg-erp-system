"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { commissionsApi, PAYOUT_STATUS_COLORS, PayoutStatus } from "@/lib/commissions";

const STATUSES: PayoutStatus[] = ["DRAFT", "SUBMITTED", "APPROVED", "PAID", "CANCELLED"];

export default function PayoutsPage() {
  const qc = useQueryClient();
  const today = new Date().toISOString().split("T")[0];
  const currentPeriod = today.slice(0, 7);
  const [statusFilter, setStatusFilter] = useState("");
  const [form, setForm] = useState({ entity_id: "", applies_to: "SALES_REP", period: currentPeriod });

  const { data: payouts = [], isLoading } = useQuery({
    queryKey: ["cm-payouts-all", statusFilter],
    queryFn: () => commissionsApi.listPayouts({ status: statusFilter || undefined }),
  });

  const createMut = useMutation({
    mutationFn: (data: any) => commissionsApi.createPayout(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["cm-payouts-all"] }); },
  });

  const approveMut = useMutation({
    mutationFn: (id: string) => commissionsApi.approvePayout(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cm-payouts-all"] }),
  });

  const markPaidMut = useMutation({
    mutationFn: (id: string) => commissionsApi.markPaid(id, today),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cm-payouts-all"] }),
  });

  const upd = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <div className="p-6 space-y-5 min-h-screen bg-[#060d18] text-slate-200">
      <div>
        <h1 className="text-xl font-bold text-white">Commission Payouts</h1>
        <p className="text-slate-500 text-sm mt-0.5">Period close-out and payment tracking</p>
      </div>

      {/* Create payout */}
      <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-5 space-y-3">
        <h2 className="text-sm font-semibold text-white">Generate Payout for Period</h2>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="text-[10px] text-slate-400 mb-1 block">Entity ID (UUID)</label>
            <input value={form.entity_id} onChange={(e) => upd("entity_id", e.target.value)}
              className="w-full bg-white/[0.04] border border-white/[0.08] rounded px-3 py-2 text-sm text-white focus:outline-none font-mono" />
          </div>
          <div>
            <label className="text-[10px] text-slate-400 mb-1 block">Applies To</label>
            <select value={form.applies_to} onChange={(e) => upd("applies_to", e.target.value)}
              className="w-full bg-[#0d1829] border border-white/[0.08] rounded px-3 py-2 text-sm text-white focus:outline-none">
              {["SALES_REP","DISTRIBUTOR","TEAM"].map((a) => <option key={a} value={a}>{a.replace("_"," ")}</option>)}
            </select>
          </div>
          <div>
            <label className="text-[10px] text-slate-400 mb-1 block">Period</label>
            <input value={form.period} onChange={(e) => upd("period", e.target.value)}
              className="w-full bg-white/[0.04] border border-white/[0.08] rounded px-3 py-2 text-sm text-white focus:outline-none" placeholder="YYYY-MM" />
          </div>
        </div>
        <button onClick={() => createMut.mutate(form)} disabled={!form.entity_id || createMut.isPending}
          className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium disabled:opacity-50">
          {createMut.isPending ? "Generating…" : "Generate Payout"}
        </button>
      </div>

      {/* Filter */}
      <div className="flex gap-2 flex-wrap">
        {["", ...STATUSES].map((s) => (
          <button key={s} onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${statusFilter === s ? "bg-indigo-600 border-indigo-500 text-white" : "border-white/[0.08] text-slate-400 hover:border-white/20"}`}>
            {s || "All"}
          </button>
        ))}
      </div>

      {/* Payouts */}
      <div className="space-y-3">
        {isLoading && <p className="text-slate-500 text-sm">Loading…</p>}
        {payouts.map((p) => (
          <div key={p.id} className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${PAYOUT_STATUS_COLORS[p.status]}`}>{p.status}</span>
                  <span className="text-xs text-slate-500">{p.period} · {p.applies_to.replace("_"," ")}</span>
                </div>
                <p className="text-xs text-slate-400 font-mono mb-2">{p.entity_id.slice(0, 8)}…</p>
                <div className="grid grid-cols-3 gap-4 text-xs">
                  <div><p className="text-slate-500">Commission</p><p className="text-white font-medium">KES {Number(p.total_commission).toLocaleString()}</p></div>
                  <div><p className="text-slate-500">Adjustments</p><p className={Number(p.adjustments_total) >= 0 ? "text-emerald-400" : "text-red-400"}>{Number(p.adjustments_total) >= 0 ? "+" : ""}KES {Number(p.adjustments_total).toLocaleString()}</p></div>
                  <div><p className="text-slate-500">Net Payout</p><p className="text-emerald-400 font-bold">KES {Number(p.net_commission).toLocaleString()}</p></div>
                </div>
                {p.payment_date && <p className="text-xs text-slate-600 mt-1">Paid: {p.payment_date}</p>}
                {p.txn_ids && <p className="text-[10px] text-slate-600 mt-0.5">{p.txn_ids.length} transactions included</p>}
              </div>
              <div className="flex gap-2 shrink-0">
                {p.status === "DRAFT" && (
                  <button onClick={() => approveMut.mutate(p.id)} disabled={approveMut.isPending}
                    className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs disabled:opacity-50">Approve</button>
                )}
                {p.status === "APPROVED" && (
                  <button onClick={() => markPaidMut.mutate(p.id)} disabled={markPaidMut.isPending}
                    className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs disabled:opacity-50">Mark Paid</button>
                )}
              </div>
            </div>
          </div>
        ))}
        {!isLoading && payouts.length === 0 && (
          <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-8 text-center text-slate-600">No payouts</div>
        )}
      </div>
    </div>
  );
}
