"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { allergenApi, riskColor, type ProductAllergenSummary } from "@/lib/allergen";

export default function ProductAllergensPage() {
  const qc = useQueryClient();
  const [showCalc, setShowCalc] = useState<string | null>(null);
  const [calcForm, setCalcForm] = useState({ bom_id: "", recipe_id: "" });

  const { data: summaries } = useQuery({ queryKey: ["allergen-summaries"], queryFn: allergenApi.listAllergenSummaries });

  const calculate = useMutation({
    mutationFn: (productId: string) => allergenApi.calculateAllergenSummary(productId, { bom_id: calcForm.bom_id || undefined, recipe_id: calcForm.recipe_id || undefined }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["allergen-summaries"] }); setShowCalc(null); alert("Allergen summary recalculated"); },
  });

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Product Allergen Summaries</h1>
        <p className="text-sm text-gray-500">{summaries?.length || 0} products</p>
      </div>

      {/* Calculate Modal */}
      {showCalc && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-4 w-96 space-y-3">
            <h3 className="text-sm font-medium text-gray-900">Recalculate Allergen Summary</h3>
            <div>
              <label className="text-xs text-gray-500">BOM ID (UUID)</label>
              <input className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm font-mono" value={calcForm.bom_id} onChange={(e) => setCalcForm((p) => ({ ...p, bom_id: e.target.value }))} placeholder="bom-uuid..." />
            </div>
            <p className="text-xs text-gray-400 text-center">— or —</p>
            <div>
              <label className="text-xs text-gray-500">Recipe ID (UUID)</label>
              <input className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm font-mono" value={calcForm.recipe_id} onChange={(e) => setCalcForm((p) => ({ ...p, recipe_id: e.target.value }))} placeholder="recipe-uuid..." />
            </div>
            <div className="flex gap-2">
              <button onClick={() => calculate.mutate(showCalc)} disabled={calculate.isPending || (!calcForm.bom_id && !calcForm.recipe_id)} className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded disabled:opacity-50">Calculate</button>
              <button onClick={() => setShowCalc(null)} className="px-3 py-1.5 text-sm border rounded">Cancel</button>
            </div>
          </div>
        </div>
      )}

      <div className="bg-white border rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>{["Product", "Contains", "May Contain", "Cross-Contact", "Label Statement", "Version", "Stale", "Last Calc", "Actions"].map((h) => <th key={h} className="px-3 py-2 text-left whitespace-nowrap">{h}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {!summaries?.length && <tr><td colSpan={9} className="px-4 py-6 text-center text-gray-400">No allergen summaries. Calculate from BOM/Recipe per product.</td></tr>}
              {summaries?.map((s) => (
                <tr key={s.id} className={`hover:bg-gray-50 ${s.is_stale ? "bg-yellow-50/30" : ""}`}>
                  <td className="px-3 py-2 font-medium">{s.product_name || s.product_id.slice(0, 8)}</td>
                  <td className="px-3 py-2">
                    {s.contains_allergens?.length ? (
                      <div className="flex flex-wrap gap-0.5">
                        {s.contains_allergens.slice(0, 3).map((a) => <span key={a} className="text-xs bg-red-100 text-red-700 px-1.5 py-0.5 rounded">{a}</span>)}
                        {(s.contains_allergens.length > 3) && <span className="text-xs text-gray-400">+{s.contains_allergens.length - 3}</span>}
                      </div>
                    ) : <span className="text-green-600 text-xs">None</span>}
                  </td>
                  <td className="px-3 py-2">
                    {s.may_contain_allergens?.length ? (
                      <div className="flex flex-wrap gap-0.5">
                        {s.may_contain_allergens.slice(0, 2).map((a) => <span key={a} className="text-xs bg-orange-100 text-orange-700 px-1.5 py-0.5 rounded">{a}</span>)}
                        {(s.may_contain_allergens.length > 2) && <span className="text-xs text-gray-400">+{s.may_contain_allergens.length - 2}</span>}
                      </div>
                    ) : <span className="text-gray-400 text-xs">—</span>}
                  </td>
                  <td className="px-3 py-2">
                    {s.cross_contact_risk && <span className={`text-xs px-2 py-0.5 rounded font-medium ${riskColor[s.cross_contact_risk]}`}>{s.cross_contact_risk}</span>}
                  </td>
                  <td className="px-3 py-2 text-xs text-gray-500 max-w-xs truncate">{s.label_statement || "—"}</td>
                  <td className="px-3 py-2 text-gray-400 text-xs">{s.bom_version || "—"}</td>
                  <td className="px-3 py-2">{s.is_stale ? <span className="text-orange-600 text-xs font-medium">⚠ Stale</span> : <span className="text-green-600 text-xs">✓</span>}</td>
                  <td className="px-3 py-2 text-gray-400 text-xs">{s.last_calculated_at ? new Date(s.last_calculated_at).toLocaleDateString() : "—"}</td>
                  <td className="px-3 py-2">
                    <button onClick={() => { setShowCalc(s.product_id); setCalcForm({ bom_id: s.bom_id || "", recipe_id: "" }); }} className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded hover:bg-blue-100">Recalc</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
