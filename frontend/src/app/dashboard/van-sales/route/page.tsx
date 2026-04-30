"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { vanSalesApi, VISIT_STATUS_COLORS } from "@/lib/van_sales";
import Link from "next/link";

export default function RouteExecutionPage() {
  const qc = useQueryClient();
  const today = new Date().toISOString().split("T")[0];
  const [selectedVanId, setSelectedVanId] = useState("");

  const { data: vans = [] } = useQuery({ queryKey: ["vans"], queryFn: () => vanSalesApi.listVans({ status: "ACTIVE" }) });
  const { data: visits = [], refetch } = useQuery({
    queryKey: ["visits", selectedVanId, today],
    queryFn: () => vanSalesApi.listVisits(selectedVanId, today),
    enabled: !!selectedVanId,
  });

  const checkInMut = useMutation({
    mutationFn: (id: string) => vanSalesApi.checkIn(id, {}),
    onSuccess: () => refetch(),
  });
  const checkOutMut = useMutation({
    mutationFn: (id: string) => vanSalesApi.checkOut(id),
    onSuccess: () => refetch(),
  });
  const missedMut = useMutation({
    mutationFn: (id: string) => vanSalesApi.markMissed(id, "Customer unavailable"),
    onSuccess: () => refetch(),
  });

  const completed = visits.filter((v) => v.status === "COMPLETED").length;
  const missed = visits.filter((v) => v.status === "MISSED").length;
  const remaining = visits.filter((v) => v.status === "PLANNED").length;

  return (
    <div className="p-6 space-y-5 text-slate-200">
      <div>
        <h1 className="text-xl font-bold text-white">Route Execution</h1>
        <p className="text-slate-500 text-sm mt-0.5">{today} — Visit tracking</p>
      </div>

      <div>
        <label className="text-xs text-slate-400 mb-1 block">Select Van / Driver</label>
        <select value={selectedVanId} onChange={(e) => setSelectedVanId(e.target.value)}
          className="bg-[#0d1829] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 w-64">
          <option value="">Select van…</option>
          {vans.map((v) => <option key={v.id} value={v.id}>{v.van_code} — {v.plate_number ?? "no plate"}</option>)}
        </select>
      </div>

      {selectedVanId && (
        <>
          {/* Progress */}
          <div className="grid grid-cols-3 gap-4">
            <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-4 text-center">
              <p className="text-2xl font-bold text-emerald-400">{completed}</p>
              <p className="text-xs text-slate-500 mt-0.5">Completed</p>
            </div>
            <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-4 text-center">
              <p className="text-2xl font-bold text-amber-400">{remaining}</p>
              <p className="text-xs text-slate-500 mt-0.5">Remaining</p>
            </div>
            <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-4 text-center">
              <p className="text-2xl font-bold text-red-400">{missed}</p>
              <p className="text-xs text-slate-500 mt-0.5">Missed</p>
            </div>
          </div>

          {/* Visit list */}
          <div className="space-y-2">
            {visits.sort((a, b) => (a.sequence_no ?? 99) - (b.sequence_no ?? 99)).map((v) => (
              <div key={v.id} className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-4">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="w-7 h-7 rounded-full bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-xs text-indigo-300 font-bold">
                      {v.sequence_no ?? "?"}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-white font-mono">{v.customer_id.slice(0, 8)}…</p>
                      <p className="text-xs text-slate-500">{v.planned_time ? new Date(v.planned_time).toLocaleTimeString() : "No scheduled time"}</p>
                    </div>
                  </div>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${VISIT_STATUS_COLORS[v.status]}`}>{v.status}</span>
                </div>

                {v.status === "PLANNED" && (
                  <div className="flex gap-2">
                    <button onClick={() => checkInMut.mutate(v.id)}
                      className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium">
                      Check In
                    </button>
                    <button onClick={() => missedMut.mutate(v.id)}
                      className="px-3 py-1.5 rounded-lg border border-red-500/40 text-red-400 hover:bg-red-500/10 text-xs">
                      Mark Missed
                    </button>
                  </div>
                )}
                {v.status === "CHECKED_IN" && (
                  <div className="flex gap-2">
                    <Link href={`/dashboard/van-sales/pos?van_id=${selectedVanId}`}
                      className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium">
                      Create Sale
                    </Link>
                    <button onClick={() => checkOutMut.mutate(v.id)}
                      className="px-3 py-1.5 rounded-lg border border-white/[0.08] text-slate-400 hover:border-white/20 text-xs">
                      Check Out
                    </button>
                  </div>
                )}
                {v.check_in_time && (
                  <p className="text-xs text-slate-600 mt-2">
                    In: {new Date(v.check_in_time).toLocaleTimeString()}
                    {v.check_out_time && ` · Out: ${new Date(v.check_out_time).toLocaleTimeString()}`}
                  </p>
                )}
              </div>
            ))}
            {visits.length === 0 && (
              <div className="text-center py-10 text-slate-600">No visits planned for today on this van.</div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
