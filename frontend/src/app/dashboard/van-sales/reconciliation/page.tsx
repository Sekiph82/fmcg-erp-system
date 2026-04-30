"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { vanSalesApi, RECON_STATUS_COLORS } from "@/lib/van_sales";

export default function ReconciliationPage() {
  const qc = useQueryClient();
  const today = new Date().toISOString().split("T")[0];
  const [selectedVanId, setSelectedVanId] = useState("");

  const { data: vans = [] } = useQuery({ queryKey: ["vans"], queryFn: () => vanSalesApi.listVans() });
  const { data: recons = [], refetch } = useQuery({
    queryKey: ["recons", selectedVanId],
    queryFn: () => vanSalesApi.listReconciliations(selectedVanId),
    enabled: !!selectedVanId,
  });

  const submitMut = useMutation({
    mutationFn: () => vanSalesApi.createReconciliation(selectedVanId, { route_date: today, notes: "End of day reconciliation" }),
    onSuccess: () => refetch(),
  });

  const approveMut = useMutation({
    mutationFn: (id: string) => vanSalesApi.approveReconciliation(id),
    onSuccess: () => refetch(),
  });

  const todayRecon = recons.find((r) => r.route_date === today);

  return (
    <div className="p-6 space-y-5 text-slate-200">
      <div>
        <h1 className="text-xl font-bold text-white">Daily Reconciliation</h1>
        <p className="text-slate-500 text-sm mt-0.5">End-of-day stock and payment close-out</p>
      </div>

      <div>
        <label className="text-xs text-slate-400 mb-1 block">Select Van</label>
        <select value={selectedVanId} onChange={(e) => setSelectedVanId(e.target.value)}
          className="bg-[#0d1829] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 w-64">
          <option value="">Select van…</option>
          {vans.map((v) => <option key={v.id} value={v.id}>{v.van_code} — {v.plate_number ?? "no plate"}</option>)}
        </select>
      </div>

      {selectedVanId && (
        <>
          {/* Today's reconciliation */}
          <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-white">Today — {today}</h2>
              {!todayRecon && (
                <button onClick={() => submitMut.mutate()} disabled={submitMut.isPending}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium disabled:opacity-50">
                  {submitMut.isPending ? "Submitting…" : "Submit Close-Out"}
                </button>
              )}
              {todayRecon && todayRecon.status === "SUBMITTED" && (
                <button onClick={() => approveMut.mutate(todayRecon.id)} disabled={approveMut.isPending}
                  className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium disabled:opacity-50">
                  {approveMut.isPending ? "Approving…" : "Approve"}
                </button>
              )}
            </div>

            {todayRecon ? (
              <div className="space-y-3">
                <div className="flex items-center gap-2 mb-2">
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${RECON_STATUS_COLORS[todayRecon.status]}`}>{todayRecon.status}</span>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {[
                    { label: "Total Sales", value: todayRecon.total_sales, color: "text-emerald-400" },
                    { label: "Cash", value: todayRecon.total_cash, color: "text-white" },
                    { label: "M-Pesa", value: todayRecon.total_mpesa, color: "text-blue-400" },
                    { label: "Returns", value: todayRecon.total_returns, color: "text-red-400" },
                  ].map((c) => (
                    <div key={c.label} className="rounded-lg bg-white/[0.03] p-3">
                      <p className="text-[10px] text-slate-500 mb-1">{c.label}</p>
                      <p className={`text-lg font-bold ${c.color}`}>KES {((c.value ?? 0) as number).toLocaleString()}</p>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-slate-600 text-sm">No reconciliation submitted yet for today</p>
            )}
          </div>

          {/* History */}
          <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-5">
            <h2 className="text-sm font-semibold text-white mb-4">History</h2>
            <div className="space-y-2">
              {recons.map((r) => (
                <div key={r.id} className="flex items-center justify-between p-3 rounded-lg bg-white/[0.025]">
                  <div>
                    <p className="text-sm text-white">{r.route_date}</p>
                    <p className="text-xs text-slate-500">Sales: KES {(r.total_sales ?? 0).toLocaleString()} · Cash: KES {(r.total_cash ?? 0).toLocaleString()}</p>
                  </div>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${RECON_STATUS_COLORS[r.status]}`}>{r.status}</span>
                </div>
              ))}
              {recons.length === 0 && <p className="text-slate-600 text-sm text-center py-4">No reconciliation history</p>}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
