"use client";
import React, { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
  BarChart, Bar,
} from "recharts";
import { mrpApi, STATUS_COLOR, fmtQty, Forecast, ForecastSummary } from "@/lib/mrp";

const MODELS = [
  { value: "EXPONENTIAL_SMOOTHING", label: "Exponential Smoothing" },
  { value: "MOVING_AVG",            label: "Moving Average" },
  { value: "WEIGHTED_MOVING_AVG",   label: "Weighted Moving Average" },
  { value: "SEASONAL",              label: "Seasonal Index" },
];

const PERIODS = [
  { value: "MONTHLY", label: "Monthly" },
  { value: "WEEKLY",  label: "Weekly" },
  { value: "DAILY",   label: "Daily" },
];

function ForecastDetailPanel({ forecast }: { forecast: Forecast }) {
  const qc = useQueryClient();

  const approveMutation = useMutation({
    mutationFn: () => mrpApi.approveForecast(forecast.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mrp-forecasts"] }),
  });

  const backfillMutation = useMutation({
    mutationFn: () => mrpApi.backfillActuals(forecast.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mrp-forecast", forecast.id] });
      qc.invalidateQueries({ queryKey: ["mrp-forecasts"] });
    },
  });

  const chartData = forecast.lines.map(l => ({
    date: l.period_date.slice(0, 7),
    forecast: Number(l.forecast_qty),
    adjusted: l.adjusted_qty != null ? Number(l.adjusted_qty) : undefined,
    actual: l.actual_qty != null ? Number(l.actual_qty) : undefined,
  }));

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex justify-between items-start flex-wrap gap-3">
          <div>
            <p className="text-xs text-gray-500">Product</p>
            <p className="font-semibold">{forecast.product_name} <span className="text-gray-400 font-mono text-xs ml-2">{forecast.product_sku}</span></p>
            <div className="flex gap-3 mt-2 text-xs text-gray-500">
              <span>Model: <b>{forecast.forecast_model}</b></span>
              <span>Period: <b>{forecast.period_type}</b></span>
              <span>{forecast.start_date} → {forecast.end_date}</span>
              {forecast.mape != null && (
                <span>MAPE: <b className={forecast.mape < 10 ? "text-green-600" : forecast.mape < 20 ? "text-yellow-600" : "text-red-600"}>
                  {Number(forecast.mape).toFixed(1)}%
                </b></span>
              )}
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={() => backfillMutation.mutate()}
              disabled={backfillMutation.isPending}
              className="px-3 py-1.5 text-xs bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200">
              ↻ Backfill Actuals
            </button>
            {forecast.status !== "APPROVED" && (
              <button onClick={() => approveMutation.mutate()}
                disabled={approveMutation.isPending}
                className="px-3 py-1.5 text-xs bg-green-600 text-white rounded-lg hover:bg-green-700">
                ✓ Approve
              </button>
            )}
            {forecast.status === "APPROVED" && (
              <span className="px-3 py-1.5 text-xs bg-green-100 text-green-700 rounded-lg">✓ Approved</span>
            )}
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <h3 className="text-sm font-semibold mb-4">Forecast vs Actual</h3>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="forecast" name="Forecast" stroke="#6366f1" dot={false} strokeWidth={2} />
            <Line type="monotone" dataKey="adjusted" name="Adjusted" stroke="#f97316" dot={false} strokeWidth={2} strokeDasharray="4 2" />
            <Line type="monotone" dataKey="actual" name="Actual" stroke="#22c55e" dot={{ r: 3 }} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Lines table */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-700 text-xs uppercase text-gray-500">
              <tr>
                {["Period", "Forecast Qty", "Adjusted Qty", "Actual Qty", "Error %", "Flags", "Notes"].map(h => (
                  <th key={h} className="px-3 py-3 text-left font-medium whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {forecast.lines.map((l, i) => (
                <tr key={i} className={`hover:bg-gray-50 dark:hover:bg-gray-750 ${l.is_spike ? "bg-orange-50/40" : ""} ${l.is_outlier ? "bg-red-50/40" : ""}`}>
                  <td className="px-3 py-2 font-mono text-xs">{l.period_date}</td>
                  <td className="px-3 py-2 text-right font-semibold">{fmtQty(l.forecast_qty)}</td>
                  <td className="px-3 py-2 text-right text-orange-600">{l.adjusted_qty != null ? fmtQty(l.adjusted_qty) : "—"}</td>
                  <td className="px-3 py-2 text-right text-green-600">{l.actual_qty != null ? fmtQty(l.actual_qty) : "—"}</td>
                  <td className="px-3 py-2 text-right text-xs">
                    {l.error_pct != null ? (
                      <span className={Number(l.error_pct) < 10 ? "text-green-600" : Number(l.error_pct) < 25 ? "text-yellow-600" : "text-red-600"}>
                        {Number(l.error_pct).toFixed(1)}%
                      </span>
                    ) : "—"}
                  </td>
                  <td className="px-3 py-2">
                    {l.is_spike && <span className="mr-1 px-1.5 py-0.5 rounded text-xs bg-orange-100 text-orange-700">⚡ Spike</span>}
                    {l.is_outlier && <span className="px-1.5 py-0.5 rounded text-xs bg-red-100 text-red-700">⚠ Outlier</span>}
                  </td>
                  <td className="px-3 py-2 text-xs text-gray-400">{l.notes ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default function ForecastPage() {
  const qc = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [tab, setTab] = useState<"list" | "generate" | "accuracy">("list");

  // Generate form state
  const [productId, setProductId] = useState("");
  const [model, setModel] = useState("EXPONENTIAL_SMOOTHING");
  const [periodType, setPeriodType] = useState("MONTHLY");
  const [periodsAhead, setPeriodsAhead] = useState(6);
  const [historyPeriods, setHistoryPeriods] = useState(12);

  const { data: forecasts = [], isLoading } = useQuery({
    queryKey: ["mrp-forecasts"],
    queryFn: () => mrpApi.listForecasts({ limit: 100 }),
  });

  const { data: selectedForecast } = useQuery({
    queryKey: ["mrp-forecast", selectedId],
    queryFn: () => mrpApi.getForecast(selectedId!),
    enabled: !!selectedId,
  });

  const { data: accuracy = [] } = useQuery({
    queryKey: ["mrp-forecast-accuracy"],
    queryFn: () => mrpApi.forecastAccuracy(),
    enabled: tab === "accuracy",
  });

  const generateMutation = useMutation({
    mutationFn: () => mrpApi.generateForecast({
      product_id: productId,
      forecast_model: model,
      period_type: periodType,
      periods_ahead: periodsAhead,
      history_periods: historyPeriods,
    }),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["mrp-forecasts"] });
      setSelectedId(data.id);
      setTab("list");
    },
  });

  const sel = "rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm";

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6 space-y-6">
      <div className="flex items-center gap-3 mb-1">
        <Link href="/dashboard/mrp" className="text-sm text-gray-500 hover:text-indigo-600">← MRP Dashboard</Link>
      </div>
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white" style={{ borderLeft: "4px solid #6366f1", paddingLeft: 12 }}>
        Demand Forecasting
      </h1>

      {/* Tabs */}
      <div className="flex gap-2">
        {[
          { id: "list", label: "Forecast List" },
          { id: "generate", label: "+ Generate Forecast" },
          { id: "accuracy", label: "Accuracy (MAPE)" },
        ].map(t => (
          <button key={t.id} onClick={() => setTab(t.id as any)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              tab === t.id ? "bg-indigo-600 text-white" : "bg-white dark:bg-gray-800 text-gray-600 border border-gray-200 dark:border-gray-700 hover:bg-gray-50"
            }`}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === "generate" && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
          <h3 className="text-sm font-semibold mb-4">Generate Statistical Forecast</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Product ID (UUID)</label>
              <input type="text" className={sel} placeholder="xxxxxxxx-xxxx-…"
                value={productId} onChange={e => setProductId(e.target.value)} />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Forecast Model</label>
              <select className={sel} value={model} onChange={e => setModel(e.target.value)}>
                {MODELS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Period Type</label>
              <select className={sel} value={periodType} onChange={e => setPeriodType(e.target.value)}>
                {PERIODS.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Periods Ahead</label>
              <input type="number" className={sel} min={1} max={24} value={periodsAhead}
                onChange={e => setPeriodsAhead(Number(e.target.value))} />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">History Periods</label>
              <input type="number" className={sel} min={3} max={36} value={historyPeriods}
                onChange={e => setHistoryPeriods(Number(e.target.value))} />
            </div>
          </div>
          <button
            onClick={() => generateMutation.mutate()}
            disabled={!productId || generateMutation.isPending}
            className="mt-4 px-5 py-2 rounded-lg text-sm font-semibold bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-60"
          >
            {generateMutation.isPending ? "⟳ Generating…" : "Generate Forecast"}
          </button>
          {generateMutation.isSuccess && (
            <p className="mt-2 text-sm text-green-600">✓ Forecast generated successfully</p>
          )}
          {generateMutation.isError && (
            <p className="mt-2 text-sm text-red-600">✗ Failed — check product ID and sales history</p>
          )}
        </div>
      )}

      {tab === "accuracy" && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-700 text-xs uppercase text-gray-500">
                <tr>
                  {["SKU", "Product", "Forecasts", "Avg MAPE", "Min MAPE", "Max MAPE", "Accuracy"].map(h => (
                    <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {accuracy.map((r, i) => {
                  const mape = Number(r.avg_mape);
                  const tier = mape < 10 ? "text-green-600" : mape < 20 ? "text-yellow-600" : "text-red-600";
                  const grade = mape < 10 ? "Excellent" : mape < 20 ? "Good" : mape < 30 ? "Fair" : "Poor";
                  return (
                    <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-750">
                      <td className="px-4 py-3 font-mono text-xs">{r.product_sku ?? "—"}</td>
                      <td className="px-4 py-3 font-medium">{r.product_name ?? "—"}</td>
                      <td className="px-4 py-3 text-center">{r.periods}</td>
                      <td className={`px-4 py-3 text-right font-bold ${tier}`}>
                        {r.avg_mape != null ? Number(r.avg_mape).toFixed(1) + "%" : "—"}
                      </td>
                      <td className="px-4 py-3 text-right text-xs">{r.min_mape != null ? Number(r.min_mape).toFixed(1) + "%" : "—"}</td>
                      <td className="px-4 py-3 text-right text-xs">{r.max_mape != null ? Number(r.max_mape).toFixed(1) + "%" : "—"}</td>
                      <td className={`px-4 py-3 font-semibold ${tier}`}>{grade}</td>
                    </tr>
                  );
                })}
                {accuracy.length === 0 && (
                  <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No accuracy data yet — backfill actuals on forecasts first</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "list" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Forecast list */}
          <div className="lg:col-span-1">
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700">
                <p className="text-sm font-semibold">{forecasts.length} Forecasts</p>
              </div>
              <div className="divide-y divide-gray-100 dark:divide-gray-700 max-h-[600px] overflow-y-auto">
                {forecasts.map(f => (
                  <button
                    key={f.id}
                    onClick={() => setSelectedId(f.id)}
                    className={`w-full text-left px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors ${
                      selectedId === f.id ? "bg-indigo-50 dark:bg-indigo-950/20 border-l-2 border-indigo-500" : ""
                    }`}
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="text-xs font-semibold text-gray-900 dark:text-white">{f.product_name ?? f.product_sku}</p>
                        <p className="text-xs text-gray-400 mt-0.5">{f.forecast_model} · {f.period_type}</p>
                        <p className="text-xs font-mono text-gray-400">{f.start_date} → {f.end_date}</p>
                      </div>
                      <div className="text-right">
                        <span className={`block text-xs px-2 py-0.5 rounded-full ${STATUS_COLOR[f.status] ?? "bg-gray-100"}`}>{f.status}</span>
                        {f.mape != null && (
                          <span className={`text-xs mt-1 block ${Number(f.mape) < 10 ? "text-green-600" : Number(f.mape) < 20 ? "text-yellow-600" : "text-red-600"}`}>
                            {Number(f.mape).toFixed(1)}% MAPE
                          </span>
                        )}
                      </div>
                    </div>
                  </button>
                ))}
                {forecasts.length === 0 && (
                  <p className="px-4 py-6 text-center text-xs text-gray-400">No forecasts yet</p>
                )}
              </div>
            </div>
          </div>

          {/* Detail */}
          <div className="lg:col-span-2">
            {selectedForecast ? (
              <ForecastDetailPanel forecast={selectedForecast} />
            ) : (
              <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-8 text-center text-gray-400">
                Select a forecast to view details
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
