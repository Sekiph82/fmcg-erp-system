"use client";
import { useEffect, useState } from "react";
import Link from "next/link";

interface AccuracyRow {
  product_id: string;
  product_name: string;
  forecast_count: number;
  avg_mape: number | null;
  avg_rmse: number | null;
  best_model: string | null;
}

export default function ForecastAccuracyPage() {
  const [rows, setRows] = useState<AccuracyRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/v1/mrp/forecasts/accuracy")
      .then(r => r.json())
      .then(setRows)
      .finally(() => setLoading(false));
  }, []);

  const mapeColor = (mape: number | null) => {
    if (mape === null) return "text-gray-400";
    if (mape <= 10) return "text-green-600 font-bold";
    if (mape <= 20) return "text-amber-600";
    return "text-red-600 font-semibold";
  };

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center gap-3">
        <Link href="/dashboard/mrp/forecast" className="text-sm text-blue-600 hover:text-blue-800">← Forecasts</Link>
      </div>
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Forecast Accuracy</h1>
        <p className="text-sm text-gray-500 mt-0.5">MAPE and RMSE per product across all forecast runs</p>
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800">
        <strong>MAPE</strong> = Mean Absolute Percentage Error (lower is better; &lt;10% = excellent, &lt;20% = acceptable).
        <strong className="ml-2">RMSE</strong> = Root Mean Squared Error (in units; penalises large errors more).
      </div>

      <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
        <div className="px-4 py-3 border-b bg-gray-50">
          <h2 className="text-sm font-semibold text-gray-700">Accuracy by Product ({rows.length})</h2>
        </div>
        {loading ? <div className="p-6 text-sm text-gray-400 text-center">Loading…</div> :
         rows.length === 0 ? <div className="p-6 text-sm text-gray-400 text-center">No approved forecasts with actuals yet. Run backfill after actuals are available.</div> : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500">
              <tr>
                <th className="text-left px-4 py-2">Product</th>
                <th className="text-left px-4 py-2">Forecasts</th>
                <th className="text-left px-4 py-2">Avg MAPE</th>
                <th className="text-left px-4 py-2">Avg RMSE</th>
                <th className="text-left px-4 py-2">Best Model</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {rows.map((r) => (
                <tr key={r.product_id}>
                  <td className="px-4 py-2.5 font-medium text-gray-900">{r.product_name}</td>
                  <td className="px-4 py-2.5 text-gray-500">{r.forecast_count}</td>
                  <td className={`px-4 py-2.5 ${mapeColor(r.avg_mape)}`}>
                    {r.avg_mape !== null ? `${r.avg_mape.toFixed(1)}%` : "—"}
                  </td>
                  <td className="px-4 py-2.5 text-gray-600 font-mono text-xs">
                    {r.avg_rmse !== null ? r.avg_rmse.toFixed(1) : "—"}
                  </td>
                  <td className="px-4 py-2.5 text-xs text-gray-500">{r.best_model?.replace(/_/g, " ") ?? "—"}</td>
                  <td className="px-4 py-2.5">
                    <Link href={`/dashboard/mrp/forecast?product_id=${r.product_id}`}
                      className="text-xs text-blue-600 hover:text-blue-800">Forecasts</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
