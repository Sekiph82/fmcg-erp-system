"use client";
import { useState } from "react";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  tpmApi, fmtCurrency,
  PROMOTION_TYPE_LABEL, OBJECTIVE_TYPE_LABEL, PROMOTION_STATUS_BADGE, CLAIM_STATUS_BADGE,
} from "@/lib/tpm";
import Link from "next/link";

export default function TPMPromotionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState<"overview" | "budget" | "performance" | "claims">("overview");

  const { data: promo, isLoading } = useQuery({
    queryKey: ["tpm-promotion", id],
    queryFn: () => tpmApi.getPromotion(id),
  });

  const approve = useMutation({
    mutationFn: () => tpmApi.approvePromotion(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tpm-promotion", id] }),
  });

  const updateStatus = useMutation({
    mutationFn: (status: any) => tpmApi.updatePromotionStatus(id, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tpm-promotion", id] }),
  });

  if (isLoading) return <div className="p-6 text-gray-400">Loading…</div>;
  if (!promo) return <div className="p-6 text-red-400">Promotion not found.</div>;

  const totalPlanned = promo.budget_lines.reduce((s, b) => s + b.planned_spend_amount, 0);
  const totalActual  = promo.budget_lines.reduce((s, b) => s + b.actual_spend_amount, 0);
  const exp = promo.expected_perf;
  const act = promo.actual_perf;

  return (
    <div className="p-6 space-y-5 max-w-4xl">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <Link href="/dashboard/tpm/promotions" className="text-xs text-gray-500 hover:text-indigo-400">← Back to Promotions</Link>
          <h1 className="text-2xl font-bold text-gray-900 mt-1">{promo.promotion_name}</h1>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <span className="font-mono text-xs text-indigo-300">{promo.promotion_code}</span>
            <span className="text-xs text-gray-400">{PROMOTION_TYPE_LABEL[promo.promotion_type]}</span>
            <span className="text-xs text-gray-400">·</span>
            <span className="text-xs text-gray-400">{OBJECTIVE_TYPE_LABEL[promo.objective_type]}</span>
            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${PROMOTION_STATUS_BADGE[promo.status]}`}>{promo.status}</span>
          </div>
        </div>
        <div className="flex gap-2 flex-shrink-0">
          {promo.status === "DRAFT" && (
            <button onClick={() => updateStatus.mutate("PROPOSED")} className="glow-button-secondary text-sm">Propose</button>
          )}
          {promo.status === "PROPOSED" && (
            <button onClick={() => approve.mutate()} disabled={approve.isPending} className="glow-button text-sm">
              {approve.isPending ? "Approving…" : "Approve"}
            </button>
          )}
          {promo.status === "APPROVED" && (
            <button onClick={() => updateStatus.mutate("ACTIVE")} className="glow-button text-sm">Activate</button>
          )}
          {promo.status === "ACTIVE" && (
            <button onClick={() => updateStatus.mutate("COMPLETED")} className="glow-button-secondary text-sm">Mark Complete</button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-blue-900/30">
        {(["overview","budget","performance","claims"] as const).map((tab) => (
          <button key={tab} onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm capitalize transition-colors ${activeTab === tab ? "text-indigo-400 border-b-2 border-indigo-400" : "text-gray-500 hover:text-gray-300"}`}>
            {tab}
          </button>
        ))}
      </div>

      {activeTab === "overview" && (
        <div className="space-y-4">
          <div className="liquid-glass p-5 grid grid-cols-2 md:grid-cols-4 gap-4">
            <div><p className="text-xs text-gray-500">Valid From</p><p className="text-sm text-gray-200">{promo.valid_from}</p></div>
            <div><p className="text-xs text-gray-500">Valid To</p><p className="text-sm text-gray-200">{promo.valid_to}</p></div>
            <div><p className="text-xs text-gray-500">Brand</p><p className="text-sm text-gray-200">{promo.brand_id || "—"}</p></div>
            <div><p className="text-xs text-gray-500">Category</p><p className="text-sm text-gray-200">{promo.category_id || "—"}</p></div>
            <div><p className="text-xs text-gray-500">Channel</p><p className="text-sm text-gray-200">{promo.channel_id || "—"}</p></div>
            <div><p className="text-xs text-gray-500">Region</p><p className="text-sm text-gray-200">{promo.region_id || "—"}</p></div>
            <div><p className="text-xs text-gray-500">Distributor Group</p><p className="text-sm text-gray-200">{promo.distributor_group_id || "—"}</p></div>
            <div><p className="text-xs text-gray-500">Linked Scheme</p>
              {promo.linked_scheme_id
                ? <Link href={`/dashboard/promotions/schemes/${promo.linked_scheme_id}`} className="text-sm text-indigo-400 hover:text-indigo-300">View Scheme →</Link>
                : <p className="text-sm text-gray-500">Not linked</p>}
            </div>
          </div>
          {promo.notes && (
            <div className="liquid-glass p-4">
              <p className="text-xs text-gray-500 mb-1">Notes</p>
              <p className="text-sm text-gray-300">{promo.notes}</p>
            </div>
          )}
        </div>
      )}

      {activeTab === "budget" && (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div className="glow-card p-4 text-center">
              <p className="text-xs text-gray-500">Total Planned</p>
              <p className="text-lg font-bold text-indigo-400">{fmtCurrency(totalPlanned)}</p>
            </div>
            <div className="glow-card p-4 text-center">
              <p className="text-xs text-gray-500">Total Actual</p>
              <p className="text-lg font-bold text-orange-400">{fmtCurrency(totalActual)}</p>
            </div>
            <div className="glow-card p-4 text-center">
              <p className="text-xs text-gray-500">Remaining</p>
              <p className={`text-lg font-bold ${totalPlanned - totalActual < 0 ? "text-red-400" : "text-green-400"}`}>
                {fmtCurrency(totalPlanned - totalActual)}
              </p>
            </div>
          </div>
          {promo.budget_lines.length === 0 ? (
            <div className="liquid-glass p-8 text-center text-gray-400 text-sm">No budget lines configured.</div>
          ) : (
            <div className="glass-table overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-blue-900/30">
                    <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Type</th>
                    <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Planned</th>
                    <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Approved</th>
                    <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Actual</th>
                    <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Accrued</th>
                    <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Remaining</th>
                  </tr>
                </thead>
                <tbody>
                  {promo.budget_lines.map((bl) => (
                    <tr key={bl.id} className="border-b border-blue-900/20">
                      <td className="px-4 py-3 text-xs text-gray-400">{bl.budget_type.replace(/_/g, " ")}</td>
                      <td className="px-4 py-3 text-right text-gray-300">{fmtCurrency(bl.planned_spend_amount)}</td>
                      <td className="px-4 py-3 text-right text-blue-300">{fmtCurrency(bl.approved_spend_amount)}</td>
                      <td className="px-4 py-3 text-right text-orange-400">{fmtCurrency(bl.actual_spend_amount)}</td>
                      <td className="px-4 py-3 text-right text-yellow-400">{fmtCurrency(bl.accrued_spend_amount)}</td>
                      <td className={`px-4 py-3 text-right font-medium ${bl.remaining_budget_amount < 0 ? "text-red-400" : "text-green-400"}`}>
                        {fmtCurrency(bl.remaining_budget_amount)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === "performance" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div className="liquid-glass p-5 space-y-3">
            <h2 className="text-sm font-semibold text-gray-700">Expected Performance</h2>
            {!exp ? (
              <p className="text-sm text-gray-400">No expected performance set.</p>
            ) : (
              <div className="space-y-2 text-sm">
                {[
                  ["Baseline Volume",    exp.baseline_volume],
                  ["Target Volume",      exp.target_volume],
                  ["Uplift Qty",         exp.expected_uplift_qty],
                  ["Uplift %",           `${exp.expected_uplift_pct}%`],
                  ["Expected Revenue",   fmtCurrency(exp.expected_revenue)],
                  ["Margin Impact",      fmtCurrency(exp.expected_margin_impact)],
                  ["Expected ROI %",     `${exp.expected_roi_pct}%`],
                  ["Baseline Method",    exp.baseline_method],
                ].map(([label, value]) => (
                  <div key={String(label)} className="flex justify-between">
                    <span className="text-gray-500">{label}</span>
                    <span className="text-gray-200 font-medium">{String(value)}</span>
                  </div>
                ))}
                {exp.assumptions && <p className="text-xs text-gray-500 pt-2 border-t border-blue-900/20">{exp.assumptions}</p>}
              </div>
            )}
          </div>
          <div className="liquid-glass p-5 space-y-3">
            <h2 className="text-sm font-semibold text-gray-700">Actual Performance</h2>
            {!act ? (
              <p className="text-sm text-gray-400">No actuals recorded yet.</p>
            ) : (
              <div className="space-y-2 text-sm">
                {[
                  ["Actual Volume",   act.actual_volume],
                  ["Uplift Qty",      act.actual_uplift_qty],
                  ["Uplift %",        `${Number(act.actual_uplift_pct).toFixed(1)}%`],
                  ["Revenue",         fmtCurrency(act.actual_revenue)],
                  ["Margin Impact",   fmtCurrency(act.actual_margin_impact)],
                  ["Actual Spend",    fmtCurrency(act.actual_spend)],
                  ["Actual ROI %",    `${Number(act.actual_roi_pct).toFixed(1)}%`],
                ].map(([label, value]) => (
                  <div key={String(label)} className="flex justify-between">
                    <span className="text-gray-500">{label}</span>
                    <span className="text-gray-200 font-medium">{String(value)}</span>
                  </div>
                ))}
                {act.post_event_notes && <p className="text-xs text-gray-500 pt-2 border-t border-blue-900/20">{act.post_event_notes}</p>}
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === "claims" && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-400">{promo.claims?.length ?? 0} claim(s) for this promotion</p>
            <Link href={`/dashboard/tpm/claims?promotion_id=${id}`} className="glow-button-secondary text-xs">View in Claims Queue →</Link>
          </div>
          {(!promo.claims || promo.claims.length === 0) ? (
            <div className="liquid-glass p-8 text-center text-gray-400">No claims submitted.</div>
          ) : promo.claims.map((c: any) => (
            <div key={c.id} className="liquid-glass p-4 flex items-center justify-between gap-3">
              <div>
                <span className="font-mono text-xs text-indigo-300">{c.claim_no}</span>
                <p className="text-sm text-gray-200">{c.claim_type?.replace(/_/g, " ")}</p>
                <p className="text-xs text-gray-500">{c.claim_date}</p>
              </div>
              <div className="text-right">
                <p className="text-sm font-bold text-orange-400">{fmtCurrency(c.claimed_amount)}</p>
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${CLAIM_STATUS_BADGE[c.status as import("@/lib/tpm").TPMClaimStatus] ?? ""}`}>{c.status}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
