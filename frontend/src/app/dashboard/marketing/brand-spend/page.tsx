"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { marketingApi, BrandSpend, ApprovalStatus, APPROVAL_STATUS_COLORS } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

export default function BrandSpendPage() {
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("");

  const { data: records = [], isLoading } = useQuery({
    queryKey: ["brand-spend", statusFilter],
    queryFn: () =>
      marketingApi.brandSpend
        .list({ limit: 100 })
        .then((r) => r.data),
  });

  const approveMut = useMutation({
    mutationFn: (id: string) => marketingApi.brandSpend.approve(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["brand-spend"] }),
  });

  const filtered = statusFilter ? records.filter((r) => r.approval_status === statusFilter) : records;
  const totalSpend = filtered.reduce((s, b) => s + Number(b.amount), 0);

  return (
    <RequirePermission permission="brand_spend.view">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">Brand Spend</h1>
            <p className="text-slate-400 text-sm mt-1">{filtered.length} records</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 px-4 py-2 text-right">
              <p className="text-xs text-slate-400">Total</p>
              <p className="text-lg font-bold text-emerald-400">KES {totalSpend.toLocaleString()}</p>
            </div>
            <RequirePermission permission="brand_spend.create">
              <Link href="/dashboard/marketing/brand-spend/new"
                className="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-sm font-medium text-white">
                + New
              </Link>
            </RequirePermission>
          </div>
        </div>

        <div className="flex gap-3 mb-6">
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-[#131c2e] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
            <option value="">All statuses</option>
            {(["PENDING", "APPROVED", "REJECTED"] as ApprovalStatus[]).map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>

        {isLoading ? (
          <p className="text-slate-400">Loading...</p>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-700/50">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700/50 bg-[#131c2e]">
                  {["Category", "Amount", "Currency", "Vendor", "Date", "Status", "Notes", "Actions"].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((b: BrandSpend) => (
                  <tr key={b.id} className="border-b border-slate-800 hover:bg-slate-800/30">
                    <td className="px-4 py-3 text-slate-300">{b.spend_category.replace(/_/g, " ")}</td>
                    <td className="px-4 py-3 font-medium">{Number(b.amount).toLocaleString()}</td>
                    <td className="px-4 py-3 text-slate-400">{b.currency}</td>
                    <td className="px-4 py-3 text-slate-300">{b.vendor ?? "—"}</td>
                    <td className="px-4 py-3 text-slate-400">{b.spend_date}</td>
                    <td className="px-4 py-3">
                      <span className={`font-medium ${APPROVAL_STATUS_COLORS[b.approval_status as ApprovalStatus]}`}>
                        {b.approval_status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-400 max-w-xs truncate">{b.notes ?? "—"}</td>
                    <td className="px-4 py-3 flex items-center gap-2">
                      <Link href={`/dashboard/marketing/brand-spend/${b.id}`}
                        className="px-2 py-1 rounded bg-slate-700/50 hover:bg-slate-700 text-slate-300 text-xs">
                        View
                      </Link>
                      {b.approval_status === "PENDING" && (
                        <button onClick={() => approveMut.mutate(b.id)}
                          className="px-2 py-1 rounded bg-emerald-600/20 text-emerald-400 hover:bg-emerald-600/40 text-xs">
                          Approve
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </RequirePermission>
  );
}
