"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motoSalesApi, MPESA_STATUS_COLORS, MpesaStatus } from "@/lib/moto_sales";

export default function MpesaPage() {
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("");
  const [stkForm, setStkForm] = useState({ txn_id: "", phone_number: "", amount: "" });
  const [showStk, setShowStk] = useState(false);

  const { data: payments = [], isLoading } = useQuery({
    queryKey: ["mpesa-payments", statusFilter],
    queryFn: () => motoSalesApi.listMpesa({ status: statusFilter || undefined }),
  });

  const stkMut = useMutation({
    mutationFn: () => motoSalesApi.stkPush({
      txn_id: stkForm.txn_id,
      phone_number: stkForm.phone_number,
      amount: parseFloat(stkForm.amount),
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mpesa-payments"] });
      setShowStk(false);
      setStkForm({ txn_id: "", phone_number: "", amount: "" });
    },
  });

  const statuses: MpesaStatus[] = ["PENDING", "SUCCESS", "FAILED", "TIMEOUT", "CANCELLED"];
  const pending = payments.filter((p) => p.status === "PENDING").length;
  const success = payments.filter((p) => p.status === "SUCCESS").length;
  const failed = payments.filter((p) => p.status === "FAILED").length;

  return (
    <div className="p-6 space-y-5 min-h-screen bg-[#060d18] text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">M-Pesa Payments</h1>
          <p className="text-slate-500 text-sm mt-0.5">STK Push management and reconciliation</p>
        </div>
        <button onClick={() => setShowStk(true)}
          className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium">
          + STK Push
        </button>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4">
          <p className="text-[10px] text-slate-500 mb-1">Pending</p>
          <p className="text-3xl font-bold text-amber-400">{pending}</p>
        </div>
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4">
          <p className="text-[10px] text-slate-500 mb-1">Successful</p>
          <p className="text-3xl font-bold text-emerald-400">{success}</p>
        </div>
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4">
          <p className="text-[10px] text-slate-500 mb-1">Failed</p>
          <p className="text-3xl font-bold text-red-400">{failed}</p>
        </div>
      </div>

      {/* STK Push form */}
      {showStk && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-5 space-y-3">
          <h2 className="text-sm font-semibold text-emerald-300">Initiate STK Push</h2>
          <div className="grid grid-cols-3 gap-3">
            {[
              { k: "txn_id", label: "Transaction ID (UUID)", placeholder: "UUID" },
              { k: "phone_number", label: "Phone (254...)", placeholder: "254712345678" },
              { k: "amount", label: "Amount (KES)", placeholder: "500.00" },
            ].map(({ k, label, placeholder }) => (
              <div key={k}>
                <label className="text-[10px] text-slate-400 mb-1 block">{label}</label>
                <input value={(stkForm as any)[k]} onChange={(e) => setStkForm((f) => ({ ...f, [k]: e.target.value }))}
                  placeholder={placeholder}
                  className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none" />
              </div>
            ))}
          </div>
          <div className="flex gap-2">
            <button onClick={() => stkMut.mutate()} disabled={!stkForm.txn_id || !stkForm.phone_number || !stkForm.amount || stkMut.isPending}
              className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium disabled:opacity-50">
              {stkMut.isPending ? "Sending…" : "Send STK Push"}
            </button>
            <button onClick={() => setShowStk(false)} className="px-4 py-2 rounded-lg border border-white/[0.08] text-slate-400 text-sm">Cancel</button>
          </div>
        </div>
      )}

      {/* Filter */}
      <div className="flex gap-2 flex-wrap">
        {["", ...statuses].map((s) => (
          <button key={s} onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${statusFilter === s ? "bg-indigo-600 border-indigo-500 text-white" : "border-white/[0.08] text-slate-400 hover:border-white/20"}`}>
            {s || "All"}
          </button>
        ))}
      </div>

      {/* Payments table */}
      <div className="rounded-xl border border-white/[0.07] overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-white/[0.03] text-slate-500 text-xs uppercase tracking-wider">
            <tr>
              <th className="px-4 py-3 text-left">Phone</th>
              <th className="px-4 py-3 text-right">Amount</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Receipt</th>
              <th className="px-4 py-3 text-left">Requested</th>
              <th className="px-4 py-3 text-left">Callback</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {isLoading && <tr><td colSpan={6} className="text-center py-8 text-slate-600">Loading…</td></tr>}
            {!isLoading && payments.length === 0 && <tr><td colSpan={6} className="text-center py-8 text-slate-600">No M-Pesa payments</td></tr>}
            {payments.map((p) => (
              <tr key={p.id} className="hover:bg-white/[0.02]">
                <td className="px-4 py-3 text-slate-300 font-mono text-xs">{p.phone_number}</td>
                <td className="px-4 py-3 text-right text-white font-medium">KES {Number(p.amount).toLocaleString()}</td>
                <td className="px-4 py-3">
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${MPESA_STATUS_COLORS[p.status]}`}>{p.status}</span>
                </td>
                <td className="px-4 py-3 text-slate-400 font-mono text-xs">{p.mpesa_receipt_no ?? "—"}</td>
                <td className="px-4 py-3 text-slate-500 text-xs">{new Date(p.request_time).toLocaleString()}</td>
                <td className="px-4 py-3 text-slate-500 text-xs">{p.callback_time ? new Date(p.callback_time).toLocaleString() : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
