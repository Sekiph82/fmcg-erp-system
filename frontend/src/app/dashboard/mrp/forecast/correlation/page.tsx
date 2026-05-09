"use client";
import { useState } from "react";
import Link from "next/link";

interface CorrelationPair {
  product_a_id: string;
  product_b_id: string;
  pearson_r: number;
  strength: string;
  periods_compared: number;
}

export default function CrossSKUCorrelationPage() {
  const [productIds, setProductIds] = useState("");
  const [periods, setPeriods] = useState(12);
  const [result, setResult] = useState<{ product_count: number; correlated_pairs: CorrelationPair[]; periods: number } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    if (!productIds.trim()) return;
    setLoading(true); setError(null); setResult(null);
    try {
      const r = await fetch(
        `/api/v1/mrp/forecasts/cross-sku-correlation?product_ids=${encodeURIComponent(productIds)}&periods=${periods}`
      );
      if (!r.ok) throw new Error(await r.text());
      setResult(await r.json());
    } catch (e) { setError(String(e)); }
    setLoading(false);
  };

  const rColor = (r: number) => {
    const abs = Math.abs(r);
    if (abs >= 0.8) return "text-green-600 font-bold";
    if (abs >= 0.6) return "text-amber-600";
    return "text-gray-500";
  };

  return (
    <div className="p-6 space-y-6 max-w-4xl mx-auto">
      <div className="flex items-center gap-3">
        <Link href="/dashboard/mrp/forecast" className="text-sm text-blue-600 hover:text-blue-800">← Forecasts</Link>
      </div>
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Cross-SKU Demand Correlation</h1>
        <p className="text-sm text-gray-500 mt-0.5">Identify products whose demand moves together — use to improve forecast accuracy.</p>
      </div>

      <div className="bg-white border rounded-lg p-5 shadow-sm space-y-3">
        <h2 className="text-sm font-semibold text-gray-700">Run Correlation Analysis</h2>
        <div>
          <label className="text-xs text-gray-500 block mb-1">Product UUIDs (comma-separated, min 2, max 20)</label>
          <textarea
            rows={3}
            value={productIds}
            onChange={(e) => setProductIds(e.target.value)}
            placeholder="uuid1, uuid2, uuid3, ..."
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm font-mono focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="text-xs text-gray-500 block mb-1">Monthly periods to compare: {periods}</label>
          <input type="range" min={4} max={36} value={periods} onChange={(e) => setPeriods(Number(e.target.value))}
            className="w-48" />
        </div>
        <button onClick={run} disabled={loading || !productIds.trim()}
          className="bg-blue-600 text-white text-sm px-4 py-2 rounded disabled:opacity-50">
          {loading ? "Computing…" : "Run Analysis"}
        </button>
      </div>

      {error && <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">{error}</div>}

      {result && (
        <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b bg-gray-50">
            <h2 className="text-sm font-semibold text-gray-700">
              Results — {result.product_count} products · {result.periods} months · {result.correlated_pairs.length} correlated pairs (|r| ≥ 0.6)
            </h2>
          </div>
          {result.correlated_pairs.length === 0 ? (
            <div className="p-6 text-sm text-gray-400 text-center">
              No strongly correlated pairs found. Ensure products have sufficient sales history ({result.periods} months).
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500">
                <tr>
                  <th className="text-left px-4 py-2">Product A</th>
                  <th className="text-left px-4 py-2">Product B</th>
                  <th className="text-left px-4 py-2">Pearson r</th>
                  <th className="text-left px-4 py-2">Strength</th>
                  <th className="text-left px-4 py-2">Periods</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {result.correlated_pairs.map((p, i) => (
                  <tr key={i}>
                    <td className="px-4 py-2.5 font-mono text-xs text-gray-600">{p.product_a_id.slice(0, 8)}…</td>
                    <td className="px-4 py-2.5 font-mono text-xs text-gray-600">{p.product_b_id.slice(0, 8)}…</td>
                    <td className={`px-4 py-2.5 font-mono ${rColor(p.pearson_r)}`}>{p.pearson_r.toFixed(4)}</td>
                    <td className="px-4 py-2.5 text-xs capitalize text-gray-600">{p.strength}</td>
                    <td className="px-4 py-2.5 text-gray-400">{p.periods_compared}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <div className="px-4 py-3 border-t bg-gray-50 text-xs text-gray-500">
            Strong correlation (|r| ≥ 0.8): use both products' history to refine forecasts. Moderate (0.6–0.8): consider cross-product demand signals.
          </div>
        </div>
      )}
    </div>
  );
}
