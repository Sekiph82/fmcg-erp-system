"use client";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { promoApi, EvaluateOrderResult, fmtCurrency } from "@/lib/promotions";

interface LineForm {
  item_id: string;
  item_category: string;
  item_brand: string;
  qty: string;
  unit_price: string;
}

const BLANK_LINE: LineForm = {
  item_id: "", item_category: "", item_brand: "", qty: "1", unit_price: "0",
};

export default function SimulatePage() {
  const [channel, setChannel] = useState("");
  const [region, setRegion] = useState("");
  const [lines, setLines] = useState<LineForm[]>([{ ...BLANK_LINE }]);
  const [result, setResult] = useState<EvaluateOrderResult | null>(null);

  const evaluate = useMutation({
    mutationFn: () => promoApi.evaluateOrder({
      sales_order_id: "00000000-0000-0000-0000-000000000000",
      channel: channel || undefined,
      region: region || undefined,
      order_lines: lines.filter((l) => l.item_id || l.item_category).map((l) => ({
        item_id: l.item_id || "00000000-0000-0000-0000-000000000001",
        item_category: l.item_category || undefined,
        item_brand: l.item_brand || undefined,
        qty: Number(l.qty),
        unit_price: Number(l.unit_price),
        line_total: Number(l.qty) * Number(l.unit_price),
      })),
    }),
    onSuccess: (data) => setResult(data),
  });

  const setLine = (i: number, k: keyof LineForm, v: string) =>
    setLines(lines.map((l, idx) => idx === i ? { ...l, [k]: v } : l));

  const lineTotal = lines.reduce((s, l) => s + Number(l.qty) * Number(l.unit_price), 0);

  return (
    <div className="p-6 space-y-5 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Promotion Simulator</h1>
        <p className="text-sm text-gray-500">Test which promotions would apply to a sample order without creating a real order.</p>
      </div>

      <div className="liquid-glass p-5 space-y-4">
        <h2 className="text-sm font-semibold text-gray-700">Order Context</h2>
        <div className="grid grid-cols-2 gap-4">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Channel</label>
            <input type="text" value={channel} onChange={(e) => setChannel(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" placeholder="e.g. modern-trade" />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Region</label>
            <input type="text" value={region} onChange={(e) => setRegion(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" placeholder="e.g. Nairobi" />
          </div>
        </div>
      </div>

      <div className="liquid-glass p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-700">Order Lines</h2>
          <button onClick={() => setLines([...lines, { ...BLANK_LINE }])} className="glow-button-secondary text-xs !py-1">+ Add Line</button>
        </div>
        {lines.map((line, i) => (
          <div key={i} className="grid grid-cols-5 gap-2 items-end">
            <div className="flex flex-col gap-1 col-span-2">
              <label className="text-xs text-gray-500">Category</label>
              <input type="text" value={line.item_category} onChange={(e) => setLine(i, "item_category", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm" placeholder="e.g. Detergent" />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Brand</label>
              <input type="text" value={line.item_brand} onChange={(e) => setLine(i, "item_brand", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Qty</label>
              <input type="number" value={line.qty} onChange={(e) => setLine(i, "qty", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm" min="1" />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Unit Price</label>
              <input type="number" value={line.unit_price} onChange={(e) => setLine(i, "unit_price", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm" min="0" />
            </div>
          </div>
        ))}
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-400">Order Total: <span className="font-bold text-indigo-300">{fmtCurrency(lineTotal)}</span></span>
          <button onClick={() => evaluate.mutate()} disabled={evaluate.isPending}
            className="glow-button">
            {evaluate.isPending ? "Evaluating…" : "Simulate Promotions"}
          </button>
        </div>
      </div>

      {result && (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div className="glow-card p-4 text-center">
              <p className="text-xs text-gray-500">Applied Promos</p>
              <p className="text-2xl font-bold text-green-400">{result.applied_promos.length}</p>
            </div>
            <div className="glow-card p-4 text-center">
              <p className="text-xs text-gray-500">Total Discount</p>
              <p className="text-xl font-bold text-orange-400">{fmtCurrency(result.total_discount)}</p>
            </div>
            <div className="glow-card p-4 text-center">
              <p className="text-xs text-gray-500">Free Goods Value</p>
              <p className="text-xl font-bold text-purple-400">{fmtCurrency(result.total_free_goods_value)}</p>
            </div>
          </div>

          {result.applied_promos.length > 0 && (
            <div className="liquid-glass p-5 space-y-3">
              <h2 className="text-sm font-semibold text-gray-700 text-green-400">✓ Applied Promotions</h2>
              {result.applied_promos.map((p) => (
                <div key={p.scheme_id} className="glass-panel rounded-xl border border-green-900/30 p-3 space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-green-400">{p.scheme_code}</span>
                    <span className="font-medium text-gray-200 text-sm">{p.scheme_name}</span>
                    <span className="text-xs text-gray-400">#{p.stack_sequence}</span>
                  </div>
                  <p className="text-xs text-green-400">Benefit: {fmtCurrency(p.calculated_benefit)}</p>
                  {p.line_impacts.map((impact, j) => (
                    <p key={j} className="text-xs text-gray-400">{impact.notes}</p>
                  ))}
                </div>
              ))}
            </div>
          )}

          {result.skipped_promos.length > 0 && (
            <div className="liquid-glass p-5 space-y-2">
              <h2 className="text-sm font-semibold text-gray-700">Skipped Promotions</h2>
              {result.skipped_promos.map((s, i) => (
                <div key={i} className="flex items-start gap-2 text-xs">
                  <span className="font-mono text-gray-500">{s.scheme_code ?? s.scheme_id.slice(0, 8)}</span>
                  <span className="text-gray-400">{s.reason}</span>
                  {s.next_threshold_hint && (
                    <span className="text-yellow-400 ml-auto">{s.next_threshold_hint}</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
