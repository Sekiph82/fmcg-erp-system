"use client";
import { useEffect, useState } from "react";

interface Dash { total_observations: number; observations_last_30d: number; oos_incidents_30d: number; avg_shelf_share_30d: number | null; market_share_estimates: number; }
interface ShelfSummary { category: string; avg_shelf_share_pct: number | null; observations: number; oos_rate_pct: number; competitor_promo_rate_pct: number; }
interface Obs { id: string; obs_ref: string; outlet_name: string; outlet_type: string; location: string | null; category: string; observation_date: string; our_brand: string | null; our_facings: number | null; total_facings: number | null; our_shelf_share_pct: number | null; our_promo_active: boolean; competitor_promo_active: boolean; our_oos_flag: boolean; notes: string | null; }
interface ShareEst { id: string; category: string; period_month: string; our_brand: string | null; our_share_pct: number | null; total_market_value_kes: number | null; competitor_shares: Record<string, number> | null; source: string | null; }

const OUTLET_TYPES = ["SUPERMARKET", "HYPERMARKET", "CONVENIENCE", "WHOLESALE", "KIOSK", "PHARMACY", "ONLINE", "OTHER"];

interface ObsForm { outlet_name: string; outlet_type: string; location: string; category: string; observation_date: string; observer_name: string; our_brand: string; our_facings: string; total_facings: string; our_promo_active: boolean; competitor_promo_active: boolean; our_oos_flag: boolean; competitor_promo_notes: string; notes: string; }
interface ShareForm { category: string; period_month: string; our_brand: string; our_share_pct: string; total_market_value_kes: string; source: string; notes: string; }

const EMPTY_OBS: ObsForm = { outlet_name: "", outlet_type: "SUPERMARKET", location: "", category: "", observation_date: new Date().toISOString().split("T")[0], observer_name: "", our_brand: "", our_facings: "", total_facings: "", our_promo_active: false, competitor_promo_active: false, our_oos_flag: false, competitor_promo_notes: "", notes: "" };
const EMPTY_SHARE: ShareForm = { category: "", period_month: new Date().toISOString().slice(0, 7), our_brand: "", our_share_pct: "", total_market_value_kes: "", source: "manual", notes: "" };

