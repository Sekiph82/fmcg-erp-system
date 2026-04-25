"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { allergenApi, type ProductNutritionSummary } from "@/lib/allergen";

const KEY_NUTRIENTS = ["energy_kcal", "protein", "total_fat", "carbohydrates", "sugars", "fiber", "sodium"];

export default function ProductNutritionPage() {
  const qc = useQueryClient();
  const [showCalc, setShowCalc] = useState<string | null>(null);
  const [calcForm, setCalcForm] = useState({ bom_id: "", recipe_id: "", serving_size_g: "" });
  const [selected, setSelected] = useState<ProductNutritionSummary | null>(null);

  const { data: summaries } = useQuery({ queryKey: ["nutrition-summaries"], queryFn: allergenApi.listNutritionSummaries });

  const calculate = useMutation({
    mutationFn: (productId: string) => allergenApi.calculateNutritionSummary(productId, {
      bom_id: calcForm.bom_id || undefined,
      recipe_id: calcForm.recipe_id || undefined,
      serving_size_g: calcForm.serving_size_g ? Number(calcForm.serving_size_g) : undefined,
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["nutrition-summaries"] }); setShowCalc(null); alert("Nutrition summary recalculated"); },
  });

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Product Nutrition Summaries</h1>
      </div>

      {/* Calculate Modal */}
      {showCalc && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-4 w-96 space-y-3">
            <h3 className="text-sm font-medium text-gray-900">Recalculate Nutrition Summary</h3>
            <div>
              <label className="text-xs text-gray-500">BOM ID (UUID)</label>
              <input className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm font-mono" value={calcForm.bom_id} onChange={(e) => setCalcForm((p) => ({ ...p, bom_id: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500">Recipe ID (UUID)</label>
              <input className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm font-mono" value={calcForm.recipe_id} onChange={(e) => setCalcForm((p) => ({ ...p, recipe_id: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500">Serving Size (g)</label>
              <input type="number" className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm" value={calcForm.serving_size_g} onChange={(e) => setCalcForm((p) => ({ ...p, serving_size_g: e.target.value }))} />
            </div>
            <div className="flex gap-2">
              <button onClick={() => calculate.mutate(showCalc)} disabled={calculate.isPending} className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded disabled:opacity-50">Calculate</button>
              <button onClick={() => setShowCalc(null)} className="px-3 py-1.5 text-sm border rounded">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Nutrition Panel Modal */}
      {selected && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setSelected(null)}>
          <div className="bg-white rounded-lg p-6 max-w-lg w-full max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-sm font-medium text-gray-900 mb-1">Nutrition Information</h3>
            <p className="text-xs text-gray-500 mb-3">{selected.product_name}</p>
            <div className="border-2 border-gray-900 p-3 rounded font-mono text-xs space-y-1">
              <p className="text-base font-bold border-b-2 border-gray-900 pb-1">Nutrition Facts</p>
              {selected.serving_size_value && <p>Serving Size: {selected.serving_size_value}{selected.serving_size_uom}</p>}
              {selected.nutrition_per_100g && Object.entries(selected.nutrition_per_100g).map(([code, data]) => (
                <div key={code} className="flex justify-between border-b border-gray-200 py-0.5">
                  <span>{(data as Record<string, string>).name}</span>
                  <span>{(data as Record<string, number | string>).value} {(data as Record<string, string>).unit}</span>
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-400 mt-2">Values per 100g · {selected.bom_version ? `BOM v${selected.bom_version}` : "Recipe"}</p>
            <button onClick={() => setSelected(null)} className="mt-3 px-3 py-1.5 text-sm border rounded">Close</button>
          </div>
        </div>
      )}

      <div className="bg-white border rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                <th className="px-3 py-2 text-left">Product</th>
                {KEY_NUTRIENTS.map((k) => <th key={k} className="px-2 py-2 text-right whitespace-nowrap">{k.replace(/_/g, " ")}</th>)}
                <th className="px-3 py-2 text-left">Serving</th>
                <th className="px-3 py-2 text-left">Stale</th>
                <th className="px-3 py-2 text-left">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {!summaries?.length && <tr><td colSpan={KEY_NUTRIENTS.length + 4} className="px-4 py-6 text-center text-gray-400">No nutrition summaries. Calculate from BOM/Recipe per product.</td></tr>}
              {summaries?.map((s) => {
                const per100 = s.nutrition_per_100g || {};
                return (
                  <tr key={s.id} className={`hover:bg-gray-50 ${s.is_stale ? "bg-yellow-50/30" : ""}`}>
                    <td className="px-3 py-2 font-medium">{s.product_name || s.product_id.slice(0, 8)}</td>
                    {KEY_NUTRIENTS.map((k) => {
                      const val = per100[k];
                      return (
                        <td key={k} className="px-2 py-2 text-right font-mono text-xs">
                          {val ? `${(val as Record<string, number>).value?.toFixed(1)} ${(val as Record<string, string>).unit}` : "—"}
                        </td>
                      );
                    })}
                    <td className="px-3 py-2 text-xs text-gray-500">{s.serving_size_value ? `${s.serving_size_value}${s.serving_size_uom}` : "—"}</td>
                    <td className="px-3 py-2">{s.is_stale ? <span className="text-orange-600 text-xs">⚠ Stale</span> : <span className="text-green-600 text-xs">✓</span>}</td>
                    <td className="px-3 py-2">
                      <div className="flex gap-1">
                        <button onClick={() => setSelected(s)} className="text-xs bg-gray-50 border rounded px-2 py-0.5 hover:bg-gray-100">Panel</button>
                        <button onClick={() => { setShowCalc(s.product_id); setCalcForm({ bom_id: s.bom_id || "", recipe_id: "", serving_size_g: s.serving_size_value || "" }); }} className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded hover:bg-blue-100">Recalc</button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
