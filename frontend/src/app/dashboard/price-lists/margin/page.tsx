"use client";
import { useState } from "react";
import { plApi, MarginCheckResult, MARGIN_STATUS_COLORS } from "@/lib/price_list";

export default function MarginChecker() {
  const [form, setForm] = useState({ product_id: "", proposed_price: "", quantity: "1", currency: "KES" });
  const [result, setResult] = useState<MarginCheckResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [belowMargin, setBelowMargin] = useState<any[]>([]);
  const [loadingBelow, setLoadingBelow] = useState(false);

  const check = async () => {
    setLoading(true);
    try {
      const r = await plApi.checkMargin({
        product_id: form.product_id,
        proposed_price: Number(form.proposed_price),
        quantity: Number(form.quantity),
        currency: form.currency,
      });
      setResult(r);
    } finally {
      setLoading(false);
    }
  };

  const loadBelow = async () => {
    setLoadingBelow(true);
    const data = await plApi.getBelowMargin();
    setBelowMargin(data);
    setLoadingBelow(false);
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Margin Guardrails</h1>
        <p className="text-sm text-gray-500 mt-1">Check proposed prices against product cost for margin compliance</p>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Margin Check */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
          <h2 className="font-semibold text-gray-900">Margin Check</h2>
          <div>
            <label className="text-xs font-medium text-gray-700">Product ID</label>
            <input value={form.product_id} onChange={(e) => setForm({ ...form, product_id: e.target.value })}
              className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="UUID" />
          </div>
          <div className="grid grid-cols-3 gap-2">
            <div>
              <label className="text-xs font-medium text-gray-700">Proposed Price</label>
              <input type="number" value={form.proposed_price} onChange={(e) => setForm({ ...form, proposed_price: e.target.value })}
                className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700">Quantity</label>
              <input type="number" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })}
                className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700">Currency</label>
              <input value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })}
                className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
          </div>
          <button onClick={check} disabled={loading || !form.product_id || !form.proposed_price}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium disabled:opacity-50">
            {loading ? "Checking…" : "Check Margin"}
          </button>

          {result && (
            <div className={`rounded-xl p-4 border ${result.blocked ? "border-red-300 bg-red-50" : result.requires_approval ? "border-yellow-300 bg-yellow-50" : "border-green-300 bg-green-50"}`}>
              <div className="flex items-center gap-2 mb-2">
                <span className={`text-lg font-bold ${MARGIN_STATUS_COLORS[result.margin_status]}`}>
                  {result.margin_status.replace(/_/g, " ")}
                </span>
                {result.blocked && <span className="px-2 py-0.5 bg-red-100 text-red-800 rounded-full text-xs font-bold">BLOCKED</span>}
                {result.requires_approval && !result.blocked && <span className="px-2 py-0.5 bg-yellow-100 text-yellow-800 rounded-full text-xs font-bold">APPROVAL NEEDED</span>}
              </div>
              <p className="text-sm text-gray-700">{result.message}</p>
              <div className="mt-3 grid grid-cols-3 gap-3 text-sm">
                {[
                  ["Proposed", result.proposed_price?.toLocaleString()],
                  ["Cost", result.cost_price?.toLocaleString() ?? "N/A"],
                  ["Margin", result.margin_pct != null ? `${Number(result.margin_pct).toFixed(1)}%` : "N/A"],
                ].map(([k, v]) => (
                  <div key={String(k)} className="text-center">
                    <div className="font-bold text-gray-900">{v}</div>
                    <div className="text-xs text-gray-500">{k}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Legend */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
          <h2 className="font-semibold text-gray-900">Margin Rules</h2>
          <div className="space-y-3">
            {[
              { status: "BELOW_COST", label: "Below Cost — Hard Block", desc: "Price is below product cost. Executive approval required. Cannot proceed.", color: "border-red-300 bg-red-50" },
              { status: "BELOW_MINIMUM", label: "Below 10% Margin — Approval Required", desc: "Price produces less than 10% gross margin. Finance / management approval needed.", color: "border-orange-300 bg-orange-50" },
              { status: "WARNING", label: "10–20% Margin — Warning", desc: "Margin is low but above the minimum floor. Review recommended but not blocked.", color: "border-yellow-300 bg-yellow-50" },
              { status: "OK", label: "20%+ Margin — Acceptable", desc: "Price meets or exceeds the target margin threshold. No action needed.", color: "border-green-300 bg-green-50" },
            ].map((rule) => (
              <div key={rule.status} className={`border rounded-lg p-3 ${rule.color}`}>
                <div className={`font-semibold text-sm ${MARGIN_STATUS_COLORS[rule.status]}`}>{rule.label}</div>
                <div className="text-xs text-gray-600 mt-0.5">{rule.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Below Margin Report */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="font-semibold text-gray-900">Below-Margin Price Lines</h2>
          <button onClick={loadBelow} disabled={loadingBelow} className="px-3 py-1.5 bg-red-600 text-white rounded-lg text-xs font-medium">
            {loadingBelow ? "Loading…" : "Load Report"}
          </button>
        </div>
        {belowMargin.length > 0 ? (
          <table className="w-full text-sm">
            <thead className="bg-red-50 border-b border-red-200">
              <tr>
                {["Product ID", "Base Price", "Cost Price", "Margin %", "Price List"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-red-800 uppercase">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {belowMargin.map((r, i) => (
                <tr key={i} className="hover:bg-red-50/30">
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{r.product_id?.slice(0, 12)}…</td>
                  <td className="px-4 py-3 font-mono">{r.base_price?.toLocaleString()}</td>
                  <td className="px-4 py-3 font-mono text-gray-500">{r.cost_price?.toLocaleString()}</td>
                  <td className="px-4 py-3 font-bold text-red-700">{r.margin_pct}%</td>
                  <td className="px-4 py-3">
                    <a href={`/dashboard/price-lists/${r.header_id}`} className="text-blue-600 hover:underline text-xs">View List</a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="p-6 text-center text-gray-400 text-sm">Click "Load Report" to identify below-margin price lines.</div>
        )}
      </div>
    </div>
  );
}
