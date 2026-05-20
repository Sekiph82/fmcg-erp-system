"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { mpsApi, MPSPlanSummary, MPSCampaign, MPSLine } from "@/lib/mps";

export default function CampaignsPage() {
  const qc = useQueryClient();
  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null);

  const { data: plans = [] } = useQuery<MPSPlanSummary[]>({
    queryKey: ["mps-plans"],
    queryFn: () => mpsApi.listPlans(),
  });

  const { data: campaigns = [], isLoading } = useQuery<MPSCampaign[]>({
    queryKey: ["mps-campaigns", selectedPlanId],
    queryFn: () => mpsApi.getCampaigns(selectedPlanId!),
    enabled: !!selectedPlanId,
  });

  const { data: lines = [] } = useQuery<MPSLine[]>({
    queryKey: ["mps-lines", selectedPlanId],
    queryFn: () => mpsApi.listLines(selectedPlanId!),
    enabled: !!selectedPlanId,
  });

  const runCampaigns = useMutation({
    mutationFn: () => mpsApi.runCampaigns(selectedPlanId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mps-campaigns", selectedPlanId] });
      qc.invalidateQueries({ queryKey: ["mps-lines", selectedPlanId] });
    },
  });

  const campaignLines = Object.fromEntries(
    campaigns.map((c) => [c.id, lines.filter((l) => l.campaign_id === c.id)])
  );
  const uncampaigned = lines.filter((l) => !l.campaign_id);

  const totalProduction = campaigns.reduce((s, c) => s + Number(c.total_production_hrs), 0);
  const totalChangeover = campaigns.reduce((s, c) => s + Number(c.total_changeover_hrs), 0);
  const efficiency = totalProduction + totalChangeover > 0
    ? (totalProduction / (totalProduction + totalChangeover) * 100).toFixed(1)
    : "—";

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Campaign Planning</h1>
        <a href="/dashboard/mps" className="text-xs text-blue-600 hover:underline">← MPS Dashboard</a>
      </div>

      {/* Plan selector + actions */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 flex flex-wrap items-center gap-3">
        <select
          className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm min-w-64"
          value={selectedPlanId || ""}
          onChange={(e) => setSelectedPlanId(e.target.value || null)}
        >
          <option value="">-- select plan --</option>
          {plans.map((p) => (
            <option key={p.id} value={p.id}>{p.plan_no} — {p.plan_name}</option>
          ))}
        </select>
        {selectedPlanId && (
          <button
            onClick={() => runCampaigns.mutate()}
            disabled={runCampaigns.isPending}
            className="px-3 py-1.5 text-xs font-medium bg-purple-100 text-purple-700 hover:bg-purple-200 rounded-lg"
          >
            {runCampaigns.isPending ? "Grouping…" : "Re-run Campaign Grouping"}
          </button>
        )}
      </div>

      {selectedPlanId && campaigns.length > 0 && (
        <>
          {/* Summary */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: "Campaigns", value: campaigns.length },
              { label: "Total SKUs", value: campaigns.reduce((s, c) => s + c.sku_count, 0) },
              { label: "Production Hours", value: `${totalProduction.toFixed(1)}h` },
              { label: "Campaign Efficiency", value: `${efficiency}%`, color: "text-green-600" },
            ].map((kpi) => (
              <div key={kpi.label} className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
                <p className="text-xs text-gray-400 font-medium">{kpi.label}</p>
                <p className={`text-2xl font-bold mt-1 ${kpi.color || "text-gray-900"}`}>{kpi.value}</p>
              </div>
            ))}
          </div>

          {/* Campaigns List */}
          <div className="space-y-4">
            {campaigns.map((camp) => {
              const cLines = campaignLines[camp.id] || [];
              const efficiency_pct = Number(camp.total_production_hrs) + Number(camp.total_changeover_hrs) > 0
                ? (Number(camp.total_production_hrs) / (Number(camp.total_production_hrs) + Number(camp.total_changeover_hrs)) * 100).toFixed(1)
                : "—";

              return (
                <div key={camp.id} className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
                  <div className="px-5 py-3 bg-gradient-to-r from-purple-50 to-indigo-50 border-b border-gray-100 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-xs font-bold text-purple-700 bg-purple-100 px-2 py-0.5 rounded">
                        #{camp.sequence_order}
                      </span>
                      <div>
                        <p className="text-sm font-semibold text-gray-800">{camp.campaign_name}</p>
                        <p className="text-xs text-gray-400">{camp.campaign_code}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-6 text-xs text-gray-500">
                      <span>{camp.sku_count} SKU{camp.sku_count !== 1 ? "s" : ""}</span>
                      <span>{Number(camp.total_production_hrs).toFixed(1)}h production</span>
                      <span className="text-orange-500">{Number(camp.total_changeover_hrs).toFixed(1)}h changeover</span>
                      <span className="text-green-600 font-medium">{efficiency_pct}% efficient</span>
                      {camp.campaign_start && (
                        <span>{camp.campaign_start} → {camp.campaign_end}</span>
                      )}
                    </div>
                  </div>

                  {cLines.length > 0 ? (
                    <table className="w-full text-xs">
                      <thead className="bg-gray-50">
                        <tr>
                          {["Seq", "Product", "Period", "Planned Qty", "Req Hrs", "Priority", "Status"].map((h) => (
                            <th key={h} className="px-3 py-2 text-left font-medium text-gray-400">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-50">
                        {cLines.map((l, i) => (
                          <tr key={l.id} className="hover:bg-gray-50">
                            <td className="px-3 py-2 text-gray-400">{i + 1}</td>
                            <td className="px-3 py-2">
                              <p className="font-medium text-gray-700">{l.product_name || l.product_id.slice(0, 8)}</p>
                              {l.product_code && <p className="text-gray-400">{l.product_code}</p>}
                            </td>
                            <td className="px-3 py-2 text-gray-500">{l.period_label || l.period_start}</td>
                            <td className="px-3 py-2 font-medium text-right">{Number(l.planned_production_qty).toLocaleString()}</td>
                            <td className="px-3 py-2 text-right">{l.required_hours ? `${Number(l.required_hours).toFixed(1)}h` : "—"}</td>
                            <td className="px-3 py-2 text-center">{Number(l.priority_score).toFixed(0)}</td>
                            <td className="px-3 py-2">
                              <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                                l.feasibility_status === "FEASIBLE" ? "bg-green-100 text-green-700" :
                                l.feasibility_status === "OVERLOADED" ? "bg-red-100 text-red-700" :
                                "bg-gray-100 text-gray-600"
                              }`}>
                                {l.feasibility_status}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <p className="px-5 py-3 text-xs text-gray-400">No lines in this campaign</p>
                  )}
                </div>
              );
            })}
          </div>

          {/* Uncampaigned lines */}
          {uncampaigned.length > 0 && (
            <div className="bg-white rounded-xl border border-yellow-200 shadow-sm p-4">
              <h3 className="text-sm font-semibold text-yellow-700 mb-2">
                {uncampaigned.length} lines not grouped into any campaign
              </h3>
              <div className="flex flex-wrap gap-2">
                {uncampaigned.map((l) => (
                  <span key={l.id} className="text-xs bg-yellow-50 border border-yellow-100 rounded px-2 py-1">
                    {l.product_name || l.product_id.slice(0, 8)}
                  </span>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {selectedPlanId && !isLoading && campaigns.length === 0 && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-8 text-center text-sm text-gray-400">
          No campaigns yet. Run campaign grouping to group SKUs automatically.
        </div>
      )}
    </div>
  );
}
