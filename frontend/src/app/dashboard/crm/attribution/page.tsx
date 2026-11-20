"use client";
// M36.S05.T001 journey attribution: source -> lead -> opportunity -> order -> repeat purchase.
import { useCallback, useEffect, useState } from "react";
import { crmApi, type AttributionReport } from "@/lib/crm_pipeline";

const iso = (d: Date) => d.toISOString().slice(0, 10);
const MODELS = [["first", "First touch"], ["last", "Last touch"], ["linear", "Linear (equal split)"]] as const;

export default function CRMAttributionPage() {
  const today = new Date();
  const [range, setRange] = useState({ from: iso(new Date(today.getFullYear(), today.getMonth() - 2, 1)), to: iso(today) });
  const [model, setModel] = useState("first");
  const [rep, setRep] = useState<AttributionReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try { setRep(await crmApi.getAttribution({ date_from: range.from, date_to: range.to, model })); }
    catch (e) {
      const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
      setError(typeof d === "string" ? d : "The report could not be loaded.");
    }
  }, [range, model]);
  useEffect(() => { load(); }, [load]);

  const money = (m: Record<string, string>) =>
    Object.keys(m).length ? Object.entries(m).map(([c, v]) => `${c} ${Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 })}`).join(" · ") : "—";
  const input = "text-sm border rounded-lg px-2 py-1.5";
  return (
    <div className="p-6 space-y-4">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Journey Attribution</h1>
        <p className="text-sm text-gray-500">Which sources bring leads, opportunities, paying customers and repeat orders.</p>
      </div>
      <div className="flex flex-wrap gap-2 items-end">
        <label className="text-xs text-gray-500">From<input type="date" value={range.from} onChange={(e) => setRange({ ...range, from: e.target.value })} className={`block ${input}`} /></label>
        <label className="text-xs text-gray-500">To<input type="date" value={range.to} onChange={(e) => setRange({ ...range, to: e.target.value })} className={`block ${input}`} /></label>
        <label className="text-xs text-gray-500">Model
          <select value={model} onChange={(e) => setModel(e.target.value)} className={`block ${input}`}>
            {MODELS.map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </label>
      </div>
      {error && <p role="alert" className="rounded-lg p-3 text-sm bg-red-50 border border-red-200 text-red-700">{error}</p>}
      {rep && (
        <>
          <p className="text-sm">
            {rep.totals.journeys} journeys · {rep.totals.customers_with_orders} paying customers · {rep.totals.orders} orders · {money(rep.totals.revenue)}
            <span className={`ml-2 text-xs ${rep.reconciled ? "text-emerald-700" : "text-red-700"}`}>{rep.reconciled ? "✓ reconciles with order totals" : "⚠ does not reconcile"}</span>
          </p>
          <div className="bg-white rounded-xl border overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="text-left text-xs text-gray-500"><th className="p-2">Source</th><th>Journeys</th><th>Leads</th><th>Opportunities</th><th>Won</th><th>Paying customers</th><th>Orders</th><th>Repeat</th><th className="pr-2">Revenue</th></tr></thead>
              <tbody>
                {rep.rows.length === 0 ? <tr><td colSpan={9} className="p-3 text-gray-400">No journeys in this period.</td></tr> : rep.rows.map((r) => (
                  <tr key={r.source} className="border-t">
                    <td className="p-2">{r.source}</td><td>{r.journeys}</td><td>{r.leads}</td><td>{r.opportunities}</td><td>{r.won}</td>
                    <td>{r.customers_with_orders}</td><td>{r.orders}</td><td>{r.repeat_customers}</td><td className="pr-2 whitespace-nowrap">{money(r.revenue)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <details className="text-xs text-gray-500"><summary>How it is counted</summary><ul className="list-disc ml-5 mt-1">{rep.assumptions.map((a) => <li key={a}>{a}</li>)}</ul></details>
        </>
      )}
    </div>
  );
}
