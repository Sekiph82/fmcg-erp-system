"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { bomApi, BOMSummary, fmtKES } from "@/lib/bom";
import { RequirePermission } from "@/components/PermissionGuard";

export default function BOMComparePage() {
  const [bomA, setBomA] = useState("");
  const [bomB, setBomB] = useState("");
  const [compareResult, setCompareResult] = useState<any>(null);
  const [comparing, setComparing] = useState(false);

  const { data: boms = [] } = useQuery<BOMSummary[]>({
    queryKey: ["boms-all"],
    queryFn: () => bomApi.list(),
  });

  const doCompare = async () => {
    if (!bomA || !bomB) return;
    setComparing(true);
    try {
      const res = await bomApi.compare(bomA, bomB);
      setCompareResult(res);
    } finally {
      setComparing(false);
    }
  };

  const bomADetail = boms.find((b) => b.id === bomA);
  const bomBDetail = boms.find((b) => b.id === bomB);

  return (
    <RequirePermission permission="bom.view">
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <a href="/dashboard/bom" className="text-sm text-gray-400 hover:text-gray-600">← BOMs</a>
        <h1 className="text-xl font-bold text-gray-900">BOM Version Comparison</h1>
      </div>

      {/* BOM Selector */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="text-sm font-medium text-gray-700 mb-2 block">BOM A (Base)</label>
            <select className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={bomA} onChange={(e) => setBomA(e.target.value)}>
              <option value="">Select BOM…</option>
              {boms.map((b) => <option key={b.id} value={b.id}>{b.bom_code} — {b.bom_name} (v{b.version_no})</option>)}
            </select>
            {bomADetail && (
              <div className="mt-2 text-xs text-gray-500 space-y-0.5">
                <p>Type: {bomADetail.bom_type} · Status: {bomADetail.lifecycle}</p>
                {bomADetail.standard_batch_cost && <p>Std cost: {fmtKES(Number(bomADetail.standard_batch_cost))}</p>}
              </div>
            )}
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700 mb-2 block">BOM B (Comparison)</label>
            <select className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={bomB} onChange={(e) => setBomB(e.target.value)}>
              <option value="">Select BOM…</option>
              {boms.filter((b) => b.id !== bomA).map((b) => <option key={b.id} value={b.id}>{b.bom_code} — {b.bom_name} (v{b.version_no})</option>)}
            </select>
            {bomBDetail && (
              <div className="mt-2 text-xs text-gray-500 space-y-0.5">
                <p>Type: {bomBDetail.bom_type} · Status: {bomBDetail.lifecycle}</p>
                {bomBDetail.standard_batch_cost && <p>Std cost: {fmtKES(Number(bomBDetail.standard_batch_cost))}</p>}
              </div>
            )}
          </div>
        </div>
        <button
          onClick={doCompare}
          disabled={!bomA || !bomB || comparing}
          className="mt-4 px-6 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-40"
        >
          {comparing ? "Comparing…" : "Compare BOMs"}
        </button>
      </div>

      {/* Results */}
      {compareResult && (
        <div className="space-y-4">
          {/* Cost Delta */}
          {compareResult.cost_delta !== undefined && (
            <div className={`rounded-xl border shadow-sm p-4 ${compareResult.cost_delta > 0 ? "bg-red-50 border-red-200" : compareResult.cost_delta < 0 ? "bg-green-50 border-green-200" : "bg-gray-50 border-gray-200"}`}>
              <p className="text-sm font-medium text-gray-700">Cost Delta (B vs A)</p>
              <p className={`text-2xl font-bold mt-1 ${compareResult.cost_delta > 0 ? "text-red-700" : compareResult.cost_delta < 0 ? "text-green-700" : "text-gray-600"}`}>
                {compareResult.cost_delta > 0 ? "+" : ""}{fmtKES(compareResult.cost_delta)}
              </p>
            </div>
          )}

          {/* Allergen Changes */}
          {compareResult.allergen_changes && Object.keys(compareResult.allergen_changes).length > 0 && (
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
              <h3 className="font-semibold text-gray-800 mb-3">Allergen Changes</h3>
              <div className="flex flex-wrap gap-2">
                {Object.entries(compareResult.allergen_changes).map(([allergen, change]: [string, any]) => (
                  <span key={allergen} className={`text-xs px-2 py-1 rounded-full font-medium ${
                    change === "added" ? "bg-red-100 text-red-700" :
                    change === "removed" ? "bg-green-100 text-green-700" :
                    "bg-yellow-100 text-yellow-700"
                  }`}>
                    {change === "added" ? "+" : change === "removed" ? "-" : "~"} {allergen}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Added Lines */}
          {compareResult.added && compareResult.added.length > 0 && (
            <div className="bg-white rounded-xl border border-green-200 shadow-sm p-4">
              <h3 className="font-semibold text-green-700 mb-3">Added in B ({compareResult.added.length})</h3>
              <div className="space-y-1">
                {compareResult.added.map((line: any, i: number) => (
                  <div key={i} className="text-sm text-green-800 bg-green-50 rounded px-3 py-1.5 flex items-center gap-3">
                    <span className="font-medium">+ {line.item_name || line.item_code || "—"}</span>
                    <span className="text-green-600">{line.required_qty} {line.required_uom}</span>
                    <span className="text-xs text-green-500">{line.component_type}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Removed Lines */}
          {compareResult.removed && compareResult.removed.length > 0 && (
            <div className="bg-white rounded-xl border border-red-200 shadow-sm p-4">
              <h3 className="font-semibold text-red-700 mb-3">Removed from A ({compareResult.removed.length})</h3>
              <div className="space-y-1">
                {compareResult.removed.map((line: any, i: number) => (
                  <div key={i} className="text-sm text-red-800 bg-red-50 rounded px-3 py-1.5 flex items-center gap-3">
                    <span className="font-medium">- {line.item_name || line.item_code || "—"}</span>
                    <span className="text-red-600">{line.required_qty} {line.required_uom}</span>
                    <span className="text-xs text-red-500">{line.component_type}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Changed Lines */}
          {compareResult.changed && compareResult.changed.length > 0 && (
            <div className="bg-white rounded-xl border border-yellow-200 shadow-sm p-4">
              <h3 className="font-semibold text-yellow-700 mb-3">Changed ({compareResult.changed.length})</h3>
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-gray-400">
                    {["Item", "Field", "A (Base)", "B (Comparison)"].map((h) => (
                      <th key={h} className="text-left pb-2 pr-4">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {compareResult.changed.map((ch: any, i: number) => (
                    Object.entries(ch.changes || {}).map(([field, vals]: [string, any]) => (
                      <tr key={`${i}-${field}`}>
                        <td className="py-1 pr-4 font-medium">{ch.item_name}</td>
                        <td className="py-1 pr-4 text-gray-400">{field}</td>
                        <td className="py-1 pr-4 text-red-600">{String(vals.a)}</td>
                        <td className="py-1 text-green-600">{String(vals.b)}</td>
                      </tr>
                    ))
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {(!compareResult.added?.length && !compareResult.removed?.length && !compareResult.changed?.length) && (
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-8 text-center text-sm text-gray-400">
              No differences found between the two BOMs.
            </div>
          )}
        </div>
      )}
    </div>
    </RequirePermission>
  );
}
