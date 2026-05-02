"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { allergenApi } from "@/lib/allergen";

type Tab = "rm-allergens" | "fg-allergens" | "nutrition-completeness" | "missing-statements";

export default function AllergenReportsPage() {
  const [tab, setTab] = useState<Tab>("rm-allergens");

  const { data: rmAllergens } = useQuery({ queryKey: ["report-rm-allergens"], queryFn: allergenApi.reportRMAllergens, enabled: tab === "rm-allergens" });
  const { data: fgAllergens } = useQuery({ queryKey: ["report-fg-allergens"], queryFn: allergenApi.reportFGAllergens, enabled: tab === "fg-allergens" });
  const { data: nutritionComp } = useQuery({ queryKey: ["report-nutrition-completeness"], queryFn: allergenApi.reportNutritionCompleteness, enabled: tab === "nutrition-completeness" });
  const { data: missingStmts } = useQuery({ queryKey: ["report-missing-statements"], queryFn: allergenApi.reportMissingStatements, enabled: tab === "missing-statements" });

  function downloadCSV(data: Record<string, unknown>[], filename: string) {
    if (!data?.length) return;
    const headers = Object.keys(data[0]);
    const csv = [headers.join(","), ...data.map((r) => headers.map((h) => JSON.stringify(r[h] ?? "")).join(","))].join("\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    a.download = filename;
    a.click();
  }

  const tabs: { id: Tab; label: string }[] = [
    { id: "rm-allergens", label: "RM Allergen Report" },
    { id: "fg-allergens", label: "FG Allergen Declaration" },
    { id: "nutrition-completeness", label: "Nutrition Completeness" },
    { id: "missing-statements", label: "Missing Supplier Statements" },
  ];

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-semibold text-gray-900">Allergen + Nutrition Reports</h1>
      <div className="border-b flex gap-1">
        {tabs.map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)} className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${tab === t.id ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}>{t.label}</button>
        ))}
      </div>

      {tab === "rm-allergens" && (
        <div className="bg-white border rounded-lg overflow-hidden">
          <div className="px-4 py-3 border-b flex justify-between">
            <h2 className="text-sm font-medium text-gray-700">Raw Material Allergen Report</h2>
            <button onClick={() => downloadCSV((rmAllergens || []) as Record<string, unknown>[], "rm_allergens.csv")} className="text-xs text-blue-600 hover:underline">Export CSV</button>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>{["Code", "Material", "Contains", "May Contain", "Cross-Contact Risk", "Statement Ref", "Review Date"].map((h) => <th key={h} className="px-3 py-2 text-left">{h}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {!(rmAllergens as unknown[])?.length && <tr><td colSpan={7} className="px-4 py-6 text-center text-gray-400">No data</td></tr>}
              {(rmAllergens as Record<string, string>[] || []).map((r, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-3 py-2 font-mono text-xs">{r.code}</td>
                  <td className="px-3 py-2 font-medium">{r.name}</td>
                  <td className="px-3 py-2">{r.allergen_present_flag === "true" || (r.allergen_present_flag as unknown) === true ? <span className="text-red-600 text-xs font-medium">YES</span> : <span className="text-green-600 text-xs">No</span>}</td>
                  <td className="px-3 py-2">{r.allergen_may_contain_flag === "true" || (r.allergen_may_contain_flag as unknown) === true ? <span className="text-orange-600 text-xs">YES</span> : <span className="text-gray-400 text-xs">No</span>}</td>
                  <td className="px-3 py-2 text-xs">{r.cross_contact_risk_level}</td>
                  <td className="px-3 py-2 text-gray-500 text-xs">{r.supplier_allergen_statement_ref || "—"}</td>
                  <td className="px-3 py-2 text-gray-400 text-xs">{r.allergen_review_date || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "fg-allergens" && (
        <div className="bg-white border rounded-lg overflow-hidden">
          <div className="px-4 py-3 border-b flex justify-between">
            <h2 className="text-sm font-medium text-gray-700">Finished Product Allergen Declaration</h2>
            <button onClick={() => downloadCSV((fgAllergens || []) as Record<string, unknown>[], "fg_allergens.csv")} className="text-xs text-blue-600 hover:underline">Export CSV</button>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>{["Product", "Contains", "May Contain", "Label Statement", "Stale"].map((h) => <th key={h} className="px-3 py-2 text-left">{h}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {!(fgAllergens as unknown[])?.length && <tr><td colSpan={5} className="px-4 py-6 text-center text-gray-400">No data</td></tr>}
              {(fgAllergens as Record<string, unknown>[] || []).map((r, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-3 py-2 font-medium">{String(r.product_name)}</td>
                  <td className="px-3 py-2 text-xs">{Array.isArray(r.contains) ? r.contains.join(", ") : "None"}</td>
                  <td className="px-3 py-2 text-xs">{Array.isArray(r.may_contain) ? r.may_contain.join(", ") : "—"}</td>
                  <td className="px-3 py-2 text-xs text-gray-500">{String(r.label_statement || "—")}</td>
                  <td className="px-3 py-2">{r.is_stale ? <span className="text-orange-600 text-xs">⚠</span> : <span className="text-green-600 text-xs">✓</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "nutrition-completeness" && (
        <div className="bg-white border rounded-lg overflow-hidden">
          <div className="px-4 py-3 border-b flex justify-between">
            <h2 className="text-sm font-medium text-gray-700">Nutrition Profile Completeness</h2>
            <button onClick={() => downloadCSV((nutritionComp || []) as Record<string, unknown>[], "nutrition_completeness.csv")} className="text-xs text-blue-600 hover:underline">Export CSV</button>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>{["Code", "Material", "Nutrient Count", "All Approved"].map((h) => <th key={h} className="px-3 py-2 text-left">{h}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {(nutritionComp as Record<string, string>[] || []).map((r, i) => (
                <tr key={i} className={`hover:bg-gray-50 ${!r.nutrient_count ? "bg-red-50/30" : ""}`}>
                  <td className="px-3 py-2 font-mono text-xs">{r.code}</td>
                  <td className="px-3 py-2 font-medium">{r.name}</td>
                  <td className="px-3 py-2">{r.nutrient_count || <span className="text-red-600 text-xs">Missing</span>}</td>
                  <td className="px-3 py-2">{r.all_approved ? <span className="text-green-600 text-xs">✓</span> : <span className="text-orange-600 text-xs">Partial</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "missing-statements" && (
        <div className="bg-white border rounded-lg overflow-hidden">
          <div className="px-4 py-3 border-b flex justify-between">
            <h2 className="text-sm font-medium text-gray-700">Missing Supplier Allergen Statements</h2>
            <button onClick={() => downloadCSV((missingStmts || []) as Record<string, unknown>[], "missing_statements.csv")} className="text-xs text-blue-600 hover:underline">Export CSV</button>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>{["Code", "Material", "Cross-Contact Risk", "Review Date"].map((h) => <th key={h} className="px-3 py-2 text-left">{h}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {!(missingStmts as unknown[])?.length && <tr><td colSpan={4} className="px-4 py-6 text-center text-green-600 text-sm">✓ All materials have supplier allergen statements</td></tr>}
              {(missingStmts as Record<string, string>[] || []).map((r, i) => (
                <tr key={i} className="hover:bg-gray-50 bg-orange-50/30">
                  <td className="px-3 py-2 font-mono text-xs">{r.code}</td>
                  <td className="px-3 py-2 font-medium">{r.name}</td>
                  <td className="px-3 py-2 text-xs">{r.cross_contact_risk_level}</td>
                  <td className="px-3 py-2 text-gray-400 text-xs">{r.allergen_review_date || "Never reviewed"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
