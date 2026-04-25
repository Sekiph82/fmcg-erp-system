"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { allergenApi, type LabelReadiness } from "@/lib/allergen";

function ScoreBar({ score }: { score: number }) {
  const color = score >= 80 ? "bg-green-500" : score >= 50 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-200 rounded-full h-2">
        <div className={`${color} h-2 rounded-full transition-all`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-sm font-bold w-10 text-right">{score}%</span>
    </div>
  );
}

export default function LabelReadinessPage() {
  const [productId, setProductId] = useState("");
  const [result, setResult] = useState<LabelReadiness | null>(null);

  const check = useMutation({
    mutationFn: () => allergenApi.getLabelReadiness(productId),
    onSuccess: (r) => setResult(r),
  });

  const readinessItems = result ? [
    { label: "Allergen Summary", ok: result.allergen_summary_complete && !result.allergen_summary_stale, partial: result.allergen_summary_complete && result.allergen_summary_stale, msg: result.allergen_summary_stale ? "Stale — needs recalculation" : result.allergen_summary_complete ? "Complete" : "Missing" },
    { label: "Nutrition Summary", ok: result.nutrition_summary_complete && !result.nutrition_summary_stale, partial: result.nutrition_summary_complete && result.nutrition_summary_stale, msg: result.nutrition_summary_stale ? "Stale — needs recalculation" : result.nutrition_summary_complete ? "Complete" : "Missing" },
    { label: "Serving Size Config", ok: result.serving_config_present, partial: false, msg: result.serving_config_present ? "Configured" : "Not configured" },
    { label: "Open Change Logs", ok: result.open_change_logs === 0, partial: false, msg: result.open_change_logs > 0 ? `${result.open_change_logs} open` : "All clear" },
    { label: "Pending Label Reviews", ok: result.pending_label_reviews === 0, partial: false, msg: result.pending_label_reviews > 0 ? `${result.pending_label_reviews} pending` : "All clear" },
    { label: "Pending QC Reviews", ok: result.pending_qc_reviews === 0, partial: false, msg: result.pending_qc_reviews > 0 ? `${result.pending_qc_reviews} pending` : "All clear" },
  ] : [];

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-semibold text-gray-900">Label Readiness Check</h1>
      <p className="text-sm text-gray-500">Verify that a product is ready for label declaration — allergens, nutrition, serving size, and review status.</p>

      <div className="bg-white border rounded-lg p-4 space-y-3">
        <label className="text-xs text-gray-500">Product ID (UUID)</label>
        <div className="flex gap-2">
          <input
            className="flex-1 border rounded px-2 py-1.5 text-sm font-mono"
            value={productId}
            onChange={(e) => setProductId(e.target.value)}
            placeholder="product-uuid..."
          />
          <button
            onClick={() => check.mutate()}
            disabled={!productId.trim() || check.isPending}
            className="px-4 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {check.isPending ? "Checking…" : "Check Readiness"}
          </button>
        </div>
        {check.isError && <p className="text-red-600 text-xs">{(check.error as Error).message}</p>}
      </div>

      {result && (
        <div className="space-y-4">
          {/* Score */}
          <div className="bg-white border rounded-lg p-4">
            <h2 className="text-sm font-medium text-gray-700 mb-2">{result.product_name}</h2>
            <p className="text-xs text-gray-500 mb-2">Label Readiness Score</p>
            <ScoreBar score={result.readiness_score} />
          </div>

          {/* Checklist */}
          <div className="bg-white border rounded-lg p-4 space-y-2">
            <h2 className="text-sm font-medium text-gray-700 mb-3">Readiness Checklist</h2>
            {readinessItems.map((item) => (
              <div key={item.label} className="flex items-center justify-between py-2 border-b last:border-0">
                <div className="flex items-center gap-2">
                  <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs ${item.ok ? "bg-green-100 text-green-700" : item.partial ? "bg-yellow-100 text-yellow-700" : "bg-red-100 text-red-700"}`}>
                    {item.ok ? "✓" : item.partial ? "⚠" : "✕"}
                  </span>
                  <span className="text-sm text-gray-700">{item.label}</span>
                </div>
                <span className={`text-xs ${item.ok ? "text-green-600" : item.partial ? "text-yellow-600" : "text-red-600"}`}>{item.msg}</span>
              </div>
            ))}
          </div>

          {/* Warnings */}
          {result.warnings.length > 0 && (
            <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
              <h2 className="text-sm font-medium text-orange-800 mb-2">⚠ Warnings</h2>
              <ul className="space-y-1">
                {result.warnings.map((w, i) => <li key={i} className="text-xs text-orange-700">• {w}</li>)}
              </ul>
            </div>
          )}

          {result.readiness_score >= 80 && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <p className="text-sm font-medium text-green-800">✅ Product is label-ready</p>
              <p className="text-xs text-green-600 mt-0.5">All critical label declaration requirements have been met.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
