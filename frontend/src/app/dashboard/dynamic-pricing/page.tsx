"use client";
import { useEffect, useState } from "react";

interface Dashboard {
  total_competitor_observations: number;
  pending_recommendations: number;
  applied_recommendations: number;
  competitor_undercut_alerts: number;
  competitor_data_by_channel: Record<string, number>;
}

interface CompetitorObs {
  id: string;
  product_name: string;
  our_sku: string | null;
  competitor_name: string;
  price: number;
  currency: string;
  channel: string;
  observed_date: string;
  source: string | null;
  location: string | null;
}

interface Recommendation {
  id: string;
  product_name: string;
  channel: string;
  current_price: number | null;
  recommended_price: number;
  avg_competitor_price: number | null;
  margin_pct: number | null;
  confidence_score: number | null;
  rationale: string | null;
  trigger: string | null;
  status: string;
  created_at: string;
}

interface LogForm {
  product_name: string; our_sku: string; competitor_name: string;
  price: string; channel: string; pack_size: string;
  observed_date: string; source: string; location: string; notes: string;
}

interface GenForm {
  product_name: string; our_sku: string; current_price: string;
  cost_price: string; channel: string;
  floor_margin_pct: string; target_margin_pct: string;
}

const CHANNELS = ["MODERN_TRADE", "DISTRIBUTOR", "EXPORT", "VAN_SALES", "ONLINE", "WHOLESALE"];

const TRIGGER_COLOR: Record<string, string> = {
  COMPETITOR_UNDERCUT: "bg-red-100 text-red-700",
  LOW_MARGIN: "bg-orange-100 text-orange-700",
  HOLD: "bg-gray-100 text-gray-500",
  HIGH_DEMAND: "bg-green-100 text-green-700",
};

const STATUS_COLOR: Record<string, string> = {
  PENDING: "bg-amber-100 text-amber-700",
  APPLIED: "bg-green-100 text-green-700",
  REJECTED: "bg-gray-100 text-gray-500",
  EXPIRED: "bg-red-100 text-red-500",
};

