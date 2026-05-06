"use client";

import { useQuery } from "@tanstack/react-query";
import { productionCostApi, fmtKES, WIPRow } from "@/lib/productionCosting";

function fmtDate(s: string | null) {
  if (!s) return "—";
  return new Date(s).toLocaleDateString("en-KE", { day: "2-digit", month: "short", year: "numeric" });
}

function pct(actual: number, planned: number) {
  if (!planned) return null;
  return Math.round(actual / planned * 100);
}

export default function WIPPage() {
  const { data: rows = [], isLoading } = useQuery({
    queryKey: ["production-wip"],
    queryFn: () => productionCostApi.wip(),
    refetchInterval: 60_000,
  });

  const totalWIP = rows.reduce((s, r) => s + r.wip_total, 0);
  const totalMaterial = rows.reduce((s, r) => s + r.wip_material_cost, 0);
  const totalLabor = rows.reduce((s, r) => s + r.wip_labor_cost, 0);
  const totalMachine = rows.reduce((s, r) => s + r.wip_machine_cost, 0);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">WIP Valuation</h1>
        <p className="text-sm text-gray-500 mt-1">Work-in-progress financial value for all active production orders</p>
      </div>

      {/* Summary KPIs */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "Total WIP Value", value: fmtKES(totalWIP), color: "text-indigo-700" },
          { label: "Material Cost", value: fmtKES(totalMaterial), color: "text-blue-700" },
          { label: "Labor Cost", value: fmtKES(totalLabor), color: "text-emerald-700" },
          { label: "Machine Cost", value: fmtKES(totalMachine), color: "text-amber-700" },
        ].map((k) => (
          <div key={k.label} className="bg-white rounded-lg border p-4">
            <p className="text-xs text-gray-500 mb-1">{k.label}</p>
            <p className={`text-xl font-bold ${k.color}`}>{k.value}</p>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-lg border">
        <div className="px-5 py-3 border-b flex items-center justify-between">
          <h2 className="font-semibold text-gray-800">In-Progress Orders — WIP Detail</h2>
          <span className="text-xs text-gray-500">{rows.length} active orders · refreshes every 60s</span>
        </div>

        {isLoading ? (
          <p className="px-5 py-8 text-center text-gray-400">Loading…</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-4 py-2 text-left">Order</th>
                <th className="px-4 py-2 text-left">Product</th>
                <th className="px-4 py-2 text-right">Planned Qty</th>
                <th className="px-4 py-2 text-right">Actual Qty</th>
                <th className="px-4 py-2 text-right">Progress</th>
                <th className="px-4 py-2 text-right">Material</th>
                <th className="px-4 py-2 text-right">Labor</th>
                <th className="px-4 py-2 text-right">Machine</th>
                <th className="px-4 py-2 text-right font-bold">WIP Total</th>
                <th className="px-4 py-2 text-left">Due</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {rows.map((r) => {
                const progress = pct(r.actual_quantity ?? 0, r.planned_quantity);
                return (
                  <tr key={r.order_id} className="hover:bg-gray-50">
                    <td className="px-4 py-2.5 font-mono text-indigo-700 font-semibold">{r.order_no}</td>
                    <td className="px-4 py-2.5 text-gray-700">
                      <span className="font-medium">{r.product_name ?? "—"}</span>
                      {r.product_sku && <span className="text-xs text-gray-400 ml-1">({r.product_sku})</span>}
                    </td>
                    <td className="px-4 py-2.5 text-right text-gray-600">{r.planned_quantity.toLocaleString()} {r.uom}</td>
                    <td className="px-4 py-2.5 text-right text-gray-600">
                      {r.actual_quantity != null ? `${r.actual_quantity.toLocaleString()} ${r.uom}` : "—"}
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      {progress != null ? (
                        <div className="flex items-center gap-2 justify-end">
                          <div className="w-16 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full ${progress >= 100 ? "bg-emerald-500" : progress >= 50 ? "bg-blue-500" : "bg-amber-400"}`}
                              style={{ width: `${Math.min(progress, 100)}%` }}
                            />
                          </div>
                          <span className="text-xs text-gray-500">{progress}%</span>
                        </div>
                      ) : "—"}
                    </td>
                    <td className="px-4 py-2.5 text-right text-gray-600">{fmtKES(r.wip_material_cost)}</td>
                    <td className="px-4 py-2.5 text-right text-gray-600">{fmtKES(r.wip_labor_cost)}</td>
                    <td className="px-4 py-2.5 text-right text-gray-600">{fmtKES(r.wip_machine_cost)}</td>
                    <td className="px-4 py-2.5 text-right font-bold text-indigo-700">{fmtKES(r.wip_total)}</td>
                    <td className="px-4 py-2.5 text-left text-gray-500 text-xs">{fmtDate(r.scheduled_end)}</td>
                  </tr>
                );
              })}
              {rows.length === 0 && (
                <tr><td colSpan={10} className="px-5 py-8 text-center text-gray-400">No in-progress production orders</td></tr>
              )}
            </tbody>
            {rows.length > 0 && (
              <tfoot>
                <tr className="border-t bg-gray-50 font-semibold text-sm">
                  <td colSpan={5} className="px-4 py-2 text-gray-600">Total</td>
                  <td className="px-4 py-2 text-right text-gray-700">{fmtKES(totalMaterial)}</td>
                  <td className="px-4 py-2 text-right text-gray-700">{fmtKES(totalLabor)}</td>
                  <td className="px-4 py-2 text-right text-gray-700">{fmtKES(totalMachine)}</td>
                  <td className="px-4 py-2 text-right text-indigo-700">{fmtKES(totalWIP)}</td>
                  <td />
                </tr>
              </tfoot>
            )}
          </table>
        )}
      </div>
    </div>
  );
}
