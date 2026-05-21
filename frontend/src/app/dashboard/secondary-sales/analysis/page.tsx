"use client";

import { useState, useEffect } from "react";
import {
  secondarySalesApi, SellThroughRow, ProductSellThroughRow, AIInsightResult,
} from "@/lib/secondarySales";

const ST_BADGE: Record<string, string> = {
  FAST_MOVING: "bg-green-100 text-green-700",
  NORMAL: "bg-blue-100 text-blue-700",
  SLOW_MOVING: "bg-yellow-100 text-yellow-700",
  NO_DATA: "bg-gray-100 text-gray-400",
};

export default function SellThroughAnalysisPage() {
  const [sellThrough, setSellThrough] = useState<SellThroughRow[]>([]);
  const [products, setProducts] = useState<ProductSellThroughRow[]>([]);
  const [aiPromo, setAiPromo] = useState<AIInsightResult | null>(null);
  const [tab, setTab] = useState<"sell-through" | "products" | "promotion">("sell-through");
  const [loading, setLoading] = useState(true);
  const [promoStart, setPromoStart] = useState("");
  const [promoEnd, setPromoEnd] = useState("");
  const [promoLoading, setPromoLoading] = useState(false);
  const [filterStatus, setFilterStatus] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  useEffect(() => {
    Promise.all([
      secondarySalesApi.sellThroughReport({
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      }),
      secondarySalesApi.productPerformance({
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      }),
    ]).then(([st, pp]) => {
      setSellThrough(st);
      setProducts(pp);
    }).finally(() => setLoading(false));
  }, [dateFrom, dateTo]);

  const runPromoAnalysis = async () => {
    if (!promoStart || !promoEnd) return;
    setPromoLoading(true);
    try {
      const res = await secondarySalesApi.aiPromotionImpact({ promo_start: promoStart, promo_end: promoEnd });
      setAiPromo(res);
    } finally {
      setPromoLoading(false);
    }
  };

  const filtered = filterStatus ? sellThrough.filter((r) => r.status === filterStatus) : sellThrough;

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Sell-Through Analysis</h1>
        <p className="text-sm text-gray-500 mt-1">Product velocity and market pull signals</p>
      </div>

      {/* Date filters */}
      <div className="flex gap-3 flex-wrap items-end">
        <div>
          <label className="block text-xs text-gray-500 mb-1">From</label>
          <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="border rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">To</label>
          <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="border rounded-lg px-3 py-2 text-sm" />
        </div>
      </div>

      {/* Summary cards */}
      {!loading && (
        <div className="grid grid-cols-4 gap-3">
          {[
            { label: "Total SKUs", value: sellThrough.length },
            { label: "Fast Moving", value: sellThrough.filter((r) => r.status === "FAST_MOVING").length, color: "text-green-600" },
            { label: "Slow Moving", value: sellThrough.filter((r) => r.status === "SLOW_MOVING").length, color: "text-yellow-600" },
            { label: "At Risk (>60d stock)", value: sellThrough.filter((r) => r.days_of_stock != null && Number(r.days_of_stock) > 60).length, color: "text-red-600" },
          ].map((k) => (
            <div key={k.label} className="bg-white rounded-lg border p-3">
              <p className="text-xs text-gray-500">{k.label}</p>
              <p className={`text-2xl font-bold mt-1 ${k.color || "text-gray-800"}`}>{k.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="border-b flex gap-4">
        {(["sell-through", "products", "promotion"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`pb-2 text-sm font-medium capitalize border-b-2 -mb-px ${tab === t ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}
          >
            {t.replace("-", " ")}
          </button>
        ))}
      </div>

      {/* Sell-Through tab */}
      {tab === "sell-through" && (
        <>
          <div className="flex gap-2">
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="border rounded-lg px-3 py-2 text-sm"
            >
              <option value="">All Statuses</option>
              {["FAST_MOVING", "NORMAL", "SLOW_MOVING", "NO_DATA"].map((s) => (
                <option key={s} value={s}>{s.replace("_", " ")}</option>
              ))}
            </select>
          </div>
          <div className="bg-white rounded-lg border overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
                <tr>
                  <th className="px-4 py-3 text-left">Distributor</th>
                  <th className="px-4 py-3 text-left">SKU</th>
                  <th className="px-4 py-3 text-left">Product</th>
                  <th className="px-4 py-3 text-right">Sell-Out</th>
                  <th className="px-4 py-3 text-right">Stock</th>
                  <th className="px-4 py-3 text-right">Days</th>
                  <th className="px-4 py-3 text-right">ST %</th>
                  <th className="px-4 py-3 text-left">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {loading ? (
                  <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>
                ) : filtered.length === 0 ? (
                  <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">No data found</td></tr>
                ) : (
                  filtered.map((r, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-4 py-2 text-sm">{r.distributor_name}</td>
                      <td className="px-4 py-2 font-mono text-xs">{r.product_sku}</td>
                      <td className="px-4 py-2">{r.product_name}</td>
                      <td className="px-4 py-2 text-right">{Number(r.sell_out_qty).toLocaleString()}</td>
                      <td className="px-4 py-2 text-right">{r.stock_at_distributor != null ? Number(r.stock_at_distributor).toLocaleString() : "—"}</td>
                      <td className="px-4 py-2 text-right">{r.days_of_stock != null ? Number(r.days_of_stock).toFixed(0) : "—"}</td>
                      <td className="px-4 py-2 text-right font-bold">{Number(r.sell_through_rate).toFixed(1)}%</td>
                      <td className="px-4 py-2">
                        <span className={`px-2 py-0.5 rounded-full text-xs ${ST_BADGE[r.status]}`}>
                          {r.status.replace("_", " ")}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* Products tab */}
      {tab === "products" && (
        <div className="bg-white rounded-lg border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
              <tr>
                <th className="px-4 py-3 text-left">Rank</th>
                <th className="px-4 py-3 text-left">SKU</th>
                <th className="px-4 py-3 text-left">Product</th>
                <th className="px-4 py-3 text-right">Total Qty Sold</th>
                <th className="px-4 py-3 text-right">Total Value</th>
                <th className="px-4 py-3 text-right">Distributor Coverage</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {products.length === 0 ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No product data yet</td></tr>
              ) : (
                products.map((p, i) => (
                  <tr key={p.product_id} className="hover:bg-gray-50">
                    <td className="px-4 py-2 text-gray-400 text-sm">#{i + 1}</td>
                    <td className="px-4 py-2 font-mono text-xs">{p.product_sku}</td>
                    <td className="px-4 py-2 font-medium">{p.product_name}</td>
                    <td className="px-4 py-2 text-right">{Number(p.total_qty_sold).toLocaleString()}</td>
                    <td className="px-4 py-2 text-right">KES {Number(p.total_value).toLocaleString()}</td>
                    <td className="px-4 py-2 text-right">{p.distributor_count}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Promotion Impact tab */}
      {tab === "promotion" && (
        <div className="space-y-4">
          <div className="bg-white rounded-lg border p-5">
            <h2 className="font-semibold mb-4">Promotion Impact Analysis</h2>
            <div className="flex gap-4 items-end">
              <div>
                <label className="block text-xs text-gray-500 mb-1">Promo Start</label>
                <input type="date" value={promoStart} onChange={(e) => setPromoStart(e.target.value)} className="border rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Promo End</label>
                <input type="date" value={promoEnd} onChange={(e) => setPromoEnd(e.target.value)} className="border rounded-lg px-3 py-2 text-sm" />
              </div>
              <button
                onClick={runPromoAnalysis}
                disabled={promoLoading || !promoStart || !promoEnd}
                className="px-4 py-2 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
              >
                {promoLoading ? "Analyzing…" : "Analyze"}
              </button>
            </div>
          </div>

          {aiPromo && (
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-5">
              <h3 className="font-semibold text-purple-800 mb-3">{aiPromo.agent}</h3>
              <ul className="space-y-2">
                {aiPromo.insights.map((i, idx) => (
                  <li key={idx} className="text-sm text-purple-700">• {i}</li>
                ))}
              </ul>
              {aiPromo.details && aiPromo.details.length > 0 && (
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full text-xs border-t pt-3">
                    <thead><tr className="text-gray-500">
                      <th className="text-left py-1">Product</th>
                      <th className="text-right py-1">Uplift %</th>
                      <th className="text-left py-1">Result</th>
                    </tr></thead>
                    <tbody>
                      {aiPromo.details.map((d, i) => (
                        <tr key={i} className="border-t">
                          <td className="py-1">{d.product}</td>
                          <td className={`py-1 text-right font-semibold ${d.uplift_pct > 0 ? "text-green-600" : "text-red-600"}`}>{d.uplift_pct > 0 ? "+" : ""}{d.uplift_pct}%</td>
                          <td className="py-1">{d.result}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
