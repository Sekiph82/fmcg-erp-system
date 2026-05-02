"use client";
import { useEffect, useState } from "react";
import { crmApi, fmtCurrency } from "@/lib/crm_pipeline";

interface ForecastRow {
  month: string;
  expected_revenue: number;
  weighted_revenue: number;
  deal_count: number;
}

export default function ForecastPage() {
  const [forecast, setForecast] = useState<ForecastRow[]>([]);
  const [pipeline, setPipeline] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [months, setMonths] = useState(6);

  const load = async () => {
    setLoading(true);
    try {
      const [fc, pp] = await Promise.all([
        crmApi.getForecast(months),
        crmApi.getPipelineReport(),
      ]);
      setForecast(fc as unknown as ForecastRow[]);
      setPipeline(pp);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  useEffect(() => { load(); }, [months]);

  const totalExpected = forecast.reduce((s, r) => s + r.expected_revenue, 0);
  const totalWeighted = forecast.reduce((s, r) => s + r.weighted_revenue, 0);
  const totalDeals = forecast.reduce((s, r) => s + r.deal_count, 0);
  const maxWeighted = Math.max(...forecast.map(r => r.weighted_revenue), 1);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Revenue Forecast</h1>
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-600">Horizon:</label>
          <select value={months} onChange={e => setMonths(+e.target.value)}
            className="text-sm border rounded-lg px-2 py-1.5">
            <option value={3}>3 Months</option>
            <option value={6}>6 Months</option>
            <option value={12}>12 Months</option>
          </select>
        </div>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border shadow-sm p-4">
          <div className="text-xs text-gray-500">Total Expected Revenue</div>
          <div className="text-xl font-bold text-gray-800 mt-1">{fmtCurrency(totalExpected)}</div>
        </div>
        <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-4">
          <div className="text-xs text-gray-500">Weighted Pipeline</div>
          <div className="text-xl font-bold text-indigo-700 mt-1">{fmtCurrency(totalWeighted)}</div>
        </div>
        <div className="bg-white rounded-xl border shadow-sm p-4">
          <div className="text-xs text-gray-500">Deals in Forecast</div>
          <div className="text-xl font-bold text-gray-800 mt-1">{totalDeals}</div>
        </div>
      </div>

      {/* Bar Chart */}
      <div className="bg-white rounded-xl border shadow-sm p-4">
        <h2 className="font-semibold text-gray-800 mb-4">Monthly Forecast</h2>
        {loading ? (
          <div className="text-gray-400 py-4 text-center">Loading…</div>
        ) : (
          <div className="space-y-3">
            {forecast.map(row => (
              <div key={row.month} className="flex items-center gap-3">
                <div className="w-16 text-xs text-gray-600 font-medium">{row.month}</div>
                <div className="flex-1 space-y-1">
                  <div className="flex items-center gap-2">
                    <div className="h-4 bg-blue-100 rounded relative overflow-hidden"
                      style={{ width: `${(row.expected_revenue / Math.max(totalExpected / months, 1)) * 60}%`, minWidth: 4 }}>
                      <div className="h-full bg-blue-400 rounded" />
                    </div>
                    <span className="text-xs text-gray-500">{fmtCurrency(row.expected_revenue)}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="h-4 rounded overflow-hidden"
                      style={{ width: `${(row.weighted_revenue / Math.max(totalWeighted / months, 1)) * 60}%`, minWidth: 4, background: "#E0E7FF" }}>
                      <div className="h-full rounded" style={{ background: "#6366F1" }} />
                    </div>
                    <span className="text-xs text-indigo-600">{fmtCurrency(row.weighted_revenue)} weighted</span>
                  </div>
                </div>
                <div className="text-xs text-gray-400 w-14 text-right">{row.deal_count} deals</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Pipeline by Stage */}
      <div className="bg-white rounded-xl border shadow-sm p-4">
        <h2 className="font-semibold text-gray-800 mb-3">Pipeline by Stage</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-xs text-gray-600 bg-gray-50">
                <th className="px-3 py-2 text-left">Stage</th>
                <th className="px-3 py-2 text-right">Deals</th>
                <th className="px-3 py-2 text-right">Total Value</th>
                <th className="px-3 py-2 text-right">Weighted</th>
                <th className="px-3 py-2 text-right">Avg Prob</th>
              </tr>
            </thead>
            <tbody>
              {pipeline.map((row: Record<string, unknown>, i) => (
                <tr key={i} className="border-b hover:bg-gray-50">
                  <td className="px-3 py-2 font-medium text-gray-800">{row.stage_name as string}</td>
                  <td className="px-3 py-2 text-right text-gray-600">{row.record_count as number}</td>
                  <td className="px-3 py-2 text-right text-gray-800">{fmtCurrency(row.total_value as number)}</td>
                  <td className="px-3 py-2 text-right text-indigo-700">{fmtCurrency(row.weighted_value as number)}</td>
                  <td className="px-3 py-2 text-right text-gray-500">{Math.round(row.avg_probability as number)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
