"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { commissionsApi, TXN_STATUS_COLORS, TxnStatus } from "@/lib/commissions";

const STATUSES: TxnStatus[] = ["PENDING", "APPROVED", "PAID", "REJECTED", "REVERSED"];

export default function TransactionsPage() {
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("PENDING");
  const [calcForm, setCalcForm] = useState({ sales_rep_id: "", base_amount: "", calculation_date: new Date().toISOString().split("T")[0] });
  const [showCalc, setShowCalc] = useState(false);
  const [reviewId, setReviewId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState("");

  const { data: txns = [], isLoading } = useQuery({
    queryKey: ["cm-txns", statusFilter],
    queryFn: () => commissionsApi.listTransactions({ status: statusFilter || undefined, limit: 100 }),
  });

  const calcMut = useMutation({
    mutationFn: (data: any) => commissionsApi.calculate(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["cm-txns"] }); setShowCalc(false); },
  });

  const approveMut = useMutation({
    mutationFn: (id: string) => commissionsApi.approveTxn(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["cm-txns"] }); setReviewId(null); },
  });

  const rejectMut = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => commissionsApi.rejectTxn(id, reason),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["cm-txns"] }); setReviewId(null); setRejectReason(""); },
  });

  const upd = (k: string, v: string) => setCalcForm((f) => ({ ...f, [k]: v }));

  return (
    <div className="p-6 space-y-5 min-h-screen bg-[#060d18] text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Commission Transactions</h1>
          <p className="text-slate-500 text-sm mt-0.5">{txns.length} transactions</p>
        </div>
        <button onClick={() => setShowCalc(true)}
          className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium">
          + Calculate Commission
        </button>
      </div>

      {/* Calc form */}
      {showCalc && (
        <form onSubmit={(e) => { e.preventDefault(); calcMut.mutate({ sales_rep_id: calcForm.sales_rep_id, base_amount: parseFloat(calcForm.base_amount), calculation_date: calcForm.calculation_date }); }}
          className="rounded-xl border border-indigo-500/30 bg-indigo-500/10 p-4 space-y-3">
          <h2 className="text-sm font-semibold text-indigo-300">Calculate Commission</h2>
          <div className="grid grid-cols-3 gap-3">
            {[
              { k: "sales_rep_id", label: "Sales Rep ID (UUID)" },
              { k: "base_amount", label: "Base Amount (KES)" },
              { k: "calculation_date", label: "Calculation Date", type: "date" },
            ].map(({ k, label, type }) => (
              <div key={k}>
                <label className="text-[10px] text-slate-400 mb-1 block">{label}</label>
                <input type={type ?? "text"} value={(calcForm as any)[k]} onChange={(e) => upd(k, e.target.value)} required
                  className="w-full bg-white/[0.04] border border-white/[0.08] rounded px-3 py-2 text-sm text-white focus:outline-none font-mono" />
              </div>
            ))}
          </div>
          <div className="flex gap-2">
            <button type="submit" disabled={calcMut.isPending}
              className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium disabled:opacity-50">
              {calcMut.isPending ? "Calculating…" : "Calculate"}
            </button>
            <button type="button" onClick={() => setShowCalc(false)}
              className="px-4 py-2 rounded-lg border border-white/[0.08] text-slate-400 text-sm">Cancel</button>
          </div>
        </form>
      )}

      {/* Status filter */}
      <div className="flex gap-2 flex-wrap">
        {["", ...STATUSES].map((s) => (
          <button key={s} onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${statusFilter === s ? "bg-indigo-600 border-indigo-500 text-white" : "border-white/[0.08] text-slate-400 hover:border-white/20"}`}>
            {s || "All"}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="space-y-2">
        {isLoading && <p className="text-slate-500 text-sm">Loading…</p>}
        {txns.map((t) => (
          <div key={t.id} className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${TXN_STATUS_COLORS[t.status]}`}>{t.status}</span>
                  {t.is_reversal && <span className="text-[10px] px-2 py-0.5 rounded-full bg-red-500/20 text-red-400 font-medium">REVERSAL</span>}
                  <span className="text-xs text-slate-500">{t.period} · {t.calculation_date}</span>
                </div>
                <div className="grid grid-cols-3 gap-3 text-xs">
                  <div><p className="text-slate-500">Rep/Dist</p><p className="text-white font-mono">{(t.sales_rep_id || t.distributor_id || "—")?.slice(0, 8)}…</p></div>
                  <div><p className="text-slate-500">Base Amount</p><p className="text-white font-medium">KES {Number(t.base_amount).toLocaleString()}</p></div>
                  <div><p className="text-slate-500">Commission</p><p className="text-emerald-400 font-bold">KES {Number(t.commission_amount).toLocaleString()}</p></div>
                </div>
                {t.calc_detail && (
                  <p className="text-[10px] text-slate-600 mt-1.5">
                    Rule: {(t.calc_detail as any).rule_code} · {(t.calc_detail as any).commission_value}%
                  </p>
                )}
                {t.rejection_reason && <p className="text-xs text-red-400 mt-1">Rejected: {t.rejection_reason}</p>}
              </div>
              {t.status === "PENDING" && reviewId !== t.id && (
                <div className="flex gap-2 shrink-0">
                  <button onClick={() => approveMut.mutate(t.id)} disabled={approveMut.isPending}
                    className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs disabled:opacity-50">Approve</button>
                  <button onClick={() => setReviewId(t.id)}
                    className="px-3 py-1.5 rounded-lg border border-red-500/40 text-red-400 text-xs hover:bg-red-500/10">Reject</button>
                </div>
              )}
            </div>
            {reviewId === t.id && (
              <div className="mt-3 space-y-2 border-t border-white/[0.07] pt-3">
                <input value={rejectReason} onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="Rejection reason (required)"
                  className="w-full bg-white/[0.04] border border-white/[0.08] rounded px-3 py-1.5 text-xs text-white focus:outline-none" />
                <div className="flex gap-2">
                  <button onClick={() => rejectMut.mutate({ id: t.id, reason: rejectReason })}
                    disabled={!rejectReason || rejectMut.isPending}
                    className="px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-500 text-white text-xs disabled:opacity-50">Confirm Reject</button>
                  <button onClick={() => setReviewId(null)} className="px-3 py-1.5 text-slate-500 text-xs hover:text-slate-300">Cancel</button>
                </div>
              </div>
            )}
          </div>
        ))}
        {!isLoading && txns.length === 0 && (
          <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-8 text-center text-slate-600">No transactions</div>
        )}
      </div>
    </div>
  );
}
