"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { allergenApi, presenceColor, riskColor, type AllergenRollupResult, type NutritionRollupResult } from "@/lib/allergen";

export default function RollupViewerPage() {
  const [sourceType, setSourceType] = useState<"bom" | "recipe">("bom");
  const [sourceId, setSourceId] = useState("");
  const [servingSize, setServingSize] = useState("");
  const [allergenResult, setAllergenResult] = useState<AllergenRollupResult | null>(null);
  const [nutritionResult, setNutritionResult] = useState<NutritionRollupResult | null>(null);

  const runAllergen = useMutation({
    mutationFn: () => sourceType === "bom" ? allergenApi.bomAllergenRollup(sourceId) : allergenApi.recipeAllergenRollup(sourceId),
    onSuccess: (r) => setAllergenResult(r),
  });
  const runNutrition = useMutation({
    mutationFn: () => sourceType === "bom"
      ? allergenApi.bomNutritionRollup(sourceId, servingSize ? Number(servingSize) : undefined)
      : allergenApi.recipeNutritionRollup(sourceId, servingSize ? Number(servingSize) : undefined),
    onSuccess: (r) => setNutritionResult(r),
  });

  const runBoth = () => { runAllergen.mutate(); runNutrition.mutate(); };

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-semibold text-gray-900">Allergen + Nutrition Roll-Up Viewer</h1>

      {/* Source Selector */}
      <div className="bg-white border rounded-lg p-4 space-y-3">
        <div className="flex gap-2">
          {["bom", "recipe"].map((t) => (
            <button key={t} onClick={() => setSourceType(t as "bom" | "recipe")} className={`px-3 py-1 text-sm rounded border ${sourceType === t ? "bg-gray-900 text-white" : "bg-white hover:bg-gray-50"}`}>
              {t === "bom" ? "BOM / Formula" : "Recipe"}
            </button>
          ))}
        </div>
        <div className="flex gap-3">
          <div className="flex-1">
            <label className="text-xs text-gray-500">{sourceType === "bom" ? "BOM" : "Recipe"} ID (UUID)</label>
            <input className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm font-mono" value={sourceId} onChange={(e) => setSourceId(e.target.value)} placeholder="uuid..." />
          </div>
          <div className="w-32">
            <label className="text-xs text-gray-500">Serving Size (g)</label>
            <input type="number" className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm" value={servingSize} onChange={(e) => setServingSize(e.target.value)} placeholder="e.g. 30" />
          </div>
          <div className="flex items-end">
            <button onClick={runBoth} disabled={!sourceId || runAllergen.isPending || runNutrition.isPending} className="px-4 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50">
              {(runAllergen.isPending || runNutrition.isPending) ? "Calculating…" : "Calculate"}
            </button>
          </div>
        </div>
        {(runAllergen.isError || runNutrition.isError) && (
          <p className="text-red-600 text-xs">{((runAllergen.error || runNutrition.error) as Error)?.message}</p>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Allergen Roll-Up Result */}
        <div className="space-y-4">
          <div className="bg-white border rounded-lg overflow-hidden">
            <div className="px-4 py-3 border-b flex items-center justify-between bg-red-50">
              <h2 className="text-sm font-medium text-red-800">Allergen Roll-Up</h2>
              {allergenResult && (
                <span className={`text-xs px-2 py-0.5 rounded font-medium ${riskColor[allergenResult.cross_contact_risk]}`}>
                  {allergenResult.cross_contact_risk} risk
                </span>
              )}
            </div>
            {!allergenResult && <div className="p-8 text-center text-gray-400 text-sm">Run calculation to see allergen roll-up</div>}
            {allergenResult && (
              <div className="p-4 space-y-4">
                {/* Contains */}
                {allergenResult.contains.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-red-700 mb-1.5">CONTAINS ({allergenResult.contains.length})</p>
                    <div className="space-y-1.5">
                      {allergenResult.contains.map((a) => (
                        <div key={a.allergen_code} className="flex items-start justify-between bg-red-50 rounded p-2">
                          <div>
                            <span className="text-sm font-medium text-red-800">{a.allergen_name}</span>
                            {a.critical_flag && <span className="ml-2 text-xs text-red-600 font-medium">CRITICAL</span>}
                            <p className="text-xs text-red-500 mt-0.5">Sources: {a.source_materials.join(", ")}</p>
                          </div>
                          {a.declaration_required && <span className="text-xs bg-red-100 text-red-700 px-1.5 py-0.5 rounded">Declare</span>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* May Contain */}
                {allergenResult.may_contain.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-orange-700 mb-1.5">MAY CONTAIN ({allergenResult.may_contain.length})</p>
                    <div className="space-y-1">
                      {allergenResult.may_contain.map((a) => (
                        <div key={a.allergen_code} className="flex items-center justify-between bg-orange-50 rounded p-2">
                          <span className="text-sm text-orange-800">{a.allergen_name}</span>
                          <span className="text-xs text-orange-600">{a.source_materials.join(", ")}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Label Statement */}
                {allergenResult.label_statement && (
                  <div className="bg-gray-50 rounded p-3">
                    <p className="text-xs text-gray-500 font-medium mb-1">Label Statement</p>
                    <p className="text-sm font-medium text-gray-900">{allergenResult.label_statement}</p>
                    {allergenResult.may_contain_statement && (
                      <p className="text-sm text-orange-700 mt-1">{allergenResult.may_contain_statement}</p>
                    )}
                  </div>
                )}

                {/* Ingredient Map */}
                {Object.keys(allergenResult.ingredient_allergen_map).length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-gray-600 mb-1.5">Ingredient Allergen Map</p>
                    <div className="space-y-1">
                      {Object.entries(allergenResult.ingredient_allergen_map).map(([mat, allergens]) => (
                        <div key={mat} className="flex items-start gap-2 text-xs">
                          <span className="text-gray-700 font-medium w-32 shrink-0 truncate">{mat}</span>
                          <div className="flex flex-wrap gap-1">
                            {allergens.map((a) => <span key={a} className="bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">{a}</span>)}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Nutrition Roll-Up Result */}
        <div className="bg-white border rounded-lg overflow-hidden">
          <div className="px-4 py-3 border-b bg-green-50">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-medium text-green-800">Nutrition Roll-Up (per 100g)</h2>
              {nutritionResult && (
                <span className="text-xs text-green-600">{nutritionResult.completeness_pct}% complete</span>
              )}
            </div>
          </div>
          {!nutritionResult && <div className="p-8 text-center text-gray-400 text-sm">Run calculation to see nutrition panel</div>}
          {nutritionResult && (
            <div className="p-4 space-y-4">
              {nutritionResult.missing_profiles.length > 0 && (
                <div className="bg-yellow-50 border border-yellow-200 rounded p-2 text-xs text-yellow-800">
                  Missing nutrition profiles: {nutritionResult.missing_profiles.join(", ")}
                </div>
              )}

              <table className="w-full text-sm">
                <thead className="text-xs text-gray-500"><tr><th className="text-left py-1">Nutrient</th><th className="text-right py-1">Per 100g</th>{nutritionResult.per_serving && Object.keys(nutritionResult.per_serving).length > 0 && <th className="text-right py-1">Per Serving</th>}<th className="text-left py-1 pl-2">Unit</th></tr></thead>
                <tbody className="divide-y divide-gray-100">
                  {nutritionResult.nutrients.map((n) => (
                    <tr key={n.nutrient_code} className="hover:bg-gray-50">
                      <td className="py-1.5 text-gray-700">{n.nutrient_name}</td>
                      <td className="py-1.5 text-right font-mono font-medium">{Number(n.value_per_100g).toFixed(2)}</td>
                      {nutritionResult.per_serving && Object.keys(nutritionResult.per_serving).length > 0 && (
                        <td className="py-1.5 text-right font-mono text-gray-500">{n.value_per_serving ? Number(n.value_per_serving).toFixed(2) : "—"}</td>
                      )}
                      <td className="py-1.5 pl-2 text-gray-400">{n.unit}</td>
                    </tr>
                  ))}
                  {nutritionResult.nutrients.length === 0 && <tr><td colSpan={4} className="py-4 text-center text-gray-400">No nutrition data available</td></tr>}
                </tbody>
              </table>

              {nutritionResult.serving_size_g && (
                <p className="text-xs text-gray-500">Serving size: {String(nutritionResult.serving_size_g)}g</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