export default function DynamicPricingPage() {
  const [dash, setDash] = useState<Dashboard | null>(null);
  const [recs, setRecs] = useState<Recommendation[]>([]);
  const [obs, setObs] = useState<CompetitorObs[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"recs" | "competitors" | "log" | "generate">("recs");

  const [logForm, setLogForm] = useState<LogForm>({
    product_name: "", our_sku: "", competitor_name: "", price: "",
    channel: "MODERN_TRADE", pack_size: "", observed_date: new Date().toISOString().split("T")[0],
    source: "", location: "", notes: "",
  });
  const [genForm, setGenForm] = useState<GenForm>({
    product_name: "", our_sku: "", current_price: "", cost_price: "",
    channel: "MODERN_TRADE", floor_margin_pct: "20", target_margin_pct: "35",
  });
  const [saving, setSaving] = useState(false);
  const [genResult, setGenResult] = useState<Recommendation | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const [d, r, o] = await Promise.all([
        fetch("/api/v1/dynamic-pricing/dashboard").then((x) => x.json()),
        fetch("/api/v1/dynamic-pricing/recommendations?limit=30").then((x) => x.json()),
        fetch("/api/v1/dynamic-pricing/competitor-prices?limit=50").then((x) => x.json()),
      ]);
      setDash(d); setRecs(r); setObs(o);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const logPrice = async () => {
    setSaving(true); setError(null);
    try {
      const r = await fetch("/api/v1/dynamic-pricing/competitor-prices", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          product_name: logForm.product_name, our_sku: logForm.our_sku || undefined,
          competitor_name: logForm.competitor_name, price: Number(logForm.price),
          channel: logForm.channel, pack_size: logForm.pack_size || undefined,
          observed_date: logForm.observed_date, source: logForm.source || undefined,
          location: logForm.location || undefined, notes: logForm.notes || undefined,
        }),
      });
      if (!r.ok) throw new Error(await r.text());
      setTab("competitors"); load();
    } catch (e) { setError(String(e)); }
    setSaving(false);
  };

  const generate = async () => {
    setSaving(true); setError(null); setGenResult(null);
    try {
      const r = await fetch("/api/v1/dynamic-pricing/recommendations/generate", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          product_name: genForm.product_name, our_sku: genForm.our_sku || undefined,
          current_price: Number(genForm.current_price),
          cost_price: genForm.cost_price ? Number(genForm.cost_price) : undefined,
          channel: genForm.channel,
          floor_margin_pct: Number(genForm.floor_margin_pct),
          target_margin_pct: Number(genForm.target_margin_pct),
        }),
      });
      if (!r.ok) throw new Error(await r.text());
      setGenResult(await r.json());
      load();
    } catch (e) { setError(String(e)); }
    setSaving(false);
  };

  const applyRec = async (id: string) => {
    await fetch(`/api/v1/dynamic-pricing/recommendations/${id}/apply?applied_by=PricingManager`, { method: "POST" });
    load();
  };

  const rejectRec = async (id: string) => {
    await fetch(`/api/v1/dynamic-pricing/recommendations/${id}/reject`, { method: "POST" });
    load();
  };

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dynamic / AI Pricing Engine</h1>
        <p className="text-sm text-gray-500 mt-0.5">Competitor tracking, margin protection, and AI price recommendations</p>
      </div>

      {error && <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">{error}</div>}

      {/* KPI strip */}
      {dash && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[
            { label: "Competitor Observations", value: dash.total_competitor_observations, color: "text-gray-800" },
            { label: "Pending Recommendations", value: dash.pending_recommendations, color: "text-amber-600" },
            { label: "Applied", value: dash.applied_recommendations, color: "text-green-600" },
            { label: "Undercut Alerts", value: dash.competitor_undercut_alerts, color: "text-red-600" },
          ].map((k) => (
            <div key={k.label} className={`bg-white border rounded-lg p-4 shadow-sm ${k.label === "Undercut Alerts" && k.value > 0 ? "border-red-300 bg-red-50" : ""}`}>
              <p className="text-xs text-gray-500">{k.label}</p>
              <p className={`text-2xl font-bold mt-1 ${k.color}`}>{k.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        {([["recs", "Price Recommendations"], ["competitors", "Competitor Data"], ["log", "Log Price"], ["generate", "Generate Recommendation"]] as const).map(([t, label]) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${tab === t ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
            {label}
          </button>
        ))}
      </div>

      {/* Recommendations tab */}
      {tab === "recs" && (
        <div className="space-y-3">
          {loading && <p className="text-gray-400 text-sm">Loading…</p>}
          {recs.length === 0 && !loading && (
            <div className="bg-gray-50 border rounded-lg p-6 text-center text-sm text-gray-400">
              No recommendations yet. Use &quot;Generate Recommendation&quot; to run the pricing engine.
            </div>
          )}
          {recs.map((r) => (
            <div key={r.id} className="bg-white border rounded-lg p-4 shadow-sm space-y-2">
              <div className="flex items-start justify-between gap-3 flex-wrap">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="font-semibold text-gray-900 text-sm">{r.product_name}</p>
                    <span className="text-xs text-gray-400">{r.channel.replace(/_/g, " ")}</span>
                    {r.trigger && (
                      <span className={`text-xs rounded-full px-2 py-0.5 font-medium ${TRIGGER_COLOR[r.trigger] ?? "bg-gray-100 text-gray-500"}`}>
                        {r.trigger.replace(/_/g, " ")}
                      </span>
                    )}
                    <span className={`text-xs rounded-full px-2 py-0.5 ${STATUS_COLOR[r.status] ?? "bg-gray-100"}`}>{r.status}</span>
                  </div>
                  <div className="flex gap-4 mt-1 text-xs text-gray-500 flex-wrap">
                    {r.current_price !== null && <span>Current: KES {r.current_price.toLocaleString()}</span>}
                    <span className="font-semibold text-blue-600">Recommended: KES {r.recommended_price.toLocaleString()}</span>
                    {r.avg_competitor_price !== null && <span>Competitor avg: KES {r.avg_competitor_price.toLocaleString()}</span>}
                    {r.margin_pct !== null && <span>Margin: {r.margin_pct.toFixed(1)}%</span>}
                    {r.confidence_score !== null && <span>Confidence: {r.confidence_score}%</span>}
                  </div>
                  {r.rationale && <p className="text-xs text-gray-500 mt-1 leading-relaxed">{r.rationale}</p>}
                </div>
                {r.status === "PENDING" && (
                  <div className="flex gap-2 shrink-0">
                    <button onClick={() => applyRec(r.id)}
                      className="text-xs bg-green-600 hover:bg-green-700 text-white px-3 py-1.5 rounded">Apply</button>
                    <button onClick={() => rejectRec(r.id)}
                      className="text-xs border border-gray-300 text-gray-600 px-3 py-1.5 rounded hover:bg-gray-50">Reject</button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Competitor data tab */}
      {tab === "competitors" && (
        <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b bg-gray-50">
            <h2 className="text-sm font-semibold text-gray-700">Recent Competitor Observations ({obs.length})</h2>
          </div>
          {obs.length === 0 ? (
            <div className="p-6 text-sm text-gray-400 text-center">No observations yet. Use &quot;Log Price&quot; to record competitor prices.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-xs text-gray-500">
                  <tr>
                    <th className="text-left px-4 py-2">Product</th>
                    <th className="text-left px-4 py-2">Competitor</th>
                    <th className="text-left px-4 py-2">Price</th>
                    <th className="text-left px-4 py-2">Channel</th>
                    <th className="text-left px-4 py-2">Date</th>
                    <th className="text-left px-4 py-2">Location</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {obs.map((o) => (
                    <tr key={o.id} className="hover:bg-gray-50">
                      <td className="px-4 py-2.5">
                        <p className="font-medium text-gray-900">{o.product_name}</p>
                        {o.our_sku && <p className="text-xs text-gray-400 font-mono">{o.our_sku}</p>}
                      </td>
                      <td className="px-4 py-2.5 text-gray-700">{o.competitor_name}</td>
                      <td className="px-4 py-2.5 font-semibold text-gray-900">{o.currency} {o.price.toLocaleString()}</td>
                      <td className="px-4 py-2.5 text-xs text-gray-500">{o.channel.replace(/_/g, " ")}</td>
                      <td className="px-4 py-2.5 text-gray-400 text-xs">{o.observed_date}</td>
                      <td className="px-4 py-2.5 text-gray-400 text-xs">{o.location ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Log price tab */}
      {tab === "log" && (
        <div className="bg-white border rounded-lg p-5 shadow-sm space-y-3 max-w-2xl">
          <h2 className="text-sm font-semibold text-gray-700">Log Competitor Price Observation</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {([
              ["Product Name *", "product_name", "e.g. Mango Juice 500ml"],
              ["Our SKU", "our_sku", "e.g. MJ-500"],
              ["Competitor Name *", "competitor_name", "e.g. Fresh Corp"],
              ["Price *", "price", "e.g. 85.00"],
              ["Pack Size", "pack_size", "e.g. 500ml"],
              ["Source", "source", "field rep | web | nielsen"],
              ["Location", "location", "e.g. Naivas Karen"],
            ] as const).map(([label, key, ph]) => (
              <div key={key}>
                <label className="text-xs text-gray-500 block mb-1">{label}</label>
                <input type="text" placeholder={ph}
                  value={(logForm as unknown as Record<string, string>)[key]}
                  onChange={(e) => setLogForm((p) => ({ ...p, [key]: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
              </div>
            ))}
            <div>
              <label className="text-xs text-gray-500 block mb-1">Channel</label>
              <select value={logForm.channel} onChange={(e) => setLogForm((p) => ({ ...p, channel: e.target.value }))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none">
                {CHANNELS.map((c) => <option key={c} value={c}>{c.replace(/_/g, " ")}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Observed Date *</label>
              <input type="date" value={logForm.observed_date}
                onChange={(e) => setLogForm((p) => ({ ...p, observed_date: e.target.value }))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none" />
            </div>
          </div>
          <button onClick={logPrice} disabled={saving || !logForm.product_name || !logForm.competitor_name || !logForm.price}
            className="bg-blue-600 text-white text-sm px-4 py-2 rounded disabled:opacity-50">{saving ? "Logging…" : "Log Price"}</button>
        </div>
      )}

      {/* Generate tab */}
      {tab === "generate" && (
        <div className="max-w-2xl space-y-4">
          <div className="bg-white border rounded-lg p-5 shadow-sm space-y-3">
            <h2 className="text-sm font-semibold text-gray-700">Generate Price Recommendation</h2>
            <p className="text-xs text-gray-400">Compares your price against recent competitor data and margin rules to produce a recommendation.</p>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {([
                ["Product Name *", "product_name", "e.g. Mango Juice 500ml"],
                ["Our SKU", "our_sku", "e.g. MJ-500"],
                ["Current Price (KES) *", "current_price", "e.g. 95.00"],
                ["Cost Price / COGS (KES)", "cost_price", "e.g. 55.00"],
                ["Floor Margin %", "floor_margin_pct", "e.g. 20"],
                ["Target Margin %", "target_margin_pct", "e.g. 35"],
              ] as const).map(([label, key, ph]) => (
                <div key={key}>
                  <label className="text-xs text-gray-500 block mb-1">{label}</label>
                  <input type="text" placeholder={ph}
                    value={(genForm as unknown as Record<string, string>)[key]}
                    onChange={(e) => setGenForm((p) => ({ ...p, [key]: e.target.value }))}
                    className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
                </div>
              ))}
              <div>
                <label className="text-xs text-gray-500 block mb-1">Channel</label>
                <select value={genForm.channel} onChange={(e) => setGenForm((p) => ({ ...p, channel: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none">
                  {CHANNELS.map((c) => <option key={c} value={c}>{c.replace(/_/g, " ")}</option>)}
                </select>
              </div>
            </div>
            <button onClick={generate} disabled={saving || !genForm.product_name || !genForm.current_price}
              className="bg-blue-600 text-white text-sm px-4 py-2 rounded disabled:opacity-50">{saving ? "Generating…" : "Generate Recommendation"}</button>
          </div>

          {genResult && (
            <div className={`bg-white border rounded-lg p-4 shadow-sm space-y-2 ${genResult.trigger === "COMPETITOR_UNDERCUT" || genResult.trigger === "LOW_MARGIN" ? "border-amber-300" : "border-green-300"}`}>
              <p className="text-sm font-semibold text-gray-800">
                Result: {genResult.trigger === "HOLD" ? "Hold — No Change Needed" : `Action Required — ${genResult.trigger?.replace(/_/g, " ")}`}
              </p>
              <div className="flex gap-4 text-sm flex-wrap">
                <span>Current: KES {genResult.current_price?.toLocaleString()}</span>
                <span className="font-bold text-blue-700">Recommended: KES {genResult.recommended_price.toLocaleString()}</span>
                {genResult.avg_competitor_price && <span>Competitor avg: KES {genResult.avg_competitor_price.toLocaleString()}</span>}
                {genResult.confidence_score !== null && <span>Confidence: {genResult.confidence_score}%</span>}
              </div>
              <p className="text-xs text-gray-500">{genResult.rationale}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
