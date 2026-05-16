"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { bomApi, CostingResult, fmtKES } from "@/lib/bom";
import { RequirePermission } from "@/components/PermissionGuard";

function CostBar({ label, value, total, color }: { label: string; value: number; total: number; color: string }) {
  const pct = total > 0 ? (value / total) * 100 : 0;
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-gray-600">{label}</span>
        <span className="font-medium">{fmtKES(value)} <span className="text-gray-400 text-xs">({pct.toFixed(1)}%)</span></span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function CostingPage() {
  const { id } = useParams<{ id: string }>();

  const { data, isLoading } = useQuery<CostingResult>({
    queryKey: ["bom-costing", id],
    queryFn: () => bomApi.costing(id),
  });

  if (isLoading) return <div className="p-8 text-center text-gray-400">Calculating costs…</div>;
  if (!data) return null;

  const gross = data.raw_material_cost + data.intermediate_cost + data.packaging_cost + data.utility_cost;

  return (
    <RequirePermission permission="bom.cost">
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <a href={`/dashboard/bom/${id}`} className="text-sm text-gray-400 hover:text-gray-600">← BOM Detail</a>
        <h1 className="text-xl font-bold text-gray-900">Cost Roll-Up</h1>
      </div>

      {/* Summary KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Total Batch Cost", value: fmtKES(data.total_batch_cost), color: "text-gray-900" },
          { label: "Cost per UOM", value: fmtKES(data.cost_per_uom), color: "text-indigo-700" },
          { label: "By-Product Credit", value: fmtKES(data.by_product_credit), color: "text-green-700" },
          { label: "Batch Size", value: `${data.base_qty.toLocaleString()} ${data.base_uom}`, color: "text-gray-600" },
        ].map((k) => (
          <div key={k.label} className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
            <p className="text-xs text-gray-400">{k.label}</p>
            <p className={`text-xl font-bold mt-1 ${k.color}`}>{k.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Cost Breakdown */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 space-y-4">
          <h3 className="font-semibold text-gray-800">Cost Breakdown</h3>
          <CostBar label="Raw Materials" value={data.raw_material_cost} total={gross} color="bg-blue-500" />
          <CostBar label="Intermediates" value={data.intermediate_cost} total={gross} color="bg-purple-500" />
          <CostBar label="Packaging" value={data.packaging_cost} total={gross} color="bg-teal-500" />
          <CostBar label="Utilities" value={data.utility_cost} total={gross} color="bg-orange-500" />
          {data.by_product_credit > 0 && (
            <div className="pt-2 border-t border-gray-100">
              <div className="flex justify-between text-sm">
                <span className="text-green-700">By-Product Credits</span>
                <span className="font-medium text-green-700">- {fmtKES(data.by_product_credit)}</span>
              </div>
            </div>
          )}
          <div className="pt-2 border-t border-gray-200 flex justify-between text-sm font-semibold">
            <span>Net Batch Cost</span>
            <span>{fmtKES(data.total_batch_cost)}</span>
          </div>
        </div>

        {/* Line Details */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
          <h3 className="font-semibold text-gray-800 mb-3">Line-Level Cost</h3>
          <div className="overflow-y-auto max-h-72">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-white">
                <tr className="text-gray-400">
                  {["#", "Item", "Type", "Qty", "Unit Cost", "Extended"].map((h) => (
                    <th key={h} className="text-left pb-2 pr-3">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {data.lines.map((line) => (
                  <tr key={line.line_no} className={line.is_by_product_credit ? "text-green-700" : ""}>
                    <td className="py-1 pr-3 text-gray-400">{line.line_no}</td>
                    <td className="py-1 pr-3 font-medium">{line.item_name || "—"}</td>
                    <td className="py-1 pr-3 text-gray-400">{line.component_type}</td>
                    <td className="py-1 pr-3 text-right font-mono">{line.qty.toFixed(3)} {line.uom}</td>
                    <td className="py-1 pr-3 text-right">{line.unit_cost ? fmtKES(line.unit_cost) : "—"}</td>
                    <td className="py-1 text-right font-semibold">
                      {line.is_by_product_credit ? "- " : ""}{fmtKES(line.extended_cost)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
    </RequirePermission>
  );
}