export default function MarketIntelligencePage() {
  const [dash, setDash] = useState<Dash | null>(null);
  const [shelf, setShelf] = useState<ShelfSummary[]>([]);
  const [obs, setObs] = useState<Obs[]>([]);
  const [shares, setShares] = useState<ShareEst[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"shelf" | "obs" | "share" | "log" | "logshare">("shelf");
  const [obsForm, setObsForm] = useState<ObsForm>(EMPTY_OBS);
  const [shareForm, setShareForm] = useState<ShareForm>(EMPTY_SHARE);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const [d, s, o, sh] = await Promise.all([
        fetch("/api/v1/market-intel/dashboard").then(r => r.json()),
        fetch("/api/v1/market-intel/shelf-share/summary").then(r => r.json()),
        fetch("/api/v1/market-intel/observations?limit=50").then(r => r.json()),
        fetch("/api/v1/market-intel/market-share?limit=30").then(r => r.json()),
      ]);
      setDash(d); setShelf(s); setObs(o); setShares(sh);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const logObs = async () => {
    setSaving(true); setError(null);
    try {
      const r = await fetch("/api/v1/market-intel/observations", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          outlet_name: obsForm.outlet_name, outlet_type: obsForm.outlet_type,
          location: obsForm.location || undefined, category: obsForm.category,
          observation_date: obsForm.observation_date,
          observer_name: obsForm.observer_name || undefined,
          our_brand: obsForm.our_brand || undefined,
          our_facings: obsForm.our_facings ? Number(obsForm.our_facings) : undefined,
          total_facings: obsForm.total_facings ? Number(obsForm.total_facings) : undefined,
          our_promo_active: obsForm.our_promo_active,
          competitor_promo_active: obsForm.competitor_promo_active,
          our_oos_flag: obsForm.our_oos_flag,
          competitor_promo_notes: obsForm.competitor_promo_notes || undefined,
          notes: obsForm.notes || undefined,
        }),
      });
      if (!r.ok) throw new Error(await r.text());
      setObsForm(EMPTY_OBS); setTab("obs"); load();
    } catch (e) { setError(String(e)); }
    setSaving(false);
  };

  const logShare = async () => {
    setSaving(true); setError(null);
    try {
      const r = await fetch("/api/v1/market-intel/market-share", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          category: shareForm.category, period_month: shareForm.period_month,
          our_brand: shareForm.our_brand || undefined,
          our_share_pct: shareForm.our_share_pct ? Number(shareForm.our_share_pct) : undefined,
          total_market_value_kes: shareForm.total_market_value_kes ? Number(shareForm.total_market_value_kes) : undefined,
          source: shareForm.source || undefined, notes: shareForm.notes || undefined,
        }),
      });
      if (!r.ok) throw new Error(await r.text());
      setShareForm(EMPTY_SHARE); setTab("share"); load();
    } catch (e) { setError(String(e)); }
    setSaving(false);
  };

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Market Intelligence</h1>
        <p className="text-sm text-gray-500 mt-0.5">Shelf share, market share, competitor activity from field observations</p>
      </div>

      {error && <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">{error}</div>}

      {/* KPI strip */}
      {dash && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
          {[
            { label: "Total Observations", value: dash.total_observations, color: "text-gray-800" },
            { label: "Last 30d", value: dash.observations_last_30d, color: "text-blue-600" },
            { label: "OOS Incidents (30d)", value: dash.oos_incidents_30d, color: "text-red-600" },
            { label: "Avg Shelf Share %", value: dash.avg_shelf_share_30d !== null ? `${dash.avg_shelf_share_30d}%` : "—", color: "text-green-600" },
            { label: "Share Estimates", value: dash.market_share_estimates, color: "text-gray-600" },
          ].map((k) => (
            <div key={k.label} className="bg-white border rounded-lg p-3 shadow-sm">
              <p className="text-xs text-gray-500">{k.label}</p>
              <p className={`text-xl font-bold mt-1 ${k.color}`}>{k.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b flex-wrap">
        {([["shelf","Shelf Share Analytics"],["obs","Field Observations"],["share","Market Share"],["log","Log Observation"],["logshare","Log Market Share"]] as const).map(([t,label]) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${tab===t?"border-blue-600 text-blue-600":"border-transparent text-gray-500 hover:text-gray-700"}`}>
            {label}
          </button>
        ))}
      </div>

      {/* Shelf share summary */}
      {tab === "shelf" && (
        <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b bg-gray-50">
            <h2 className="text-sm font-semibold text-gray-700">Shelf Share by Category (Last 90 days)</h2>
          </div>
          {shelf.length === 0 ? (
            <div className="p-6 text-sm text-gray-400 text-center">No shelf share data. Log observations using "Log Observation".</div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500">
                <tr>
                  <th className="text-left px-4 py-2">Category</th>
                  <th className="text-left px-4 py-2">Avg Shelf Share</th>
                  <th className="text-left px-4 py-2">Observations</th>
                  <th className="text-left px-4 py-2">OOS Rate</th>
                  <th className="text-left px-4 py-2">Comp. Promo Rate</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {shelf.map((s) => (
                  <tr key={s.category}>
                    <td className="px-4 py-2.5 font-medium text-gray-900">{s.category}</td>
                    <td className="px-4 py-2.5">
                      {s.avg_shelf_share_pct !== null ? (
                        <div className="flex items-center gap-2">
                          <span className={`font-bold ${s.avg_shelf_share_pct >= 30 ? "text-green-600" : s.avg_shelf_share_pct >= 15 ? "text-amber-500" : "text-red-500"}`}>
                            {s.avg_shelf_share_pct}%
                          </span>
                          <div className="w-20 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                            <div className={`h-full rounded-full ${s.avg_shelf_share_pct >= 30 ? "bg-green-500" : s.avg_shelf_share_pct >= 15 ? "bg-amber-400" : "bg-red-400"}`}
                              style={{ width: `${Math.min(s.avg_shelf_share_pct, 100)}%` }} />
                          </div>
                        </div>
                      ) : "—"}
                    </td>
                    <td className="px-4 py-2.5 text-gray-500">{s.observations}</td>
                    <td className={`px-4 py-2.5 text-sm ${s.oos_rate_pct > 20 ? "text-red-600 font-semibold" : "text-gray-500"}`}>{s.oos_rate_pct}%</td>
                    <td className="px-4 py-2.5 text-gray-500">{s.competitor_promo_rate_pct}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Observations list */}
      {tab === "obs" && (
        <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b bg-gray-50">
            <h2 className="text-sm font-semibold text-gray-700">Field Observations ({obs.length})</h2>
          </div>
          {obs.length === 0 ? (
            <div className="p-6 text-sm text-gray-400 text-center">No observations yet.</div>
          ) : (
            <div className="divide-y">
              {obs.map((o) => (
                <div key={o.id} className={`px-4 py-3 ${o.our_oos_flag ? "bg-red-50" : ""}`}>
                  <div className="flex items-center gap-3 flex-wrap">
                    {o.our_oos_flag && <span className="text-xs bg-red-500 text-white rounded px-2 py-0.5 font-bold">OOS</span>}
                    {o.competitor_promo_active && <span className="text-xs bg-amber-100 text-amber-700 rounded px-2 py-0.5">Comp. Promo</span>}
                    <span className="font-medium text-gray-900 text-sm">{o.outlet_name}</span>
                    <span className="text-xs text-gray-400">{o.outlet_type.replace(/_/g, " ")} · {o.location ?? ""}</span>
                    <span className="text-xs text-gray-400">{o.observation_date}</span>
                  </div>
                  <div className="flex gap-4 mt-1 text-xs text-gray-500 flex-wrap">
                    <span>Category: {o.category}</span>
                    {o.our_shelf_share_pct !== null && (
                      <span className={`font-semibold ${o.our_shelf_share_pct >= 30 ? "text-green-600" : o.our_shelf_share_pct >= 15 ? "text-amber-500" : "text-red-500"}`}>
                        Shelf share: {o.our_shelf_share_pct}% ({o.our_facings}/{o.total_facings} facings)
                      </span>
                    )}
                    {o.our_promo_active && <span className="text-blue-600">Our promo active</span>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Market share */}
      {tab === "share" && (
        <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b bg-gray-50">
            <h2 className="text-sm font-semibold text-gray-700">Market Share Estimates ({shares.length})</h2>
          </div>
          {shares.length === 0 ? (
            <div className="p-6 text-sm text-gray-400 text-center">No market share data. Use "Log Market Share".</div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500">
                <tr>
                  <th className="text-left px-4 py-2">Category</th>
                  <th className="text-left px-4 py-2">Period</th>
                  <th className="text-left px-4 py-2">Our Share</th>
                  <th className="text-left px-4 py-2">Market Value (KES)</th>
                  <th className="text-left px-4 py-2">Source</th>
                  <th className="text-left px-4 py-2">Competitors</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {shares.map((s) => (
                  <tr key={s.id}>
                    <td className="px-4 py-2.5 font-medium text-gray-900">{s.category}</td>
                    <td className="px-4 py-2.5 text-gray-500 font-mono text-xs">{s.period_month}</td>
                    <td className={`px-4 py-2.5 font-bold ${s.our_share_pct && s.our_share_pct >= 20 ? "text-green-600" : "text-amber-500"}`}>
                      {s.our_share_pct !== null ? `${s.our_share_pct}%` : "—"}
                    </td>
                    <td className="px-4 py-2.5 text-gray-500">{s.total_market_value_kes ? `${(s.total_market_value_kes / 1e6).toFixed(1)}M` : "—"}</td>
                    <td className="px-4 py-2.5 text-gray-400 text-xs">{s.source ?? "—"}</td>
                    <td className="px-4 py-2.5 text-xs text-gray-400">
                      {s.competitor_shares ? Object.entries(s.competitor_shares).map(([b, p]) => `${b}: ${p}%`).join(" · ") : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Log observation form */}
      {tab === "log" && (
        <div className="bg-white border rounded-lg p-5 shadow-sm space-y-4 max-w-2xl">
          <h2 className="text-sm font-semibold text-gray-700">Log Field Observation</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {([["Outlet Name *","outlet_name","e.g. Naivas Karen"],["Category *","category","e.g. Juices"],["Our Brand","our_brand","e.g. POVU"],["Observer","observer_name","e.g. Field Rep"],["Location","location","e.g. Nairobi, Karen"],["Our Facings","our_facings","e.g. 6"],["Total Facings","total_facings","e.g. 20"],["Notes","notes","Optional"]] as const).map(([label,key,ph]) => (
              <div key={key}>
                <label className="text-xs text-gray-500 block mb-1">{label}</label>
                <input type="text" placeholder={ph} value={(obsForm as unknown as Record<string,string>)[key]}
                  onChange={(e) => setObsForm((p) => ({ ...p, [key]: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
              </div>
            ))}
            <div>
              <label className="text-xs text-gray-500 block mb-1">Outlet Type</label>
              <select value={obsForm.outlet_type} onChange={(e) => setObsForm((p) => ({ ...p, outlet_type: e.target.value }))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none">
                {OUTLET_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Date *</label>
              <input type="date" value={obsForm.observation_date}
                onChange={(e) => setObsForm((p) => ({ ...p, observation_date: e.target.value }))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none" />
            </div>
          </div>
          <div className="flex flex-wrap gap-4">
            {([ ["our_promo_active","Our Promo Active"], ["competitor_promo_active","Competitor Promo Active"], ["our_oos_flag","We Are Out of Stock"] ] as const).map(([key,label]) => (
              <label key={key} className="flex items-center gap-2 cursor-pointer text-sm text-gray-700">
                <input type="checkbox" checked={(obsForm as unknown as Record<string,boolean>)[key]}
                  onChange={(e) => setObsForm((p) => ({ ...p, [key]: e.target.checked }))} className="h-4 w-4" />
                {label}
              </label>
            ))}
          </div>
          <button onClick={logObs} disabled={saving || !obsForm.outlet_name || !obsForm.category}
            className="bg-blue-600 text-white text-sm px-4 py-2 rounded disabled:opacity-50">{saving ? "Saving…" : "Log Observation"}</button>
        </div>
      )}

      {/* Log market share form */}
      {tab === "logshare" && (
        <div className="bg-white border rounded-lg p-5 shadow-sm space-y-3 max-w-lg">
          <h2 className="text-sm font-semibold text-gray-700">Log Market Share Estimate</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {([["Category *","category","e.g. Juices"],["Our Brand","our_brand","e.g. POVU"],["Our Share %","our_share_pct","e.g. 18.5"],["Market Value (KES)","total_market_value_kes","e.g. 50000000"],["Source","source","field | nielsen | IRI | manual"],["Notes","notes","Optional"]] as const).map(([label,key,ph]) => (
              <div key={key}>
                <label className="text-xs text-gray-500 block mb-1">{label}</label>
                <input type="text" placeholder={ph} value={(shareForm as unknown as Record<string,string>)[key]}
                  onChange={(e) => setShareForm((p) => ({ ...p, [key]: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
              </div>
            ))}
            <div>
              <label className="text-xs text-gray-500 block mb-1">Period Month *</label>
              <input type="month" value={shareForm.period_month}
                onChange={(e) => setShareForm((p) => ({ ...p, period_month: e.target.value }))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none" />
            </div>
          </div>
          <button onClick={logShare} disabled={saving || !shareForm.category}
            className="bg-blue-600 text-white text-sm px-4 py-2 rounded disabled:opacity-50">{saving ? "Saving…" : "Log Market Share"}</button>
        </div>
      )}
    </div>
  );
}
