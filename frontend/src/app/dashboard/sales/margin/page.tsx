"use client";
import { useEffect, useState } from "react";
import { salesApi, MarginSummaryRow, OrderMarginSummary } from "@/lib/sales";

function fmt(n?: number | null, dp = 2) {
  if (n == null) return "—";
  return n.toLocaleString(undefined, { minimumFractionDigits: dp, maximumFractionDigits: dp });
}

function MarginBadge({ pct }: { pct?: number | null }) {
  if (pct == null) return <span className="text-gray-400 text-xs">No cost data</span>;
  const color = pct >= 30 ? "bg-green-100 text-green-700" : pct >= 15 ? "bg-amber-100 text-amber-700" : "bg-red-100 text-red-600";
  return <span className={`text-xs rounded-full px-2 py-0.5 font-semibold ${color}`}>{pct.toFixed(1)}%</span>;
}

export default function SalesMarginPage() {
  const [rows, setRows] = useState<MarginSummaryRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<OrderMarginSummary | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    salesApi.getMarginSummary(100).then(setRows).finally(() => setLoading(false));
  }, []);

  const openDetail = async (soId: string) => {
    setDetailLoading(true);
    setSelected(null);
    try {
      const detail = await salesApi.getOrderMargin(soId);
      setSelected(detail);
    } finally {
      setDetailLoading(false);
    }
  };

  const rowsWithMargin = rows.filter(r => r.gross_margin_pct != null);
  const avgMargin = rowsWithMargin.length > 0
    ? rowsWithMargin.reduce((sum, r) => sum + (r.gross_margin_pct ?? 0), 0) / rowsWithMargin.length
    : null;
  const totalRevenue = rows.reduce((sum, r) => sum + r.total_revenue, 0);
  const totalCost = rows.reduce((sum, r) => sum + (r.total_cost ?? 0), 0);

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Sales Margin Analysis</h1>
        <p className="text-xs text-gray-500 mt-0.5">
          Gross margin per order. Set cost_price on SO lines to see margin data.
        </p>
      </div>

      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "Orders Analyzed", value: rows.length, color: "text-blue-600" },
          { label: "Avg Gross Margin", value: avgMargin != null ? `${avgMargin.toFixed(1)}%` : "—", color: avgMargin != null && avgMargin >= 20 ? "text-green-600" : "text-amber-600" },
          { label: "Total Revenue", value: `${fmt(totalRevenue, 0)}`, color: "text-gray-800" },
          { label: "With Cost Data", value: rowsWithMargin.length, color: "text-purple-600" },
        ].map(s => (
          <div key={s.label} className="bg-white border rounded-lg p-4 shadow-sm">
            <p className="text-xs text-gray-500">{s.label}</p>
            <p className={`text-xl font-bold mt-1 ${s.color}`}>{loading ? "—" : s.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Order list */}
        <div className="lg:col-span-2">
          {loading ? (
            <p className="text-sm text-gray-500">Loading…</p>
          ) : rows.length === 0 ? (
            <div className="bg-white border rounded-lg p-10 text-center text-gray-400">
              <p className="text-sm">No confirmed orders found.</p>
            </div>
          ) : (
            <div className="bg-white border rounded-lg shadow-sm overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    {["Order No.", "Customer", "Date", "Revenue", "Cost", "Gross Margin", ""].map(h => (
                      <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {rows.map(r => (
                    <tr key={r.so_id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-mono text-xs text-gray-700">{r.order_no}</td>
                      <td className="px-4 py-3 text-xs text-gray-700">{r.customer_name ?? "—"}</td>
                      <td className="px-4 py-3 text-xs text-gray-500">{r.order_date ?? "—"}</td>
                      <td className="px-4 py-3 text-xs text-right font-medium">{fmt(r.total_revenue)}</td>
                      <td className="px-4 py-3 text-xs text-right text-gray-600">{fmt(r.total_cost)}</td>
                      <td className="px-4 py-3"><MarginBadge pct={r.gross_margin_pct} /></td>
                      <td className="px-4 py-3">
                        <button onClick={() => openDetail(r.so_id)} className="text-xs text-blue-600 hover:underline">
                          Details
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Detail Panel */}
        <div className="bg-white border rounded-lg p-5 h-fit">
          {detailLoading ? (
            <p className="text-sm text-gray-500">Loading…</p>
          ) : selected ? (
            <div className="space-y-4">
              <div>
                <h3 className="text-sm font-semibold text-gray-800">{selected.order_no}</h3>
                <p className="text-xs text-gray-500">{selected.customer_name}</p>
              </div>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: "Revenue", value: fmt(selected.total_revenue), color: "text-gray-800" },
                  { label: "Cost", value: fmt(selected.total_cost), color: "text-gray-600" },
                  { label: "Gross Profit", value: fmt(selected.gross_profit), color: "text-green-700" },
                  { label: "Gross Margin", value: selected.gross_margin_pct != null ? `${selected.gross_margin_pct.toFixed(1)}%` : "—", color: (selected.gross_margin_pct ?? 0) >= 20 ? "text-green-700" : "text-red-600" },
                ].map(s => (
                  <div key={s.label} className="bg-gray-50 rounded p-2">
                    <p className="text-xs text-gray-500">{s.label}</p>
                    <p className={`text-sm font-bold ${s.color}`}>{s.value}</p>
                  </div>
                ))}
              </div>
              {selected.lines_without_cost > 0 && (
                <p className="text-xs text-amber-600 bg-amber-50 rounded p-2">
                  {selected.lines_without_cost} line(s) missing cost price.
                </p>
              )}
              <div className="border-t pt-3">
                <p className="text-xs font-semibold text-gray-600 mb-2">Line Breakdown</p>
                <div className="space-y-2">
                  {selected.lines.map(l => (
                    <div key={l.line_no} className="text-xs border-b pb-1">
                      <div className="flex justify-between">
                        <span className="font-medium text-gray-700 truncate max-w-32">{l.product_name ?? l.product_id.slice(0, 8)}</span>
                        <MarginBadge pct={l.gross_margin_pct} />
                      </div>
                      <div className="flex justify-between text-gray-500 mt-0.5">
                        <span>Price: {fmt(l.net_price, 4)}</span>
                        <span>Cost: {fmt(l.cost_price, 4)}</span>
                      </div>
                      <div className="text-gray-500">Rev: {fmt(l.line_revenue)} · Cost: {fmt(l.line_cost)}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-400">
              <p className="text-2xl mb-2">📊</p>
              <p className="text-sm">Click an order to view margin breakdown.</p>
            </div>
          )}
        </div>
      </div>

      <div className="bg-amber-50 border border-amber-100 rounded-lg px-4 py-3">
        <p className="text-xs text-amber-700 font-medium mb-1">How to get margin data</p>
        <p className="text-xs text-amber-600">
          Set <code className="bg-amber-100 px-1 rounded">cost_price</code> on each SO line when creating orders.
          This field represents the unit cost (COGS) for the product on that line.
          Gross margin = (net_price - cost_price) / net_price × 100.
        </p>
      </div>
    </div>
  );
}
