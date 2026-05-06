"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { inventoryApi, ValuationRow, AgingRow } from "@/lib/inventory";

function fmtKES(n?: number | null) {
  if (n == null) return "—";
  return `KES ${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtQty(n?: number | null) {
  if (n == null) return "—";
  return n.toLocaleString(undefined, { maximumFractionDigits: 3 });
}

const BUCKET_COLOR: Record<string, string> = {
  "0-30":   "bg-green-100 text-green-700",
  "31-60":  "bg-yellow-100 text-yellow-700",
  "61-90":  "bg-orange-100 text-orange-700",
  "91-180": "bg-red-100 text-red-700",
  "180+":   "bg-red-200 text-red-800",
};

export default function ValuationPage() {
  const [tab, setTab] = useState<"valuation" | "aging">("valuation");

  const { data: valuation, isLoading: valLoading } = useQuery({
    queryKey: ["inventory-valuation"],
    queryFn: () => inventoryApi.valuation(),
    enabled: tab === "valuation",
  });

  const { data: aging = [], isLoading: agingLoading } = useQuery({
    queryKey: ["inventory-aging"],
    queryFn: () => inventoryApi.aging(),
    enabled: tab === "aging",
  });

  // Aging bucket summary
  const buckets = ["0-30", "31-60", "61-90", "91-180", "180+"];
  const bucketTotals = buckets.map((b) => ({
    bucket: b,
    value: aging.filter((r) => r.aging_bucket === b).reduce((s, r) => s + r.total_value, 0),
    count: aging.filter((r) => r.aging_bucket === b).length,
  }));

  const rows = valuation?.rows ?? [];
  const fifoTotal = valuation?.total_value ?? 0;
  const stdTotal = rows.reduce((s, r) => s + (r.std_total_value ?? 0), 0);
  const agingTotal = aging.reduce((s, r) => s + r.total_value, 0);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Inventory Valuation</h1>
        <p className="text-sm text-gray-500 mt-1">FIFO / Weighted Average / Standard cost · Aging analysis</p>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-lg border p-4">
          <p className="text-xs text-gray-500 mb-1">FIFO Total Value</p>
          <p className="text-xl font-bold text-indigo-700">{fmtKES(fifoTotal)}</p>
          <p className="text-xs text-gray-400 mt-1">{valuation?.item_count ?? 0} stock lines</p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-xs text-gray-500 mb-1">Standard Cost Value</p>
          <p className="text-xl font-bold text-blue-700">{fmtKES(stdTotal)}</p>
          <p className={`text-xs mt-1 font-medium ${stdTotal > fifoTotal ? "text-red-500" : "text-emerald-500"}`}>
            {fifoTotal > 0 ? `${((stdTotal - fifoTotal) / fifoTotal * 100).toFixed(1)}% vs FIFO` : "—"}
          </p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-xs text-gray-500 mb-1">Aging Inventory Value</p>
          <p className="text-xl font-bold text-amber-700">{fmtKES(agingTotal)}</p>
          <p className="text-xs text-gray-400 mt-1">{aging.length} cost layers</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        {([
          { key: "valuation", label: "Valuation Report" },
          { key: "aging",     label: "Inventory Aging" },
        ] as const).map((t) => (
          <button
            key={t.key}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${tab === t.key ? "border-indigo-600 text-indigo-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* VALUATION tab */}
      {tab === "valuation" && (
        <div className="bg-white rounded-lg border overflow-x-auto">
          <div className="px-5 py-3 border-b font-semibold text-gray-800">
            Stock Valuation — FIFO / WAC / Standard ({rows.length} lines)
          </div>
          {valLoading ? (
            <p className="px-5 py-8 text-center text-gray-400">Loading…</p>
          ) : (
            <table className="w-full text-sm min-w-[900px]">
              <thead>
                <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                  <th className="px-4 py-2 text-left">Item</th>
                  <th className="px-4 py-2 text-left">Warehouse</th>
                  <th className="px-4 py-2 text-left">Lot</th>
                  <th className="px-4 py-2 text-right">Qty on Hand</th>
                  <th className="px-4 py-2 text-right">FIFO Unit</th>
                  <th className="px-4 py-2 text-right">FIFO Value</th>
                  <th className="px-4 py-2 text-right">Std Unit</th>
                  <th className="px-4 py-2 text-right">Std Value</th>
                  <th className="px-4 py-2 text-right">Std vs FIFO</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {rows.map((r, i) => {
                  const delta = (r.std_total_value != null && r.fifo_total_value != null)
                    ? r.std_total_value - r.fifo_total_value : null;
                  return (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-4 py-2.5">
                        <span className="font-medium text-gray-800">{r.item_name ?? "—"}</span>
                        {r.item_sku && <span className="text-xs text-gray-400 ml-1">({r.item_sku})</span>}
                      </td>
                      <td className="px-4 py-2.5 text-gray-500 text-xs">{r.warehouse_name ?? "—"}</td>
                      <td className="px-4 py-2.5 text-gray-500 text-xs">{r.lot_number ?? "—"}</td>
                      <td className="px-4 py-2.5 text-right font-medium">{fmtQty(r.qty_on_hand)}</td>
                      <td className="px-4 py-2.5 text-right text-gray-600">{fmtKES(r.fifo_unit_cost)}</td>
                      <td className="px-4 py-2.5 text-right text-indigo-700 font-semibold">{fmtKES(r.fifo_total_value)}</td>
                      <td className="px-4 py-2.5 text-right text-gray-600">{fmtKES(r.std_unit_cost)}</td>
                      <td className="px-4 py-2.5 text-right text-blue-700">{fmtKES(r.std_total_value)}</td>
                      <td className={`px-4 py-2.5 text-right text-xs font-medium ${delta == null ? "text-gray-400" : delta > 0 ? "text-amber-600" : delta < 0 ? "text-emerald-600" : "text-gray-500"}`}>
                        {delta != null ? `${delta > 0 ? "+" : ""}${fmtKES(delta)}` : "—"}
                      </td>
                    </tr>
                  );
                })}
                {rows.length === 0 && (
                  <tr><td colSpan={9} className="px-5 py-8 text-center text-gray-400">No active stock — create cost layers via goods receipts</td></tr>
                )}
              </tbody>
              {rows.length > 0 && (
                <tfoot>
                  <tr className="border-t bg-gray-50 font-semibold text-sm">
                    <td colSpan={5} className="px-4 py-2 text-gray-600">Total</td>
                    <td className="px-4 py-2 text-right text-indigo-700">{fmtKES(fifoTotal)}</td>
                    <td />
                    <td className="px-4 py-2 text-right text-blue-700">{fmtKES(stdTotal)}</td>
                    <td className={`px-4 py-2 text-right text-xs font-medium ${stdTotal > fifoTotal ? "text-amber-600" : "text-emerald-600"}`}>
                      {fmtKES(stdTotal - fifoTotal)}
                    </td>
                  </tr>
                </tfoot>
              )}
            </table>
          )}
        </div>
      )}

      {/* AGING tab */}
      {tab === "aging" && (
        <>
          {/* Bucket summary */}
          <div className="grid grid-cols-5 gap-3">
            {bucketTotals.map((b) => (
              <div key={b.bucket} className="bg-white rounded-lg border p-3 text-center">
                <span className={`text-xs font-bold px-2 py-0.5 rounded ${BUCKET_COLOR[b.bucket]}`}>{b.bucket} days</span>
                <p className="text-lg font-bold text-gray-800 mt-2">{fmtKES(b.value)}</p>
                <p className="text-xs text-gray-400">{b.count} layers</p>
              </div>
            ))}
          </div>

          <div className="bg-white rounded-lg border overflow-x-auto">
            <div className="px-5 py-3 border-b font-semibold text-gray-800">
              Aging Detail ({aging.length} cost layers)
            </div>
            {agingLoading ? (
              <p className="px-5 py-8 text-center text-gray-400">Loading…</p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                    <th className="px-4 py-2 text-left">Item</th>
                    <th className="px-4 py-2 text-left">Lot</th>
                    <th className="px-4 py-2 text-left">Receipt Date</th>
                    <th className="px-4 py-2 text-right">Days Held</th>
                    <th className="px-4 py-2 text-left">Bucket</th>
                    <th className="px-4 py-2 text-right">Qty Remaining</th>
                    <th className="px-4 py-2 text-right">Unit Cost</th>
                    <th className="px-4 py-2 text-right">Value</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {aging.map((r, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-4 py-2.5">
                        <span className="font-medium text-gray-800">{r.item_name ?? "—"}</span>
                        {r.item_sku && <span className="text-xs text-gray-400 ml-1">({r.item_sku})</span>}
                      </td>
                      <td className="px-4 py-2.5 text-gray-500 text-xs">{r.lot_number ?? "—"}</td>
                      <td className="px-4 py-2.5 text-gray-500 text-xs">
                        {new Date(r.receipt_date).toLocaleDateString("en-KE", { day: "2-digit", month: "short", year: "numeric" })}
                      </td>
                      <td className="px-4 py-2.5 text-right font-medium text-gray-700">{r.days_held}</td>
                      <td className="px-4 py-2.5">
                        <span className={`text-xs font-bold px-2 py-0.5 rounded ${BUCKET_COLOR[r.aging_bucket] ?? "bg-gray-100 text-gray-600"}`}>
                          {r.aging_bucket}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-right">{fmtQty(r.qty_remaining)}</td>
                      <td className="px-4 py-2.5 text-right text-gray-600">{fmtKES(r.unit_cost)}</td>
                      <td className="px-4 py-2.5 text-right font-semibold text-amber-700">{fmtKES(r.total_value)}</td>
                    </tr>
                  ))}
                  {aging.length === 0 && (
                    <tr><td colSpan={8} className="px-5 py-8 text-center text-gray-400">No cost layers found — receive stock to create layers</td></tr>
                  )}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </div>
  );
}
