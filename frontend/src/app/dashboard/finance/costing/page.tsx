"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { financeApi, ProductCost, CostType } from "@/lib/finance";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

const costTypeColors: Record<CostType, string> = {
  RAW_MATERIAL: "text-blue-700",
  PACKAGING: "text-purple-700",
  LABOR: "text-orange-600",
  UTILITY: "text-yellow-600",
  OVERHEAD: "text-gray-600",
};

export default function CostingPage() {
  const qc = useQueryClient();
  const [period, setPeriod] = useState(new Date().toISOString().slice(0, 7).replace("-", ""));
  const [showRollup, setShowRollup] = useState(false);

  const { data: productCosts = [], isLoading } = useQuery({
    queryKey: ["finance-product-costs", period],
    queryFn: () => financeApi.listProductCosts({ period_ym: period }),
  });

  const rollupProduct = useMutation({
    mutationFn: ({ productId, periodYm }: { productId: string; periodYm: string }) =>
      financeApi.rollupProductCost(productId, periodYm),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["finance-product-costs"] });
      setShowRollup(false);
    },
  });

  const totalCost = productCosts.reduce((s, r) => {
    const total = (r.raw_material_cost + r.packaging_cost + r.labor_cost + r.utility_cost + r.overhead_cost);
    return s + total;
  }, 0);

  // Format period for display e.g. "202504" → "Apr 2025"
  const displayPeriod = (ym: string) => {
    const y = ym.slice(0, 4);
    const m = parseInt(ym.slice(4, 6), 10);
    return `${["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][m-1]} ${y}`;
  };

  const parsedPeriod = period.length === 6 ? `${period.slice(0, 4)}-${period.slice(4, 6)}` : "";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Product Costing</h1>
          <p className="text-sm text-gray-500 mt-1">Production cost rollup and unit cost analysis</p>
        </div>
        <Button onClick={() => setShowRollup(true)}>Rollup Product Cost</Button>
      </div>

      {/* Period selector */}
      <div className="flex items-center gap-3">
        <label className="text-sm font-medium text-gray-600">Period (YYYYMM):</label>
        <input
          className="border rounded px-3 py-1.5 text-sm w-32"
          value={period}
          onChange={(e) => setPeriod(e.target.value)}
          placeholder="202504"
          maxLength={6}
        />
        {parsedPeriod && <span className="text-sm text-gray-500">{displayPeriod(period)}</span>}
        <span className="ml-4 text-sm text-gray-500">Total production cost: <span className="font-semibold text-gray-800">KES {totalCost.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span></span>
      </div>

      {/* Product costs table */}
      <div className="bg-white rounded-lg border overflow-x-auto">
        {isLoading ? (
          <p className="px-5 py-8 text-center text-gray-400">Loading…</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-5 py-2 text-left">Product</th>
                <th className="px-5 py-2 text-left">SKU</th>
                <th className="px-5 py-2 text-right">Raw Material</th>
                <th className="px-5 py-2 text-right">Packaging</th>
                <th className="px-5 py-2 text-right">Labor</th>
                <th className="px-5 py-2 text-right">Utility</th>
                <th className="px-5 py-2 text-right">Overhead</th>
                <th className="px-5 py-2 text-right">Units</th>
                <th className="px-5 py-2 text-right">Std Cost/Unit</th>
                <th className="px-5 py-2 text-right">Actual/Unit</th>
                <th className="px-5 py-2 text-right">Variance</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {productCosts.map((pc) => {
                const variance = pc.variance_amount ?? 0;
                const variancePct = pc.variance_pct ?? 0;
                return (
                  <tr key={pc.id} className="hover:bg-gray-50">
                    <td className="px-5 py-3 font-medium text-gray-900">{pc.product_name || "—"}</td>
                    <td className="px-5 py-3 font-mono text-xs text-gray-500">{pc.product_sku || "—"}</td>
                    <td className={`px-5 py-3 text-right ${costTypeColors.RAW_MATERIAL}`}>{Number(pc.raw_material_cost).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                    <td className={`px-5 py-3 text-right ${costTypeColors.PACKAGING}`}>{Number(pc.packaging_cost).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                    <td className={`px-5 py-3 text-right ${costTypeColors.LABOR}`}>{Number(pc.labor_cost).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                    <td className={`px-5 py-3 text-right ${costTypeColors.UTILITY}`}>{Number(pc.utility_cost).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                    <td className={`px-5 py-3 text-right ${costTypeColors.OVERHEAD}`}>{Number(pc.overhead_cost).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                    <td className="px-5 py-3 text-right">{pc.total_units_produced.toLocaleString()}</td>
                    <td className="px-5 py-3 text-right">{pc.standard_cost_per_unit != null ? Number(pc.standard_cost_per_unit).toLocaleString(undefined, { minimumFractionDigits: 4 }) : "—"}</td>
                    <td className="px-5 py-3 text-right font-semibold">{pc.actual_cost_per_unit != null ? Number(pc.actual_cost_per_unit).toLocaleString(undefined, { minimumFractionDigits: 4 }) : "—"}</td>
                    <td className={`px-5 py-3 text-right text-xs font-medium ${variance > 0 ? "text-red-600" : variance < 0 ? "text-green-600" : "text-gray-400"}`}>
                      {variance !== 0 ? `${variance > 0 ? "+" : ""}${Number(variance).toLocaleString(undefined, { minimumFractionDigits: 2 })} (${variancePct > 0 ? "+" : ""}${Number(variancePct).toFixed(1)}%)` : "—"}
                    </td>
                  </tr>
                );
              })}
              {productCosts.length === 0 && (
                <tr><td colSpan={11} className="px-5 py-8 text-center text-gray-400">No cost data for this period</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      {/* Legend */}
      <div className="flex gap-4 text-xs text-gray-500">
        {(Object.entries(costTypeColors) as [CostType, string][]).map(([k, c]) => (
          <span key={k} className={`font-medium ${c}`}>{k.replace("_", " ")}</span>
        ))}
        <span className="ml-2">· Variance = Actual − Standard (positive = over budget)</span>
      </div>

      {/* Rollup modal */}
      {showRollup && (
        <RollupModal
          defaultPeriod={period}
          onClose={() => setShowRollup(false)}
          onSubmit={({ productId, periodYm }) => rollupProduct.mutate({ productId, periodYm })}
          loading={rollupProduct.isPending}
        />
      )}
    </div>
  );
}

function RollupModal({ defaultPeriod, onClose, onSubmit, loading }: { defaultPeriod: string; onClose: () => void; onSubmit: (d: { productId: string; periodYm: string }) => void; loading: boolean }) {
  const [productId, setProductId] = useState("");
  const [periodYm, setPeriodYm] = useState(defaultPeriod);

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6 space-y-4">
        <div>
          <h2 className="font-semibold text-lg">Rollup Product Cost</h2>
          <p className="text-xs text-gray-500 mt-1">Aggregates all production cost entries for the product in the selected period.</p>
        </div>
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Product ID (UUID)</label>
            <input className="w-full border rounded px-3 py-2 text-sm font-mono" value={productId} onChange={(e) => setProductId(e.target.value)} placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Period (YYYYMM)</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={periodYm} onChange={(e) => setPeriodYm(e.target.value)} maxLength={6} />
          </div>
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button loading={loading} onClick={() => onSubmit({ productId, periodYm })}>Run Rollup</Button>
        </div>
      </div>
    </div>
  );
}
