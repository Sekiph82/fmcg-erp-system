"use client";
import React, { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { mrpApi, STATUS_COLOR, fmtQty, MRPRun, MRPResult } from "@/lib/mrp";

const StatusBadge = ({ s }: { s: string }) => (
  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLOR[s] ?? "bg-gray-100 text-gray-600"}`}>{s}</span>
);

function RunResultsPanel({ runId }: { runId: string }) {
  const [shortageOnly, setShortageOnly] = useState(false);
  const { data: results = [] } = useQuery({
    queryKey: ["mrp-results", runId, shortageOnly],
    queryFn: () => mrpApi.getRunResults(runId, shortageOnly),
  });

  const chartData = results.slice(0, 20).map(r => ({
    name: r.product_sku ?? r.product_name?.slice(0, 12) ?? "?",
    demand: Number(r.gross_demand_qty),
    supply: Number(r.total_supply_qty),
    net: Number(r.net_requirement_qty),
  }));

  return (
    <div className="space-y-5">
      {chartData.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <h3 className="text-sm font-semibold mb-4">Demand vs Supply (Top 20 Products)</h3>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Legend />
              <Bar dataKey="demand" name="Gross Demand" fill="#f97316" radius={[2, 2, 0, 0]} />
              <Bar dataKey="supply" name="Total Supply" fill="#22c55e" radius={[2, 2, 0, 0]} />
              <Bar dataKey="net" name="Net Req." fill="#ef4444" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700 flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input type="checkbox" checked={shortageOnly} onChange={e => setShortageOnly(e.target.checked)}
              className="rounded" />
            Show shortages only
          </label>
          <span className="text-xs text-gray-400">{results.length} products</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-700 text-xs uppercase text-gray-500">
              <tr>
                {["SKU", "Product", "SO Demand", "Forecast", "Safety", "Gross Demand",
                  "Stock", "Incoming PO", "Incoming Prod", "Total Supply", "Net Req.", "Status"].map(h => (
                  <th key={h} className="px-3 py-3 text-left font-medium whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {results.map((r, i) => (
                <tr key={i} className={`hover:bg-gray-50 dark:hover:bg-gray-750 ${r.shortage_flag ? "bg-red-50/40 dark:bg-red-950/10" : ""}`}>
                  <td className="px-3 py-2 font-mono text-xs">{r.product_sku ?? "—"}</td>
                  <td className="px-3 py-2 font-medium text-xs">{r.product_name ?? "—"}</td>
                  <td className="px-3 py-2 text-right">{fmtQty(r.so_demand_qty)}</td>
                  <td className="px-3 py-2 text-right">{fmtQty(r.forecast_demand_qty)}</td>
                  <td className="px-3 py-2 text-right">{fmtQty(r.safety_stock_qty)}</td>
                  <td className="px-3 py-2 text-right font-semibold">{fmtQty(r.gross_demand_qty)}</td>
                  <td className="px-3 py-2 text-right text-green-700">{fmtQty(r.stock_on_hand_qty)}</td>
                  <td className="px-3 py-2 text-right">{fmtQty(r.incoming_po_qty)}</td>
                  <td className="px-3 py-2 text-right">{fmtQty(r.incoming_prod_qty)}</td>
                  <td className="px-3 py-2 text-right font-semibold text-green-700">{fmtQty(r.total_supply_qty)}</td>
                  <td className={`px-3 py-2 text-right font-bold ${r.shortage_flag ? "text-red-600" : "text-gray-400"}`}>
                    {fmtQty(r.net_requirement_qty)}
                  </td>
                  <td className="px-3 py-2">
                    {r.shortage_flag
                      ? <span className="px-2 py-0.5 rounded-full text-xs bg-red-100 text-red-700">⚠ SHORT</span>
                      : <span className="px-2 py-0.5 rounded-full text-xs bg-green-100 text-green-700">OK</span>}
                  </td>
                </tr>
              ))}
              {results.length === 0 && (
                <tr><td colSpan={12} className="px-4 py-8 text-center text-gray-400">No results</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default function MRPRunPage() {
  const searchParams = useSearchParams();
  const selectedId = searchParams.get("id");
  const qc = useQueryClient();
  const [horizon, setHorizon] = useState(90);
  const [incForecast, setIncForecast] = useState(true);
  const [incSafety, setIncSafety] = useState(true);

  const { data: runs = [], isLoading } = useQuery({
    queryKey: ["mrp-runs"],
    queryFn: () => mrpApi.listRuns({ limit: 20 }),
  });

  const selectedRun = runs.find(r => r.id === selectedId) ?? runs[0];

  const runMutation = useMutation({
    mutationFn: () => mrpApi.triggerRun({
      planning_horizon_days: horizon,
      include_forecast: incForecast,
      include_safety_stock: incSafety,
    }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mrp-runs"] }),
  });

  const sel = "rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm";

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6 space-y-6">
      <div className="flex items-center gap-3 mb-1">
        <Link href="/dashboard/mrp" className="text-sm text-gray-500 hover:text-indigo-600">← MRP Dashboard</Link>
      </div>
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white" style={{ borderLeft: "4px solid #6366f1", paddingLeft: 12 }}>
        MRP Runs
      </h1>

      {/* Trigger form */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
        <h3 className="text-sm font-semibold mb-4">Trigger New MRP Run</h3>
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Planning Horizon (days)</label>
            <input type="number" className={sel} value={horizon} min={7} max={365}
              onChange={e => setHorizon(Number(e.target.value))} style={{ width: 120 }} />
          </div>
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input type="checkbox" checked={incForecast} onChange={e => setIncForecast(e.target.checked)} className="rounded" />
            Include Forecast Demand
          </label>
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input type="checkbox" checked={incSafety} onChange={e => setIncSafety(e.target.checked)} className="rounded" />
            Include Safety Stock
          </label>
          <button
            onClick={() => runMutation.mutate()}
            disabled={runMutation.isPending}
            className="px-5 py-2 rounded-lg text-sm font-semibold bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-60"
          >
            {runMutation.isPending ? "⟳ Running..." : "▶ Run MRP"}
          </button>
        </div>
        {runMutation.isSuccess && (
          <p className="mt-3 text-sm text-green-600">✓ Run completed: {runMutation.data?.run_no}</p>
        )}
        {runMutation.isError && (
          <p className="mt-3 text-sm text-red-600">✗ Run failed. Check server logs.</p>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Run list sidebar */}
        <div className="lg:col-span-1">
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700">
              <p className="text-sm font-semibold">Run History</p>
            </div>
            <div className="divide-y divide-gray-100 dark:divide-gray-700">
              {runs.map(r => (
                <Link
                  key={r.id}
                  href={`/dashboard/mrp/run?id=${r.id}`}
                  className={`block px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors ${selectedRun?.id === r.id ? "bg-indigo-50 dark:bg-indigo-950/20 border-l-2 border-indigo-500" : ""}`}
                >
                  <p className="font-mono text-xs font-semibold text-gray-900 dark:text-white">{r.run_no}</p>
                  <div className="flex items-center justify-between mt-1">
                    <span className="text-xs text-gray-400">{r.run_date}</span>
                    <StatusBadge s={r.status} />
                  </div>
                  {r.shortage_count != null && r.shortage_count > 0 && (
                    <p className="text-xs text-red-600 mt-0.5">⚠ {r.shortage_count} shortages</p>
                  )}
                </Link>
              ))}
              {runs.length === 0 && (
                <p className="px-4 py-6 text-center text-xs text-gray-400">No runs yet</p>
              )}
            </div>
          </div>
        </div>

        {/* Results panel */}
        <div className="lg:col-span-3">
          {selectedRun ? (
            <>
              <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 mb-5">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
                  <div><p className="text-xs text-gray-500">Run No</p><p className="font-mono font-bold">{selectedRun.run_no}</p></div>
                  <div><p className="text-xs text-gray-500">Status</p><StatusBadge s={selectedRun.status} /></div>
                  <div><p className="text-xs text-gray-500">Products</p><p className="font-bold">{selectedRun.product_count ?? "—"}</p></div>
                  <div><p className="text-xs text-gray-500">Shortages</p><p className="font-bold text-red-600">{selectedRun.shortage_count ?? "—"}</p></div>
                </div>
              </div>
              {selectedRun.status === "COMPLETED" && <RunResultsPanel runId={selectedRun.id} />}
              {selectedRun.status === "FAILED" && (
                <div className="bg-red-50 dark:bg-red-950/20 rounded-xl p-4 text-sm text-red-700">
                  Run failed: {selectedRun.error_message ?? "Unknown error"}
                </div>
              )}
              {selectedRun.status === "RUNNING" && (
                <div className="bg-blue-50 dark:bg-blue-950/20 rounded-xl p-4 text-sm text-blue-700 animate-pulse">
                  ⟳ MRP run in progress…
                </div>
              )}
            </>
          ) : (
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-8 text-center text-gray-400">
              Select a run from the list or trigger a new one.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
