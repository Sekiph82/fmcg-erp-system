"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { financeApi, AccountingPeriod, PeriodStatus } from "@/lib/finance";

const STATUS_PILL: Record<PeriodStatus, string> = {
  OPEN: "bg-green-100 text-green-700",
  CLOSED: "bg-yellow-100 text-yellow-700",
  LOCKED: "bg-red-100 text-red-700",
};

export default function PeriodClosingPage() {
  const qc = useQueryClient();
  const [newPeriod, setNewPeriod] = useState("");

  const { data: periods, isLoading } = useQuery<AccountingPeriod[]>({
    queryKey: ["accounting-periods"],
    queryFn: financeApi.listPeriods,
    staleTime: 30_000,
  });

  const createMut = useMutation({
    mutationFn: (data: { period_ym: string }) => financeApi.createPeriod(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["accounting-periods"] });
      setNewPeriod("");
    },
  });

  const closeMut = useMutation({
    mutationFn: (id: string) => financeApi.closePeriod(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["accounting-periods"] }),
  });

  const lockMut = useMutation({
    mutationFn: (id: string) => financeApi.lockPeriod(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["accounting-periods"] }),
  });

  return (
    <div className="max-w-4xl mx-auto space-y-5 pb-10">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Period Closing</h1>
        <p className="text-sm text-gray-400 mt-0.5">
          Open, close, and lock accounting periods. Locked periods cannot be posted to.
        </p>
      </div>

      {/* Create period */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
        <h2 className="font-semibold text-gray-800 mb-3">Open New Period</h2>
        <div className="flex gap-3 items-end">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Period (YYYY-MM)</label>
            <input
              type="month"
              value={newPeriod}
              onChange={(e) => setNewPeriod(e.target.value)}
              className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
            />
          </div>
          <button
            onClick={() => newPeriod && createMut.mutate({ period_ym: newPeriod })}
            disabled={!newPeriod || createMut.isPending}
            className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
          >
            {createMut.isPending ? "Creating…" : "Create Period"}
          </button>
        </div>
        {createMut.isError && (
          <p className="text-sm text-red-500 mt-2">Failed to create period. It may already exist.</p>
        )}
      </div>

      {/* Periods table */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-100">
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Period</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Status</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Closed At</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Notes</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {isLoading && (
              <tr><td colSpan={5} className="text-center py-8 text-gray-400">Loading…</td></tr>
            )}
            {!isLoading && (periods ?? []).length === 0 && (
              <tr><td colSpan={5} className="text-center py-8 text-gray-400">No periods created yet.</td></tr>
            )}
            {(periods ?? []).map((p) => (
              <tr key={p.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono font-semibold text-gray-800">{p.period_ym}</td>
                <td className="px-4 py-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${STATUS_PILL[p.status]}`}>
                    {p.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-500 text-xs">{p.closed_at ? p.closed_at.slice(0, 16).replace("T", " ") : "—"}</td>
                <td className="px-4 py-3 text-gray-400 text-xs">{p.notes ?? "—"}</td>
                <td className="px-4 py-3 text-right space-x-2">
                  {p.status === "OPEN" && (
                    <button
                      onClick={() => closeMut.mutate(p.id)}
                      disabled={closeMut.isPending}
                      className="text-xs bg-yellow-100 text-yellow-700 px-3 py-1 rounded-full hover:bg-yellow-200 disabled:opacity-50"
                    >
                      Close
                    </button>
                  )}
                  {(p.status === "OPEN" || p.status === "CLOSED") && (
                    <button
                      onClick={() => {
                        if (confirm(`Lock period ${p.period_ym}? This cannot be reversed.`)) {
                          lockMut.mutate(p.id);
                        }
                      }}
                      disabled={lockMut.isPending}
                      className="text-xs bg-red-100 text-red-700 px-3 py-1 rounded-full hover:bg-red-200 disabled:opacity-50"
                    >
                      Lock
                    </button>
                  )}
                  {p.status === "LOCKED" && (
                    <span className="text-xs text-gray-400 italic">Immutable</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-800">
        <strong>Note:</strong> Locked periods cannot receive new journal postings. Close periods at month-end
        after review; lock only after all adjustments are finalized.
      </div>
    </div>
  );
}
