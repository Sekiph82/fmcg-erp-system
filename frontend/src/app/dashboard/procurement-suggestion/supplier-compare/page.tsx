"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { psApi, fmt } from "@/lib/procurement_suggestion";

export default function SupplierComparePage() {
  const [materialId, setMaterialId] = useState("");
  const [query, setQuery] = useState("");

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["ps-compare-manual", query],
    queryFn: () => psApi.compareSuppliers(query),
    enabled: false,
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setQuery(materialId.trim());
    setTimeout(() => refetch(), 50);
  };

  const priorityBadge = (p: string) => ({
    PRIMARY:   "bg-blue-100 text-blue-700",
    SECONDARY: "bg-indigo-100 text-indigo-700",
    TERTIARY:  "bg-gray-100 text-gray-600",
    FALLBACK:  "bg-orange-100 text-orange-700",
  }[p] ?? "bg-gray-100 text-gray-600");

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-xl font-semibold text-gray-900">Supplier Comparison</h1>
        <p className="text-sm text-gray-500">Compare all suppliers for a given material</p>
      </div>

      <form onSubmit={handleSearch} className="flex gap-3">
        <input
          type="text"
          value={materialId}
          onChange={(e) => setMaterialId(e.target.value)}
          placeholder="Paste Material UUID…"
          className="flex-1 border rounded px-3 py-2 text-sm font-mono"
        />
        <button type="submit" className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700">
          Compare
        </button>
      </form>

      {isLoading && <div className="text-gray-400">Loading supplier comparison…</div>}
      {isError && <div className="text-red-500">Material not found or no supplier mappings.</div>}

      {data && (
        <div className="space-y-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-800">{data.material_name}</h2>
            <p className="text-sm text-gray-400 font-mono">{data.material_code}</p>
          </div>

          {data.suppliers.length === 0 ? (
            <div className="text-gray-400">No supplier price mappings found for this material.</div>
          ) : (
            <div className="bg-white border border-gray-200 rounded-lg overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                  <tr>
                    <th className="text-left px-4 py-3">Supplier</th>
                    <th className="text-left px-4 py-3">Priority</th>
                    <th className="text-right px-4 py-3">Unit Price</th>
                    <th className="text-right px-4 py-3">MOQ</th>
                    <th className="text-right px-4 py-3">Lead Time</th>
                    <th className="text-right px-4 py-3">Buffer</th>
                    <th className="text-right px-4 py-3">Total Lead</th>
                    <th className="text-right px-4 py-3">Reliability</th>
                    <th className="text-right px-4 py-3">Perf. Score</th>
                    <th className="text-right px-4 py-3">Selection Score</th>
                    <th className="text-left px-4 py-3">Contract</th>
                  </tr>
                </thead>
                <tbody>
                  {data.suppliers.map((s, idx) => (
                    <tr
                      key={s.supplier_id}
                      className={`border-t border-gray-100 ${s.supplier_id === data.recommended_supplier_id ? "bg-green-50" : ""}`}
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          {idx === 0 && (
                            <span className="w-4 h-4 bg-green-500 rounded-full text-white text-xs flex items-center justify-center font-bold">
                              ✓
                            </span>
                          )}
                          <div>
                            <p className="font-medium">{s.supplier_name}</p>
                            <p className="text-xs text-gray-400 font-mono">{s.supplier_code}</p>
                          </div>
                          {s.is_preferred && <span className="text-xs text-yellow-600">⭐ Preferred</span>}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded text-xs ${priorityBadge(s.priority)}`}>{s.priority}</span>
                      </td>
                      <td className="px-4 py-3 text-right font-mono font-medium">{s.currency} {fmt(s.unit_price)}</td>
                      <td className="px-4 py-3 text-right">{fmt(s.moq, 0)}</td>
                      <td className="px-4 py-3 text-right">{s.lead_time_days}d</td>
                      <td className="px-4 py-3 text-right">{s.total_lead_days - s.lead_time_days}d</td>
                      <td className="px-4 py-3 text-right font-semibold">{s.total_lead_days}d</td>
                      <td className="px-4 py-3 text-right">{s.reliability_score != null ? `${s.reliability_score}%` : "—"}</td>
                      <td className="px-4 py-3 text-right">{s.performance_score != null ? `${s.performance_score}%` : "—"}</td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <div className="w-16 bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-blue-500 h-2 rounded-full"
                              style={{ width: `${Math.min(s.score, 100)}%` }}
                            />
                          </div>
                          <span className="font-mono text-xs w-8">{fmt(s.score, 1)}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-500">{s.contract_no ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {data.recommended_supplier_id && data.suppliers[0] && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <p className="text-sm font-semibold text-green-800">
                Recommended Supplier: {data.suppliers[0].supplier_name}
              </p>
              <p className="text-xs text-green-600 mt-1">
                Score: {fmt(data.suppliers[0].score, 1)} / 100 ·
                Price: {data.suppliers[0].currency} {fmt(data.suppliers[0].unit_price)} ·
                Total lead time: {data.suppliers[0].total_lead_days} days
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
