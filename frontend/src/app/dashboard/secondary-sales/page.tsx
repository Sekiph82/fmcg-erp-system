"use client";

import { useState, useEffect } from "react";
import {
  secondarySalesApi, SecondarySalesHeader, SecondarySalesStatus,
  SellThroughRow, DistributorPerformanceRow, AIInsightResult,
} from "@/lib/secondarySales";
import Link from "next/link";

const STATUS_COLORS: Record<SecondarySalesStatus, string> = {
  PENDING: "bg-yellow-100 text-yellow-800",
  VALIDATED: "bg-blue-100 text-blue-700",
  PROCESSED: "bg-green-100 text-green-700",
  REJECTED: "bg-red-100 text-red-700",
};

const ST_COLORS: Record<string, string> = {
  FAST_MOVING: "text-green-600 font-semibold",
  NORMAL: "text-blue-600",
  SLOW_MOVING: "text-yellow-600",
  NO_DATA: "text-gray-400",
};

export default function SecondarySalesDashboard() {
  const [headers, setHeaders] = useState<SecondarySalesHeader[]>([]);
  const [sellThrough, setSellThrough] = useState<SellThroughRow[]>([]);
  const [distPerf, setDistPerf] = useState<DistributorPerformanceRow[]>([]);
  const [aiDemand, setAiDemand] = useState<AIInsightResult | null>(null);
  const [aiRisk, setAiRisk] = useState<AIInsightResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [aiLoading, setAiLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"uploads" | "sell-through" | "performance">("uploads");

  useEffect(() => {
    Promise.all([
      secondarySalesApi.list({ limit: 50 }),
      secondarySalesApi.sellThroughReport(),
      secondarySalesApi.distributorPerformance(),
    ]).then(([h, st, dp]) => {
      setHeaders(h);
      setSellThrough(st);
      setDistPerf(dp);
    }).finally(() => setLoading(false));
  }, []);

  const loadAI = async () => {
    setAiLoading(true);
    try {
      const [demand, risk] = await Promise.all([
        secondarySalesApi.aiDemandSignal(),
        secondarySalesApi.aiDistributorRisk(),
      ]);
      setAiDemand(demand);
      setAiRisk(risk);
    } finally {
      setAiLoading(false);
    }
  };

  const handleProcess = async (id: string) => {
    await secondarySalesApi.process(id);
    const updated = await secondarySalesApi.list({ limit: 50 });
    setHeaders(updated);
  };

  const totalValue = headers
    .filter((h) => h.status === "PROCESSED")
    .reduce((s, h) => s + h.total_value, 0);
  const pendingCount = headers.filter((h) => h.status === "PENDING" || h.status === "VALIDATED").length;
  const fastMoving = sellThrough.filter((r) => r.status === "FAST_MOVING").length;
  const atRisk = sellThrough.filter((r) => r.status === "SLOW_MOVING").length;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Secondary Sales</h1>
          <p className="text-sm text-gray-500 mt-1">Distributor sell-through & market visibility</p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/dashboard/secondary-sales/analysis"
            className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Sell-Through Analysis
          </Link>
          <Link
            href="/dashboard/secondary-sales/inventory"
            className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Dist. Inventory
          </Link>
          <Link
            href="/dashboard/secondary-sales/upload"
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            + Upload Data
          </Link>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "Total Sell-Out Value", value: `KES ${totalValue.toLocaleString()}`, color: "text-green-600" },
          { label: "Pending Validation", value: pendingCount, color: "text-yellow-600" },
          { label: "Fast Moving SKUs", value: fastMoving, color: "text-blue-600" },
          { label: "Slow Moving / At Risk", value: atRisk, color: "text-red-600" },
        ].map((k) => (
          <div key={k.label} className="bg-white rounded-lg border p-4">
            <p className="text-xs text-gray-500">{k.label}</p>
            <p className={`text-2xl font-bold mt-1 ${k.color}`}>{k.value}</p>
          </div>
        ))}
      </div>

      {/* AI Panel */}
      <div className="flex gap-2">
        <button
          onClick={loadAI}
          disabled={aiLoading}
          className="px-4 py-2 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
        >
          {aiLoading ? "Analyzing…" : "Run AI Analysis"}
        </button>
      </div>

      {(aiDemand || aiRisk) && (
        <div className="grid grid-cols-2 gap-4">
          {aiDemand && (
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-purple-800 mb-2">{aiDemand.agent}</h3>
              <ul className="space-y-1">
                {aiDemand.insights.map((i, idx) => (
                  <li key={idx} className="text-xs text-purple-700">• {i}</li>
                ))}
              </ul>
            </div>
          )}
          {aiRisk && (
            <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-orange-800 mb-2">{aiRisk.agent}</h3>
              <ul className="space-y-1">
                {aiRisk.insights.map((i, idx) => (
                  <li key={idx} className="text-xs text-orange-700">• {i}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Tabs */}
      <div className="border-b flex gap-4">
        {(["uploads", "sell-through", "performance"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`pb-2 text-sm font-medium capitalize border-b-2 -mb-px transition-colors ${
              activeTab === tab ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {tab.replace("-", " ")}
          </button>
        ))}
      </div>

      {/* Tab: Uploads */}
      {activeTab === "uploads" && (
        <div className="bg-white rounded-lg border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
              <tr>
                <th className="px-4 py-3 text-left">Reference</th>
                <th className="px-4 py-3 text-left">Distributor</th>
                <th className="px-4 py-3 text-left">Period</th>
                <th className="px-4 py-3 text-left">Source</th>
                <th className="px-4 py-3 text-right">Lines</th>
                <th className="px-4 py-3 text-right">Value</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-left">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading ? (
                <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>
              ) : headers.length === 0 ? (
                <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">No secondary sales uploads yet</td></tr>
              ) : (
                headers.map((h) => (
                  <tr key={h.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-xs font-semibold">
                      <Link href={`/dashboard/secondary-sales/${h.id}`} className="text-blue-600 hover:underline">
                        {h.reference_no}
                      </Link>
                    </td>
                    <td className="px-4 py-3">{h.distributor_name || "—"}</td>
                    <td className="px-4 py-3 text-xs text-gray-600">{h.period_from} – {h.period_to}</td>
                    <td className="px-4 py-3 text-xs text-gray-500">{h.upload_source}</td>
                    <td className="px-4 py-3 text-right">{h.total_lines}</td>
                    <td className="px-4 py-3 text-right font-medium">{h.total_value.toLocaleString()}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[h.status]}`}>
                        {h.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {h.status === "VALIDATED" && (
                        <button
                          onClick={() => handleProcess(h.id)}
                          className="text-green-600 hover:underline text-xs"
                        >
                          Process
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Tab: Sell-Through */}
      {activeTab === "sell-through" && (
        <div className="bg-white rounded-lg border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
              <tr>
                <th className="px-4 py-3 text-left">Distributor</th>
                <th className="px-4 py-3 text-left">Product</th>
                <th className="px-4 py-3 text-right">Sell-Out Qty</th>
                <th className="px-4 py-3 text-right">Stock</th>
                <th className="px-4 py-3 text-right">Days of Stock</th>
                <th className="px-4 py-3 text-right">Sell-Through %</th>
                <th className="px-4 py-3 text-left">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {sellThrough.length === 0 ? (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No sell-through data. Process uploads first.</td></tr>
              ) : (
                sellThrough.map((r, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-4 py-3">{r.distributor_name}</td>
                    <td className="px-4 py-3">
                      <span className="font-mono text-xs text-gray-500 mr-1">{r.product_sku}</span>
                      {r.product_name}
                    </td>
                    <td className="px-4 py-3 text-right">{Number(r.sell_out_qty).toLocaleString()}</td>
                    <td className="px-4 py-3 text-right">{r.stock_at_distributor != null ? Number(r.stock_at_distributor).toLocaleString() : "—"}</td>
                    <td className="px-4 py-3 text-right">{r.days_of_stock != null ? Number(r.days_of_stock).toFixed(0) : "—"}</td>
                    <td className="px-4 py-3 text-right font-semibold">{Number(r.sell_through_rate).toFixed(1)}%</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs ${ST_COLORS[r.status]}`}>{r.status.replace("_", " ")}</span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Tab: Performance */}
      {activeTab === "performance" && (
        <div className="bg-white rounded-lg border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
              <tr>
                <th className="px-4 py-3 text-left">Distributor</th>
                <th className="px-4 py-3 text-right">Total Sell-Out Qty</th>
                <th className="px-4 py-3 text-right">Total Value</th>
                <th className="px-4 py-3 text-right">Lines</th>
                <th className="px-4 py-3 text-left">Period</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {distPerf.length === 0 ? (
                <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">No performance data. Process uploads first.</td></tr>
              ) : (
                distPerf.map((r, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium">{r.distributor_name}</td>
                    <td className="px-4 py-3 text-right">{Number(r.total_sell_out_qty).toLocaleString()}</td>
                    <td className="px-4 py-3 text-right font-semibold">KES {Number(r.total_sell_out_value).toLocaleString()}</td>
                    <td className="px-4 py-3 text-right">{r.line_count}</td>
                    <td className="px-4 py-3 text-xs text-gray-500">{r.period}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
