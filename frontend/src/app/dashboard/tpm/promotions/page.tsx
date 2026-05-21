"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  tpmApi, TPMPromotion, TPMPromotionStatus,
  PROMOTION_TYPE_LABEL, OBJECTIVE_TYPE_LABEL, PROMOTION_STATUS_BADGE,
} from "@/lib/tpm";
import Link from "next/link";

export default function TPMPromotionsPage() {
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<TPMPromotionStatus | "">("");

  const { data: promotions = [], isLoading } = useQuery({
    queryKey: ["tpm-promotions", statusFilter],
    queryFn: () => tpmApi.getPromotions({ status: statusFilter || undefined }),
  });

  const approve = useMutation({
    mutationFn: (id: string) => tpmApi.approvePromotion(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tpm-promotions"] }),
  });

  const updateStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: TPMPromotionStatus }) =>
      tpmApi.updatePromotionStatus(id, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tpm-promotions"] }),
  });

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Trade Promotions</h1>
          <p className="text-sm text-gray-500">All planned and active trade promotion events.</p>
        </div>
        <div className="flex gap-2 items-center">
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as TPMPromotionStatus | "")}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
            <option value="">All Statuses</option>
            {(["DRAFT","PROPOSED","APPROVED","ACTIVE","COMPLETED","CANCELLED","SETTLED"] as TPMPromotionStatus[]).map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <Link href="/dashboard/tpm/promotions/new" className="glow-button text-sm">+ New Promotion</Link>
        </div>
      </div>

      <div className="glass-table overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-blue-900/30">
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Promotion</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Type</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Objective</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Period</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Scope</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Status</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={7} className="text-center py-10 text-gray-400">Loading…</td></tr>
            ) : promotions.length === 0 ? (
              <tr><td colSpan={7} className="text-center py-10 text-gray-400">No promotions found.</td></tr>
            ) : promotions.map((p: TPMPromotion) => (
              <tr key={p.id} className="border-b border-blue-900/20 hover:bg-blue-950/20 transition-colors">
                <td className="px-4 py-3">
                  <Link href={`/dashboard/tpm/promotions/${p.id}`} className="font-medium text-gray-200 hover:text-indigo-300">
                    {p.promotion_name}
                  </Link>
                  <p className="text-xs text-gray-500 font-mono">{p.promotion_code}</p>
                </td>
                <td className="px-4 py-3 text-xs text-gray-400">{PROMOTION_TYPE_LABEL[p.promotion_type]}</td>
                <td className="px-4 py-3 text-xs text-gray-400">{OBJECTIVE_TYPE_LABEL[p.objective_type]}</td>
                <td className="px-4 py-3 text-xs text-gray-500">
                  <span>{p.valid_from}</span>
                  <br />
                  <span>{p.valid_to}</span>
                </td>
                <td className="px-4 py-3 text-xs text-gray-400">
                  {[p.brand_id, p.channel_id, p.region_id].filter(Boolean).join(" · ") || "—"}
                </td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${PROMOTION_STATUS_BADGE[p.status]}`}>
                    {p.status}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-1 flex-wrap">
                    {p.status === "DRAFT" && (
                      <button onClick={() => updateStatus.mutate({ id: p.id, status: "PROPOSED" })}
                        disabled={updateStatus.isPending} className="glow-button-secondary text-xs !py-1">Propose</button>
                    )}
                    {p.status === "PROPOSED" && (
                      <button onClick={() => approve.mutate(p.id)}
                        disabled={approve.isPending} className="glow-button text-xs !py-1">Approve</button>
                    )}
                    {p.status === "APPROVED" && (
                      <button onClick={() => updateStatus.mutate({ id: p.id, status: "ACTIVE" })}
                        disabled={updateStatus.isPending} className="glow-button text-xs !py-1">Activate</button>
                    )}
                    {p.status === "ACTIVE" && (
                      <button onClick={() => updateStatus.mutate({ id: p.id, status: "COMPLETED" })}
                        disabled={updateStatus.isPending} className="text-xs text-blue-400 border border-blue-300 rounded px-2 py-1">Complete</button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
